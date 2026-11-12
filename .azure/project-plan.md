**Status**: Approved
**Created**: 2026-11-17
**Mode**: Manual

## 1. Project Overview

**Project**: LISA Local Assistant

**Goal**: Evolve the existing Windows-local LISA application into an original companion/chat experience with local AI chat, Skills/Tools, Thai voice input and output, memory, and quick actions. Retain the current read-only system-health dashboard without expanding its monitoring scope.

**Inspiration and originality**: OpenClaw's published product overview describes a self-hosted assistant organized around chat, sessions, skills/tools, model integration, and a control UI. This plan uses those broad functional ideas only. It does not reuse OpenClaw source, branding, assets, copy, or exact interface.

**User boundaries**:
- Read-only by default.
- Before any file or settings change, or opening/closing an application, show the exact proposed action and require an explicit, per-action approval.
- No arbitrary terminal execution or unrestricted file access.
- No gateway, external messaging channels, notifications, or new system-monitor features.
- No sign-in.

## 2. Requirements Summary

- **Target**: Windows-local, single-user assistant.
- **Frontend**: Existing Vanilla HTML/CSS/JavaScript.
- **Backend**: Existing Python + FastAPI service, bound to loopback only.
- **AI chat**: Local application and local-first model connection. Use a configured local model endpoint; do not silently send prompts to a remote provider or fall back to one. If no local model is configured, show setup guidance.
- **Voice**: Thai speech recognition and speech playback, with text chat as an accessible fallback. Explain that recognition availability and processing location depend on the installed browser/runtime; do not save audio.
- **Skills/Tools**: Discoverable skills and a small, reviewed allowlist of tools. Read-only tools need no action approval; every mutating tool must pass through the same explicit approval gate.
- **Memory**: User-directed local memory, with review, search, correction, and deletion controls. Do not infer or save memories automatically.
- **Quick actions**: Shortcuts to chat, skills, memory, and existing health dashboard. A shortcut that changes system state must display and confirm its exact action.
- **Persistence**: Local SQLite for user-approved memories and assistant configuration. Do not persist chat transcripts by default; retain at most 10 recent chat messages in browser memory for the current page session only.
- **Existing behavior**: Keep the current system-health dashboard and its read-only presentation. Do not broaden collection or monitoring.
- **Out of scope**: OpenClaw gateway, third-party channels, remote access, notifications, scheduled automation, multi-agent routing, arbitrary shell, unrestricted file operations, and expansion of system monitoring.

## 3. Services & Architecture

### Frontend — `frontend`

- JavaScript, Vanilla HTML/CSS/JavaScript, served by the existing FastAPI application.
- Presents a chat-first but original LISA interface; integrates Skills/Tools, memory, Thai voice controls, quick actions, and a confirmation dialog.
- Uses the existing health dashboard without duplicating it or adding monitoring features.

### Local Assistant API — `backend`

- Python with the existing FastAPI service.
- Owns chat/provider configuration, SQLite persistence, skill/tool registry, approval validation, and local API routes.
- Connects only to a user-configured local model endpoint in the initial scope; no remote-provider fallback.
- All computer actions are validated and executed server-side through a finite allowlist; the model cannot directly execute code or commands.

### Request flow

Browser UI → loopback FastAPI → local model adapter and/or reviewed skill → policy check → user approval for a mutation → narrowly scoped action → result returned to UI.

## 4. Data Stores

### SQLite — local app data

- Store explicit user memories and the minimum settings needed for local model configuration and shortcut preferences.
- Keep the database under the current Windows user's local application-data directory, not in the repository.
- Do not store chat transcripts or microphone audio by default.
- Memory creation, edits, and deletion are visible user actions and require approval before being committed. Provide a way to inspect and clear saved memories.
- Avoid storing API secrets in SQLite; this plan does not require remote provider credentials.
- No Azure datastore or cloud persistence.

## 5. API & Tool Contracts

Preserve the existing `/api/v1` prefix and status endpoint where practical. Define request/response models and validate inputs; do not expose a generic command or file-operation endpoint.

- `GET /api/v1/status`: local service status only.
- `POST /api/v1/assistant`: chat with the configured local model; accept bounded text and return a response without executing model-suggested actions.
- `GET /api/v1/skills`: list reviewed, installed skills and their declared permissions.
- `GET /api/v1/memory` and `POST /api/v1/memory/search`: review and search local memories.
- `POST /api/v1/actions/preview`: validate an allowlisted action and return a human-readable description of its exact effect; does not execute it.
- `POST /api/v1/actions/approve` and `POST /api/v1/actions/execute`: bind approval to one previewed action, its parameters, and a short expiry; reject changed, reused, expired, or unapproved requests.

**Action allowlist**: Begin with read-only operations. App open/close and specific settings changes may be available only as individually previewed and explicitly approved actions. No arbitrary process termination, free-form settings URI, shell, PowerShell, or file-path tool. Log action type, approval outcome, and result without logging secrets or full chat content.

## 6. Design System & UI

**Component Library**: Existing Vanilla CSS; no additional component library.

**Visual direction**: Original, calm, accessible desktop workspace that belongs to LISA; do not imitate OpenClaw's exact layout, symbols, colors, language, or branding. Retain existing LISA identity and the separate health dashboard.

**Primary experience**: A readable conversation view with a clear message composer, Thai voice controls, and a compact quick-action area. Dedicated navigation exposes Skills/Tools and Memory. A distinct confirmation dialog displays the requested operation, target, and effect before any mutation. The dialog offers explicit approve and cancel choices; cancellation is the safe default.

**Interaction and accessibility**:
- Make text chat usable when speech recognition or a Thai speech voice is unavailable.
- Show microphone listening state, permission/error feedback, and a clear stop control.
- Use keyboard-accessible controls, visible focus, semantic labels, and responsive layouts.
- Keep action previews distinct from assistant replies so suggestions cannot be mistaken for completed actions.
- Do not show a false success state until the backend reports an approved action completed.

## 7. Security, Privacy & Safety

- Bind the API to `127.0.0.1`; do not listen on LAN interfaces or add remote access.
- Restrict browser/API origins to the local app origin; do not retain permissive wildcard CORS.
- Treat model output, user prompts, and skill content as untrusted input. Enforce all permissions in backend code, not in prompts or UI alone.
- Require a fresh, explicit, per-action approval for writes, settings changes, or app open/close actions. Approval must describe the exact target and operation and must not authorize later or modified actions.
- Keep arbitrary command execution and unrestricted file operations unavailable.
- Make memory opt-in by explicit user action; provide inspect, edit, and delete flows; do not silently retain conversation context as permanent memory.
- Do not store audio. Keep chat transient by default. Minimize logs and exclude secrets.
- Preserve the existing read-only system-health experience; do not add monitoring collection as part of this project.

## 8. Implementation & Verification

1. Inspect and reuse the current FastAPI, assistant, frontend, and system-health components; avoid replacing unrelated features.
2. Add the local model adapter/configuration path and safe failure behavior when no local model is configured.
3. Implement local SQLite memory APIs and user-controlled memory workflows.
4. Add a reviewed skill/tool registry and backend-enforced read-only defaults and approval flow.
5. Connect the original chat-first UI, Thai voice controls, skills, memory, and quick actions to the API.
6. Verify existing system-health behavior remains read-only and unchanged.

**Acceptance checks**:
- The app runs locally and chat does not call a remote provider or silently fall back to one.
- Missing local model configuration yields setup guidance without exposing secrets.
- Thai voice controls work when supported and degrade to text input/output when unavailable.
- Skills are discoverable; read-only tools cannot mutate the PC.
- File/settings/app actions cannot execute without a fresh approval for the exact preview; cancel, expiry, parameter changes, and replay are rejected.
- No generic shell, arbitrary file path, or unrestricted process-control route is exposed.
- Memories are only written after an explicit user action and approval, remain local, can be reviewed and deleted, and chat/audio are not silently persisted.
- The existing health dashboard continues to function without added monitoring scope.

## 9. Research References

- OpenClaw, official product overview: https://docs.openclaw.ai/ — describes its self-hosted assistant, chat/control UI, skills, tools, model integrations, and gateway. Used only to identify high-level capability categories.
- OpenClaw, official skills documentation: https://docs.openclaw.ai/tools/skills — reference for the general concept of discoverable, reusable skills; no source or interface copied.
- OpenClaw, official security documentation: https://docs.openclaw.ai/gateway/security — reference for treating integrations and tool execution as security-sensitive; this plan instead keeps LISA local-only and approval-gated.
- Existing LISA repository `README.md`, `maichel/backend/main.py`, `maichel/backend/assistant_core.py`, `maichel/index.html`, and `maichel/app.js` — inspected for the current Vanilla JS + FastAPI/Python stack, chat/provider behavior, Thai voice support, memory behavior, control routes, and existing system-health dashboard.
