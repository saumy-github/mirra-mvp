"""Quick test of CLO REST API pattern import - QUEUE-BASED"""
import sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\Anant\mirra-mvp\clo_workspace\plugins")

from clo_automation_client import CLORestClient
import time

# Create client
client = CLORestClient()

# Test health
print("Testing health endpoint...")
health = client.health_check()
print(f"Health check: {health}")

if not health.get('status') == 'ok':
    print("❌ REST server not running!")
    print("👉 Open CLO and click: Plugins →'REST Server & Execute'")
    sys.exit(1)

print("\n✅ REST server is running!")

# Find latest generated run folder under output/
_BASE = Path(r"C:\Users\Anant\mirra-mvp\2d_patterned_garment_generation_clo3d\output")
_runs = sorted(
    [d for d in (_BASE.iterdir() if _BASE.exists() else []) if d.is_dir() and d.name.startswith("run_")],
    key=lambda d: int(d.name.split("_")[1]) if len(d.name.split("_")) > 1 and d.name.split("_")[1].isdigit() else 0
)
_patterns_dir = (_runs[-1] / "patterns_dxf") if _runs else (_BASE / "patterns_dxf")
print(f"\n📁 Using patterns from: {_patterns_dir}")

# Queue pattern imports
patterns = [str(_patterns_dir / name) for name in [
    "front_panel.dxf", "back_panel.dxf", "sleeve_left.dxf", "sleeve_right.dxf",
]]

print("\n📋 Queuing pattern imports...")
for pattern_path in patterns:
    result = client.import_pattern(pattern_path)
    print(f"  {result.get('message', result)}")

print(f"\n✅ Commands queued!")
print(f"👉 In CLO, click: Plugins → 'REST Server & Execute' to process queue")
print(f"   (This executes commands from the main thread safely)")

