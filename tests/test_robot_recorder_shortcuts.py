import unittest

from robotization.recorder_state import RecorderState
from robotization.robot_recorder import (
    apply_pasted_coordinates_to_click,
    apply_pasted_coordinates_to_click_form,
    apply_pasted_coordinates_to_state,
    consume_recorder_shortcut_popup_flag,
    create_click_action_from_coords,
    get_recorder_shortcut_hint_text,
    get_recorder_shortcut_popup_text,
)


class FakeVariable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class RobotRecorderShortcutsTests(unittest.TestCase):
    def test_create_click_action_from_coords_uses_default_after(self):
        self.assertEqual(
            create_click_action_from_coords(10, 20),
            {"action": "click", "x": 10.0, "y": 20.0, "after": 0.5},
        )

    def test_apply_pasted_coordinates_to_click_preserves_after(self):
        updated = apply_pasted_coordinates_to_click(
            {"action": "click", "x": 1, "y": 2, "after": 3},
            (100, 200),
        )

        self.assertEqual(updated, {"action": "click", "x": 100.0, "y": 200.0, "after": 3.0})

    def test_apply_pasted_coordinates_to_state_updates_selected_click(self):
        state = RecorderState.load_actions(
            [{"action": "click", "x": 1, "y": 2, "after": 3}]
        )

        selected_index, outcome = apply_pasted_coordinates_to_state(state, 0, (100, 200))

        self.assertEqual(selected_index, 0)
        self.assertEqual(outcome, "updated")
        self.assertEqual(
            state.list_actions(),
            [{"action": "click", "x": 100.0, "y": 200.0, "after": 3.0}],
        )

    def test_apply_pasted_coordinates_to_state_appends_when_selection_is_not_click(self):
        state = RecorderState.load_actions([{"action": "delay", "seconds": 1}])

        selected_index, outcome = apply_pasted_coordinates_to_state(state, 0, (100, 200))

        self.assertEqual(selected_index, 1)
        self.assertEqual(outcome, "appended")
        self.assertEqual(
            state.list_actions(),
            [
                {"action": "delay", "seconds": 1.0},
                {"action": "click", "x": 100.0, "y": 200.0, "after": 0.5},
            ],
        )

    def test_apply_pasted_coordinates_to_state_appends_when_selection_is_missing(self):
        state = RecorderState.load_actions([])

        selected_index, outcome = apply_pasted_coordinates_to_state(state, None, (100, 200))

        self.assertEqual(selected_index, 0)
        self.assertEqual(outcome, "appended")
        self.assertEqual(
            state.list_actions(),
            [{"action": "click", "x": 100.0, "y": 200.0, "after": 0.5}],
        )

    def test_apply_pasted_coordinates_to_click_form_updates_only_position_fields(self):
        widgets = {
            "x": FakeVariable("1"),
            "y": FakeVariable("2"),
            "after": FakeVariable("3"),
        }

        changed = apply_pasted_coordinates_to_click_form(widgets, (100, 200))

        self.assertTrue(changed)
        self.assertEqual(widgets["x"].get(), "100")
        self.assertEqual(widgets["y"].get(), "200")
        self.assertEqual(widgets["after"].get(), "3")

    def test_apply_pasted_coordinates_to_click_form_requires_x_and_y_widgets(self):
        widgets = {"x": FakeVariable("1")}

        changed = apply_pasted_coordinates_to_click_form(widgets, (100, 200))

        self.assertFalse(changed)

    def test_recorder_shortcut_hint_text_mentions_copy_and_paste(self):
        text = get_recorder_shortcut_hint_text()

        self.assertIn("Ctrl+C", text)
        self.assertIn("Ctrl+V", text)
        self.assertIn("X/Y", text)

    def test_recorder_shortcut_popup_text_explains_append_behavior(self):
        text = get_recorder_shortcut_popup_text()

        self.assertIn("Ctrl+C", text)
        self.assertIn("Ctrl+V", text)
        self.assertIn("add a new click", text)

    def test_consume_recorder_shortcut_popup_flag_reflects_parent_gate(self):
        self.assertTrue(consume_recorder_shortcut_popup_flag(True))
        self.assertFalse(consume_recorder_shortcut_popup_flag(False))


if __name__ == "__main__":
    unittest.main()
