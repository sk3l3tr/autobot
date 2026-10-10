import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from robotization.recorder_state import RecorderState
from robotization.robot_files import RobotFileConflictError
from robotization.robot_recorder import save_robot_state


class RobotRecorderPersistenceTests(unittest.TestCase):
    def test_save_robot_state_keeps_same_path_when_name_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "demo_bot.yaml"
            file_path.write_text("[]\n", encoding="utf-8")
            state = RecorderState.load_actions([{"action": "delay", "seconds": 1}])

            with patch("robotization.robot_recorder._save_state_to_file") as save_file:
                saved_path = save_robot_state(file_path, "demo_bot", state)

            self.assertEqual(saved_path, file_path)
            save_file.assert_called_once_with(file_path, state)

    def test_save_robot_state_renames_on_save_and_updates_target_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "demo_bot.yaml"
            file_path.write_text("[]\n", encoding="utf-8")
            state = RecorderState.load_actions([{"action": "delay", "seconds": 1}])

            with patch("robotization.robot_recorder._save_state_to_file") as save_file:
                saved_path = save_robot_state(file_path, "renamed_bot", state)

            self.assertEqual(saved_path.name, "renamed_bot.yaml")
            self.assertFalse(file_path.exists())
            self.assertTrue(saved_path.exists())
            save_file.assert_called_once_with(saved_path, state)

    def test_save_robot_state_preserves_original_file_when_rename_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "demo_bot.yaml"
            target_path = Path(temp_dir) / "existing_bot.yaml"
            file_path.write_text("[]\n", encoding="utf-8")
            target_path.write_text("[]\n", encoding="utf-8")
            state = RecorderState.load_actions([{"action": "delay", "seconds": 1}])

            with self.assertRaises(RobotFileConflictError):
                save_robot_state(file_path, "existing_bot", state)

            self.assertTrue(file_path.exists())
            self.assertTrue(target_path.exists())


if __name__ == "__main__":
    unittest.main()
