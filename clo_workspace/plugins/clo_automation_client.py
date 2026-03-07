"""
CLO REST Automation Client
Provides Python interface to control CLO3D via REST plugin
"""

import requests
import json
import os
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
        Import pattern DXF file into CLO
        
        Args:
            dxf_path: Path to DXF file
        
        Returns:
            dict: {"success": bool, "message": str, "path": str}
        """
        dxf_path = str(Path(dxf_path).as_posix())
        return self._post("/import-pattern", {"path": dxf_path})
    
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


def example_workflow():
    """Example automated workflow"""
    client = CLORestClient()
    
    # Paths
    workspace = Path("C:/Users/Anant/mirra-mvp")
    avatar_path = workspace / "clo_workspace/user_m_001_patterns/user_m_001_001_avatar.obj"
    _pat_base = workspace / "2d_patterned_garment_generation_clo3d/output"
    _pat_runs = sorted(
        [d for d in (_pat_base.iterdir() if _pat_base.exists() else []) if d.is_dir() and d.name.startswith("run_")],
        key=lambda d: int(d.name.split("_")[1]) if len(d.name.split("_")) > 1 and d.name.split("_")[1].isdigit() else 0
    )
    patterns_dir = (_pat_runs[-1] / "patterns_dxf") if _pat_runs else (_pat_base / "patterns_dxf")
    output_dir = workspace / "clo_workspace/exports"
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("CLO Automation Workflow")
    print("=" * 60)
    
    # 1. Health check
    print("\n[1/8] Checking connection...")
    if not test_connection():
        return
    
    # 2. Import avatar
    print("\n[2/8] Importing avatar...")
    result = client.import_avatar(str(avatar_path))
    print(f"  {result['message']}")
    if not result['success']:
        print(f"  Error: {result.get('error')}")
        return
    
    # 3. Import patterns
    print("\n[3/8] Importing patterns...")
    patterns = ["front_panel.dxf", "back_panel.dxf", "sleeve_left.dxf", "sleeve_right.dxf"]
    for pattern in patterns:
        pattern_path = patterns_dir / pattern
        result = client.import_pattern(str(pattern_path))
        print(f"  {pattern}: {result['message']}")
        if not result['success']:
            print(f"    Error: {result.get('error')}")
    
    # 4. Check patterns loaded
    print("\n[4/8] Checking pattern count...")
    result = client.get_pattern_count()
    print(f"  Patterns loaded: {result.get('count', 0)}")
    
    # 5. Create seams (example - you'll need to adjust indices)
    print("\n[5/8] Creating seams...")
    print("  NOTE: Pattern edge indices need to be determined manually")
    print("  Use CLO GUI to identify which edges should connect")
    
    # Example seams (adjust based on actual pattern structure)
    seams = [
        {"name": "Front-Back shoulder left", "a": 0, "la": 1, "b": 1, "lb": 1},
        {"name": "Front-Back shoulder right", "a": 0, "la": 2, "b": 1, "lb": 2},
        {"name": "Front-Sleeve left", "a": 0, "la": 3, "b": 2, "lb": 0},
        {"name": "Back-Sleeve left", "a": 1, "la": 3, "b": 2, "lb": 1},
        {"name": "Front-Sleeve right", "a": 0, "la": 4, "b": 3, "lb": 0},
        {"name": "Back-Sleeve right", "a": 1, "la": 4, "b": 3, "lb": 1},
    ]
    
    for seam in seams:
        result = client.create_seam(seam["a"], seam["la"], seam["b"], seam["lb"])
        status = "✓" if result.get("success") else "✗"
        print(f"  {status} {seam['name']}")
    
    # 6. Run simulation
    print("\n[6/8] Running simulation...")
    result = client.simulate(steps=100)
    print(f"  {result.get('message', 'Simulation started')}")
    
    # 7. Export garment
    print("\n[7/8] Exporting garment...")
    output_file = output_dir / "automated_tshirt.glb"
    result = client.export_garment(str(output_file), format="glb")
    print(f"  {result.get('message')}")
    if result.get('success'):
        print(f"  Output: {output_file}")
    
    # 8. Save project
    print("\n[8/8] Saving project...")
    project_file = workspace / "clo_workspace/projects/automated_tshirt.zprj"
    project_file.parent.mkdir(exist_ok=True)
    result = client.save_project(str(project_file))
    print(f"  {result.get('message')}")
    if result.get('success'):
        print(f"  Project: {project_file}")
    
    print("\n" + "=" * 60)
    print("Workflow complete!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Just test connection
        test_connection()
    else:
        # Run full workflow
        example_workflow()
