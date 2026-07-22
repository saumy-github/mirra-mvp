# CLO Plugin API Call Structure — The 3 Types

Reference for `clo_workspace/windows/RestPlugin_windows.cpp` (Mac file follows the
same shape). Every REST endpoint the plugin exposes falls into exactly one of
three categories, based on **whether it touches a CLO SDK API, and if so,
whether the HTTP thread needs the result back before it can respond.**

This split exists because of one hard constraint: **all CLO SDK calls
(`PATTERN_API`, `IMPORT_API`, `EXPORT_API`, `UTILITY_API`, ...) must run on
CLO's main thread.** The REST server runs on its own background thread
(`StartRESTServer`, spawned via `std::thread` in `DoFunction`). The HTTP
thread can never call a CLO API directly — it has to hand the work to the
main thread and either wait or not wait.

---

## Type 1 — Async / Queued (fire-and-forget)

**Used for:** all mutating operations — import, arrange, simulate, export,
save, set-fabric, set-properties, create-seam, new-project.

**Flow:**
1. HTTP thread receives a `POST`, builds an `APICommand` with `isSync = false`
   (the default), pushes it onto `g_commandQueue` under `g_queueMutex`.
2. HTTP thread returns immediately — response is just `{"success": true,
   "message": "... queued", "queue_size": N}`. The command has **not run
   yet**.
3. On the main thread, `QueueDrainTimer` fires every 200 ms (registered once
   via `SetTimer` in `DoFunction`) and calls `ProcessCommandQueue()` if the
   queue is non-empty.
4. `ProcessCommandQueue()` drains the whole queue into a local `batch`,
   executes each command's CLO API call inside a `type == "..."` branch, and
   appends a `CommandResult{type, success, message}` to `g_lastResults`.
5. Caller polls `GET /status` afterward to see `last_results` and find out
   whether the queued command actually succeeded.

**Why this shape:** the caller doesn't need the result synchronously — these
are pipeline steps (import this file, run N simulation steps, export here)
where the orchestration script queues a batch and then polls.

**Example endpoints:** `/import-avatar`, `/import-avatar-avt`,
`/import-avatar-measurements`, `/avatar/set-properties`, `/import-pattern`,
`/create-seam`, `/simulate`, `/export`, `/save-project`,
`/export-avatar-avt`, `/new-project`, `/arrange-pattern`, `/set-fabric`.

**Code landmark:** `APICommand cmd; cmd.type = "...";` followed by
`std::lock_guard<std::mutex> lock(g_queueMutex); g_commandQueue.push(cmd);`
in the endpoint lambda — and a matching `else if (cmd.type == "...")` branch
inside `ProcessCommandQueue()` (`RestPlugin_windows.cpp:1071-1343`).

---

## Type 2 — Sync-Read (blocking via promise/future)

**Used for:** all read-only queries that need a CLO API call — pattern
counts, bounding boxes, arrangement slots, avatar state.

**Flow:**
1. HTTP thread calls `dispatchSyncRead(type, param3, param4)`
   (`RestPlugin_windows.cpp:218-242`).
2. That helper creates a `std::promise<json>` / `std::future<json>` pair,
   builds an `APICommand` with `isSync = true` and `syncPromise` set to the
   promise, pushes it to `g_commandQueue` — **same queue as Type 1**.
3. HTTP thread blocks on `future.wait_for(std::chrono::seconds(3))`.
4. Main thread's `ProcessCommandQueue()` reaches this command in its batch
   loop, runs the matching `read-...` branch, builds a `json syncResult`, and
   calls `cmd.syncPromise->set_value(syncResult)` — this unblocks the
   waiting future.
5. HTTP thread's `future.get()` returns, and the result is written straight
   into the HTTP response.
6. If the main thread doesn't drain the queue within 3 s (CLO busy/frozen),
   `dispatchSyncRead` gives up and returns a synthetic timeout payload
   instead of hanging the HTTP connection forever.

**Why this shape:** these are read endpoints — the caller needs the actual
data back in the same HTTP response, so the HTTP thread cannot return early
the way Type 1 does. The promise/future pair is what lets one thread push
work and another thread answer it without polling.

**Example endpoints:** `/avatars/state`, `/avatar/debug`,
`/avatar/native-debug`, `/patterns/count`, `/patterns/{i}`,
`/patterns/{i}/bbox`, `/patterns/{i}/input`, `/patterns/{i}/line-lengths`,
`/arrangement-list`, `/pattern-arrangements`, `/arrangement/debug`.

**Code landmark:** `json r = dispatchSyncRead("read-...", ...);` in the
endpoint lambda — and a matching `else if (cmd.type == "read-...")` branch
inside `ProcessCommandQueue()` (`RestPlugin_windows.cpp:1343-1614`) that
assigns into `json syncResult` (not `asyncResult`).

Inside each `read-...` branch, every individual CLO API call is wrapped in
its own `try { } catch (...) {}` (see `after-1-jun/plan-01.md` Execution
Notes — "8 of 11 sync handlers had bare CLO API calls"). This is specific to
Type 2: because the whole point is returning a real answer to a blocked HTTP
caller, a single bad CLO call must not prevent `syncResult` from being built
and the promise from being fulfilled.

---

## Type 3 — Direct (no queue, no CLO API call)

**Used for:** endpoints that only need plugin-internal state — build
metadata, mutex-protected debug globals, or the queue's own bookkeeping.

**Flow:**
1. HTTP thread handles the request **entirely on itself**. No `APICommand`
   is built, nothing is pushed to `g_commandQueue`, the main thread is never
   involved.
2. Data either comes from compile-time constants (`MIRRA_PLUGIN_VERSION`
   etc. in `/health`, `/capabilities`), or from a global that's protected by
   its own dedicated mutex and written by the main thread elsewhere
   (`g_importDebugMutex`, `g_avatarPropertyDebugMutex`, `g_resultsMutex`,
   `g_queueMutex`).
3. The handler takes the matching mutex, copies the struct/value out, builds
   the JSON response, and returns — all synchronously, no wait, no timeout
   logic needed because there's nothing to wait for.

**Why this is safe without going through the queue:** these handlers never
call a CLO SDK function. They only read plain data that some *other* command
handler already wrote while running on the main thread, guarded by a mutex
taken on both sides. Since no CLO API is invoked, the "must run on CLO's
main thread" constraint doesn't apply, so there's no need to marshal the
call through `g_commandQueue` at all.

**Example endpoints:** `/health`, `/capabilities`, `/debug/import-scales`,
`/avatar/property-debug`, `/status`, `/execute`.

**Code landmark:** no `dispatchSyncRead` call and no `g_commandQueue.push`
anywhere in the handler — just a `std::lock_guard<std::mutex> lock(...)`
around a global read, e.g. `/avatar/property-debug`
(`RestPlugin_windows.cpp:479-492`) and `/status`
(`RestPlugin_windows.cpp:996-1059`).

---

## Quick comparison

| | Type 1: Async/Queued | Type 2: Sync-Read | Type 3: Direct |
|---|---|---|---|
| HTTP method | `POST` | `GET` | `GET` |
| Touches CLO SDK API | Yes | Yes | No |
| Runs on main thread | Yes (via timer drain) | Yes (via timer drain) | No — runs on HTTP thread |
| Goes through `g_commandQueue` | Yes | Yes (`isSync=true`) | No |
| HTTP thread blocks | No — returns immediately | Yes — up to 3 s | No — answers immediately |
| Result delivery | Polled later via `/status` → `g_lastResults` | Returned in the same response via `std::promise`/`std::future` | Returned in the same response directly |
| Failure-to-respond risk | None — response sent before command runs | Timeout payload after 3 s if main thread is stalled | None — no main-thread dependency |
| `APICommand` field used | `isSync = false` (default) | `isSync = true` + `syncPromise` | `APICommand` not used at all |

---

## Why three types instead of one

A single blocking-everything design (`Type 2` for everything) would make
batch pipeline operations (import → arrange → simulate → export) painfully
slow, since each step would force the HTTP thread to sit idle for up to 3 s
waiting on the main thread's 200 ms timer cadence. A single fire-and-forget
design (`Type 1` for everything) would make reads useless, since the caller
would have no way to get an answer back in the same request. Type 3 exists
purely as an optimization: skip the queue entirely for anything that doesn't
need the main thread at all, so plugin status and debug info stay
instantaneous even while the queue is backed up.
