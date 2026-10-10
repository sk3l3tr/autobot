# Tech Stack

## Runtime

- Python 3.10+ for the desktop application, local backend, CLI, scheduler, and robot execution stack.
- Node.js 18+ and DemiurgeJS Architecture for frontend tooling and the webhook agent binary build pipeline.
- TypeScript for the webhook agent.
- Browser runtime for the packaged local console served from the Flask backend.

## Tooling

- Python packaging via `setuptools` with a `project.scripts` entrypoint for `autobot`.
- PyInstaller for desktop packaging into a single-file distribution.
- Vite for frontend build and preview.
- TypeScript compiler plus `pkg` for building the webhook agent binaries.
- No established repo-wide automated test runner is present yet; current verification is largely command-based and manual.

## Runtime Dependencies

- `click`: CLI entrypoints and command parsing.
- `Flask` + `flask-cors`: local HTTP API and static asset serving for the web console.
- `APScheduler`: schedule execution from a persisted YAML job file.
- `PyYAML`: read and write robot, config, and jobs YAML files.
- `pyautogui` + `pynput`: desktop input capture and playback for robot recording and execution.
- `pywebview`: kiosk-style desktop shell for the local UI.
- `loguru`: file-based logging across backend, scheduler, recorder, and robot execution components.
- `platformdirs`: platform-specific user data and log directories.
- `socket.io-client`, `laravel-echo`, `winston`: webhook agent integration stack.

## Core Technical Rules

- The source of truth for user data is the platform-specific directory managed by `PathProvider`, not the bundled `files/` tree.
- Robots are persisted as YAML files under the user automation directory and executed by `RobotManager` through `WorkflowEngine`.
- Recorder editing concerns are separate from runtime action execution: the recorder uses its own validation and field registry so new action types can grow in the UI without coupling Tkinter to execution classes.
- Robot workflows may contain nested action containers such as loops, so recorder validation and runtime execution must both support recursive `steps` lists.
- Unknown future action payloads should round-trip through the Tkinter recorder with a generic editor even when the runtime does not yet implement them.
- Robot file naming and rename behavior should live in shared Python helpers so CLI, backend, frontend-backed routes, and Tkinter recorder do not drift on sanitization or collision rules.
- Text entry hardening for Tkinter should use reusable input-security helpers plus per-field sanitizers, instead of ad hoc `.strip()` calls spread across widgets.
- Cross-process commands flow through the local SSCA socket bridge; backend routes and scheduler jobs send action payloads instead of calling long-lived services directly.
- Desktop sub-processes are managed through `ProcessManager`, with explicit shutdown and cleanup hooks for child processes and external binaries.
- Frontend assets are built in `frontend/` and deployed into `files/www/autobot-console` for runtime serving.
- Logging is file-oriented and centralized per subsystem under the user log directory.
