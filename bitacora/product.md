# Product

## Name

Autobot Desktop

## One-liner

Desktop automation tooling for defining, scheduling, and running YAML-based robot workflows through a local web console and terminal CLI.

## Problem

Operators need a lightweight way to automate repetitive desktop actions and trigger them manually, on schedules, or from external webhook-driven systems without depending on a cloud control plane.

## Goals

- Let users create and edit robot workflows as YAML-backed action sequences using the built-in recorder GUI.
- Let users model repeated behavior in robots through loop actions that run a fixed number of times or until a manual stop request.
- Provide multiple execution entrypoints for the same automation model: local web UI, local CLI, schedules, http, socket and webhook-triggered commands.
- Package the product as a desktop-friendly distribution that runs local backend services, UI, and helper processes together.
- Persist user data outside the application bundle so robots, config, jobs, and logs survive upgrades and reinstallations.

## Non-goals

- It is not a cloud-hosted orchestration platform or multi-user SaaS.
- It does not provide advanced robot authoring abstractions beyond the current YAML action list and recorder flow.
- It is not a general-purpose browser automation framework or an RPA platform with remote agents.

## Success Criteria

- A user can create a robot, save it as YAML, and execute it from the UI or CLI without editing application internals.
- A user can configure looped robot steps from the Tkinter recorder, save them in YAML, and stop indefinite loops from the main UI without manual file edits.
- Scheduled jobs persisted in `jobs.yaml` are reloaded by the background scheduler and trigger robot execution through the local socket bridge.
- The packaged application boots its backend, kiosk, socket server, scheduler, and optional webhook agent with user data stored under the platform-specific application data directory.
- CLI entrypoints `autobot list`, `autobot run <robot>`, and `autobot write <robot>` work against the same persistent robot catalog.
