import os
import re
from pathlib import Path


class RobotFileValidationError(ValueError):
    pass


class RobotFileConflictError(FileExistsError):
    pass


def normalize_robot_base_name(robot_name: str) -> str:
    return remove_yaml_extension(sanitize_robot_file_name(robot_name))


def sanitize_robot_file_name(robot_name: str) -> str:
    normalized_name = (robot_name or "").strip()
    if not normalized_name:
        raise RobotFileValidationError("Robot name cannot be empty.")

    if any(sep in normalized_name for sep in ("/", "\\")) or ".." in normalized_name:
        raise RobotFileValidationError("Robot name must be a simple file name without directories.")

    had_extension = normalized_name.endswith(".yaml")
    base_name = remove_yaml_extension(normalized_name)
    sanitized_base_name = re.sub(r"[^\w-]+", "_", base_name, flags=re.ASCII)

    if not sanitized_base_name:
        raise RobotFileValidationError("Robot name cannot be empty.")

    return f"{sanitized_base_name}.yaml" if had_extension or True else sanitized_base_name


def remove_yaml_extension(robot_name: str) -> str:
    return robot_name[:-5] if robot_name.endswith(".yaml") else robot_name


def build_robot_file_path(base_dir: str | Path, robot_name: str) -> Path:
    root = Path(base_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_robot_file_name(robot_name)
    target = (root / safe_name).resolve()

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RobotFileValidationError("Invalid robot path.") from exc

    return target


def rename_robot_file(base_dir: str | Path, old_name: str, new_name: str) -> Path:
    old_path = build_robot_file_path(base_dir, old_name)
    new_path = build_robot_file_path(base_dir, new_name)

    if not old_path.exists():
        raise FileNotFoundError("The old robot file path does not exist.")

    if old_path == new_path:
        return old_path

    if new_path.exists():
        raise RobotFileConflictError("The new robot name exists. You must use a different one.")

    os.rename(old_path, new_path)
    return new_path
