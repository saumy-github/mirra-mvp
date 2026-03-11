"""
CLO REST Automation Client
Provides Python interface to control CLO3D via REST plugin
"""

import requests
import json
import os
import time
from pathlib import Path


class CLORestClient:
    """Client for CLO REST Plugin API"""
    
    def __init__(self, base_url="http://localhost:50505", timeout=30):
        """
        Initialize CLO REST client
        
        Args:
            base_url: Base URL of CLO REST server (default: http://localhost:50505)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url
        self.timeout = timeout
    
    def _post(self, endpoint, data):
        """Helper method for POST requests"""
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def _get(self, endpoint):
        """Helper method for GET requests"""
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def health_check(self):
        """
        Check if CLO REST server is running
        
        Returns:
            dict: {"status": "ok", "plugin": "...", "version": "..."}
        """
        return self._get("/health")
    
    def import_avatar(self, obj_path):
        """
        Import avatar OBJ file into CLO
        
        Args:
            obj_path: Path to OBJ file (use forward slashes or escaped backslashes)
        
        Returns:
            dict: {"success": bool, "message": str, "path": str}
        """
        obj_path = str(Path(obj_path).as_posix())  # Normalize path
        return self._post("/import-avatar", {"path": obj_path})
    
    def import_pattern(self, dxf_path):
        """
        Import pattern DXF file into CLO (queued — runs on next frame).

        Args:
            dxf_path: Path to DXF file

        Returns:
            dict: {"success": bool, "message": str, "path": str}
        """
        dxf_path = str(Path(dxf_path).as_posix())
        return self._post("/import-pattern", {"path": dxf_path})

    def new_project(self):
        """
        Clear the CLO scene and start a fresh project.
        Call this at the start of every pipeline run for repeatability.

        Returns:
            dict: {"success": bool, "message": str}
        """
        return self._post("/new-project", {})

    def arrange_pattern(self, pattern_index, arrangement_index=-1,
                        offset_x=0, offset_y=0, offset_z=0, orientation=0):
        """
        Place a pattern piece around the avatar.

        arrangement_index: CLO slot index from get_arrangement_list().
                           Pass -1 to skip SetArrangement and only apply offsets.
        offset_x/y/z:      Position offsets in mm from the slot centre.
                           offset_z is depth (away from avatar surface).
        orientation:       CLO orientation enum (0 = default for that slot).

        Returns:
            dict: {"success": bool, "message": str}
        """
        return self._post("/arrange-pattern", {
            "pattern_index":     pattern_index,
            "arrangement_index": arrangement_index,
            "position": {"x": offset_x, "y": offset_y, "offset": offset_z},
            "orientation":       orientation
        })

    def get_arrangement_list(self):
        """Return CLO's avatar arrangement slot list (names + indices)."""
        return self._get("/arrangement-list")

    def get_pattern_arrangements(self):
        """Return current arrangement info for every loaded pattern."""
        return self._get("/pattern-arrangements")

    def set_fabric(self, pattern_index, fabric_index=0):
        """
        Assign a fabric from CLO's internal fabric library to a pattern piece.
        Call after import, before simulate.

        fabric_index is the 0-based index into CLO's fabric list for the
        current project.  Add fabrics to the project in CLO's UI first,
        then reference them by index here.

        fabric_index 0 = first (or only) fabric in the project.

        Args:
            pattern_index: 0-based pattern index
            fabric_index:  0-based fabric index in CLO's fabric library

        Returns:
            dict: {"success": bool, "message": str}
        """
        return self._post("/set-fabric", {
            "pattern_index": pattern_index,
            "fabric_index":  fabric_index
        })

    def get_status(self):
        """
        Get current queue state and last batch results.

        Returns:
            dict: {
                "queue_size":        int,   # commands still waiting
                "queue_processing":  bool,  # True while CLO is executing
                "patterns_loaded":   int,   # patterns currently in CLO scene
                "last_results":      list   # [{type, success, message}, ...]
            }
        """
        return self._get("/status")

    def wait_for_queue(self, timeout=30, poll_interval=0.3):
        """
        Block until CLO's queue is empty and not processing.
        Use this between pipeline stages to guarantee ordering:
            import -> wait_for_queue -> create_seam -> wait_for_queue -> simulate

        Args:
            timeout:       max seconds to wait before raising TimeoutError
            poll_interval: seconds between status polls (default 0.3 s)

        Returns:
            dict: final status response

        Raises:
            TimeoutError: if CLO does not finish within timeout seconds
        """
        deadline = time.time() + timeout
        last_trigger = 0.0          # throttle /execute calls to once per 3 s
        while time.time() < deadline:
            status = self.get_status()
            if (status.get("queue_size", 1) == 0 and
                    not status.get("queue_processing", True)):
                return status

            # If the queue has items but isn't processing, the plugin's
            # DoFunctionContinuously may not be running (old DLL or CLO
            # hasn't rendered a frame yet).  Nudge it via POST /execute.
            if (status.get("queue_size", 0) > 0 and
                    not status.get("queue_processing", False) and
                    time.time() - last_trigger > 3.0):
                self._post("/execute", {})
                last_trigger = time.time()

            time.sleep(poll_interval)
        raise TimeoutError(
            f"CLO queue did not drain within {timeout}s. "
            f"Last status: {self.get_status()}"
        )
    
    def create_seam(self, pattern_a, line_a, pattern_b, line_b, 
                    direction_a=True, direction_b=True):
        """
        Create seam between two pattern edges
        
        Args:
            pattern_a: First pattern index (0-based)
            line_a: Edge/line index on first pattern
            pattern_b: Second pattern index
            line_b: Edge/line index on second pattern
            direction_a: Stitching direction for pattern A (True=forward)
            direction_b: Stitching direction for pattern B
        
        Returns:
            dict: {"success": bool, "message": str}
        """
        return self._post("/create-seam", {
            "patternA_index": pattern_a,
            "lineA_index": line_a,
            "patternB_index": pattern_b,
            "lineB_index": line_b,
            "directionA": direction_a,
            "directionB": direction_b
        })
    
    def simulate(self, steps=100):
        """
        Run garment simulation
        
        Args:
            steps: Number of simulation steps (default: 100)
        
        Returns:
            dict: {"success": bool, "message": str, "steps": int}
        """
        return self._post("/simulate", {"steps": steps})
    
    def export_garment(self, output_path, format="glb"):
        """
        Export garment as GLB or GLTF
        
        Args:
            output_path: Output file path
            format: "glb" or "gltf" (default: glb)
        
        Returns:
            dict: {"success": bool, "message": str, "output_paths": list}
        """
        output_path = str(Path(output_path).as_posix())
        return self._post("/export", {
            "path": output_path,
            "format": format
        })
    
    def get_pattern_count(self):
        """
        Get number of patterns currently in CLO
        
        Returns:
            dict: {"success": bool, "count": int}
        """
        return self._get("/patterns/count")
    
    def get_pattern_info(self, pattern_index):
        """
        Get detailed information about a pattern
        
        Args:
            pattern_index: Pattern index (0-based)
        
        Returns:
            dict: {"success": bool, "pattern_index": int, "info": dict}
        """
        return self._get(f"/patterns/{pattern_index}")
    
    def save_project(self, zprj_path, thumbnail=True):
        """
        Save current project as ZPRJ file
        
        Args:
            zprj_path: Output ZPRJ file path
            thumbnail: Create thumbnail PNG (default: True)
        
        Returns:
            dict: {"success": bool, "message": str, "output_path": str}
        """
        zprj_path = str(Path(zprj_path).as_posix())
        return self._post("/save-project", {
            "path": zprj_path,
            "thumbnail": thumbnail
        })


def test_connection():
    """Test connection to CLO REST server"""
    client = CLORestClient()
    result = client.health_check()
    
    if result.get("status") == "ok":
        print("✓ Connected to CLO REST server")
        print(f"  Plugin: {result.get('plugin')}")
        print(f"  Version: {result.get('version')}")
        return True
    else:
        print("✗ Failed to connect to CLO REST server")
        print(f"  Make sure CLO is running with RestPlugin loaded")
        print(f"  Error: {result.get('error', 'Unknown error')}")
        return False


def _resolve_patterns_dir():
    """Find the latest run_NNN/patterns_dxf directory."""
    base = Path("C:/Users/Anant/mirra-mvp/2d_patterned_garment_generation_clo3d/output")
    if not base.exists():
        return base / "patterns_dxf"
    runs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("run_")],
        key=lambda d: int(d.name.split("_")[1])
        if len(d.name.split("_")) > 1 and d.name.split("_")[1].isdigit() else 0
    )
    return (runs[-1] / "patterns_dxf") if runs else (base / "patterns_dxf")


def _ok(result, label):
    """Print result line and return success bool."""
    ok  = result.get("success", False)
    sym = "\u2713" if ok else "\u2717"
    msg = result.get("message", result.get("error", str(result)))
    print(f"  {sym} {label}: {msg}")
    return ok


def example_workflow(seam_map=None):
    """
    Full 12-step automation pipeline:
      new-project -> import avatar -> import 4 patterns -> wait
      -> inspect edge indices -> arrange in 3D -> set fabric
      -> create all seams -> simulate -> export GLB -> save ZPRJ

    Args:
        seam_map: list of dicts with keys a, la, b, lb, [da, db].
                  If None, uses placeholder indices. Run
                  plugins/discover_seam_indices.py first to get real values.
    """
    client   = CLORestClient()
    ws       = Path(__file__).resolve().parent.parent.parent  # repo root
    avatar   = ws / "pipeline_star/generated/clo_avatars/user_m_001_001_avatar.obj"
    pat_dir  = _resolve_patterns_dir()
    out_dir  = ws / "clo_workspace/exports"
    out_dir.mkdir(exist_ok=True)
    proj_dir = ws / "clo_workspace/projects"
    proj_dir.mkdir(exist_ok=True)

    PATTERNS = [
        "front_panel.dxf",
        "back_panel.dxf",
        "sleeve_left.dxf",
        "sleeve_right.dxf",
    ]

    # Arrangement slot indices for a standard CLO t-shirt project.
    # SetArrangementPosition offsets are in mm (CLO's internal garment unit).
    # offset_z is depth away from the avatar surface — start patterns 80mm
    # outside the body so they don't intersect on simulation start.
    ARRANGEMENT = [
        # pattern_index  arrangement_slot  offset_x  offset_y  offset_z  orientation
        (0,  0,  0,  0,  80,  0),   # front panel  -> slot 0 (Front Body), 8cm forward
        (1,  1,  0,  0,  80,  0),   # back panel   -> slot 1 (Back Body),  8cm back
        (2,  2,  0,  0,  80,  0),   # sleeve left  -> slot 2 (Left Sleeve), 8cm out
        (3,  3,  0,  0,  80,  0),   # sleeve right -> slot 3 (Right Sleeve), 8cm out
    ]

    # Default seam map derived from DXF geometry analysis.
    # Pattern order: 0=front_panel, 1=back_panel, 2=sleeve_left, 3=sleeve_right
    # Run plugins/discover_seam_indices.py to verify / regenerate.
    DEFAULT_SEAMS = [
        # Body structural seams
        {"name": "side-right",     "a": 0, "la": 1,  "b": 1, "lb": 1,  "da": True, "db": True},
        {"name": "side-left",      "a": 0, "la": 18, "b": 1, "lb": 17, "da": True, "db": True},
        {"name": "shoulder-right", "a": 0, "la": 8,  "b": 1, "lb": 8,  "da": True, "db": True},
        {"name": "shoulder-left",  "a": 0, "la": 11, "b": 1, "lb": 10, "da": True, "db": True},
        # Sleeve tube seams
        {"name": "sleeve-L-tube",  "a": 2, "la": 1,  "b": 2, "lb": 12, "da": True, "db": False},
        {"name": "sleeve-R-tube",  "a": 3, "la": 1,  "b": 3, "lb": 12, "da": True, "db": False},
        # Right armhole: front lower (edges 2-6) ↔ sleeve_right front cap (edges 2-6)
        {"name": "arm-R-fr-0",     "a": 0, "la": 2,  "b": 3, "lb": 2,  "da": True, "db": True},
        {"name": "arm-R-fr-1",     "a": 0, "la": 3,  "b": 3, "lb": 3,  "da": True, "db": True},
        {"name": "arm-R-fr-2",     "a": 0, "la": 4,  "b": 3, "lb": 4,  "da": True, "db": True},
        {"name": "arm-R-fr-3",     "a": 0, "la": 5,  "b": 3, "lb": 5,  "da": True, "db": True},
        {"name": "arm-R-fr-4",     "a": 0, "la": 6,  "b": 3, "lb": 6,  "da": True, "db": True},
        # Right armhole: back (edges 2-6, reversed match) ↔ sleeve_right back cap (edges 7-11)
        {"name": "arm-R-bk-0",     "a": 1, "la": 2,  "b": 3, "lb": 11, "da": True, "db": True},
        {"name": "arm-R-bk-1",     "a": 1, "la": 3,  "b": 3, "lb": 10, "da": True, "db": True},
        {"name": "arm-R-bk-2",     "a": 1, "la": 4,  "b": 3, "lb": 9,  "da": True, "db": True},
        {"name": "arm-R-bk-3",     "a": 1, "la": 5,  "b": 3, "lb": 8,  "da": True, "db": True},
        {"name": "arm-R-bk-4",     "a": 1, "la": 6,  "b": 3, "lb": 7,  "da": True, "db": True},
        # Left armhole: front lower (edges 13-17) ↔ sleeve_left back cap (edges 7-11, reversed)
        {"name": "arm-L-fr-0",     "a": 0, "la": 13, "b": 2, "lb": 11, "da": True, "db": True},
        {"name": "arm-L-fr-1",     "a": 0, "la": 14, "b": 2, "lb": 10, "da": True, "db": True},
        {"name": "arm-L-fr-2",     "a": 0, "la": 15, "b": 2, "lb": 9,  "da": True, "db": True},
        {"name": "arm-L-fr-3",     "a": 0, "la": 16, "b": 2, "lb": 8,  "da": True, "db": True},
        {"name": "arm-L-fr-4",     "a": 0, "la": 17, "b": 2, "lb": 7,  "da": True, "db": True},
        # Left armhole: back (edges 12-16) ↔ sleeve_left front cap (edges 2-6)
        {"name": "arm-L-bk-0",     "a": 1, "la": 12, "b": 2, "lb": 2,  "da": True, "db": True},
        {"name": "arm-L-bk-1",     "a": 1, "la": 13, "b": 2, "lb": 3,  "da": True, "db": True},
        {"name": "arm-L-bk-2",     "a": 1, "la": 14, "b": 2, "lb": 4,  "da": True, "db": True},
        {"name": "arm-L-bk-3",     "a": 1, "la": 15, "b": 2, "lb": 5,  "da": True, "db": True},
        {"name": "arm-L-bk-4",     "a": 1, "la": 16, "b": 2, "lb": 6,  "da": True, "db": True},
    ]

    seams = seam_map if seam_map else DEFAULT_SEAMS

    print("=" * 64)
    print("CLO Virtual Try-On Automation Pipeline")
    print("=" * 64)

    # ── Step 1: connection check ─────────────────────────────────────────
    print("\n[1] Health check ...")
    if not test_connection():
        print("Aborting — CLO plugin not reachable.")
        return False

    # ── Step 2: fresh scene ──────────────────────────────────────────────
    print("\n[2] New project ...")
    _ok(client.new_project(), "new-project")
    client.wait_for_queue(timeout=15)

    # ── Step 3: Import avatar ────────────────────────────────────────────
    print("\n[3] Importing avatar ...")
    avatar_loaded = False
    if not avatar.exists():
        print(f"  ! Avatar not found: {avatar}")
        print("  ! Simulation will be SKIPPED — CLO crashes without a body mesh.")
        print("  ! Generate an avatar OBJ via pipeline_star/ first.")
    else:
        _ok(client.import_avatar(str(avatar)), "import-avatar")
        avatar_loaded = True
    client.wait_for_queue(timeout=30)

    # ── Step 4: Import 4 pattern pieces ─────────────────────────────────
    print("\n[4] Importing patterns ...")
    for fname in PATTERNS:
        p = pat_dir / fname
        if not p.exists():
            print(f"  ! Pattern not found: {p}")
            continue
        _ok(client.import_pattern(str(p)), fname)

    print("     Waiting for CLO to finish imports ...")
    client.wait_for_queue(timeout=60)

    # ── Step 5: Verify count ─────────────────────────────────────────────
    print("\n[5] Verifying pattern count ...")
    status = client.get_status()
    loaded = status.get("patterns_loaded", 0)
    print(f"  Patterns in CLO scene: {loaded} (expected {len(PATTERNS)})")
    if loaded == 0:
        print("  No patterns loaded — check file paths and DXF format. Aborting.")
        return False

    # ── Step 6: Read edge data + query arrangement slots ─────────────────
    print("\n[6] Reading pattern edge data ...")
    for i in range(loaded):
        info = client.get_pattern_info(i)
        name = info.get("info", {}).get("name", f"pattern_{i}")
        lc   = info.get("info", {}).get("line_count", "?")
        print(f"  Pattern {i}: {name}  ({lc} edges)")

    print("\n[6b] Querying CLO arrangement slots ...")
    arr_resp = client.get_arrangement_list()
    slots = arr_resp.get("slots", [])
    if slots:
        for s in slots:
            print(f"  Slot {s.get('index','?')}: {s}")
    else:
        print("  No slots returned — avatar may not be loaded yet or CLO version")
        print("  doesn't populate arrangement list until after first simulate.")

    # Build slot index map by name (case-insensitive partial match)
    def find_slot(keywords):
        for s in slots:
            name_str = " ".join(str(v) for v in s.values()).lower()
            if all(k.lower() in name_str for k in keywords):
                return int(s.get("index", -1))
        return -1  # -1 = skip SetArrangement, just use position offsets

    front_slot = find_slot(["front"])
    back_slot  = find_slot(["back"])
    lsl_slot   = find_slot(["left", "sleeve"])
    rsl_slot   = find_slot(["right", "sleeve"])
    print(f"  Matched slots — front:{front_slot} back:{back_slot} "
          f"sleeve_L:{lsl_slot} sleeve_R:{rsl_slot}")

    # ── Step 7: Arrange pieces around avatar ─────────────────────────────
    print("\n[7] Arranging patterns in 3D around avatar ...")
    # offset_z (mm from slot centre) keeps pieces just outside the avatar surface.
    # A 178 cm person; torso ~20 cm deep → start 100 mm (10 cm) outside.
    ARRANGEMENT = [
        # pattern_idx  slot          ox  oy   oz   ori
        (0, front_slot,  0,  0,  100,  0),   # front panel
        (1, back_slot,   0,  0,  100,  0),   # back panel
        (2, lsl_slot,    0,  0,  100,  0),   # sleeve left
        (3, rsl_slot,    0,  0,  100,  0),   # sleeve right
    ]
    for idx, slot, ox, oy, oz, ori in ARRANGEMENT:
        if idx < loaded:
            _ok(client.arrange_pattern(idx, slot, ox, oy, oz, ori),
                f"pattern {idx} -> slot {slot}")
    client.wait_for_queue(timeout=15)

    # ── Step 8: Apply fabric ─────────────────────────────────────────────
    print("\n[8] Applying fabric (index 0, first fabric in CLO project) ...")
    for i in range(loaded):
        _ok(client.set_fabric(i, fabric_index=0),
            f"fabric pattern {i}")
    client.wait_for_queue(timeout=15)

    # ── Step 9: Create all seams ─────────────────────────────────────────
    print("\n[9] Creating seams ...")
    if not seam_map:
        print("  NOTE: Using placeholder edge indices.")
        print("  Run plugins/discover_seam_indices.py to get real indices.")
    for s in seams:
        _ok(client.create_seam(
            s["a"], s["la"], s["b"], s["lb"],
            s.get("da", True), s.get("db", True)
        ), s["name"])
    client.wait_for_queue(timeout=60)   # wait for all seams to stitch before simulate

    # ── Step 10: Simulate ────────────────────────────────────────────────
    print("\n[10] Running physics simulation (150 steps) ...")
    if not avatar_loaded:
        print("  ! Skipping simulation — no avatar loaded (would crash CLO).")
    else:
        _ok(client.simulate(steps=150), "simulate")
        print("     Waiting for simulation to complete ...")
        client.wait_for_queue(timeout=300)   # simulation is the slow step

    # ── Step 11 & 12: Export GLB + Save ZPRJ (disabled — crashes CLO post-sim)
    # TODO: re-enable once sewing/simulation is stable.
    # out_glb  = out_dir / "virtual_tryon_output.glb"
    # out_zprj = proj_dir / "virtual_tryon.zprj"
    # _ok(client.export_garment(str(out_glb), format="glb"), "export")
    # client.wait_for_queue(timeout=60)
    # time.sleep(3)
    # _ok(client.save_project(str(out_zprj)), "save-project")
    # client.wait_for_queue(timeout=60)
    out_glb = out_dir / "virtual_tryon_output.glb"
    print("\n[11] Export + Save skipped (re-enable in code when ready).")
    print("     To export manually: File → Export → glTF 2.0")
    print("     To save manually:   File → Save As → .zprj")

    # ── Done ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    try:
        final     = client.get_status()
        succeeded = sum(1 for r in final.get("last_results", []) if r.get("success"))
        total     = len(final.get("last_results", []))
    except Exception:
        succeeded, total = 0, 0
    print(f"Simulation complete.")
    print(f"Last batch: {succeeded}/{total} commands succeeded.")
    print("=" * 64)
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_connection()
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(CLORestClient().get_status(), indent=2))
    else:
        example_workflow()
