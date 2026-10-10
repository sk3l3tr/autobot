# Workflow

## Development Method
- Use SDD first: define or refine the spec before implementation so each change has a clear goal, constraints, acceptance criteria, and interface impact.
- After the spec is stable, execute the work in TDD order whenever the change is testable: RED -> GREEN -> REFACTOR.
- Prefer small vertical slices that keep the desktop app, backend API, scheduler, and CLI aligned around the same YAML-backed data model.
- When full automation is not practical because of GUI, multiprocessing, or packaging constraints, still keep the SDD artifact explicit and add the smallest useful automated check plus a written manual verification step.

## SDD Rules
- Start each non-trivial change by writing down the behavior to add or change, success criteria, in-scope boundaries, and assumptions.
- Make the spec decision-complete before coding: input shape, output or side effects, failure handling, persistence impact, and user-visible behavior should be explicit.
- Update the relevant `bitacora` docs when the spec changes product behavior, technical rules, workflow expectations, or UX conventions.
- Treat tracks as the execution wrapper for the spec: the track should show the goal, tasks, decisions, and latest verification state.

## TDD Rules
- Default sequence: spec -> failing test or failing check -> minimal implementation -> refactor -> verification log.
- Add tests as close as possible to the changed behavior. For CLI or service glue, prefer narrow command- or module-level tests before broader end-to-end checks.
- If a change cannot be covered well with an automated test, document why and record a deterministic manual test procedure in the track log or handoff.
- Every completed slice should leave behind either an automated regression check or an explicit note explaining the current gap.

## Implementation Rules
- Initialize user data with `initialize_user_environment()` before operating on config, jobs, or robots from CLI and app entrypoints.
- Reuse shared helpers for cross-entrypoint behavior when the same action exists in CLI, backend, and desktop flows.
- Keep robot and schedule persistence in YAML files with stable key ordering and readable block formatting.
- Treat process startup and shutdown carefully: the product relies on multiprocessing plus child processes for backend, kiosk, scheduler, socket server, recorder, and webhook agent.
- Avoid jumping straight to cross-process or UI integration work if a smaller spec-validated unit can be implemented and checked first.

## Non-negotiable Session Rules
- Always read `bitacora/index.md` at the beginning of every session.
- Always read the root bitacora docs and active tracks before implementation.
- Always anchor non-trivial work in an explicit spec or track update before editing code.
- Always update `bitacora/tracks/tracks.md` after meaningful implementation changes.
- Always compact completed tracks with the `bitacora compact --track-id <id> --complete` CLI; never compact them manually.
- Always write handoff updates before ending a session.

## Quality Gates
- SDD gate: the change has a clear behavior statement, acceptance criteria, and known assumptions.
- TDD gate: there is a failing test/check first whenever the behavior is reasonably automatable.
- Implementation gate: code changes are the minimum needed to satisfy the spec.
- Verification gate: the exact commands run and their results are written in the handoff or track log.
- Memory gate: `bitacora/tracks/tracks.md` and the touched track files reflect the latest reality before the session ends.

## Handoff Checklist
- What changed
- Spec summary or behavior contract
- Tests run (exact commands + result)
- Current TDD phase
- Blockers or assumptions
- Single best next action
- If a track was marked `completed`, confirm it was compacted through the `bitacora` CLI in the same session.
