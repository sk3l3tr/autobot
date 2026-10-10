import atexit
import multiprocessing
import signal
from typing import List, Tuple
multiprocessing.set_start_method('spawn', force=True)

import os, sys
import subprocess, platform
from multiprocessing import Process
from threading import Thread

from path_provider import PathProvider
from robotization.robot_editor import start_robot_recorder_process

from ssca_agent.main import main as ssca_main
from backend.main    import main as backend_main
from scheduler.main  import main as scheduler_main
from kiosk           import main as kiosk_main

from process_killer import terminate_pid, _kill_existing_webhook_processes

def run_ssca(host: str, port: int):
    sys.argv = [
        "ssca_agent",
        "--host", host,
        "--port", str(port)
    ]
    ssca_main()


def run_backend(
    server_port: int,
    socket_host: str,
    socket_port: int,
    static_folder: str,
    robot_dir: str,
    jobs_file: str,
    cors_origin: str,
    debug_enabled: bool,
):
    sys.argv = [
        "backend_main",
        "--port",             str(server_port),
        "--socket-host",      socket_host,
        "--socket-port",      str(socket_port),
        "--static-folder",    static_folder,
        "--robots-dir-path",  robot_dir,
        "--jobs-file-path",   jobs_file,
        "--cors-origin",      cors_origin,
    ]
    if debug_enabled:
        sys.argv.append("--debug")

    backend_main()


def run_kiosk():
    kiosk_main()


def run_scheduler(
    jobs_file: str,
    digest_frequency: int,
    misfire_grace_time: int,
    socket_host: str,
    socket_port: int
):
    sys.argv = [
        "scheduler_main",
        "--jobs-file",           jobs_file,
        "--digest-file-frecuency", str(digest_frequency),
        "--misfire-grace-time",  str(misfire_grace_time),
        "--socket-host",         socket_host,
        "--socket-port",         str(socket_port)
    ]
    scheduler_main()


def run_webhook(
    webhook_api_key: str,
    webhook_token: str,
    socket_host: str,
    socket_port: int
):
    import subprocess
    webhook_path = PathProvider.get_webhook_binary()
    args = [
        webhook_path,
        "--api-key", webhook_api_key,
        "--token-id", webhook_token,
        "--socket-host", socket_host,
        "--socket-port", str(socket_port)
    ]
    # On Windows, launch without opening a new console window
    if sys.platform == "win32" or platform.system() == "Windows":
        try:
            CREATE_NO_WINDOW = 0x08000000
            # Hide window and detach from console
            p = subprocess.Popen(args, creationflags=CREATE_NO_WINDOW)
            # Keep this process alive so ProcessManager can track and terminate tree
            p.wait()
        except Exception as e:
            print(f"[PM] Failed to start webhook (hidden): {e}")
    else:
        # Non-Windows: replace process image so PID tracking remains consistent
        os.execv(webhook_path, args)


class ProcessManager:
    def __init__(
            self,
            config,
            kiosk_enabled: bool = True,
            cors_enabled: bool = False,
        ):

        self.processes : List[Process]  = []
        self.pids: List[Tuple[str, int | None]] = []  # (name, pid)
        
        self.config = config
        self.kiosk_enabled = kiosk_enabled
        self.cors_enabled = cors_enabled

        # Prevent multiple webhook instances across app lifecycle
        self._webhook_started = False
        self._recorder_shortcut_popup_shown = False

    # --- Hooks globales de apagado ---
    def _register_shutdown_hooks(self):
        def _graceful(*_):
            try:
                self.terminate_processes()
            finally:
                # Evita que Python se quede esperando hilos
                os._exit(0)
        for sig in (getattr(signal, 'SIGINT', None),
                    getattr(signal, 'SIGTERM', None),
                    getattr(signal, 'SIGBREAK', None)):  # Windows
            if sig is not None:
                signal.signal(sig, _graceful)
        atexit.register(self.terminate_processes)
    
    # --- Arranques (sin cambios funcionales, solo tracking de PIDs) ---
    def _track(self, name: str, p: Process):
        self.processes.append(p)
        self.pids.append((name, p.pid))
        print(f"[PM] {name} started (PID: {p.pid})")

    def start_processes(self):
        self._register_shutdown_hooks()  # CRITICAL: Actually register the hooks
        self.rise_backend()
        if self.kiosk_enabled == True:
            self.rise_kiosk()
        self.rise_ssca()

    def rise_ssca(self):
        p_ssca = Process(
            target=run_ssca,
            args=(self.config.SSCA_HOST, self.config.SSCA_PORT),
            daemon=True
        )
        p_ssca.start()
        self._track("SSCA", p_ssca)

    def rise_backend(self):
        _cors_allowed = "http://127.0.0.1:5555/*" if self.cors_enabled else "*"
    
        p_backend = Process(
            target=run_backend,
            args=(
                self.config.SERVER_PORT,
                self.config.SSCA_HOST,
                self.config.SSCA_PORT,
                PathProvider.www_static_dir(),
                PathProvider.robot_dir(),
                PathProvider.get_jobs_file(),
                _cors_allowed,
                self.config.SERVER_DEBUG_ENABLED,
            ),
            daemon=True
        )
        p_backend.start()
        self._track("Backend", p_backend)

    def rise_kiosk(self):
        p_kiosk = Process(
            target=run_kiosk,
            daemon=True
        )
        p_kiosk.start()
        self._track("Kiosk", p_kiosk)

    def rise_scheduler(self):
        p_scheduler = Process(
        target=run_scheduler,
        args=(
            PathProvider.get_jobs_file(),
            self.config.DIGEST_FILE_FREQUENCY,
            self.config.MISFIRE_GRACE_TIME,
            self.config.SSCA_HOST,
            self.config.SSCA_PORT
        ),
        daemon=True
        )
        p_scheduler.start()
        self._track('Scheduler', p_scheduler)

    def rise_webhook(self):
        if getattr(self.config, "WEBHOOK_ACTIVE", False):
            # Guard: avoid spawning multiple webhook agents
            if self._webhook_started:
                print("[PM] Webhook already started. Skipping.")
                return
            # If a process with same role is alive, skip
            for (name, pid), p in zip(list(self.pids), list(self.processes)):
                if name == "Webhook(bin)" and p.is_alive():
                    print("[PM] Webhook process already alive. Skipping.")
                    self._webhook_started = True
                    return
            # Proactively cleanup any lingering instances from previous runs
            _kill_existing_webhook_processes()
            p_webhook = Process(
                target=run_webhook,
                args=(
                    self.config.WEBHOOK_API_KEY,
                    self.config.WEBHOOK_TOKEN,
                    self.config.SSCA_HOST,
                    self.config.SSCA_PORT
                ),
                daemon=True
            )
            p_webhook.start()
            self._track("Webhook(bin)", p_webhook)
            self._webhook_started = True

 # --- Cierre fuerte y recursivo ---
    def terminate_processes(self):
        # 1) Señal suave a los Process
        for p in list(self.processes):
            try: p.terminate()
            except Exception: pass

        # 2) Espera breve
        for p in list(self.processes):
            try: p.join(timeout=0.5)
            except Exception: pass

        # 3) Mata en árbol por PID (incluye nietos, hilos nativos, bins externos)
        #    Hacerlo después del terminate() evita cerrar cosas a mitad si hacen shutdown limpio.
        for name, pid in list(self.pids):
            if pid:
                try:
                    terminate_pid(pid, gentle_timeout=1.5)
                except Exception:
                    pass

        # 4) Kill final si algún multiprocessing sigue vivo
        for p in list(self.processes):
            try:
                if p.is_alive() and p.pid:
                    try: p.kill()   # Python >=3.7
                    except Exception:
                        # Fallback: matar por PID
                        terminate_pid(p.pid, gentle_timeout=0.2)
            except Exception:
                pass

        # 5) Join definitivo (no bloqueante)
        for p in list(self.processes):
            try: p.join(timeout=0.1)
            except Exception: pass

        self.processes.clear()
        self.pids.clear()
        self._webhook_started = False
        print("[PM] All processes terminated.")

    def processes_alive(self) -> bool:
        return any(p.is_alive() for p in self.processes)

    def start_robot_recorder_gui(self, file_name: str):
        should_show_shortcut_popup = not self._recorder_shortcut_popup_shown
        p_recorder = start_robot_recorder_process(
            file_name=file_name,
            robot_dir=PathProvider.robot_dir(),
            daemon=True,
            show_shortcut_popup=should_show_shortcut_popup,
        )
        self._recorder_shortcut_popup_shown = True
        self._track("RobotRecorder", p_recorder)

        # Cuando termine, lo limpiamos de la lista
        Thread(target=self._reap_process, args=(p_recorder,), daemon=True).start()

    def _reap_process(self, process: Process):
        process.join()
        try:
            print("[PM] Killing GUI process...")
            self.processes.remove(process)
            self.pids[:] = [(n, pid) for (n, pid) in self.pids if pid != process.pid]
        except ValueError:
            pass
