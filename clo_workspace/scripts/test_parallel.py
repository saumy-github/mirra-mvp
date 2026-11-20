"""Run the same commands on every live CLO session at once and time them.

    python clo_workspace/scripts/test_parallel.py [--out-dir DIR]

Sessions come from the plugin's registry (clo_workspace/logs/instances). For
each session it POSTs /save-project and /export (glb) concurrently with the
other sessions, waits for each command's own completion event, and checks that
every event carries that session's pid (no cross-talk). Writes only to --out-dir.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clo_events import EventClient  # noqa: E402
from clo_pool import discover  # noqa: E402


def run_session(info: dict, out_dir: Path, results: dict) -> None:
    client = EventClient(info["base_url"])
    port = info["port"]
    rec = {"pid": info["pid"], "steps": []}
    results[port] = rec
    steps = [
        ("save-project", "/save-project", {"path": (out_dir / f"p{port}.zprj").as_posix(), "thumbnail": False}),
        ("export-glb", "/export", {"path": (out_dir / f"p{port}.glb").as_posix(), "format": "glb"}),
    ]
    for name, path, payload in steps:
        t0 = time.monotonic()
        try:
            r = client.post_and_wait(path, payload, timeout=180)
            ev = r["event"]
            rec["steps"].append({
                "step": name, "wall_s": round(time.monotonic() - t0, 3),
                "plugin_ms": ev.get("elapsed_ms"), "success": ev.get("success"),
                "event_pid": ev.get("pid"), "message": ev.get("message", "")[:80],
            })
        except Exception as exc:  # noqa: BLE001
            rec["steps"].append({"step": name, "error": str(exc)})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else Path(tempfile.mkdtemp(prefix="clo_parallel_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    sessions = discover()
    print(f"{len(sessions)} live session(s): " + ", ".join(f"pid {s['pid']}:{s['port']}" for s in sessions))
    if len(sessions) < 2:
        print("need at least 2 sessions")
        return 1

    results: dict = {}
    t0 = time.monotonic()
    threads = [threading.Thread(target=run_session, args=(s, out_dir, results)) for s in sessions]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = time.monotonic() - t0

    ok = True
    for port, rec in sorted(results.items()):
        for st in rec["steps"]:
            bad = "error" in st or st.get("event_pid") != rec["pid"]
            ok = ok and not bad
            print(f"port {port} pid {rec['pid']}: {st}" + ("   <-- PROBLEM" if bad else ""))
    seq = sum((st.get("wall_s") or 0) for rec in results.values() for st in rec["steps"])
    print(f"concurrent wall {total:.2f}s vs summed per-step {seq:.2f}s; output dir {out_dir}")
    print("PASS: events matched their own session" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
