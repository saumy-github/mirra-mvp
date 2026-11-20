# 52 - REA binding and live 336 preflight

*Status: complete. REA target identity and live plugin read-only preflight; no mutating CLO command was sent.*
*Date: 2026-11-10*

## REA target identity

REA successfully opened the installed executable:

- Path: `C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe`
- Format: PE executable
- Architecture: x86-64
- SHA-256: `cb649bd6eeb58fb2aa3a679df8e3359ad1e67b583f79261481d8f2d4aeba3b47`

The target was bound by REA, but `binary_overview` could not run because no
deep Windows PE provider is configured:

- Ghidra: not configured; `GHIDRA_INSTALL_DIR` is unset and the configured Java
  executable is missing.
- IDA: not configured.
- Kuna: not configured and the PE target is not admitted by the available
  provider.
- Hopper: unsupported on Windows.

This pass therefore adds target identity evidence only. It does not claim new
function, pseudocode, or call-graph evidence from REA.

## Live plugin preflight

Read-only requests were sent to `http://127.0.0.1:50505` while CLO was running.

`GET /health`:

- status: `ok`
- host app: `2026.1.336`
- SDK: `2026.1.336`
- `host_matches_sdk`: `true`
- plugin: `CLO REST Automation` 1.3.2
- plugin build: `2026-10-29T09:36:26Z`
- platform sync state: `in_sync`

`GET /status`:

- queue size: `0`
- queue processing: `false`
- last results: empty

`GET /avatars/state`:

- avatar count: `0`

`GET /capabilities` confirms the installed plugin exposes native avatar import,
avatar property debug/set, fabric color/graphic/texture, pattern arrangement,
pattern bounding-box, and scene geometry probes. Avatar state read-back and
avatar AVT export are reported as unavailable.

The modal watchdog list-only pass found the CLO process and 99 windows, with no
dialogs and no disabled main window. Its output was written under
`experiments/out/`.

## Interpretation

Observed:

1. The currently running CLO process is compatible with the installed SDK 336
   plugin.
2. The REST server is accepting requests and the command queue is idle.
3. No avatar or modal dialog is present at the start of a supervised test.

Not established:

1. `import-avatar-avt` stability on the 336 plugin.
2. `clear-avatars` behavior on the 336 plugin.
3. Any mutating API behavior.
4. Native implementation details beyond the prior static analysis.

The next controlled live operation should be the smallest known-good single
avatar import, with the modal watchdog available and immediate post-command
health/status checks.
