---
track_id: TRACK-004
status: completed
priority: high
created_at: 2026-04-01T09:29:51Z
updated_at: 2026-04-01T13:38:12.094Z
completion: 100
compacted_at: 2026-04-01T13:38:12.094Z
history_path: bitacora/history/TRACK-004.md
---

# Overview
- Goal: Show live cursor coordinates in the recorder and support global `CTRL+C` / `CTRL+V` coordinate copy-paste across the main editor and nested modals.
- Scope:
- Full history: bitacora/history/TRACK-004.md

# Tasks
- No checklist tasks found.

# Decisions
- 2026-04-01T09:29:51Z | Coordinate copy/paste is recorder-local state and must not depend on system clipboard contents.
- 2026-04-01T09:40:42Z | If the selected item is not a `click`, pasting coordinates appends a new default `click` action instead of mutating unrelated action types.
- 2026-04-01T09:46:00.000Z | Completed tracks must always be compacted with the `bitacora` CLI in the same session; manual compaction is not allowed.

# Log
- 2026-04-01T13:38:12.094Z | compacted track and archived full history
