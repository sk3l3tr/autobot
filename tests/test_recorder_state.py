import unittest

from robotization.recorder_state import RecorderState, RecorderValidationError


class RecorderStateTests(unittest.TestCase):
    def test_load_actions_keeps_existing_order(self):
        state = RecorderState.load_actions(
            [
                {"action": "click", "x": 10, "y": 20, "after": 0.5},
                {"action": "delay", "seconds": 2},
            ]
        )

        self.assertEqual(
            state.list_actions(),
            [
                {"action": "click", "x": 10.0, "y": 20.0, "after": 0.5},
                {"action": "delay", "seconds": 2.0},
            ],
        )

    def test_load_actions_supports_loop_and_unknown_actions(self):
        state = RecorderState.load_actions(
            [
                {
                    "action": "loop",
                    "mode": "count",
                    "times": 2,
                    "steps": [
                        {"action": "delay", "seconds": 1},
                        {"action": "scroll", "amount": 3},
                    ],
                }
            ]
        )

        self.assertEqual(
            state.list_actions(),
            [
                {
                    "action": "loop",
                    "mode": "count",
                    "times": 2,
                    "steps": [
                        {"action": "delay", "seconds": 1.0},
                        {"action": "scroll", "amount": 3},
                    ],
                }
            ],
        )

    def test_add_action_appends_to_the_end(self):
        state = RecorderState.load_actions([])

        index = state.add_action({"action": "delay", "seconds": 1})

        self.assertEqual(index, 0)
        self.assertEqual(state.list_actions(), [{"action": "delay", "seconds": 1.0}])

    def test_update_action_replaces_existing_action(self):
        state = RecorderState.load_actions(
            [{"action": "click", "x": 10, "y": 20, "after": 0.5}]
        )

        state.update_action(0, {"action": "click", "x": 100, "y": 200, "after": 1})

        self.assertEqual(
            state.list_actions(),
            [{"action": "click", "x": 100.0, "y": 200.0, "after": 1.0}],
        )

    def test_delete_action_removes_selected_item(self):
        state = RecorderState.load_actions(
            [
                {"action": "click", "x": 10, "y": 20, "after": 0.5},
                {"action": "delay", "seconds": 2},
            ]
        )

        deleted = state.delete_action(0)

        self.assertEqual(deleted, {"action": "click", "x": 10.0, "y": 20.0, "after": 0.5})
        self.assertEqual(state.list_actions(), [{"action": "delay", "seconds": 2.0}])

    def test_move_action_up_and_down(self):
        state = RecorderState.load_actions(
            [
                {"action": "click", "x": 1, "y": 1, "after": 0.5},
                {"action": "delay", "seconds": 2},
                {"action": "click", "x": 3, "y": 3, "after": 0.5},
            ]
        )

        moved_up_index = state.move_action(1, "up")
        moved_down_index = state.move_action(0, "down")

        self.assertEqual(moved_up_index, 0)
        self.assertEqual(moved_down_index, 1)
        self.assertEqual(
            state.list_actions(),
            [
                {"action": "click", "x": 1.0, "y": 1.0, "after": 0.5},
                {"action": "delay", "seconds": 2.0},
                {"action": "click", "x": 3.0, "y": 3.0, "after": 0.5},
            ],
        )

    def test_move_action_is_noop_at_boundaries(self):
        state = RecorderState.load_actions(
            [
                {"action": "click", "x": 1, "y": 1, "after": 0.5},
                {"action": "delay", "seconds": 2},
            ]
        )

        first_index = state.move_action(0, "up")
        last_index = state.move_action(1, "down")

        self.assertEqual(first_index, 0)
        self.assertEqual(last_index, 1)
        self.assertEqual(
            state.list_actions(),
            [
                {"action": "click", "x": 1.0, "y": 1.0, "after": 0.5},
                {"action": "delay", "seconds": 2.0},
            ],
        )

    def test_update_action_allows_unknown_payload(self):
        state = RecorderState.load_actions([{"action": "delay", "seconds": 1}])

        state.update_action(0, {"action": "scroll", "amount": 3, "enabled": False})

        self.assertEqual(
            state.list_actions(),
            [{"action": "scroll", "amount": 3, "enabled": False}],
        )

    def test_load_actions_rejects_malformed_payload(self):
        with self.assertRaises(RecorderValidationError):
            RecorderState.load_actions([{"action": "click", "x": "left", "y": 20}])


if __name__ == "__main__":
    unittest.main()
