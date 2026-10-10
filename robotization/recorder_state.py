from robotization.recorder_action_editors import RecorderValidationError, normalize_action


class RecorderState:
    def __init__(self, actions: list[dict] | None = None):
        self._actions = list(actions or [])

    @classmethod
    def load_actions(cls, actions: list[dict] | None) -> "RecorderState":
        if actions is None:
            actions = []

        if not isinstance(actions, list):
            raise RecorderValidationError("Robot file content must be a list of actions.")

        normalized = [normalize_action(action) for action in actions]
        return cls(normalized)

    def list_actions(self) -> list[dict]:
        return [dict(action) for action in self._actions]

    def add_action(self, action: dict) -> int:
        normalized = normalize_action(action)
        self._actions.append(normalized)
        return len(self._actions) - 1

    def update_action(self, index: int, action: dict) -> dict:
        self._validate_index(index)
        normalized = normalize_action(action)
        self._actions[index] = normalized
        return dict(normalized)

    def delete_action(self, index: int) -> dict:
        self._validate_index(index)
        return self._actions.pop(index)

    def move_action(self, index: int, direction: str) -> int:
        self._validate_index(index)

        target_index = index
        if direction == "up" and index > 0:
            target_index = index - 1
        elif direction == "down" and index < len(self._actions) - 1:
            target_index = index + 1
        elif direction not in {"up", "down"}:
            raise RecorderValidationError(f"Unsupported move direction '{direction}'.")

        if target_index == index:
            return index

        self._actions[index], self._actions[target_index] = (
            self._actions[target_index],
            self._actions[index],
        )
        return target_index

    def _validate_index(self, index: int) -> None:
        if index < 0 or index >= len(self._actions):
            raise RecorderValidationError(f"Action index '{index}' is out of range.")
