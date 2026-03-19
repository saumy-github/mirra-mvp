"""REST client wrapper for CLO automation plugin."""

from pathlib import Path
import time

import requests


class CLORestClient:
    """Client for CLO REST Plugin API."""

    def __init__(self, base_url="http://localhost:50505", timeout=30):
        self.base_url = base_url
        self.timeout = timeout

    def _post(self, endpoint, data):
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            return {"success": False, "error": str(exc)}

    def _get(self, endpoint):
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            return {"success": False, "error": str(exc)}

    def health_check(self):
        return self._get("/health")

    def get_version(self):
        return self._get("/version")

    def import_avatar(self, obj_path):
        obj_path = str(Path(obj_path).as_posix())
        return self._post("/import-avatar", {"path": obj_path})

    def import_pattern(self, dxf_path, scale=None):
        dxf_path = str(Path(dxf_path).as_posix())
        payload = {"path": dxf_path}
        if scale is not None:
            payload["scale"] = float(scale)
        return self._post("/import-pattern", payload)

    def new_project(self):
        return self._post("/new-project", {})

    def arrange_pattern(
        self,
        pattern_index,
        arrangement_index=-1,
        offset_x=0,
        offset_y=0,
        offset_z=0,
        orientation=0,
        position_only=False,
    ):
        return self._post(
            "/arrange-pattern",
            {
                "pattern_index": pattern_index,
                "arrangement_index": arrangement_index,
                "position": {"x": offset_x, "y": offset_y, "offset": offset_z},
                "orientation": orientation,
                "position_only": position_only,
            },
        )

    def get_arrangement_list(self):
        return self._get("/arrangement-list")

    def get_pattern_arrangements(self):
        return self._get("/pattern-arrangements")

    def set_fabric(self, pattern_index, fabric_index=0):
        return self._post(
            "/set-fabric",
            {
                "pattern_index": pattern_index,
                "fabric_index": fabric_index,
            },
        )

    def get_status(self):
        return self._get("/status")

    def wait_for_queue(self, timeout=30, poll_interval=0.3):
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
                self._post("/execute", {})
                last_trigger = time.time()

            time.sleep(poll_interval)

        raise TimeoutError(
            f"CLO queue did not drain within {timeout}s. Last status: {self.get_status()}"
        )

    def create_seam(
        self,
        pattern_a,
        line_a,
        pattern_b,
        line_b,
        direction_a=True,
        direction_b=True,
    ):
        return self._post(
            "/create-seam",
            {
                "patternA_index": pattern_a,
                "lineA_index": line_a,
                "patternB_index": pattern_b,
                "lineB_index": line_b,
                "directionA": direction_a,
                "directionB": direction_b,
            },
        )

    def simulate(self, steps=100):
        return self._post("/simulate", {"steps": steps})

    def export_garment(self, output_path, format="glb"):
        output_path = str(Path(output_path).as_posix())
        return self._post(
            "/export",
            {
                "path": output_path,
                "format": format,
            },
        )

    def get_pattern_count(self):
        return self._get("/patterns/count")

    def get_pattern_info(self, pattern_index):
        return self._get(f"/patterns/{pattern_index}")

    def save_project(self, zprj_path, thumbnail=True):
        zprj_path = str(Path(zprj_path).as_posix())
        return self._post(
            "/save-project",
            {
                "path": zprj_path,
                "thumbnail": thumbnail,
            },
        )
