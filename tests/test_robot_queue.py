import unittest
from queue import Empty
from unittest.mock import patch
import types
import sys

sys.modules.setdefault(
    "loguru",
    types.SimpleNamespace(
        logger=types.SimpleNamespace(
            info=lambda *_args, **_kwargs: None,
            warning=lambda *_args, **_kwargs: None,
            error=lambda *_args, **_kwargs: None,
        )
    ),
)
sys.modules.setdefault(
    "pyautogui",
    types.SimpleNamespace(click=lambda *_args, **_kwargs: None, sleep=lambda *_args, **_kwargs: None),
)
fake_robot_manager_module = types.ModuleType("robotization.robot_manager")
fake_robot_manager_module.RobotManager = object
sys.modules.setdefault("robotization.robot_manager", fake_robot_manager_module)

from robotization.robot_queue import RobotQueue


class FakeRobotManager:
    def __init__(self):
        self.stop_calls = 0

    def stop_automation(self):
        self.stop_calls += 1

    def run_automation(self, _name):
        return True


class RobotQueueTests(unittest.TestCase):
    def tearDown(self):
        RobotQueue._instance = None

    def test_stop_all_clears_pending_queue_and_requests_stop(self):
        manager = FakeRobotManager()
        with patch("threading.Thread.start", autospec=True):
            queue = RobotQueue(robot_manager=manager)

        queue.enqueue("alpha")
        queue.enqueue("beta")
        queue.stop_all()

        self.assertEqual(manager.stop_calls, 1)
        with self.assertRaises(Empty):
            queue._queue.get_nowait()


if __name__ == "__main__":
    unittest.main()
