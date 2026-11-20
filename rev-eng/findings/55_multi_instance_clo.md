# 55 - Completion events and parallel CLO sessions

*Status: tested live on SDK 336 with two sessions; the plugin change is built and deployed, the Python wiring is in the two `wait_for_queue` clients.*
*Date: 2026-11-11*

## What was built (outside `rev-eng/`, by request)
- Plugin `clo_workspace/windows/RestPlugin_windows.cpp` (version string still 1.3.2; `/health` shows `has_events: true`):
  - Every command gets an id, returned as `X-Mirra-Command-Id`.
  - Events `command_done` (with the plugin's own `elapsed_ms`), `fabric_done`, `queue_idle`.
  - `GET /wait?id=N`, `GET /events?since=&timeout_ms=`, WebSocket `/ws?since=`.
  - `MIRRA_PLUGIN_PORT=<n>|auto` selects the port (default 50505); each session writes `clo_workspace/logs/instances/clo_<pid>.json`.
  - `/health` and `/status` carry `pid`, `port`; `/status` carries `event_seq`.
- Python: `clo_workspace/clo_events.py`, `clo_pool.py`, `scripts/test_events.py`, `scripts/test_parallel.py`; both `wait_for_queue` implementations wake on events and keep the old sleep as a fallback for plugins without `event_seq`.

## Observed
- `test_events.py` against one session: all checks passed (HTTP wait, WebSocket hello/command_done/queue_idle, timeout behaviour).
- Parallel: two sessions (ports 50505 and 50601) ran `save-project` and `export glb` at the same time; every event carried its own session's pid. Plugin-measured times for the avatar scene: save 2978 ms, GLB export 4015 ms. The empty-scene export failed as expected ("ExportGLB returned no files").
- Both pipeline clients, after the change: `simulate` plus wait returned in 0.03 to 0.16 s on both sessions.
- Several CLO windows can run at once (four were open, about 1.3 to 1.8 GB each).

## Operational facts
- Copying the plugin into `C:\Program Files\CLO Standalone OnlineAuth\plugins` needs an elevated shell; the running CLO windows did not lock the DLL.
- The plugin does not start by itself on launch, not even when CLO is started with a project file argument (no `EnsureServerStarted` trace line appeared). It starts from the Plugins menu entry "REST Server Execute" followed by OK on the info box; the box always says port 50505 regardless of `MIRRA_PLUGIN_PORT`.
- The environment variable is read by the plugin inside each CLO process, so a session must be launched with it set; sessions started without it all want 50505.
- `clo_pool.py` as written cannot start the plugin by itself; its health wait times out (and then terminates that session) until the menu click is automated.

## Open
- Concurrent sessions in production: the user checked and confirmed the licence allows it (2026-11-11); this test does not establish that.
- No separate version number was given to this plugin build; the vault copy `RestPlugin_v1.3.2.dll` was overwritten by it.

## Parallel avatar generation (worker, plugin and pipeline wired together)
*Date: 2026-11-11*

- Design: one worker process per CLO session. `worker/run_workers.py` starts N children of `worker/run_worker.py`, each with `CLO_BASE_URL` (its session's plugin port) and `WORKER_SLOT`. Both pipeline clients read `CLO_BASE_URL` when no URL is passed. `worker/slots.py` holds an OS file lock per session port, so a second worker on the same session exits, and waits for `/health` before taking jobs.
- Collisions removed: `reserve_run_number` and the upload version folder are claimed with `mkdir` (40 threads got 40 distinct numbers). Try-on renders take a cross-process lock because `clo_vto/output/` is one shared folder. Step 1 of the avatar pipeline now refuses to run when `/health` says `host_matches_sdk` is false.
- Live: two `run_avatar.py` runs at the same time (users par_a and par_b, sessions on 50601 and 50602) each passed all 12 steps, in 29 s and 27 s, with both runs overlapping step for step. Each session finished with exactly one avatar. The produced files had the same sizes in both runs (same measurements in, so expected). The test folders were deleted afterwards.
- Launcher smoke test: `run_workers.py --discover` found both sessions, started slot 0 and slot 1, each claimed its session and passed the health wait. They then stopped because Redis was not running on this machine, so no job was run through RQ; the RQ/Mongo path (`tasks.py`) is untested live.
