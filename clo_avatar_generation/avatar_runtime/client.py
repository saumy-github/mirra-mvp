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

    def clear_avatars(self, max_index: int = 7) -> dict:
        """Delete avatars 0..max_index. Older plugins lack this route — the
        caller checks `supported` rather than treating 404 as a failure."""
        try:
            return self._post("/clear-avatars", {"max_index": max_index})
        except Exception as exc:  # noqa: BLE001 - route absent on older plugins
            return {"success": False, "supported": False, "error": str(exc)}

    def execute_queue(self) -> dict:
        return self._post("/execute", {})

    def get_native_avatar_debug(self) -> dict:
        return self._get("/avatar/native-debug")

    def get_avatar_property_debug(self) -> dict:
        return self._get("/avatar/property-debug")

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

    def set_avatar_properties(
        self,
        properties: dict[str, object],
        *,
        avatar_index: int = 0,
        unit: str | None = None,
    ) -> dict:
        payload: dict[str, object] = {
            "avatar_index": int(avatar_index),
            "properties": properties,
        }
        if unit is not None:
            payload["unit"] = unit
        return self._post("/avatar/set-properties", payload)

    def save_project(self, zprj_path: str | Path, thumbnail: bool = True) -> dict:
        payload = {
            "path": str(Path(zprj_path).as_posix()),
            "thumbnail": bool(thumbnail),
        }
        return self._post("/save-project", payload)

    def export_avatar_avt(self, avt_path: str | Path) -> dict:
        payload = {"path": str(Path(avt_path).as_posix())}
        return self._post("/export-avatar-avt", payload)

    def export_avatar_glb(self, output_path: str | Path) -> dict:
        """Export the current scene as GLB via the same `/export` endpoint
        clo_vto's export_garment() uses — one CLO plugin instance, one
        command queue, shared by both pipelines."""
        payload = {"path": str(Path(output_path).as_posix()), "format": "glb"}
        return self._post("/export", payload)

    def wait_for_queue(
        self,
        timeout: int = 30,
        poll_interval: float = 0.3,
        *,
        trigger_execute_fallback: bool = False,
    ) -> dict:
        deadline = time.time() + timeout
        last_trigger = 0.0
        last_status: dict = {}
        while time.time() < deadline:
            status = self.get_status()
            last_status = status
            if status.get("queue_size", 1) == 0 and not status.get("queue_processing", True):
                return status

            if (
                trigger_execute_fallback
                and status.get("queue_size", 0) > 0
                and not status.get("queue_processing", False)
                and time.time() - last_trigger > 3.0
            ):
                self.execute_queue()
                last_trigger = time.time()

            time.sleep(poll_interval)

        raise TimeoutError(
            f"CLO queue did not drain within {timeout}s. Last status: {last_status or self.get_status()}"
        )
