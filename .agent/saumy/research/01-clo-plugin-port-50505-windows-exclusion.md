# 01 — CLO plugin port 50505 silently unreachable (Windows dynamic port exclusion)

Status: *diagnosed and worked around live, not fixed at the code/config level*
Observed: *2026-09-12*

## Symptom

CLO3D's RestPlugin shows its own dialog confirming `REST server is running on
http://localhost:50505`, and the plugin's own heartbeat log
(`clo_workspace/logs/plugin_crash_trace.log`) says `serverRunning=true`
continuously. But every external call — the Python pipeline's health check,
`curl`, PowerShell's `Invoke-WebRequest` — fails identically:

```
HTTPConnectionPool(host='localhost', port=50505): Max retries exceeded with
url: /health (Caused by NewConnectionError("... [WinError 10061] No
connection could be made because the target machine actively refused it"))
```

`netstat -ano | findstr 50505` showed **nothing at all** — not even a stale
process holding the port. No exception, no CLO crash, no visible error
anywhere in the plugin or the pipeline.

## What it was not

Ruled out, in order, before finding the real cause:

- **Not the `worker/run_worker.py` Redis timeout fix** — that process never
  talks to CLO at all; it only talks to Redis. Reverted anyway at Saumy's
  request, but confirmed unrelated.
- **Not a stale/zombie CLO process squatting on the port** — `netstat` showed
  literally nothing bound to 50505, which a squatting process would have
  shown as `LISTENING` under a different PID.
- **Not the plugin/SDK version skew** (CLO app 2026.1.224 vs. the plugin's
  SDK v10.0.3 build target) — this was the leading theory for a while and
  is a real, separately-documented risk, but it was ruled out here: added
  `TraceLog` calls at plugin entry, before/after `RunCapabilityProbesOnce()`,
  and around `svr.listen()`. The trace showed the thread starting cleanly,
  no exception, no SEH crash — `svr.listen("127.0.0.1", 50505)` simply
  returned `false` immediately and kept retrying every 2 seconds forever,
  exactly per its existing retry loop in `RestPlugin_windows.cpp`.
- **Not a CLO or Windows *update*** — no version changed between "it worked"
  and "it didn't" other than the plugin rebuild itself, and the rebuild was
  proven clean by the trace log above.

## Root cause

`WSAGetLastError()` logged immediately after the failing `listen()` call
returned `183` (`ERROR_ALREADY_EXISTS`) on every retry after the first.
Checked Windows' own TCP port exclusion table directly:

```
netsh interface ipv4 show excludedportrange protocol=tcp

Start Port    End Port
50000         50059     *
50428         50527
50528         50627
50628         50727
50728         50827
50840         50939
```

**Port 50505 fell inside the excluded range 50428–50527.** When a port sits
in one of these ranges, Windows refuses `bind()` for *any* process — the
socket is never created, which is exactly why `netstat` showed nothing.

These exclusion ranges are carved out by **Hyper-V's networking for Docker
Desktop's WSL2 backend**, and get re-derived whenever that networking stack
restarts (Docker Desktop restart, WSL shutdown, sleep/wake). Docker Desktop
was restarted several times during this same session (plugin rebuilds,
earlier Redis debugging), and one of those restarts happened to land a fresh
exclusion range on top of 50505.

## The fix that worked (session-only, not persisted)

From an Administrator terminal:

```
net stop winnat
net start winnat
```

This regenerates Windows' NAT/port-exclusion state and released 50505.
Confirmed immediately after: `netstat -ano | findstr 50505` showed
`127.0.0.1:50505 ... LISTENING` under CLO's real PID, and the pipeline's
health check succeeded.

**This is a Windows networking state fix, not a permanent one.** The
exclusion range can land on 50505 again after any future Docker
Desktop/WSL2 networking restart. Nothing has been done to prevent
recurrence — see Open Questions.

## What was kept from this investigation

Per instruction, the diagnostic `TraceLog` calls added to
`clo_workspace/windows/RestPlugin_windows.cpp` during this investigation
were **kept in the rebuilt plugin** (not reverted):

- `StartRESTServer: thread entered`
- `StartRESTServer: Server object constructed`
- `StartRESTServer: about to call svr.listen(127.0.0.1, 50505)`
- `StartRESTServer: svr.listen() returned false, WSAGetLastError()=<code>`
  / `svr.listen() returned true`
- `EnsureServerStarted: about to call RunCapabilityProbesOnce()` /
  `RunCapabilityProbesOnce() returned, spawning server thread`
- On exception: `StartRESTServer: caught std::exception - <what>` /
  `caught unknown exception (...)`

If this recurs, `clo_workspace/logs/plugin_crash_trace.log` should now show
the `WSAGetLastError()` code within seconds, rather than requiring another
multi-hour investigation to re-derive it.

## Open questions / not solved

- **No prevention has been implemented.** The port can collide again after
  any future Docker Desktop/WSL2 networking restart. Nothing here changes
  that.
- **Not fixed:** the plugin's own `g_serverRunning` flag is set to `true`
  optimistically in `EnsureServerStarted()` before the server thread even
  runs, and is never reset to `false` when `svr.listen()` fails (only an
  actual C++ exception resets it). This means CLO's own dialog and heartbeat
  log will keep falsely claiming "running" the next time this happens too —
  the only reason this was caught quickly was the new trace logging, not
  because the plugin's own state reporting is correct.
- **Possible longer-term fix, not attempted:** move the plugin off port
  50505 onto something below 49152 (outside the range Windows/Hyper-V treat
  as dynamic/ephemeral), which would make this specific collision far less
  likely. This touches `RestPlugin_windows.cpp`'s `svr.listen()` call, the
  Python client's default `base_url` in `clo_vto/native_vto/client.py` (and
  the Step 1 equivalent), and any docs/env defaults hardcoding 50505 —
  scoped as a separate task, not started.
- **Not verified:** whether this same port-exclusion collision can also
  affect Redis (`localhost:6379`, also proxied through the same Docker
  Desktop NAT) or any other fixed port this project depends on. Worth a
  quick `netsh` check next time Redis/worker connectivity acts up.
