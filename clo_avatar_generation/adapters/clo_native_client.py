"""Placeholder client wrapper for future additive native-avatar plugin endpoints.

Phase 4 keeps this file intentionally minimal so the folder structure is ready
before plugin work begins in a later phase.
"""

from __future__ import annotations

from pathlib import Path
import time

import requests


class CLONativeClient:
    """Wrapper around additive native-avatar REST endpoints."""

    def __init__(self, base_url: str = "http://localhost:50505") -> None:
        self.base_url = base_url

    def _post(self, endpoint: str, payload: dict) -> dict:
        response = requests.post(
            f"{self.base_url}{endpoint}",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint: str) -> dict:
        response = requests.get(
            f"{self.base_url}{endpoint}",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_capabilities(self) -> dict:
        return self._get("/capabilities")

    def new_project(self) -> dict:
        return self._post("/new-project", {})

    def execute(self) -> dict:
        return self._post("/execute", {})

    def get_status(self) -> dict:
        return self._get("/status")

    def get_native_avatar_debug(self) -> dict:
        return self._get("/avatar/native-debug")

    def get_arrangement_list(self) -> dict:
        return self._get("/arrangement-list")

    def get_pattern_arrangements(self) -> dict:
        return self._get("/pattern-arrangements")

    def import_pattern(self, dxf_path: str | Path, scale: float = 1.0) -> dict:
        return self._post(
            "/import-pattern",
            {
                "path": str(Path(dxf_path).as_posix()),
                "scale": float(scale),
            },
        )

    def import_avatar_avt(self, avt_path: str | Path) -> dict:
        return self._post(
            "/import-avatar-avt",
            {"path": str(Path(avt_path).as_posix())},
        )

    def import_avatar_measurements(
        self,
        csv_path: str | Path,
        template_path: str | Path | None = None,
    ) -> dict:
        payload = {"csv_path": str(Path(csv_path).as_posix())}
        if template_path is not None:
            payload["template_path"] = str(Path(template_path).as_posix())
        return self._post("/import-avatar-measurements", payload)

    def wait_for_queue(self, timeout: float = 30.0, poll_interval: float = 0.3) -> dict:
        """Wait for the plugin queue to drain."""

        deadline = time.time() + timeout
        last_trigger = 0.0
        while time.time() < deadline:
            status = self.get_status()
            if status.get("queue_size", 1) == 0 and not status.get("queue_processing", True):
                return status

            if (
                status.get("queue_size", 0) > 0
                and not status.get("queue_processing", False)
                and time.time() - last_trigger > 3.0
            ):
                self.execute()
                last_trigger = time.time()

            time.sleep(poll_interval)

        raise TimeoutError(
            f"CLO queue did not drain within {timeout}s. Last status: {self.get_status()}"
        )
