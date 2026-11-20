"""CLO session binding for parallel workers.

Each worker process owns exactly one CLO session (one plugin port). The
launcher (run_workers.py) sets two environment variables per process:

    CLO_BASE_URL   http://127.0.0.1:<plugin port of this worker's CLO session>
    WORKER_SLOT    0, 1, 2 ... (names the RQ worker and its log lines)

CLO itself is single-threaded, so one session must never serve two jobs at
once; `claim_session` enforces that across processes with an OS file lock that
disappears when the holder exits, even if it crashes.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("mirra.worker")

DEFAULT_CLO_URL = "http://localhost:50505"
_LOCK_DIR = Path(tempfile.gettempdir()) / "mirra_locks"


def clo_base_url() -> str:
    return (os.environ.get("CLO_BASE_URL") or DEFAULT_CLO_URL).rstrip("/")


def slot_name() -> str:
    slot = os.environ.get("WORKER_SLOT")
    return f"clo-slot-{slot}" if slot else f"clo-worker-{os.getpid()}"


class FileLock:
    """Cross-process lock on one byte of a file (msvcrt on Windows, flock elsewhere)."""

    def __init__(self, name: str) -> None:
        _LOCK_DIR.mkdir(parents=True, exist_ok=True)
        self.path = _LOCK_DIR / f"{name}.lock"
        self._fd: int | None = None

    def acquire(self, timeout: float = 0.0, poll: float = 0.5) -> bool:
        deadline = time.monotonic() + timeout
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
        while True:
            try:
                self._lock(fd)
                self._fd = fd
                return True
            except OSError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    return False
                time.sleep(poll)

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            self._unlock(self._fd)
        finally:
            os.close(self._fd)
            self._fd = None

    @staticmethod
    def _lock(fd: int) -> None:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(fd: int) -> None:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def exclusive(name: str, timeout: float = 3600.0):
    """Serialize something every worker shares (e.g. the try-on output folder)."""
    lock = FileLock(f"shared_{name}")
    if not lock.acquire(timeout=timeout):
        raise TimeoutError(f"Could not get the '{name}' lock within {timeout:.0f}s")
    try:
        yield
    finally:
        lock.release()


def claim_session(base_url: str) -> FileLock:
    """Hold the one-worker-per-CLO-session lock for the life of this process."""
    port = urlparse(base_url).port or 80
    lock = FileLock(f"clo_session_{port}")
    if not lock.acquire(timeout=0.0):
        raise RuntimeError(
            f"Another worker already owns the CLO session at {base_url}. "
            "One worker per CLO session: CLO is single-threaded."
        )
    return lock


def session_problems(base_url: str, timeout: float = 3.0) -> list[str]:
    """Reasons this CLO session is not ready for jobs (empty list = ready)."""
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=timeout) as resp:
            health = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any failure means not ready
        return [f"plugin not reachable at {base_url} ({exc.__class__.__name__})"]
    problems: list[str] = []
    if health.get("status") != "ok":
        problems.append(f"health status is {health.get('status')!r}")
    if health.get("host_matches_sdk") is False:
        problems.append(
            f"plugin SDK {health.get('sdk_clo_version')} != running CLO {health.get('host_app_version')}"
        )
    return problems


def wait_for_session(base_url: str, timeout: float = 300.0, log_every: float = 15.0) -> None:
    """Block until the session answers /health cleanly; raise TimeoutError otherwise."""
    deadline = time.monotonic() + timeout
    last_log = 0.0
    while True:
        problems = session_problems(base_url)
        if not problems:
            return
        now = time.monotonic()
        if now >= deadline:
            raise TimeoutError(f"CLO session {base_url} not ready after {timeout:.0f}s: {'; '.join(problems)}")
        if now - last_log >= log_every:
            logger.warning("Waiting for CLO session %s: %s", base_url, "; ".join(problems))
            last_log = now
        time.sleep(2.0)
