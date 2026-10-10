from dataclasses import dataclass
import re
from typing import Callable


def sanitize_robot_name_input(value: str) -> str:
    text = (value or "").strip()
    if text.lower().endswith(".yaml"):
        text = text[:-5]
    return re.sub(r"[^\w-]+", "_", text, flags=re.ASCII)


def sanitize_decimal_input(value: str, *, allow_negative: bool = False) -> str:
    text = (value or "").strip()
    result: list[str] = []
    seen_dot = False

    for index, char in enumerate(text):
        if char.isdigit():
            result.append(char)
            continue

        if char == "." and not seen_dot:
            result.append(char)
            seen_dot = True
            continue

        if char == "-" and allow_negative and index == 0 and "-" not in result:
            result.append(char)

    return "".join(result)


@dataclass(frozen=True)
class InputSanitizer:
    name: str
    sanitize: Callable[[str], str]


ROBOT_NAME_SANITIZER = InputSanitizer("robot_name", sanitize_robot_name_input)
DECIMAL_SANITIZER = InputSanitizer("decimal", sanitize_decimal_input)


def bind_sanitized_variable(variable, sanitizer: InputSanitizer) -> None:
    state = {"updating": False}

    def _apply(*_args):
        if state["updating"]:
            return

        current = variable.get()
        sanitized = sanitizer.sanitize(current)
        if current == sanitized:
            return

        state["updating"] = True
        try:
            variable.set(sanitized)
        finally:
            state["updating"] = False

    variable.trace_add("write", _apply)
    _apply()
