"""Cross-process GPU lock for the CV experiments.

The RTX 4050 has 6 GB, so only one large model job may use it at a time.
Usage:

    from gpu_lock import gpu_lock
    with gpu_lock("p01_segmentation"):
        ... load model to cuda, run, then free it ...

Hold the lock only while the GPU is in use, and free GPU memory
(`del model; torch.cuda.empty_cache()`) before leaving the block.
A lock left behind by a dead process is removed automatically.

Acquire the lock BEFORE loading a model (loading to CPU first also uses RAM).
The lock also waits until the machine has enough free memory: at least
MIN_FREE_RAM_GB of available RAM and MIN_FREE_COMMIT_GB of free commit
(RAM + pagefile). On 2026-11-20 two models loading at once made Windows grow
its pagefile until drive C: was full (ISSUES.md I9).
"""
from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parents[1] / "out" / ".gpu.lock"
MIN_FREE_RAM_GB = 2.5
MIN_FREE_COMMIT_GB = 3.0


def free_memory_gb() -> tuple[float, float]:
    """(available RAM, free commit = RAM + pagefile still available) in GB."""
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        st = MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
        return st.ullAvailPhys / 1e9, st.ullAvailPageFile / 1e9
    except Exception:  # noqa: BLE001
        return 99.0, 99.0


def _pid_alive(pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:  # noqa: BLE001
        return True


def _read_lock() -> dict:
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


@contextlib.contextmanager
def gpu_lock(owner: str, timeout_s: float = 3 * 3600, poll_s: float = 2.0):
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    announced = False
    mem_announced = False
    while True:
        ram, commit = free_memory_gb()
        if ram < MIN_FREE_RAM_GB or commit < MIN_FREE_COMMIT_GB:
            if not mem_announced:
                print(f"[gpu_lock] {owner} waiting for memory (RAM {ram:.1f} GB, commit {commit:.1f} GB free)", flush=True)
                mem_announced = True
            if time.time() - start > timeout_s:
                raise TimeoutError("not enough free memory to start a model job")
            time.sleep(poll_s * 5)
            continue
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"owner": owner, "pid": os.getpid(), "since": time.time()}).encode())
            os.close(fd)
            break
        except FileExistsError:
            info = _read_lock()
            pid = info.get("pid")
            if pid and not _pid_alive(int(pid)):
                with contextlib.suppress(FileNotFoundError):
                    LOCK_PATH.unlink()
                continue
            if not announced:
                print(f"[gpu_lock] {owner} waiting for GPU held by {info.get('owner')} (pid {pid})", flush=True)
                announced = True
            if time.time() - start > timeout_s:
                raise TimeoutError(f"GPU lock not acquired within {timeout_s}s (held by {info})")
            time.sleep(poll_s)
    try:
        yield
    finally:
        info = _read_lock()
        if info.get("pid") == os.getpid():
            with contextlib.suppress(FileNotFoundError):
                LOCK_PATH.unlink()
