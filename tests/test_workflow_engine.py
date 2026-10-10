import threading
import types
import unittest
import sys
from unittest.mock import patch

sys.modules.setdefault(
    "pyautogui",
    types.SimpleNamespace(click=lambda *_args, **_kwargs: None, sleep=lambda *_args, **_kwargs: None),
)

from robotization.workflow_engine import WorkflowEngine


class FakeController:
    def __init__(self):
        self.calls = []

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def delay(self, seconds):
        self.calls.append(("delay", seconds))


class WorkflowEngineTests(unittest.TestCase):
    def test_run_executes_loop_count_steps(self):
        controller = FakeController()
        engine = WorkflowEngine(
            [
                {
                    "action": "loop",
                    "mode": "count",
                    "times": 2,
                    "steps": [{"action": "delay", "seconds": 1}],
                }
            ],
            controller,
        )

        result = engine.run()

        self.assertTrue(result)
        self.assertEqual(controller.calls, [("delay", 1), ("delay", 1)])

    def test_run_logs_loop_start_and_iteration_progress(self):
        controller = FakeController()
        engine = WorkflowEngine(
            [
                {
                    "action": "loop",
                    "mode": "count",
                    "times": 2,
                    "steps": [{"action": "delay", "seconds": 1}],
                }
            ],
            controller,
        )

        with patch("builtins.print") as print_mock:
            result = engine.run()

        self.assertTrue(result)
        printed_lines = [args[0] for args, _kwargs in print_mock.call_args_list]
        self.assertIn("[ROBOT] Loop started | mode=count | times=2", printed_lines)
        self.assertIn("[ROBOT] Loop iteration 1/2", printed_lines)
        self.assertIn("[ROBOT] Loop iteration 2/2", printed_lines)

    def test_run_stops_until_stopped_loop_when_stop_event_is_set(self):
        controller = FakeController()
        stop_event = threading.Event()
        engine = WorkflowEngine(
            [
                {
                    "action": "loop",
                    "mode": "until_stopped",
                    "steps": [{"action": "delay", "seconds": 1}],
                }
            ],
            controller,
            stop_event=stop_event,
        )

        class StopAfterFirstDelay:
            def __init__(self, inner_controller, stopper):
                self.inner_controller = inner_controller
                self.stopper = stopper

            def click(self, x, y):
                self.inner_controller.click(x, y)

            def delay(self, seconds):
                self.inner_controller.delay(seconds)
                self.stopper.set()

        engine.controller = StopAfterFirstDelay(controller, stop_event)
        result = engine.run()

        self.assertFalse(result)
        self.assertEqual(controller.calls, [("delay", 1)])

    def test_run_returns_false_for_unknown_actions(self):
        controller = FakeController()
        engine = WorkflowEngine([{"action": "unknown_future_action"}], controller)

        result = engine.run()

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
