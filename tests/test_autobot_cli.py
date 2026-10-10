import unittest
from unittest.mock import patch

from click.testing import CliRunner

import autobot_cli


class WriteCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_write_opens_recorder_with_yaml_extension(self):
        with patch("autobot_cli.initialize_user_environment") as init_env, patch(
            "autobot_cli.start_robot_recorder_process"
        ) as start_recorder:
            result = self.runner.invoke(autobot_cli.cli, ["write", "demo_bot"])

        self.assertEqual(result.exit_code, 0)
        init_env.assert_called_once_with()
        start_recorder.assert_called_once_with("demo_bot.yaml", daemon=False)

    def test_write_accepts_robot_name_with_yaml_extension(self):
        with patch("autobot_cli.initialize_user_environment"), patch(
            "autobot_cli.start_robot_recorder_process"
        ) as start_recorder:
            result = self.runner.invoke(autobot_cli.cli, ["write", "demo_bot.yaml"])

        self.assertEqual(result.exit_code, 0)
        start_recorder.assert_called_once_with("demo_bot.yaml", daemon=False)

    def test_write_rejects_directory_traversal_names(self):
        result = self.runner.invoke(autobot_cli.cli, ["write", "../evil"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("simple file name", result.output)


if __name__ == "__main__":
    unittest.main()
