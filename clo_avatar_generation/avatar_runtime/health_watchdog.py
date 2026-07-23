"""Background health watchdog: detects CLO crashing or becoming unresponsive
while a pipeline run is in progress.

Polls `GET /health` every 2 seconds on a daemon thread, started once the run
directory (and therefore `run.log`) exists, and stopped when the pipeline
finishes. A healthy `/health` response has no `"success"` key at all (just
`{"status": "ok", ...}`); `CLORestClient._get()` only injects
`{"success": False, "error": ...}` when the request itself failed (e.g. CLO
is no longer listening). So "crashed" is detected as `success is False` or
`status != "ok"` — never by catching an exception, since this client never
raises one.

Scope: pipeline-scoped only, per plan-03.md Phase 3. Not a standalone
always-on watcher.
"""

from __future__ import annotations

import threading

from .context import Step1Context

POLL_INTERVAL_SECONDS = 2.0


def _is_healthy(response: dict) -> bool:
    if response.get("success") is False:
        return False
    if response.get("status") != "ok":
        return False
    return True


class HealthWatchdog:
    """Polls CLO's /health endpoint on a daemon thread until stopped."""

    def __init__(self, ctx: Step1Context) -> None:
        self._ctx = ctx
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="clo-health-watchdog", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=POLL_INTERVAL_SECONDS + 1)

    def _run(self) -> None:
        while not self._stop_event.wait(POLL_INTERVAL_SECONDS):
            response = self._ctx.client.health_check()
            if not _is_healthy(response):
                self._ctx.logger.critical(
                    "CLO appears to have crashed or stopped responding "
                    "(last step in progress: %s): %s",
                    self._ctx.current_step or "unknown",
                    response,
                )
                return
