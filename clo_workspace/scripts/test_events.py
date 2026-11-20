"""Live check of the plugin's completion events against one running CLO session.

    python clo_workspace/scripts/test_events.py [--port 50505]

Safe commands only: POST /new-project (empties the scene) and reads. It
compares event-driven completion with the old polling loop and checks the
WebSocket stream receives the same command_done event.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clo_events import EventClient  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}".rstrip())
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=50505)
    args = ap.parse_args()
    c = EventClient(f"http://127.0.0.1:{args.port}")
    results = []

    health = c._get("/health")
    results.append(check("health reports has_events", health.get("has_events") is True,
                         f"port={health.get('port')} pid={health.get('pid')}"))
    if not health.get("has_events"):
        return 1

    # WebSocket listener started before the command so it sees the new events.
    ws_seen: list[dict] = []
    ws_ready = threading.Event()

    def ws_worker() -> None:
        try:
            for ev in c.ws_events(idle_timeout=30):
                ws_seen.append(ev)
                if ev.get("type") == "hello":
                    ws_ready.set()
                if ev.get("type") == "queue_idle":
                    return
        except Exception as exc:  # noqa: BLE001
            ws_seen.append({"type": "error", "message": str(exc)})
            ws_ready.set()

    t = threading.Thread(target=ws_worker, daemon=True)
    t.start()
    results.append(check("websocket hello received", ws_ready.wait(5) and ws_seen[:1] and ws_seen[0].get("type") == "hello"))

    # Event-driven: POST then wait for that exact command.
    t0 = time.monotonic()
    r = c.post_and_wait("/new-project", {}, timeout=60)
    event_wall = time.monotonic() - t0
    ev = r["event"]
    results.append(check("post_and_wait got command_done", ev.get("type") == "command_done" and ev.get("command") == "new-project",
                         f"id={r['command_id']} plugin_elapsed_ms={ev.get('elapsed_ms')} wall={event_wall:.3f}s"))
    results.append(check("command reported success", ev.get("success") is True, ev.get("message", "")))

    # WebSocket saw the same command and the idle event.
    t.join(10)
    types = [e.get("type") for e in ws_seen]
    results.append(check("websocket delivered command_done + queue_idle",
                         "command_done" in types and "queue_idle" in types, str(types)))

    # Polling baseline for comparison (old behaviour).
    t0 = time.monotonic()
    c._post("/new-project", {})
    while True:
        s = c._get("/status")
        if s.get("queue_size", 1) == 0 and not s.get("queue_processing", True):
            break
        time.sleep(0.3)
    poll_wall = time.monotonic() - t0
    print(f"[INFO] event wait {event_wall:.3f}s vs poll(0.3s) {poll_wall:.3f}s")

    # Idle wait with nothing queued must time out cleanly, not hang.
    try:
        c.wait_idle(timeout=1.5)
        results.append(check("wait_idle times out when nothing runs", False, "returned unexpectedly"))
    except TimeoutError:
        results.append(check("wait_idle times out when nothing runs", True))

    status = c._get("/status")
    results.append(check("status carries pid/port/event_seq", all(k in status for k in ("pid", "port", "event_seq")),
                         str({k: status.get(k) for k in ("pid", "port", "event_seq")})))
    ok = all(bool(x) for x in results)
    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
