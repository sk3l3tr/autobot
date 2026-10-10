import multiprocessing
from multiprocessing import Process

from path_provider import PathProvider
from robotization.robot_files import sanitize_robot_file_name


def normalize_robot_file_name(robot_name: str) -> str:
    return sanitize_robot_file_name(robot_name)


def validate_robot_name(robot_name: str) -> str:
    try:
        return normalize_robot_file_name(robot_name)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def run_robot_recorder(file_name: str, robot_dir: str, show_shortcut_popup: bool = True):
    from robotization.robot_recorder import main as robot_recorder_main

    import sys

    sys.argv = [
        "robot_recorder_main",
        "--file", file_name,
        "--directory", robot_dir,
    ]
    if show_shortcut_popup:
        sys.argv.append("--show-shortcut-popup")
    robot_recorder_main()


def start_robot_recorder_process(
    file_name: str,
    robot_dir: str | None = None,
    daemon: bool = True,
    show_shortcut_popup: bool = True,
) -> Process:
    safe_file_name = validate_robot_name(file_name)
    target_dir = robot_dir or PathProvider.robot_dir()

    process = multiprocessing.Process(
        target=run_robot_recorder,
        args=(safe_file_name, target_dir, show_shortcut_popup),
        daemon=daemon,
    )
    process.start()
    return process
