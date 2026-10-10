import unittest

from robotization.input_security import (
    DECIMAL_SANITIZER,
    ROBOT_NAME_SANITIZER,
    bind_sanitized_variable,
    sanitize_decimal_input,
    sanitize_robot_name_input,
)


class FakeVariable:
    def __init__(self, value: str = ""):
        self._value = value
        self._callbacks = []

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for callback in list(self._callbacks):
            callback()

    def trace_add(self, _mode, callback):
        self._callbacks.append(callback)


class InputSecurityTests(unittest.TestCase):
    def test_robot_name_input_removes_extension_and_invalid_chars(self):
        self.assertEqual(sanitize_robot_name_input("../My Robot!.yaml"), "_My_Robot_")

    def test_decimal_input_keeps_only_numeric_decimal_shape(self):
        self.assertEqual(sanitize_decimal_input("12abc.3.4"), "12.34")

    def test_decimal_input_can_keep_leading_minus_when_enabled(self):
        self.assertEqual(sanitize_decimal_input("-12a.3", allow_negative=True), "-12.3")

    def test_bind_sanitized_variable_updates_robot_name_input(self):
        variable = FakeVariable("bad name!.yaml")

        bind_sanitized_variable(variable, ROBOT_NAME_SANITIZER)

        self.assertEqual(variable.get(), "bad_name_")

    def test_bind_sanitized_variable_updates_decimal_input(self):
        variable = FakeVariable("12a.3")

        bind_sanitized_variable(variable, DECIMAL_SANITIZER)

        self.assertEqual(variable.get(), "12.3")


if __name__ == "__main__":
    unittest.main()
