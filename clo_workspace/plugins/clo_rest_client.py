"""
CLO REST Client - Python interface to CLO plugin

Use this after building and loading the RestPlugin into CLO.
This lets your Python scripts control CLO automation.
"""

import requests
import sys
import time
from pathlib import Path

workspace_root = Path(__file__).resolve().parents[2]
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from avatar_generation.run_manifest import get_latest_avatar_obj_path
from product_ingestion.run_manifest import get_latest_panels_dxf_dir


class CLORestClient:
    """Python client for CLO REST plugin."""
    
    def __init__(self, host="localhost", port=50505):
        self.base_url = f"http://{host}:{port}"
        self.timeout = 30  # seconds
    
    def is_connected(self):
        """Check if CLO plugin is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def wait_for_connection(self, timeout=10):
        """Wait for CLO to start."""
        print("Waiting for CLO REST plugin...")
        start = time.time()
        while time.time() - start < timeout:
            if self.is_connected():
                print("✓ Connected to CLO")
                return True
            time.sleep(1)
        print("✗ Could not connect to CLO")
        return False
    
    def import_avatar(self, avatar_path):
        """Import OBJ avatar into CLO."""
        path = Path(avatar_path).absolute()
        if not path.exists():
            raise FileNotFoundError(f"Avatar not found: {path}")
        
        print(f"Importing avatar: {path.name}")
        response = requests.post(
            f"{self.base_url}/import-avatar",
            data=str(path),
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            print("  ✓ Avatar imported")
            return True
        else:
            error = response.json().get("message", "Unknown error")
            print(f"  ✗ Import failed: {error}")
            return False
    
    def import_pattern(self, pattern_path):
        """Import DXF pattern into CLO."""
        path = Path(pattern_path).absolute()
        if not path.exists():
            raise FileNotFoundError(f"Pattern not found: {path}")
        
        print(f"Importing pattern: {path.name}")
        response = requests.post(
            f"{self.base_url}/import-pattern",
            data=str(path),
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            print("  ✓ Pattern imported")
            return True
        else:
            error = response.json().get("message", "Unknown error")
            print(f"  ✗ Import failed: {error}")
            return False
    
    def simulate(self):
        """Run cloth simulation."""
        print("Running simulation...")
        response = requests.post(
            f"{self.base_url}/simulate",
            timeout=self.timeout * 2  # Simulation takes longer
        )
        
        if response.status_code == 200:
            print("  ✓ Simulation complete")
            return True
        else:
            error = response.json().get("message", "Unknown error")
            print(f"  ✗ Simulation failed: {error}")
            return False
    
    def export_garment(self, output_path, format="glb"):
        """Export garment from CLO."""
        path = Path(output_path).absolute()
        path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Exporting to: {path}")
        response = requests.post(
            f"{self.base_url}/export",
            data=str(path),
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            print("  ✓ Export complete")
            return True
        else:
            error = response.json().get("message", "Unknown error")
            print(f"  ✗ Export failed: {error}")
            return False


def test_clo_automation():
    """Test CLO REST automation."""
    print("=" * 60)
    print("CLO REST Automation Test")
    print("=" * 60)
    
    # Initialize client
    clo = CLORestClient()
    
    # Check connection
    if not clo.wait_for_connection(timeout=10):
        print("\n✗ CLO plugin not running!")
        print("\nMake sure:")
        print("  1. CLO is open")
        print("  2. RestPlugin.dll is in CLO plugins folder")
        print("  3. CLO was restarted after plugin install")
        return False
    
    # Test workflow
    workspace = workspace_root
    
    # 1. Import avatar
    try:
        avatar_path = Path(get_latest_avatar_obj_path())
    except FileNotFoundError:
        avatar_path = workspace / "avatar_generation/output/u_001-001/avatar.obj"

    if avatar_path.exists():
        clo.import_avatar(avatar_path)
    else:
        print(f"⚠ Avatar not found: {avatar_path}")
    
    # 2. Import patterns
    try:
        pattern_dir = Path(get_latest_panels_dxf_dir())
    except FileNotFoundError:
        pattern_dir = workspace / "product_ingestion/output/panels/dxf"
    patterns = list(pattern_dir.glob("*.dxf"))
    
    if patterns:
        for pattern in patterns:
            clo.import_pattern(pattern)
    else:
        print(f"⚠ No patterns found in: {pattern_dir}")
    
    # 3. Simulate (after manual sewing - plugin doesn't handle sewing yet)
    print("\n⚠ Note: Sewing must be done manually in CLO for now")
    print("  After sewing, run: clo.simulate()")
    
    # 4. Export
    output_path = workspace / "clo_workspace/exports/test_output.glb"
    # Uncomment after simulation:
    # clo.export_garment(output_path)
    
    print("\n" + "=" * 60)
    print("✓ Test complete")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_clo_automation()
