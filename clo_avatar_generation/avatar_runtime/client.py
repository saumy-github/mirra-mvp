"""REST client wrapper for the Step-1 CLO avatar workflow."""

from __future__ import annotations

from pathlib import Path
import time
import requests


class CLORestClient:
    """Small JSON client for the local CLO REST plugin."""
    def __init__(self, base_url: str = "http://localhost:50505", timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, endpoint: str, payload: dict) -> dict:
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            return {"success": False, "error": str(exc)}

    def _get(self, endpoint: str) -> dict:
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            return {"success": False, "error": str(exc)}

    def health_check(self) -> dict:
        return self._get("/health")

    def get_capabilities(self) -> dict:
        return self._get("/capabilities")

    def get_status(self) -> dict:
        return self._get("/status")

    def new_project(self) -> dict:
        return self._post("/new-project", {})

    def execute_queue(self) -> dict:
        return self._post("/execute", {})

    def get_native_avatar_debug(self) -> dict:
        return self._get("/avatar/native-debug")

    def get_avatar_state(self) -> dict:
        return self._get("/avatars/state")

    def import_avatar_avt(self, avt_path: str | Path) -> dict:
        path = str(Path(avt_path).as_posix())
        return self._post("/import-avatar-avt", {"path": path})

    def import_avatar_measurements(
        self,
        csv_path: str | Path,
        *,
        template_path: str | Path | None = None,
    ) -> dict:
        payload = {"csv_path": str(Path(csv_path).as_posix())}
        if template_path is not None:
            payload["template_path"] = str(Path(template_path).as_posix())
        return self._post("/import-avatar-measurements", payload)

    def save_project(self, zprj_path: str | Path, thumbnail: bool = True) -> dict:
        payload = {
            "path": str(Path(zprj_path).as_posix()),
            "thumbnail": bool(thumbnail),
        }
        return self._post("/save-project", payload)

    def wait_for_queue(self, timeout: int = 30, poll_interval: float = 0.3) -> dict:
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
                self.execute_queue()
                last_trigger = time.time()

            time.sleep(poll_interval)

        raise TimeoutError(
            f"CLO queue did not drain within {timeout}s. Last status: {self.get_status()}"
        )
