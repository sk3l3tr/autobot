import json
from dataclasses import dataclass, field


class RecorderValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RecorderField:
    name: str
    label: str
    kind: str = "number"
    options: tuple[str, ...] = field(default_factory=tuple)


class RecorderActionEditor:
    action_name: str = ""
    fields: tuple[RecorderField, ...] = ()
    supports_nested_steps: bool = False
    allows_unknown_fields: bool = False

    def normalize(self, payload: dict) -> dict:
        raise NotImplementedError

    def format_label(self, payload: dict) -> str:
        raise NotImplementedError

    def export_form_values(self, payload: dict) -> dict[str, str]:
        normalized = self.normalize(payload)
        exported: dict[str, str] = {}
        for field in self.fields:
            value = normalized.get(field.name, "")
            if isinstance(value, float):
                exported[field.name] = _format_number(value)
            elif value is None:
                exported[field.name] = ""
            else:
                exported[field.name] = str(value)
        return exported

    @staticmethod
    def _require_float(payload: dict, key: str, *, positive: bool = False, allow_zero: bool = True) -> float:
        value = payload.get(key)
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise RecorderValidationError(f"Field '{key}' must be a number.") from exc

        if positive and (number < 0 or (not allow_zero and number == 0)):
            comparator = "greater than or equal to 0" if allow_zero else "greater than 0"
            raise RecorderValidationError(f"Field '{key}' must be {comparator}.")

        return number

    @staticmethod
    def _require_int(payload: dict, key: str, *, minimum: int = 0, allow_zero: bool = True) -> int:
        value = payload.get(key)
        try:
            number = int(str(value))
        except (TypeError, ValueError) as exc:
            raise RecorderValidationError(f"Field '{key}' must be an integer.") from exc

        if str(number) != str(value).strip():
            raise RecorderValidationError(f"Field '{key}' must be an integer.")

        if number < minimum or (not allow_zero and number == 0):
            comparator = f"greater than or equal to {minimum}"
            if not allow_zero and minimum == 0:
                comparator = "greater than 0"
            raise RecorderValidationError(f"Field '{key}' must be {comparator}.")

        return number

    @staticmethod
    def _normalize_steps(payload: dict, *, required: bool = False) -> list[dict]:
        steps = payload.get("steps", [])
        if steps is None:
            steps = []

        if not isinstance(steps, list):
            raise RecorderValidationError("Field 'steps' must be a list of actions.")

        normalized_steps = [normalize_action(step) for step in steps]
        if required and not normalized_steps:
            raise RecorderValidationError("Field 'steps' must include at least one action.")

        return normalized_steps


class ClickActionEditor(RecorderActionEditor):
    action_name = "click"
    fields = (
        RecorderField("x", "X"),
        RecorderField("y", "Y"),
        RecorderField("after", "After (s)"),
    )

    def normalize(self, payload: dict) -> dict:
        x = self._require_float(payload, "x")
        y = self._require_float(payload, "y")
        after = self._require_float(payload, "after", positive=True)
        return {"action": self.action_name, "x": x, "y": y, "after": after}

    def format_label(self, payload: dict) -> str:
        normalized = self.normalize(payload)
        x = _format_number(normalized["x"])
        y = _format_number(normalized["y"])
        after = _format_number(normalized["after"])
        return f"Click | x={x}, y={y} | after={after}s"


class DelayActionEditor(RecorderActionEditor):
    action_name = "delay"
    fields = (RecorderField("seconds", "Seconds"),)

    def normalize(self, payload: dict) -> dict:
        seconds = self._require_float(payload, "seconds", positive=True, allow_zero=False)
        return {"action": self.action_name, "seconds": seconds}

    def format_label(self, payload: dict) -> str:
        normalized = self.normalize(payload)
        seconds = _format_number(normalized["seconds"])
        return f"Delay | {seconds}s"


class LoopActionEditor(RecorderActionEditor):
    action_name = "loop"
    supports_nested_steps = True
    fields = (
        RecorderField("mode", "Mode", kind="select", options=("count", "until_stopped")),
        RecorderField("times", "Times", kind="integer"),
    )

    def normalize(self, payload: dict) -> dict:
        mode = str(payload.get("mode", "count")).strip() or "count"
        if mode not in {"count", "until_stopped"}:
            raise RecorderValidationError("Field 'mode' must be 'count' or 'until_stopped'.")

        normalized = {
            "action": self.action_name,
            "mode": mode,
            "steps": self._normalize_steps(payload, required=True),
        }

        if mode == "count":
            normalized["times"] = self._require_int(payload, "times", minimum=1, allow_zero=False)

        return normalized

    def format_label(self, payload: dict) -> str:
        normalized = self.normalize(payload)
        steps_count = len(normalized["steps"])
        if normalized["mode"] == "count":
            return f"Loop | x{normalized['times']} | {steps_count} steps"
        return f"Loop | until stopped | {steps_count} steps"


class GenericActionEditor(RecorderActionEditor):
    allows_unknown_fields = True
    fields = (
        RecorderField("action", "Action", kind="text"),
        RecorderField("payload_json", "Payload (JSON)", kind="json"),
    )

    def __init__(self, action_name: str):
        self.action_name = action_name
        self.supports_nested_steps = False

    def normalize(self, payload: dict) -> dict:
        action_name = str(payload.get("action", "")).strip()
        if not action_name:
            raise RecorderValidationError("Action payload must include 'action'.")

        normalized = {"action": action_name}
        for key, value in payload.items():
            if key == "action":
                continue
            if key == "steps":
                normalized["steps"] = self._normalize_steps(payload)
                self.supports_nested_steps = True
                continue
            normalized[key] = value
        if "steps" not in normalized:
            self.supports_nested_steps = False
        return normalized

    def format_label(self, payload: dict) -> str:
        normalized = self.normalize(payload)
        extras: list[str] = []
        for key, value in normalized.items():
            if key == "action":
                continue
            if key == "steps":
                extras.append(f"steps={len(value)}")
                continue
            extras.append(f"{key}={_compact_json(value)}")

        action_label = normalized["action"].replace("_", " ").title()
        return f"{action_label} | " + (", ".join(extras) if extras else "custom")

    def export_form_values(self, payload: dict) -> dict[str, str]:
        normalized = self.normalize(payload)
        extra_payload = {
            key: value
            for key, value in normalized.items()
            if key not in {"action", "steps"}
        }
        return {
            "action": normalized["action"],
            "payload_json": json.dumps(extra_payload, indent=2, ensure_ascii=True),
        }


_EDITORS: dict[str, RecorderActionEditor] = {
    "click": ClickActionEditor(),
    "delay": DelayActionEditor(),
    "loop": LoopActionEditor(),
}


def get_action_editor(action_name: str) -> RecorderActionEditor:
    editor = _EDITORS.get(action_name)
    if editor is not None:
        return editor
    if not action_name:
        raise RecorderValidationError("Action payload must include 'action'.")
    return GenericActionEditor(action_name)


def normalize_action(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise RecorderValidationError("Action payload must be a dictionary.")

    action_name = payload.get("action")
    if not action_name:
        raise RecorderValidationError("Action payload must include 'action'.")

    return get_action_editor(action_name).normalize(payload)


def format_action_label(payload: dict) -> str:
    action_name = payload.get("action") if isinstance(payload, dict) else None
    return get_action_editor(action_name).format_label(payload)


def list_supported_action_types() -> list[str]:
    return sorted(_EDITORS)


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)


def _compact_json(value) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(", ", ": "))
