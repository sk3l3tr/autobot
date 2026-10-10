import unittest

from robotization.recorder_action_editors import (
    RecorderValidationError,
    format_action_label,
    get_action_editor,
    normalize_action,
)


class RecorderActionEditorsTests(unittest.TestCase):
    def test_click_editor_normalizes_valid_payload(self):
        action = normalize_action({"action": "click", "x": "10", "y": 20, "after": "0.5"})

        self.assertEqual(action, {"action": "click", "x": 10.0, "y": 20.0, "after": 0.5})

    def test_click_editor_rejects_invalid_coordinates(self):
        with self.assertRaises(RecorderValidationError):
            normalize_action({"action": "click", "x": "left", "y": 20, "after": 0.5})

    def test_delay_editor_normalizes_valid_payload(self):
        action = normalize_action({"action": "delay", "seconds": "2"})

        self.assertEqual(action, {"action": "delay", "seconds": 2.0})

    def test_delay_editor_rejects_non_positive_values(self):
        with self.assertRaises(RecorderValidationError):
            normalize_action({"action": "delay", "seconds": 0})

    def test_loop_editor_normalizes_count_mode(self):
        action = normalize_action(
            {
                "action": "loop",
                "mode": "count",
                "times": "3",
                "steps": [{"action": "delay", "seconds": 2}],
            }
        )

        self.assertEqual(
            action,
            {
                "action": "loop",
                "mode": "count",
                "times": 3,
                "steps": [{"action": "delay", "seconds": 2.0}],
            },
        )

    def test_loop_editor_normalizes_until_stopped_mode(self):
        action = normalize_action(
            {
                "action": "loop",
                "mode": "until_stopped",
                "steps": [{"action": "click", "x": 10, "y": 20, "after": 0.5}],
            }
        )

        self.assertEqual(
            action,
            {
                "action": "loop",
                "mode": "until_stopped",
                "steps": [{"action": "click", "x": 10.0, "y": 20.0, "after": 0.5}],
            },
        )

    def test_loop_editor_rejects_missing_steps(self):
        with self.assertRaises(RecorderValidationError):
            normalize_action({"action": "loop", "mode": "count", "times": 2, "steps": []})

    def test_unknown_actions_fall_back_to_generic_editor(self):
        action = normalize_action({"action": "scroll", "amount": 3, "enabled": True})

        self.assertEqual(action, {"action": "scroll", "amount": 3, "enabled": True})

    def test_action_labels_match_payload(self):
        click_label = format_action_label({"action": "click", "x": 10, "y": 20, "after": 0.5})
        delay_label = format_action_label({"action": "delay", "seconds": 2})
        loop_label = format_action_label(
            {
                "action": "loop",
                "mode": "count",
                "times": 2,
                "steps": [{"action": "delay", "seconds": 1}],
            }
        )
        custom_label = format_action_label({"action": "scroll", "amount": 3})

        self.assertEqual(click_label, "Click | x=10, y=20 | after=0.5s")
        self.assertEqual(delay_label, "Delay | 2s")
        self.assertEqual(loop_label, "Loop | x2 | 1 steps")
        self.assertEqual(custom_label, 'Scroll | amount=3')

    def test_editor_fields_are_exposed_for_ui_rendering(self):
        click_editor = get_action_editor("click")
        delay_editor = get_action_editor("delay")
        loop_editor = get_action_editor("loop")
        custom_editor = get_action_editor("scroll")

        self.assertEqual([field.name for field in click_editor.fields], ["x", "y", "after"])
        self.assertEqual([field.name for field in delay_editor.fields], ["seconds"])
        self.assertEqual([field.name for field in loop_editor.fields], ["mode", "times"])
        self.assertEqual([field.name for field in custom_editor.fields], ["action", "payload_json"])


if __name__ == "__main__":
    unittest.main()
