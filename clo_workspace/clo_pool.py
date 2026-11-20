"""Run several CLO sessions side by side, one REST plugin port each.

Each CLO process gets its own `MIRRA_PLUGIN_PORT` (the plugin reads it; default
50505), starts CLO, waits for /health, and exposes `acquire()` / `release()` so
a worker can lease one session per job (CLO itself is single-threaded, so one
job per session at a time).

    python clo_workspace/clo_pool.py --count 2 --base-port 50601   # start, test, keep running
    python clo_workspace/clo_pool.py --discover                    # list live sessions

Stdlib only. CLO licence/seat limits and RAM are the real caps; see
`rev-eng/findings/55_multi_instance_clo.md` for what was measured.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CLO_EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
REGISTRY_DIR = Path(__file__).resolve().parent / "logs" / "instances"


def _health(base_url: str, timeout: float = 2.0) -> dict | None:
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def discover(registry_dir: Path = REGISTRY_DIR) -> list[dict]:
    """Live sessions from the plugin's registry files (dead pids are skipped)."""
    out = []
    for path in sorted(registry_dir.glob("clo_*.json")):
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        base = f"http://127.0.0.1:{info.get('port')}"
        health = _health(base)
        if health and health.get("pid") == info.get("pid"):
            out.append({**info, "base_url": base})
    return out


@dataclass
class CloSession:
    index: int
    port: int
    proc: subprocess.Popen | None = None
    pid: int | None = None
    started_at: float = field(default_factory=time.time)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


class CloPool:
    def __init__(self, count: int, base_port: int = 50601, clo_exe: str = DEFAULT_CLO_EXE,
                 stagger_s: float = 15.0, ready_timeout_s: float = 240.0) -> None:
        self.count = count
        self.base_port = base_port
        self.clo_exe = clo_exe
        self.stagger_s = stagger_s
        self.ready_timeout_s = ready_timeout_s
        self.sessions: list[CloSession] = []
        self._free: "queue.Queue[CloSession]" = queue.Queue()

    def start(self) -> list[CloSession]:
        for i in range(self.count):
            session = self._launch(i)
            self.sessions.append(session)
            # CLO instances contend for startup resources (licence check, GPU
            # context); starting them one after another is far more reliable
            # than launching all at once.
            self._wait_ready(session)
            self._free.put(session)
            if i + 1 < self.count:
                time.sleep(self.stagger_s)
        return self.sessions

    def _launch(self, index: int) -> CloSession:
        port = self.base_port + index
        env = dict(os.environ)
        env["MIRRA_PLUGIN_PORT"] = str(port)
        proc = subprocess.Popen([self.clo_exe], env=env, cwd=str(Path(self.clo_exe).parent))
        return CloSession(index=index, port=port, proc=proc, pid=proc.pid)

    def _wait_ready(self, session: CloSession) -> None:
        deadline = time.monotonic() + self.ready_timeout_s
        while time.monotonic() < deadline:
            if session.proc is not None and session.proc.poll() is not None:
                raise RuntimeError(f"CLO session {session.index} exited early (code {session.proc.returncode})")
            h = _health(session.base_url)
            if h and h.get("status") == "ok" and h.get("port") == session.port:
                return
            time.sleep(1.0)
        raise TimeoutError(f"CLO session {session.index} (port {session.port}) not ready in {self.ready_timeout_s}s")

    def acquire(self, timeout: float | None = None) -> CloSession:
        return self._free.get(timeout=timeout)

    def release(self, session: CloSession) -> None:
        self._free.put(session)

    def stop(self) -> None:
        for s in self.sessions:
            if s.proc is not None and s.proc.poll() is None:
                s.proc.terminate()
        self.sessions.clear()


def main() -> int:
    ap = argparse.ArgumentParser(description="Start and inspect parallel CLO sessions")
    ap.add_argument("--count", type=int, default=0, help="sessions to start")
    ap.add_argument("--base-port", type=int, default=50601)
    ap.add_argument("--clo-exe", default=DEFAULT_CLO_EXE)
    ap.add_argument("--discover", action="store_true", help="list live sessions and exit")
    args = ap.parse_args()

    if args.discover or args.count == 0:
        print(json.dumps(discover(), indent=2))
        return 0

    pool = CloPool(args.count, args.base_port, args.clo_exe)
    try:
        for s in pool.start():
            print(f"session {s.index}: pid={s.pid} {s.base_url}", flush=True)
        print("running; Ctrl+C stops the sessions started here", flush=True)
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        return 0
    finally:
        pool.stop()


if __name__ == "__main__":
    sys.exit(main())
