# Worker exits with "Redis connection timeout, quitting..."

Status: *diagnosed, fix not yet applied*
First observed: *2026-08-30, `worker/run_worker.py` on Windows*
**Affects:** the native CLO worker only. The Dockerized backend is unaffected.

---

## Symptom

The worker starts normally, runs for tens of minutes with no work to do, then exits
on its own. Nothing was killed and no job was running.

```
16:30:22 INFO  mirra.worker: Starting CLO worker: redis=redis://localhost:6379/0 queue='clo'
16:30:22 INFO  rq.worker: Worker 5241...: started with PID 20064, version 2.10.0
16:30:22 INFO  rq.worker: *** Listening on clo...
16:30:22 INFO  rq.worker: Worker 5241...: cleaning registries for queue: clo
16:43:52 INFO  rq.worker: Worker 5241...: cleaning registries for queue: clo
16:57:22 INFO  rq.worker: Worker 5241...: cleaning registries for queue: clo
17:10:52 INFO  rq.worker: Worker 5241...: cleaning registries for queue: clo
17:50:01 ERROR rq.worker: Worker 5241...: Redis connection timeout, quitting...
17:50:01 INFO  rq.worker: Worker 5241...: unsubscribing from channel rq:pubsub:5241...
```

Because the worker is gone, any avatar or VTO job enqueued afterwards sits in the
`clo` queue untouched. The backend still accepts the request and returns success,
so from the website the job simply never completes.

---

## Short version

The idle TCP connection from the worker to Redis is dropped inside Docker Desktop's
Windows port-forward. RQ blocks on that socket for 405 seconds at a time, so it does
not notice until its own 415-second socket timeout fires. RQ treats **any** socket
timeout as fatal and exits without retrying.

Redis itself is not involved. It never restarted and never closed the connection.

---

## Why RQ exits rather than reconnecting

`.venv/Lib/site-packages/rq/worker/base.py:645-647`:

```python
except redis.exceptions.TimeoutError:
    self.log.error('Worker %s: Redis connection timeout, quitting...', self.name)
    break
```

`break` leaves the work loop and the process ends. There is no retry, no backoff, and
no reconnect. This is RQ's design, not a bug in this repo, and it means **a single
transient network blip ends the worker permanently**.

---

## The timing, and why the log proves it

RQ's defaults, read from the installed package:

| Value | Computed | Source |
|---|---|---|
| `worker_ttl` | 420 s | `rq/defaults.py:32` |
| `dequeue_timeout` | `max(1, 420 - 15)` = **405 s** | `rq/worker/base.py:442-443` |
| `connection_timeout` (becomes `socket_timeout`) | `405 + 10` = **415 s** | `rq/worker/base.py:446-447` |
| maintenance interval | 600 s | `rq/defaults.py:66` |

So the worker spends its life inside a `BLPOP` that blocks for 405 seconds, on a
socket whose read timeout is 415 seconds.

The `cleaning registries` lines in the log land at **810-second intervals**
(16:30:22 → 16:43:52 → 16:57:22 → 17:10:52). That is exactly `2 x 405`: maintenance
becomes due every 600 s, but can only actually run when a dequeue cycle returns, so it
fires on every second cycle. The loop was behaving perfectly normally right up to the
end.

After 17:10:52 the next cycle never completed. The socket had been silently dropped,
the blocking read returned nothing, the 415-second timeout expired, and RQ quit.

---

## It is not Redis

Checked while the failure was still fresh:

| Check | Command | Result |
|---|---|---|
| Did Redis restart? | `docker compose exec redis redis-cli INFO server` | `uptime_in_seconds: 21983` (~6 h) — spans the entire worker lifetime |
| Does Redis close idle clients? | `docker compose exec redis redis-cli CONFIG GET timeout` | `0` — never |
| Server-side keepalive | `docker compose exec redis redis-cli CONFIG GET tcp-keepalive` | `300` — enabled |
| Container health | `docker compose ps redis` | `Up 6 hours` |

Redis was up and healthy throughout, and with `timeout 0` it does not disconnect idle
clients at all.

---

## Root cause

`localhost:6379` on the worker's machine is **not** Redis. It is Docker Desktop's NAT
port-forward into the Linux VM. That proxy reclaims TCP flows it considers idle, and
frequently does so without sending an RST — the client end never learns the socket is
dead and stays blocked in `recv()` until its own timeout.

A `BLPOP` idling for 405 seconds is close to a worst case for that proxy, and the
connection is built with no protection against it:

```python
conn = Redis.from_url(redis_url)   # worker/run_worker.py
```

No `socket_keepalive`, so the OS sends nothing to keep the flow alive. No
`health_check_interval`, so redis-py never probes it.

This is long-standing and predates the 2026-08-30 config refactor, which only changed
where the URL string comes from (`worker/.env` directly, instead of via the backend's
`Settings`). The bare connection was the same before.

The same failure mode is expected after the host sleeps or hibernates, and after
Docker Desktop restarts.

---

## Fixes, in the order worth applying

### 1. Shorten the blocking window (highest value)

Attacks the idle duration itself, which is the actual trigger.

`worker_ttl` is a **constructor** argument, not a `work()` argument
(`Worker.__init__(..., worker_ttl=None)`; `work()` accepts only `burst`,
`logging_level`, `date_format`, `log_format`, `max_jobs`, `max_idle_time`,
`with_scheduler`, `dequeue_strategy`):

```python
worker = SimpleWorker([queue], connection=conn, worker_ttl=120)
worker.work(with_scheduler=False)   # 105 s BLPOP instead of 405 s
```

Cost: slightly more Redis chatter. Nothing else changes — jobs are still delivered
instantly by the blocking pop, not by polling.

### 2. Add keepalive and health checks

```python
conn = Redis.from_url(
    redis_url,
    socket_keepalive=True,
    health_check_interval=30,
)
```

One caveat worth understanding: `health_check_interval` only PINGs a connection that
is idle **between** commands. It cannot help while the socket is blocked inside a
`BLPOP`, which is where this failure occurs. It protects the heartbeat and maintenance
calls. `socket_keepalive` is the part that keeps the NAT from seeing the blocking read
as idle — but Windows defaults to a 2-hour keepalive idle time, which is why fix 1
does most of the real work here.

### 3. Supervise the work loop

Since RQ treats the timeout as fatal by design, the only way to make the worker
genuinely unattended is to restart it:

```python
while True:
    worker = SimpleWorker([queue], connection=conn, worker_ttl=120)
    try:
        worker.work(with_scheduler=False)
    except redis.exceptions.ConnectionError:
        logger.warning("Redis connection lost; reconnecting in 5s")
        time.sleep(5)
        continue
    # work() returned. That is EITHER a clean shutdown (Ctrl-C / SIGTERM) OR the
    # fatal-timeout path at base.py:645, which logs and `break`s without raising.
    # The two are indistinguishable from the return value alone, so check whether
    # a stop was actually requested before deciding to exit.
    if worker._stop_requested:
        break
    logger.warning("Worker loop ended without a stop request; restarting in 5s")
    time.sleep(5)
```

The important subtlety: RQ **catches** `TimeoutError` internally and `break`s out of
the loop, so `work()` returns normally rather than raising. A `try/except` around it
will therefore never fire for this specific failure — the restart decision has to be
made on the return path, which is what the `_stop_requested` check above is for.
Verify that attribute against the installed RQ version before relying on it; it is
private API and has changed name across releases.

This also covers laptop sleep and Docker Desktop restarts.

**Applying 1 and 2 together is the small, low-risk change. 3 is only needed if the
worker must survive unattended overnight.**

---

## Diagnosing a recurrence

Distinguish "the network dropped" from "Redis actually went away":

```bash
# Did Redis restart? Compare uptime against how long the worker had been running.
docker compose exec redis redis-cli INFO server | grep uptime_in_seconds

# Is Redis closing idle clients? Should be 0.
docker compose exec redis redis-cli CONFIG GET timeout

# Registered workers, and whether they are actually alive.
docker compose exec redis redis-cli --raw SMEMBERS rq:workers
docker compose exec redis redis-cli --raw HMGET rq:worker:<id> state death
```

A worker killed this way leaves a **stale registration** in `rq:workers` with no
`death` timestamp, so it still looks `idle` even though the process is gone. Do not
read that as a live worker. The next worker to start clears it — that is what the
`cleaning registries for queue: clo` line does.

---

## References

- `worker/run_worker.py` — the connection and work loop
- `rq/worker/base.py:645-647` — the fatal `TimeoutError` handler
- `rq/worker/base.py:442-447` — `dequeue_timeout` and `connection_timeout`
- `rq/defaults.py:32,66` — `DEFAULT_WORKER_TTL`, `DEFAULT_MAINTENANCE_TASK_INTERVAL`
- `docker-compose.yml` — the `redis` service and its `6379:6379` port mapping
- `worker/README.md` — worker setup, and why `SimpleWorker` is required on Windows

**Environment when observed:** rq 2.10.0, redis-py 8.1.0, Redis server 7.4.10
(`redis:7-alpine`), Python 3.12.10, Windows 11, Docker Desktop.
