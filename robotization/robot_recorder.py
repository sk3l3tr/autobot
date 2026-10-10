import argparse
import json
import logging
import multiprocessing
import os
from pathlib import Path
from typing import Any

multiprocessing.set_start_method("spawn", force=True)

try:
    from loguru import logger
except ImportError:  # pragma: no cover - fallback for lightweight test environments
    logger = logging.getLogger(__name__)

from robotization.input_security import (
    DECIMAL_SANITIZER,
    ROBOT_NAME_SANITIZER,
    bind_sanitized_variable,
)
from robotization.recorder_action_editors import (
    RecorderValidationError,
    format_action_label,
    get_action_editor,
    normalize_action,
)
from robotization.recorder_state import RecorderState
from robotization.robot_files import (
    RobotFileConflictError,
    RobotFileValidationError,
    normalize_robot_base_name,
    rename_robot_file,
)

RECORDER_SHORTCUT_POPUP_TITLE = "Recorder shortcuts"
RECORDER_SHORTCUT_HINT_TEXT = (
    "Tip: Press Ctrl+C to copy the current X/Y and Ctrl+V to paste it into a click action."
)
RECORDER_SHORTCUT_POPUP_TEXT = (
    "Press Ctrl+C to copy the current cursor X/Y.\n"
    "Press Ctrl+V to paste those coordinates into the selected click action.\n"
    "If no click is selected, Recorder will add a new click with those coordinates."
)


def _set_logs():
    from path_provider import PathProvider

    logs_dir = PathProvider.get_logs_dir()
    os.makedirs(logs_dir, exist_ok=True)

    if hasattr(logger, "remove") and hasattr(logger, "add"):
        logger.remove()
        logger.add(
            os.path.join(logs_dir, "r0b0t_r3c0rd3r.log"),
            rotation="1 MB",
            retention=3,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
        )


def _resolve_and_prepare_path(file_arg: str | None, dir_arg: str | None) -> Path:
    file_name = (file_arg or "my_robot.yaml").strip()
    dir_path = Path(dir_arg).expanduser() if dir_arg else Path.cwd()

    file_path = Path(file_name)
    if not file_path.is_absolute():
        file_path = dir_path / file_name

    file_path = file_path.expanduser().resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        with open(file_path, "w", encoding="utf-8", newline="\n") as file:
            file.write("[]\n")

    return file_path


def _load_state_from_file(file_path: Path) -> RecorderState:
    import yaml

    with open(file_path, "r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or []
    return RecorderState.load_actions(payload)


def _save_state_to_file(file_path: Path, state: RecorderState) -> None:
    import yaml

    with open(file_path, "w", encoding="utf-8") as file:
        yaml.dump(state.list_actions(), file, sort_keys=False)


def save_robot_state(current_file_path: Path, robot_name: str, state: RecorderState) -> Path:
    target_file_path = current_file_path
    requested_base_name = normalize_robot_base_name(robot_name)
    current_base_name = current_file_path.stem

    if requested_base_name != current_base_name:
        target_file_path = rename_robot_file(
            current_file_path.parent,
            current_base_name,
            requested_base_name,
        )

    _save_state_to_file(target_file_path, state)
    return target_file_path


def get_current_cursor_position() -> tuple[int, int]:
    import pyautogui

    x, y = pyautogui.position()
    return int(x), int(y)


def create_click_action_from_coords(x: float, y: float, after: float = 0.5) -> dict:
    return normalize_action({"action": "click", "x": x, "y": y, "after": after})


def apply_pasted_coordinates_to_click(action: dict, coords: tuple[float, float]) -> dict:
    if action.get("action") != "click":
        raise RecorderValidationError("Selected action must be a click.")

    x, y = coords
    after = action.get("after", 0.5)
    return create_click_action_from_coords(x, y, after)


def apply_pasted_coordinates_to_state(
    state: RecorderState,
    selected_index: int | None,
    coords: tuple[float, float],
) -> tuple[int, str]:
    actions = state.list_actions()

    if selected_index is not None and 0 <= selected_index < len(actions):
        selected_action = actions[selected_index]
        if selected_action.get("action") == "click":
            state.update_action(selected_index, apply_pasted_coordinates_to_click(selected_action, coords))
            return selected_index, "updated"

    appended_index = state.add_action(create_click_action_from_coords(*coords))
    return appended_index, "appended"


def apply_pasted_coordinates_to_click_form(
    widgets: dict[str, Any],
    coords: tuple[float, float],
) -> bool:
    x_widget = widgets.get("x")
    y_widget = widgets.get("y")
    if x_widget is None or y_widget is None:
        return False

    x, y = coords
    x_widget.set(str(int(x)) if float(x).is_integer() else str(float(x)))
    y_widget.set(str(int(y)) if float(y).is_integer() else str(float(y)))
    return True


def get_recorder_shortcut_hint_text() -> str:
    return RECORDER_SHORTCUT_HINT_TEXT


def get_recorder_shortcut_popup_text() -> str:
    return RECORDER_SHORTCUT_POPUP_TEXT


def consume_recorder_shortcut_popup_flag(should_show: bool) -> bool:
    return bool(should_show)


def load_args():
    parser = argparse.ArgumentParser(
        description="Robot Recorder Tool - GUI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--file", type=str, default="my_robot.yaml", help="YAML file path")
    parser.add_argument("--directory", type=str, help="Directory where save the robotization files")
    parser.add_argument(
        "--show-shortcut-popup",
        action="store_true",
        help="Show the Recorder shortcut help popup on startup",
    )
    return parser.parse_args()


def main():
    import tkinter as tk
    from pynput import keyboard
    from pynput import mouse
    from tkinter import simpledialog

    _set_logs()

    args = load_args()
    file_path = _resolve_and_prepare_path(args.file, args.directory)
    logger.info(f"Robot file ready at: {file_path}")

    is_recording = False
    listener = None
    keyboard_listener = None
    selected_index: int | None = None
    copied_coordinates: tuple[int, int] | None = None
    pressed_keys: set[object] = set()
    paste_target_stack: list[dict[str, Any]] = []

    try:
        state = _load_state_from_file(file_path)
        initial_status = "Robot loaded"
    except RecorderValidationError as exc:
        logger.error(f"Error loading robot: {exc}")
        state = RecorderState.load_actions([])
        initial_status = f"Error loading robot: {exc}"
    except OSError as exc:
        logger.error(f"Error loading robot: {exc}")
        state = RecorderState.load_actions([])
        initial_status = f"Error loading robot: {exc}"
    except Exception as exc:
        logger.error(f"Error loading robot: {exc}")
        state = RecorderState.load_actions([])
        initial_status = f"Error loading robot: {exc}"

    root = tk.Tk()
    root.title("🤖 Autobot Recorder")
    root.geometry("860x640")
    root.resizable(False, False)

    status_var = tk.StringVar(value="")

    def set_status(message: str):
        status_var.set(message)
        logger.info(message)

    def show_shortcut_popup():
        dialog = tk.Toplevel(root)
        dialog.title(RECORDER_SHORTCUT_POPUP_TITLE)
        dialog.geometry("420x170")
        dialog.transient(root)
        dialog.resizable(False, False)
        dialog.grab_set()

        container = tk.Frame(dialog)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            container,
            text=get_recorder_shortcut_popup_text(),
            justify="left",
            anchor="w",
            wraplength=380,
        ).pack(fill="both", expand=True)

        tk.Button(container, text="OK", command=dialog.destroy, width=10).pack(
            anchor="e",
            pady=(12, 0),
        )

        dialog.update_idletasks()
        x = root.winfo_rootx() + max((root.winfo_width() - dialog.winfo_width()) // 2, 0)
        y = root.winfo_rooty() + max((root.winfo_height() - dialog.winfo_height()) // 2, 0)
        dialog.geometry(f"+{x}+{y}")

    def create_default_click_action() -> dict:
        x, y = get_current_cursor_position()
        return create_click_action_from_coords(x, y)

    def create_default_delay_action() -> dict:
        return {"action": "delay", "seconds": 1}

    def create_default_loop_action() -> dict:
        return {
            "action": "loop",
            "mode": "count",
            "times": 2,
            "steps": [create_default_delay_action()],
        }

    def prompt_custom_action_name(parent) -> str | None:
        action_name = simpledialog.askstring("New action", "Action name:", parent=parent)
        if action_name is None:
            return None
        action_name = action_name.strip()
        if not action_name:
            set_status("Action name cannot be empty")
            return None
        return action_name

    def open_sequence_editor_dialog(parent, initial_actions: list[dict], title: str) -> list[dict] | None:
        sequence_state = RecorderState.load_actions(initial_actions)
        result: list[dict] | None = None
        sequence_selected_index: int | None = None

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("760x520")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        root_frame = tk.Frame(dialog)
        root_frame.pack(fill="both", expand=True, padx=12, pady=12)

        content_frame = tk.Frame(root_frame)
        content_frame.pack(fill="both", expand=True)

        list_frame = tk.Frame(content_frame, bd=2, relief="solid")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        action_listbox = tk.Listbox(list_frame, font=("Consolas", 11), activestyle="none")
        action_listbox.pack(side="left", fill="both", expand=True)

        list_scroll = tk.Scrollbar(list_frame, orient="vertical", command=action_listbox.yview)
        list_scroll.pack(side="right", fill="y")
        action_listbox.config(yscrollcommand=list_scroll.set)

        side_frame = tk.Frame(content_frame, width=250, bd=2, relief="solid")
        side_frame.pack(side="left", fill="y")
        side_frame.pack_propagate(False)

        details_var = tk.StringVar(value="Select an action")
        tk.Label(side_frame, textvariable=details_var, justify="left", anchor="nw").pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        button_frame = tk.Frame(side_frame)
        button_frame.pack(fill="x", padx=8, pady=(0, 8))

        def get_sequence_selected_index() -> int | None:
            selection = action_listbox.curselection()
            if not selection:
                return None
            return int(selection[0])

        def render_sequence_details(index: int | None):
            if index is None:
                details_var.set("Select an action")
                return

            action = sequence_state.list_actions()[index]
            details = [format_action_label(action)]
            if "steps" in action:
                details.append(f"Nested steps: {len(action.get('steps', []))}")
            details_var.set("\n".join(details))

        def update_sequence_buttons():
            index = get_sequence_selected_index()
            has_selection = index is not None
            state_size = len(sequence_state.list_actions())
            edit_btn.config(state="normal" if has_selection else "disabled")
            delete_btn.config(state="normal" if has_selection else "disabled")
            move_up_btn.config(state="normal" if has_selection and index > 0 else "disabled")
            move_down_btn.config(
                state="normal" if has_selection and index < state_size - 1 else "disabled"
            )

        def refresh_sequence_list(select_index: int | None = None):
            nonlocal sequence_selected_index

            actions = sequence_state.list_actions()
            action_listbox.delete(0, tk.END)
            for index, item in enumerate(actions, start=1):
                action_listbox.insert(tk.END, f"{index}. {format_action_label(item)}")

            if not actions:
                sequence_selected_index = None
                render_sequence_details(None)
                update_sequence_buttons()
                return

            if select_index is None:
                select_index = sequence_selected_index if sequence_selected_index is not None else 0

            select_index = max(0, min(select_index, len(actions) - 1))
            sequence_selected_index = select_index
            action_listbox.selection_clear(0, tk.END)
            action_listbox.selection_set(select_index)
            action_listbox.activate(select_index)
            render_sequence_details(select_index)
            update_sequence_buttons()

        def on_sequence_selected(_event=None):
            nonlocal sequence_selected_index
            sequence_selected_index = get_sequence_selected_index()
            render_sequence_details(sequence_selected_index)
            update_sequence_buttons()

        def append_sequence_action(action_payload: dict):
            nonlocal sequence_selected_index
            sequence_selected_index = sequence_state.add_action(action_payload)
            refresh_sequence_list(sequence_selected_index)

        def paste_into_sequence():
            nonlocal sequence_selected_index
            if copied_coordinates is None:
                set_status("Copy coordinates first with CTRL+C")
                return

            sequence_selected_index, outcome = apply_pasted_coordinates_to_state(
                sequence_state,
                get_sequence_selected_index(),
                copied_coordinates,
            )
            refresh_sequence_list(sequence_selected_index)
            if outcome == "updated":
                set_status(
                    f"Click updated with copied coordinates x={copied_coordinates[0]}, y={copied_coordinates[1]}"
                )
            else:
                set_status(
                    f"Click added with copied coordinates x={copied_coordinates[0]}, y={copied_coordinates[1]}"
                )

        def add_click_action():
            append_sequence_action(create_default_click_action())

        def add_delay_action():
            append_sequence_action(create_default_delay_action())

        def add_loop_action():
            append_sequence_action(create_default_loop_action())

        def add_custom_action():
            action_name = prompt_custom_action_name(dialog)
            if not action_name:
                return
            append_sequence_action({"action": action_name})

        def edit_selected_sequence_action():
            index = get_sequence_selected_index()
            if index is None:
                return
            updated = open_action_dialog(dialog, sequence_state.list_actions()[index], "Edit action")
            if updated is None:
                return
            sequence_state.update_action(index, updated)
            refresh_sequence_list(index)

        def delete_selected_sequence_action():
            nonlocal sequence_selected_index
            index = get_sequence_selected_index()
            if index is None:
                return
            sequence_state.delete_action(index)
            next_index = None if not sequence_state.list_actions() else min(
                index,
                len(sequence_state.list_actions()) - 1,
            )
            sequence_selected_index = next_index
            refresh_sequence_list(next_index)

        def move_selected_sequence_action(direction: str):
            nonlocal sequence_selected_index
            index = get_sequence_selected_index()
            if index is None:
                return
            sequence_selected_index = sequence_state.move_action(index, direction)
            refresh_sequence_list(sequence_selected_index)

        def save_sequence():
            nonlocal result
            result = sequence_state.list_actions()
            dialog.destroy()

        action_listbox.bind("<<ListboxSelect>>", on_sequence_selected)

        tk.Button(button_frame, text="+ CLICK", command=add_click_action).pack(fill="x", pady=2)
        tk.Button(button_frame, text="+ DELAY", command=add_delay_action).pack(fill="x", pady=2)
        tk.Button(button_frame, text="+ LOOP", command=add_loop_action).pack(fill="x", pady=2)
        tk.Button(button_frame, text="+ CUSTOM", command=add_custom_action).pack(fill="x", pady=2)

        edit_btn = tk.Button(button_frame, text="EDIT", command=edit_selected_sequence_action)
        edit_btn.pack(fill="x", pady=(10, 2))

        move_up_btn = tk.Button(
            button_frame,
            text="MOVE UP",
            command=lambda: move_selected_sequence_action("up"),
        )
        move_up_btn.pack(fill="x", pady=2)

        move_down_btn = tk.Button(
            button_frame,
            text="MOVE DOWN",
            command=lambda: move_selected_sequence_action("down"),
        )
        move_down_btn.pack(fill="x", pady=2)

        delete_btn = tk.Button(button_frame, text="DELETE", command=delete_selected_sequence_action)
        delete_btn.pack(fill="x", pady=2)

        footer_frame = tk.Frame(root_frame)
        footer_frame.pack(fill="x", pady=(10, 0))
        tk.Button(footer_frame, text="SAVE", command=save_sequence, width=12).pack(
            side="right",
            padx=4,
        )
        tk.Button(footer_frame, text="CANCEL", command=dialog.destroy, width=12).pack(
            side="right",
            padx=4,
        )

        push_paste_target(
            dialog,
            {
                "kind": "sequence_dialog",
                "handler": paste_into_sequence,
            },
        )
        refresh_sequence_list(0 if sequence_state.list_actions() else None)
        dialog.wait_window()
        return result

    def open_action_dialog(parent, initial_action: dict | None, title: str) -> dict | None:
        action = normalize_action(initial_action or create_default_delay_action())
        result: dict | None = None

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("520x520")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        container = tk.Frame(dialog)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        header_var = tk.StringVar(value=f"Editing {action['action']}")
        tk.Label(container, textvariable=header_var, anchor="w").pack(fill="x", pady=(0, 8))

        form_frame = tk.Frame(container, bd=2, relief="solid")
        form_frame.pack(fill="both", expand=True)

        footer_frame = tk.Frame(container)
        footer_frame.pack(fill="x", pady=(10, 0))

        widgets: dict[str, object] = {}
        nested_steps = [dict(step) for step in action.get("steps", [])]
        editor = get_action_editor(action["action"])

        def edit_nested_steps():
            nonlocal nested_steps
            edited_steps = open_sequence_editor_dialog(dialog, nested_steps, f"{title} - Steps")
            if edited_steps is not None:
                nested_steps = edited_steps
                refresh_form()

        def read_form_values() -> dict:
            payload: dict = {}
            for field in editor.fields:
                widget = widgets[field.name]
                if field.kind == "json":
                    raw_json = widget.get("1.0", tk.END).strip()
                    if raw_json:
                        try:
                            parsed = json.loads(raw_json)
                        except json.JSONDecodeError as exc:
                            raise RecorderValidationError(
                                f"Field '{field.name}' must be valid JSON."
                            ) from exc
                        if not isinstance(parsed, dict):
                            raise RecorderValidationError(
                                f"Field '{field.name}' must contain a JSON object."
                            )
                    else:
                        parsed = {}
                    payload[field.name] = parsed
                else:
                    payload[field.name] = widget.get().strip()

            if editor.allows_unknown_fields:
                generic_payload = payload.pop("payload_json", {})
                payload = {"action": payload.get("action", "").strip(), **generic_payload}
            else:
                payload["action"] = editor.action_name

            if editor.supports_nested_steps or nested_steps:
                payload["steps"] = nested_steps

            return payload

        def on_save():
            nonlocal result
            try:
                result = normalize_action(read_form_values())
            except RecorderValidationError as exc:
                set_status(str(exc))
                return
            dialog.destroy()

        def paste_into_action_form():
            if copied_coordinates is None:
                set_status("Copy coordinates first with CTRL+C")
                return

            if action.get("action") != "click":
                set_status(f"Active action '{action.get('action')}' does not accept pasted coordinates")
                return

            if not apply_pasted_coordinates_to_click_form(widgets, copied_coordinates):
                set_status("Active click form is missing X/Y fields")
                return

            set_status(
                f"Click form updated with copied coordinates x={copied_coordinates[0]}, y={copied_coordinates[1]}"
            )

        def refresh_form():
            for child in form_frame.winfo_children():
                child.destroy()
            widgets.clear()

            exported = editor.export_form_values(action)
            header_var.set(f"Editing {action['action']}")

            for field in editor.fields:
                row = tk.Frame(form_frame)
                row.pack(fill="x", padx=8, pady=6)

                label = tk.Label(row, text=f"{field.label}:", width=14, anchor="w")
                label.pack(side="left")

                if field.kind == "json":
                    text = tk.Text(row, width=34, height=10)
                    text.insert("1.0", exported.get(field.name, "{}"))
                    text.pack(side="left", fill="both", expand=True)
                    widgets[field.name] = text
                    continue

                variable = tk.StringVar(value=exported.get(field.name, ""))
                if field.kind in {"number", "integer"}:
                    bind_sanitized_variable(variable, DECIMAL_SANITIZER)

                if field.kind == "select":
                    option = tk.OptionMenu(row, variable, *field.options)
                    option.config(width=16)
                    option.pack(side="left", fill="x", expand=True)
                    widgets[field.name] = variable
                    continue

                entry = tk.Entry(row, textvariable=variable)
                entry.pack(side="left", fill="x", expand=True)
                widgets[field.name] = variable

            if editor.supports_nested_steps or "steps" in action:
                nested_frame = tk.Frame(form_frame)
                nested_frame.pack(fill="x", padx=8, pady=6)
                tk.Label(
                    nested_frame,
                    text=f"Steps: {len(nested_steps)}",
                    anchor="w",
                ).pack(side="left")
                tk.Button(nested_frame, text="EDIT STEPS", command=edit_nested_steps).pack(
                    side="right"
                )

        tk.Button(footer_frame, text="SAVE", command=on_save, width=12).pack(
            side="right",
            padx=4,
        )
        tk.Button(footer_frame, text="CANCEL", command=dialog.destroy, width=12).pack(
            side="right",
            padx=4,
        )

        push_paste_target(
            dialog,
            {
                "kind": "action_dialog",
                "handler": paste_into_action_form,
            },
        )
        refresh_form()
        dialog.wait_window()
        return result

    def push_paste_target(window, target: dict[str, Any]):
        paste_target_stack.append(target)

        def remove_target(event=None):
            if event is not None and getattr(event, "widget", None) is not window:
                return
            if target in paste_target_stack:
                paste_target_stack.remove(target)

        window.bind("<Destroy>", remove_target, add="+")

    def get_active_paste_target_handler():
        if paste_target_stack:
            return paste_target_stack[-1]["handler"]
        return paste_into_main_list

    top_frame = tk.Frame(root)
    top_frame.pack(fill="x", padx=12, pady=(8, 0))
    tk.Label(
        top_frame,
        text=get_recorder_shortcut_hint_text(),
        justify="left",
        anchor="w",
        wraplength=560,
    ).pack(side="left", fill="x", expand=True, padx=10, pady=5)
    label_pos = tk.Label(top_frame, text="x=0, y=0")
    label_pos.pack(side="right", padx=10, pady=5)

    frame_name = tk.Frame(root)
    frame_name.pack(pady=(8, 0))
    tk.Label(frame_name, text="Robot name:").grid(row=0, column=0, padx=5)

    robot_name_var = tk.StringVar(value=file_path.stem)
    bind_sanitized_variable(robot_name_var, ROBOT_NAME_SANITIZER)
    tk.Entry(frame_name, textvariable=robot_name_var, width=24).grid(row=0, column=1, padx=5)

    frame_actions = tk.Frame(root)
    frame_actions.pack(pady=8)

    tk.Label(frame_actions, text="Delay (s):").grid(row=0, column=0, padx=5)

    entry_delay_var = tk.StringVar()
    bind_sanitized_variable(entry_delay_var, DECIMAL_SANITIZER)
    entry_delay = tk.Entry(frame_actions, textvariable=entry_delay_var, width=12)
    entry_delay.grid(row=0, column=1, padx=5)

    label_actions = tk.Label(root, text="ACTIONS")
    label_actions.pack(pady=(4, 6))

    content_frame = tk.Frame(root)
    content_frame.pack(fill="both", expand=True, padx=12)

    list_frame = tk.Frame(content_frame, bd=2, relief="solid")
    list_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

    action_list = tk.Listbox(list_frame, font=("Consolas", 11), activestyle="none")
    action_list.pack(side="left", fill="both", expand=True)

    list_scroll = tk.Scrollbar(list_frame, orient="vertical", command=action_list.yview)
    list_scroll.pack(side="right", fill="y")
    action_list.config(yscrollcommand=list_scroll.set)

    editor_panel = tk.Frame(content_frame, width=250, bd=2, relief="solid")
    editor_panel.pack(side="left", fill="y")
    editor_panel.pack_propagate(False)

    details_var = tk.StringVar(value="Select an action to inspect or edit")
    tk.Label(
        editor_panel,
        textvariable=details_var,
        anchor="nw",
        justify="left",
    ).pack(fill="both", expand=True, padx=8, pady=8)

    action_buttons = tk.Frame(editor_panel)
    action_buttons.pack(fill="x", padx=8, pady=(0, 8))

    def get_selected_index() -> int | None:
        selection = action_list.curselection()
        if not selection:
            return None
        return int(selection[0])

    def render_details(index: int | None):
        if index is None:
            details_var.set("Select an action to inspect or edit")
            return

        action = state.list_actions()[index]
        details = [format_action_label(action)]
        if "steps" in action:
            details.append(f"Nested steps: {len(action.get('steps', []))}")
        details_var.set("\n".join(details))

    def update_buttons():
        index = get_selected_index()
        has_selection = index is not None
        state_size = len(state.list_actions())
        edit_btn.config(state="normal" if has_selection else "disabled")
        delete_btn.config(state="normal" if has_selection else "disabled")
        move_up_btn.config(state="normal" if has_selection and index > 0 else "disabled")
        move_down_btn.config(
            state="normal" if has_selection and index < state_size - 1 else "disabled"
        )

    def refresh_action_list(select_index: int | None = None):
        nonlocal selected_index

        actions = state.list_actions()
        action_list.delete(0, tk.END)
        for index, action in enumerate(actions, start=1):
            action_list.insert(tk.END, f"{index}. {format_action_label(action)}")

        if not actions:
            selected_index = None
            render_details(None)
            update_buttons()
            return

        if select_index is None:
            select_index = selected_index if selected_index is not None else 0

        select_index = max(0, min(select_index, len(actions) - 1))
        selected_index = select_index
        action_list.selection_clear(0, tk.END)
        action_list.selection_set(select_index)
        action_list.activate(select_index)
        action_list.see(select_index)
        render_details(select_index)
        update_buttons()

    def on_action_selected(_event=None):
        nonlocal selected_index
        selected_index = get_selected_index()
        render_details(selected_index)
        update_buttons()

    def append_action(action: dict, message: str):
        nonlocal selected_index
        selected_index = state.add_action(action)
        refresh_action_list(selected_index)
        set_status(message)

    def start_rec():
        nonlocal is_recording, listener
        if is_recording:
            return
        is_recording = True
        listener = mouse.Listener(on_click=add_click)
        listener.start()
        set_status("REC started ...")

    def stop_rec():
        nonlocal is_recording, listener
        if not is_recording:
            return
        is_recording = False
        if listener is not None:
            listener.stop()
            listener = None
        set_status("REC stopped ...")

    def add_click(x, y, _button, pressed):
        if not is_recording or not pressed:
            return

        root.update_idletasks()
        x0 = root.winfo_rootx()
        y0 = root.winfo_rooty()
        x1 = x0 + root.winfo_width()
        y1 = y0 + root.winfo_height()
        if x0 <= x <= x1 and y0 <= y <= y1:
            return

        append_action({"action": "click", "x": x, "y": y, "after": 0.5}, f"Click added at x={x}, y={y}")

    def add_delay():
        try:
            seconds = float(entry_delay.get())
            append_action({"action": "delay", "seconds": seconds}, f"Delay ({seconds}s) added")
            entry_delay.delete(0, tk.END)
        except ValueError:
            set_status("Invalid DELAY value")
        except RecorderValidationError as exc:
            set_status(str(exc))

    def add_manual_click():
        click_action = create_default_click_action()
        append_action(click_action, f"Click added at x={click_action['x']}, y={click_action['y']}")

    def add_loop():
        append_action(create_default_loop_action(), "Loop action added")

    def add_custom_action():
        action_name = prompt_custom_action_name(root)
        if not action_name:
            return
        append_action({"action": action_name}, f"Custom action '{action_name}' added")

    def clear_actions():
        nonlocal selected_index, state
        state = RecorderState.load_actions([])
        selected_index = None
        refresh_action_list(None)
        set_status("Actions cleared successfully")

    def edit_selected_action():
        index = get_selected_index()
        if index is None:
            set_status("Select an action first")
            return
        updated = open_action_dialog(root, state.list_actions()[index], "Edit action")
        if updated is None:
            set_status("Action edit cancelled")
            return
        state.update_action(index, updated)
        refresh_action_list(index)
        set_status("Action updated successfully")

    def delete_selected_action():
        nonlocal selected_index
        index = get_selected_index()
        if index is None:
            set_status("Select an action first")
            return
        state.delete_action(index)
        next_index = None if not state.list_actions() else min(index, len(state.list_actions()) - 1)
        selected_index = next_index
        refresh_action_list(next_index)
        set_status("Action deleted successfully")

    def move_selected_action(direction: str):
        nonlocal selected_index
        index = get_selected_index()
        if index is None:
            set_status("Select an action first")
            return
        selected_index = state.move_action(index, direction)
        refresh_action_list(selected_index)
        set_status("Action cannot move further" if selected_index == index else f"Action moved {direction}")

    def save_and_exit():
        nonlocal file_path
        try:
            file_path = save_robot_state(file_path, robot_name_var.get(), state)
            robot_name_var.set(file_path.stem)
            cleanup_listeners()
            set_status("Automation saved successfully")
            root.quit()
        except (RobotFileValidationError, RobotFileConflictError, FileNotFoundError) as exc:
            set_status(str(exc))

    def exit_without_save():
        cleanup_listeners()
        set_status("Exit without save")
        root.quit()

    def cleanup_listeners():
        nonlocal keyboard_listener
        stop_rec()
        if keyboard_listener is not None:
            keyboard_listener.stop()
            keyboard_listener = None

    def copy_current_coordinates():
        nonlocal copied_coordinates
        copied_coordinates = get_current_cursor_position()
        set_status(f"Coordinates copied: x={copied_coordinates[0]}, y={copied_coordinates[1]}")

    def paste_into_main_list():
        nonlocal selected_index
        if copied_coordinates is None:
            set_status("Copy coordinates first with CTRL+C")
            return

        selected_index, outcome = apply_pasted_coordinates_to_state(
            state,
            get_selected_index(),
            copied_coordinates,
        )
        refresh_action_list(selected_index)
        if outcome == "updated":
            set_status(
                f"Click updated with copied coordinates x={copied_coordinates[0]}, y={copied_coordinates[1]}"
            )
        else:
            set_status(
                f"Click added with copied coordinates x={copied_coordinates[0]}, y={copied_coordinates[1]}"
            )

    def invoke_hotkey(action):
        try:
            root.after(0, action)
        except tk.TclError:
            return
        except RuntimeError:
            return

    def on_key_press(key):
        nonlocal pressed_keys
        if key in pressed_keys:
            return
        pressed_keys.add(key)

        is_ctrl_pressed = any(
            ctrl_key in pressed_keys
            for ctrl_key in (
                keyboard.Key.ctrl,
                keyboard.Key.ctrl_l,
                keyboard.Key.ctrl_r,
            )
        )
        if not is_ctrl_pressed:
            return

        key_char = getattr(key, "char", None)
        if not key_char:
            return

        if key_char.lower() == "c":
            invoke_hotkey(copy_current_coordinates)
        elif key_char.lower() == "v":
            invoke_hotkey(get_active_paste_target_handler())

    def on_key_release(key):
        pressed_keys.discard(key)

    def update_position():
        x, y = get_current_cursor_position()
        label_pos.config(text=f"x={x}, y={y}")
        root.after(100, update_position)

    tk.Button(frame_actions, text="+ DELAY", command=add_delay, width=10).grid(row=0, column=2, padx=4)
    tk.Button(frame_actions, text="+ CLICK", command=add_manual_click, width=10).grid(row=0, column=3, padx=4)
    tk.Button(frame_actions, text="+ LOOP", command=add_loop, width=10).grid(row=0, column=4, padx=4)
    tk.Button(frame_actions, text="+ CUSTOM", command=add_custom_action, width=10).grid(row=0, column=5, padx=4)

    action_list.bind("<<ListboxSelect>>", on_action_selected)

    move_up_btn = tk.Button(action_buttons, text="MOVE UP", command=lambda: move_selected_action("up"))
    move_up_btn.pack(fill="x", pady=2)

    move_down_btn = tk.Button(
        action_buttons,
        text="MOVE DOWN",
        command=lambda: move_selected_action("down"),
    )
    move_down_btn.pack(fill="x", pady=2)

    delete_btn = tk.Button(action_buttons, text="DELETE", command=delete_selected_action)
    delete_btn.pack(fill="x", pady=2)

    edit_btn = tk.Button(action_buttons, text="EDIT", command=edit_selected_action)
    edit_btn.pack(fill="x", pady=2)

    tk.Label(root, textvariable=status_var, anchor="w").pack(fill="x", padx=14, pady=(6, 0))

    frame_btn_actions = tk.Frame(root)
    frame_btn_actions.pack(pady=12)
    tk.Button(frame_btn_actions, text="START", command=start_rec, width=10).grid(row=0, column=0, padx=4)
    tk.Button(frame_btn_actions, text="STOP", command=stop_rec, width=10).grid(row=0, column=1, padx=4)
    tk.Button(frame_btn_actions, text="CLEAR", command=clear_actions, width=10).grid(row=0, column=2, padx=4)
    tk.Button(frame_btn_actions, text="SAVE", command=save_and_exit, width=10).grid(row=0, column=3, padx=4)
    tk.Button(frame_btn_actions, text="QUIT", command=exit_without_save, width=10).grid(row=0, column=4, padx=4)

    keyboard_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    keyboard_listener.start()
    root.protocol("WM_DELETE_WINDOW", exit_without_save)
    refresh_action_list(0 if state.list_actions() else None)
    set_status(initial_status)
    update_position()
    if consume_recorder_shortcut_popup_flag(args.show_shortcut_popup):
        root.after(150, show_shortcut_popup)
    root.mainloop()


if __name__ == "__main__" and multiprocessing.current_process().name == "MainProcess":
    multiprocessing.freeze_support()
    main()
