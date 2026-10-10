import os, sys, time, signal, subprocess
import platform

try:
    import psutil
except Exception:
    psutil = None

def terminate_pid(pid: int, gentle_timeout=2.0):
    if pid <= 0:
        return
    if psutil:
        try:
            p = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return
        # Primero a los hijos (recursivo)
        children = p.children(recursive=True)
        for c in children:
            try: c.terminate()
            except Exception: pass
        try: p.terminate()
        except Exception: pass
        # Espera suave
        gone, alive = psutil.wait_procs([p, *children], timeout=gentle_timeout)
        # Fuerza lo que quede
        for a in alive:
            try: a.kill()
            except Exception: pass
    else:
        # Fallback sin psutil
        if os.name == "posix":
            try:
                # Intenta matar el grupo si existe
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(gentle_timeout)
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                return
            except Exception:
                pass
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(gentle_timeout)
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
        else:
            # Windows - improved termination
            try:
                # First try gentle termination with CTRL_BREAK_EVENT
                try:
                    os.kill(pid, signal.CTRL_BREAK_EVENT)
                    time.sleep(gentle_timeout)
                except (OSError, AttributeError):
                    pass
                
                # Then force kill entire process tree
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception:
                pass

def _kill_existing_webhook_processes():
    """Best-effort cleanup of lingering webhook agent processes from previous runs."""
    try:
        if sys.platform == "win32" or platform.system() == "Windows":
            # Kill by image name on Windows (ignores if not running)
            subprocess.run(
                ["taskkill", "/IM", "webhook_agent-win.exe", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            # Try to kill by name on Unix-like systems
            subprocess.run(
                ["pkill", "-f", "webhook_agent"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    except Exception:
        # Non-fatal if cleanup fails
        pass

# ---------- kill sin abrir consolas (usa psutil si existe) ----------
def kill_residual_children():
    names = {"webhook_agent.exe", "webhook_agent", "Autobot.exe"}

    try:
        import psutil
        # 1) Terminar amable
        victims = []
        for p in psutil.process_iter(["pid","name","exe"]):
            n = (p.info.get("name") or "")
            e = (p.info.get("exe") or "")
            if any(n == x or e.endswith("\\"+x) or e.endswith("/"+x) for x in names):
                victims.append(p)
        for p in victims:
            try: p.terminate()
            except Exception: pass
        _, alive = psutil.wait_procs(victims, timeout=2)
        # 2) Forzar kill a lo que quede
        for p in alive:
            try: p.kill()
            except Exception: pass
        return
    except Exception:
        pass

    # Fallback SIN taskkill: WinAPI
    if os.name == "nt":
        try:
            import ctypes, ctypes.wintypes as wt
            PROCESS_TERMINATE = 0x0001
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            OpenProcess = k32.OpenProcess
            TerminateProcess = k32.TerminateProcess
            CloseHandle = k32.CloseHandle

            # Enumerar procesos con psapi
            psapi = ctypes.WinDLL("Psapi.dll", use_last_error=True)
            EnumProcesses = psapi.EnumProcesses

            arr_size = 4096
            while True:
                buf = (wt.DWORD * arr_size)()
                needed = wt.DWORD(0)
                if not EnumProcesses(buf, ctypes.sizeof(buf), ctypes.byref(needed)):
                    break
                count = needed.value // ctypes.sizeof(wt.DWORD())
                if count < arr_size:
                    pids = buf[:count]
                    break
                arr_size *= 2

            # Función para obtener nombre de imagen
            QueryFullProcessImageNameW = k32.QueryFullProcessImageNameW
            GetProcessImageFileNameW = psapi.GetProcessImageFileNameW  # opcional

            for pid in pids:
                if pid in (0, os.getpid()):
                    continue
                h = OpenProcess(0x0410, False, pid)  # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
                if not h:
                    continue
                try:
                    # Intentar nombre completo
                    buf = ctypes.create_unicode_buffer(32768)
                    size = wt.DWORD(len(buf))
                    exe = ""
                    if QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                        exe = buf.value
                    # Chequear contra tu lista
                    if any(exe.endswith("\\"+x) or exe.endswith("/"+x) for x in names):
                        hkill = OpenProcess(PROCESS_TERMINATE, False, pid)
                        if hkill:
                            TerminateProcess(hkill, 1)
                            CloseHandle(hkill)
                finally:
                    CloseHandle(h)
        except Exception:
            pass
