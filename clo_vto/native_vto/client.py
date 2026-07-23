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

    def get_capabilities(self):
        return self._get("/capabilities")

    def get_import_scale_debug(self):
        return self._get("/debug/import-scales")

    def get_arrangement_debug(self):
        return self._get("/arrangement/debug")

    def get_avatar_debug(self):
        return self._get("/avatar/debug")

    def get_native_avatar_debug(self):
        return self._get("/avatar/native-debug")

    def import_avatar(self, obj_path, scale=1.0):
        obj_path = str(Path(obj_path).as_posix())
        return self._post("/import-avatar", {"path": obj_path, "scale": float(scale)})

    def import_avatar_avt(self, avt_path):
        avt_path = str(Path(avt_path).as_posix())
        return self._post("/import-avatar-avt", {"path": avt_path})

    def import_avatar_measurements(self, csv_path, template_path=None):
        payload = {"csv_path": str(Path(csv_path).as_posix())}
        if template_path is not None:
            payload["template_path"] = str(Path(template_path).as_posix())
        return self._post("/import-avatar-measurements", payload)

    def import_pattern(self, dxf_path, scale=1.0):
        dxf_path = str(Path(dxf_path).as_posix())
        return self._post("/import-pattern", {"path": dxf_path, "scale": float(scale)})

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
    ):
        return self._post(
            "/arrange-pattern",
            {
                "pattern_index": pattern_index,
                "arrangement_index": arrangement_index,
                "position": {"x": offset_x, "y": offset_y, "offset": offset_z},
                "orientation": orientation,
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

    def set_fabric_color(self, pattern_index, r: int, g: int, b: int):
        """Set the diffuse color of the fabric assigned to a pattern piece.

        r, g, b are integers in [0, 255].  Requires the CLO plugin to expose
        POST /set-fabric-color (added in plugin v2).
        """
        return self._post(
            "/set-fabric-color",
            {"pattern_index": pattern_index, "r": int(r), "g": int(g), "b": int(b)},
        )

    def set_fabric_texture(self, pattern_index, texture_path: str):
        """Load a PNG/JPEG as the diffuse texture for a pattern piece's fabric.

        texture_path must be an absolute path accessible from the CLO process.
        Requires POST /set-fabric-texture (plugin v2).
        """
        texture_path = str(Path(texture_path).as_posix())
        return self._post(
            "/set-fabric-texture",
            {"pattern_index": pattern_index, "texture_path": texture_path},
        )

    def set_fabric_graphic(
        self,
        pattern_index,
        graphic_path: str,
        u: float = 0.5,
        v: float = 0.3,
        scale: float = 1.0,
    ):
        """Place a graphic overlay (logo, print) on a pattern piece's fabric.

        u, v are normalised UV coordinates [0, 1] for the graphic centre.
        scale is a multiplier relative to the fabric tile size.
        Requires POST /set-fabric-graphic (plugin v2).
        """
        graphic_path = str(Path(graphic_path).as_posix())
        return self._post(
            "/set-fabric-graphic",
            {
                "pattern_index": pattern_index,
                "graphic_path": graphic_path,
                "u": float(u),
                "v": float(v),
                "scale": float(scale),
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
                # Small pause so CLO finishes writing results to last_results
                # before the caller reads get_status() again.
                time.sleep(0.4)
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

    def reset_fabric_status(self) -> dict:
        """Clear plugin-side fabric dispatch counters before a new batch.

        Call this before issuing a sequence of set_fabric_color / set_fabric_texture
        commands so the subsequent wait_for_fabric() sees only the current batch.
        """
        return self._post("/fabric-status/reset", {})

    def wait_for_fabric(self, timeout: int = 15, poll_interval: float = 0.15) -> bool:
        """Poll /fabric-status until all dispatched fabric CAPI calls have completed.

        The plugin dispatches color/texture calls via PostMessage (Windows) or
        Qt::QueuedConnection (macOS) — they execute asynchronously after the queue
        drain. This method waits until completed+failed >= pending.

        Returns True if all calls completed successfully, False on timeout or failure.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                r = self._get("/fabric-status")
                if r.get("all_done"):
                    ok = r.get("last_success", False)
                    if not ok:
                        print(f"  [fabric-status] FAILED: {r.get('last_message', '')}")
                    return ok
            except Exception as exc:
                print(f"  [fabric-status] poll error: {exc}")
            time.sleep(poll_interval)
        print(f"  [fabric-status] TIMEOUT after {timeout}s — CLO may be busy")
        return False

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

    def get_pattern_bbox(self, pattern_index):
        return self._get(f"/patterns/{pattern_index}/bbox")

    def get_pattern_input_info(self, pattern_index):
        return self._get(f"/patterns/{pattern_index}/input")

    def get_pattern_line_lengths(self, pattern_index):
        return self._get(f"/patterns/{pattern_index}/line-lengths")

    def save_project(self, zprj_path, thumbnail=True):
        zprj_path = str(Path(zprj_path).as_posix())
        return self._post(
            "/save-project",
            {
                "path": zprj_path,
                "thumbnail": thumbnail,
            },
        )
