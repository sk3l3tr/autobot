import multiprocessing
multiprocessing.set_start_method('spawn', force=True)

import socket, json, os, time, threading, yaml, argparse, logging
from datetime import datetime
from loguru import logger
from path_provider import PathProvider

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

def send_action_via_socket(action_name: str, kwargs: dict, host: str, port: int):
    try:
        payload = {
            'action': action_name,
            'kwargs': kwargs or {}
        }
        message = json.dumps(payload).encode('utf-8')

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(message)

        logger.info(f"[SCHEDULER] Sent action '{action_name}' to {host}:{port}")
    except Exception:
        logger.exception(f"[SCHEDULER] Error sending action '{action_name}'")

def load_jobs(scheduler, yaml_path, socket_host, socket_port):
    yaml_path = os.path.abspath(yaml_path)
    with open(yaml_path) as f:
        jobs = yaml.safe_load(f) or []
    scheduler.remove_all_jobs()

    for job in jobs:
        # parámetros comunes
        job_id = job['id']
        trigger = job['trigger']
        trigger_args = job.get('trigger_args', {})

        # ─────────────────────────────────────────────────────────────────────
        # For datetime-local inputs (no seconds), compare at minute precision so
        # jobs created for "this minute" are not discarded as already past.
        if 'run_date' in trigger_args:
            run_date_str = trigger_args['run_date']

            # Convertir 'Z' a +00:00 para que fromisoformat lo acepte
            if run_date_str.endswith('Z'):
                run_date_str = run_date_str[:-1] + '+00:00'
            run_dt = datetime.fromisoformat(run_date_str)
            run_dt = run_dt.replace(microsecond=0)

            # comparar con ahora (considerando timezone) si no es tipo 'interval'
            if trigger != 'interval':
                now = datetime.now(run_dt.tzinfo) if run_dt.tzinfo else datetime.now()
                now_minute = now.replace(second=0, microsecond=0)
                if run_dt < now_minute:
                    logger.warning(f"[SCHEDULER] Skipping job {job_id}: run_date {run_dt} in the past")
                    continue
                else:
                    logger.info(f"[SCHEDULER] Scheduling job {job_id} at {run_dt}")

            # sustituir string por datetime en los args
            trigger_args['run_date'] = run_dt
        # ─────────────────────────────────────────────────────────────────────

        # if type interval, then adds the start_date param as run_date
        # With this, we can calculate the interval of execution from
        # provided original date (start_date) with no extra params
        if trigger == 'interval':
            value = trigger_args.pop('run_date', None)
            trigger_args['start_date'] = value

        # socket info xtraction
        action = job['action']
        kwargs = job.get('kwargs', {})
        host = job.get('socket_host', socket_host)
        port = job.get('socket_port', socket_port)

        # schedule
        scheduler.add_job(
            func=send_action_via_socket,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            kwargs={
                'action_name': action,
                'kwargs': kwargs,
                'host': host,
                'port': port
            },
            **trigger_args
        )

def watch_yaml(path, interval, scheduler, socket_host, socket_port):
    last_mtime = os.path.getmtime(path)
    while True:
        time.sleep(interval)
        mtime = os.path.getmtime(path)
        if mtime != last_mtime:
            last_mtime = mtime
            logger.info(f"[SCHEDULER] Detected change in {path}, reloading jobs")
            load_jobs(scheduler, path, socket_host, socket_port)

def job_listener(event):
    if event.exception:
        logger.exception(f"[SCHEDULER] Job {event.job_id} failed")
    else:
        logger.info(f"[SCHEDULER] Job {event.job_id} completed successfully")

def main():
    # ─── Configuración de Loguru ────────────────────────────────────────────────
    # Carpeta de logs junto al script
    _logs_dir = PathProvider.get_logs_dir()
    os.makedirs(_logs_dir, exist_ok=True)

    # Eliminamos el sink por defecto y añadimos uno a fichero con rotación y retención
    logger.remove()
    logger.add(
        os.path.join(_logs_dir, "sch3dvl3r.log"),
        rotation="1 MB",      # rota cada X MB
        retention=3,          # conserva los últimos X archivos
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}"
    )

    # (Opcional) Interceptar también los logs internos de APScheduler
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            lvl = record.levelname
            logger.log(lvl, record.getMessage())

    aps_logger = logging.getLogger("apscheduler")
    aps_logger.handlers = [InterceptHandler()]
    aps_logger.setLevel(logging.INFO)
    # ─────────────────────────────────────────────────────────────────────────────


    parser = argparse.ArgumentParser()

    # scheduler params
    parser.add_argument('--jobs-file', type=str, default="scheduler/jobs.yaml")
    parser.add_argument('--digest-file-frecuency', type=int, default=5)
    parser.add_argument('--misfire-grace-time', type=int, default=5)

    # socket params
    parser.add_argument('--socket-host', type=str, default='127.0.0.1')
    parser.add_argument('--socket-port', type=int, default=65432)

    args = parser.parse_args()

    scheduler = BackgroundScheduler(
        executors={'default': ThreadPoolExecutor(10)},
        job_defaults={'misfire_grace_time': args.misfire_grace_time, 'coalesce': False}
    )

    # listen to events result
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    load_jobs(
        scheduler,
        args.jobs_file,
        socket_host=args.socket_host,
        socket_port=args.socket_port
    )

    scheduler.start()
    threading.Thread(
        target=watch_yaml,
        args=(
            args.jobs_file,
            args.digest_file_frecuency,
            scheduler,
            args.socket_host,
            args.socket_port,
        ),
        daemon=True).start()
    
    logger.info("[SCHEDULER] Started background scheduler. Waiting for jobs...")
    
    # Use a shutdown event instead of infinite loop
    shutdown_event = threading.Event()
    
    def signal_handler(signum, frame):
        logger.info(f"[SCHEDULER] Received signal {signum}, shutting down...")
        shutdown_event.set()
    
    # Register signal handlers
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGBREAK'):  # Windows
        signal.signal(signal.SIGBREAK, signal_handler)
    
    try:
        # Wait for shutdown signal instead of infinite loop
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=1.0)
    except (KeyboardInterrupt, SystemExit) as e:
        logger.warning(f"[SCHEDULER] Shutdown requested: {e}")
    finally:
        shutdown_event.set()
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Scheduler stopped")

if __name__ == "__main__" and multiprocessing.current_process().name == "MainProcess":
    multiprocessing.freeze_support()
    main()
