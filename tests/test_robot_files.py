import tempfile
import unittest
from pathlib import Path

from robotization.robot_files import (
    RobotFileConflictError,
    RobotFileValidationError,
    build_robot_file_path,
    rename_robot_file,
    sanitize_robot_file_name,
)


class RobotFilesTests(unittest.TestCase):
    def test_sanitize_robot_file_name_adds_extension(self):
        self.assertEqual(sanitize_robot_file_name("demo_bot"), "demo_bot.yaml")

    def test_sanitize_robot_file_name_preserves_existing_extension(self):
        self.assertEqual(sanitize_robot_file_name("demo_bot.yaml"), "demo_bot.yaml")

    def test_sanitize_robot_file_name_rejects_empty_name(self):
        with self.assertRaises(RobotFileValidationError):
            sanitize_robot_file_name("")

    def test_sanitize_robot_file_name_rejects_subpaths(self):
        with self.assertRaises(RobotFileValidationError):
            sanitize_robot_file_name("../demo")

    def test_sanitize_robot_file_name_matches_backend_sanitization(self):
        self.assertEqual(sanitize_robot_file_name("My Robot!"), "My_Robot_.yaml")

    def test_build_robot_file_path_stays_inside_base_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = build_robot_file_path(temp_dir, "demo")
            self.assertEqual(path, Path(temp_dir).resolve() / "demo.yaml")

    def test_rename_robot_file_renames_when_destination_is_free(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            old_path = Path(temp_dir) / "old_bot.yaml"
            old_path.write_text("[]\n", encoding="utf-8")

            new_path = rename_robot_file(temp_dir, "old_bot", "new_bot")

            self.assertFalse(old_path.exists())
            self.assertTrue(new_path.exists())
            self.assertEqual(new_path.name, "new_bot.yaml")

    def test_rename_robot_file_errors_when_destination_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "old_bot.yaml").write_text("[]\n", encoding="utf-8")
            (Path(temp_dir) / "new_bot.yaml").write_text("[]\n", encoding="utf-8")

            with self.assertRaises(RobotFileConflictError):
                rename_robot_file(temp_dir, "old_bot", "new_bot")


if __name__ == "__main__":
    unittest.main()
