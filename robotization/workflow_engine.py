from threading import Event

from robotization.robot_actions import registry


class WorkflowEngine:
    def __init__(self, steps: list, controller, stop_event: Event | None = None):
        self.steps = list(steps or [])
        self.controller = controller
        self.stop_event = stop_event or Event()

    def run(self) -> bool:
        success = self._run_steps(self.steps)
        if self.stop_event.is_set():
            print("[ROBOT] Automation stopped manually.\n")
            return False
        if success:
            print("[ROBOT] Automation finished!🏁\n")
        return success

    def _run_steps(self, steps: list[dict]) -> bool:
        for step in steps:
            if self.stop_event.is_set():
                return False
            if not self._execute_step(step):
                return False
        return True

    def _execute_step(self, step: dict) -> bool:
        action = (step or {}).get("action")
        if action == "loop":
            return self._execute_loop(step)

        cmd_cls = registry.get(action)
        if not cmd_cls:
            print(f"[ROBOT] Workflow error: Unknown action: {action}")
            return False

        params = {key: value for key, value in step.items() if key != "action"}
        cmd = cmd_cls(self.controller, **params)
        cmd.execute()
        return not self.stop_event.is_set()

    def _execute_loop(self, step: dict) -> bool:
        steps = step.get("steps") or []
        mode = step.get("mode", "count")

        if mode == "until_stopped":
            print("[ROBOT] Loop started | mode=until_stopped")
            iteration = 1
            while not self.stop_event.is_set():
                print(f"[ROBOT] Loop iteration {iteration}")
                if not self._run_steps(steps):
                    return False
                iteration += 1
            return False

        try:
            times = int(step.get("times", 0))
        except (TypeError, ValueError):
            print(f"[ROBOT] Workflow error: Invalid loop times: {step.get('times')}")
            return False

        if times <= 0:
            print(f"[ROBOT] Workflow error: Invalid loop times: {times}")
            return False

        print(f"[ROBOT] Loop started | mode=count | times={times}")
        for iteration in range(1, times + 1):
            if self.stop_event.is_set():
                return False
            print(f"[ROBOT] Loop iteration {iteration}/{times}")
            if not self._run_steps(steps):
                return False

        return True
