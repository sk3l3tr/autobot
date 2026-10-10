import multiprocessing
multiprocessing.set_start_method('spawn', force=True)

import sys, socket, time, atexit

from autobot_runtime import initialize_user_environment
from process_no_console import _patch_subprocess_no_console
from process_bundled_binary import prepare_external_binaries
from robotization.robot_manager import RobotManager
from process_killer import kill_residual_children
from robotization.robot_queue import RobotQueue
from ssca_agent.ssca_client import SSCAClient
from process_manager import ProcessManager
from config import Configuration

_patch_subprocess_no_console()

def print_header():
    ascii_art = r"""
 █████  ██    ██ ████████  ██████  ██████   ██████  ████████ 
██   ██ ██    ██    ██    ██  ████ ██   ██ ██  ████    ██    
███████ ██    ██    ██    ██ ██ ██ ██████  ██ ██ ██    ██    
██   ██ ██    ██    ██    ████  ██ ██   ██ ████  ██    ██    
██   ██  ██████     ██     ██████  ██████   ██████     ██    
                                                                    
    .--.      .--.                          .--.      .--.  
:::::::.\::::::::.\::::::::[v3.1.2]::.\::::::::.\::::::::.\:
--'      `--'      `--'                `--'      `--'      `
    """
    print(ascii_art)

def wait_for_ssca(host, port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False

def main():
    print_header()
    initialize_user_environment()
    prepare_external_binaries()
    CONFIG = Configuration.from_yaml()
    HOST = CONFIG.SSCA_HOST
    PORT = CONFIG.SSCA_PORT

    process_manager = ProcessManager(CONFIG)
    robot_manager = RobotManager()
    robot_queue = RobotQueue(robot_manager=robot_manager)

    @atexit.register
    def _cleanup():
        try:
            process_manager.terminate_processes()
        except Exception:
            pass
        kill_residual_children()

    process_manager.start_processes()

    try:
        print("[MAIN] Waiting for SSCA Server …")
        if not wait_for_ssca(HOST, PORT):
            print("[MAIN] Error: Failed to connect to SSCA Server after 10s. Aborting.")
            process_manager.terminate_processes()
            sys.exit(1)
        print("[MAIN] SSCA Server available, starting client...")

        actions = {
            'open_robot_recorder': process_manager.start_robot_recorder_gui,
            'kill':  process_manager.terminate_processes,
            'run_robot': robot_queue.enqueue,
            'stop_robot': robot_queue.stop_all,
        }

        client = SSCAClient(host=HOST, port=PORT, actions=actions)
        print("[MAIN] Trying to connect to the SSCA Server…")
        client.connect()

        process_manager.rise_webhook()
        process_manager.rise_scheduler()

        while process_manager.processes_alive():
            time.sleep(1)

    except (SystemExit, KeyboardInterrupt, Exception):
        print("[MAIN] Execution interrupted. Ending processes...")
        process_manager.terminate_processes()
        kill_residual_children()

if __name__ == "__main__" and multiprocessing.current_process().name == "MainProcess":
    multiprocessing.freeze_support()
    main()
