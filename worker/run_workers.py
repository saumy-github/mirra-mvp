"""Start one CLO worker per CLO session, so avatar jobs run in parallel.

CLO is single-threaded, so parallelism means several CLO sessions, each with
its own plugin port, each served by its own worker process. Start the CLO
sessions first (set MIRRA_PLUGIN_PORT before launching each CLO, then click
Plugins > REST Server Execute once per session), then:

    python worker/run_workers.py --discover            # one worker per live session
    python worker/run_workers.py --ports 50601,50602   # explicit ports
    python worker/run_workers.py --count 3 --base-port 50601

Each child is `worker/run_worker.py` with CLO_BASE_URL / WORKER_SLOT set. A
child that dies is restarted after a short delay; Ctrl+C stops them all.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "clo_workspace"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mirra.workers")

RESTART_DELAY_SECONDS = 5.0
EXIT_CONFIG_ERROR = 2  # run_worker.py: missing REDIS_URL; restarting cannot help


def _ports_from_args(args: argparse.Namespace) -> list[int]:
    if args.ports:
        return [int(p) for p in args.ports.split(",") if p.strip()]
    if args.count:
        return [args.base_port + i for i in range(args.count)]
    from clo_pool import discover

    return sorted(int(s["port"]) for s in discover())


def _spawn(slot: int, port: int) -> subprocess.Popen:
    env = dict(os.environ)
    env["CLO_BASE_URL"] = f"http://127.0.0.1:{port}"
    env["WORKER_SLOT"] = str(slot)
    return subprocess.Popen([sys.executable, str(REPO_ROOT / "worker" / "run_worker.py")], env=env, cwd=str(REPO_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="One worker process per CLO session")
    ap.add_argument("--discover", action="store_true", help="use the live sessions in clo_workspace/logs/instances")
    ap.add_argument("--ports", help="comma-separated plugin ports, one worker each")
    ap.add_argument("--count", type=int, default=0, help="number of workers (with --base-port)")
    ap.add_argument("--base-port", type=int, default=50601)
    args = ap.parse_args()

    ports = _ports_from_args(args)
    if not ports:
        logger.error("No CLO sessions: start CLO with MIRRA_PLUGIN_PORT set and the plugin running, "
                     "or pass --ports / --count.")
        return 1
    logger.info("Starting %d worker(s) for plugin ports %s", len(ports), ports)

    children: dict[int, subprocess.Popen] = {}
    started_at: dict[int, float] = {}
    try:
        for slot, port in enumerate(ports):
            children[slot] = _spawn(slot, port)
            started_at[slot] = time.monotonic()
        while children:
            time.sleep(1.0)
            for slot in list(children):
                code = children[slot].poll()
                if code is None:
                    continue
                if code == EXIT_CONFIG_ERROR:
                    logger.error("slot %d exited with a configuration error; not restarting", slot)
                    del children[slot]
                    continue
                logger.warning("slot %d (port %d) exited with code %s; restarting in %.0fs",
                               slot, ports[slot], code, RESTART_DELAY_SECONDS)
                time.sleep(RESTART_DELAY_SECONDS)
                children[slot] = _spawn(slot, ports[slot])
                started_at[slot] = time.monotonic()
    except KeyboardInterrupt:
        logger.info("Stopping workers")
    finally:
        for proc in children.values():
            if proc.poll() is None:
                proc.terminate()
        for proc in children.values():
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
