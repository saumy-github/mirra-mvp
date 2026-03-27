"""CLO REST Automation Client.

This file is now a thin orchestrator that imports modular step files from
clo_automation_steps and runs the full pipeline.
"""

import json
import sys
from pathlib import Path

# Ensure repository root is importable so `vto.clo_automation_steps` resolves
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vto.clo_automation_steps.client import CLORestClient
from vto.clo_automation_steps.helpers import print_result as _ok
from vto.clo_automation_steps.helpers import resolve_patterns_dir as _resolve_patterns_dir
from vto.clo_automation_steps.pipeline import run_pipeline
from pathlib import Path
import json


INPUT_ROOT = REPO_ROOT / "vto" / "input"


def select_input_run() -> Path | None:
    """Prompt the user to select a run folder under `vto/input`.

    If no folders exist, returns None.
    """
    if not INPUT_ROOT.exists():
        return None

    runs = sorted([p for p in INPUT_ROOT.iterdir() if p.is_dir()])
    if not runs:
        return None

    print("Available VTO input runs:")
    for i, p in enumerate(runs, start=1):
        print(f"  {i}. {p.name}")

    try:
        choice = input(f"Select run [1-{len(runs)}] (default: {len(runs)}): ").strip()
    except KeyboardInterrupt:
        raise

    if not choice:
        return runs[-1]

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(runs):
            return runs[idx]
    except ValueError:
        pass

    return None


def test_connection():
    """Backward-compatible helper for testing CLO REST connectivity."""
    client = CLORestClient()
    result = client.health_check()

    if result.get("status") == "ok":
        print("\u2713 Connected to CLO REST server")
        print(f"  Plugin: {result.get('plugin')}")
        print(f"  Version: {result.get('version')}")
        return True

    print("\u2717 Failed to connect to CLO REST server")
    print("  Make sure CLO is running with RestPlugin loaded")
    print(f"  Error: {result.get('error', 'Unknown error')}")
    return False


def example_workflow(seam_map=None):
    """Backward-compatible entrypoint that runs the modular pipeline."""
    # Allow the user to choose a prepared `vto/input` run; if chosen,
    # pass explicit avatar and patterns paths into the pipeline.
    chosen = select_input_run()
    if chosen:
        try:
            with (chosen / "input.json").open("r", encoding="utf8") as f:
                data = json.load(f)
            resolved = data.get("resolved_paths", {})
            avatar_p = resolved.get("avatar_obj") or resolved.get("avatar_glb")
            patterns_p = resolved.get("panels_dxf_dir")
            return run_pipeline(seam_map=seam_map, avatar_path=avatar_p, patterns_dir=patterns_p)
        except FileNotFoundError:
            print("Selected run has no input.json; falling back to discovery")
        except Exception as exc:
            print(f"Error reading selected input run: {exc}; falling back to discovery")

    return run_pipeline(seam_map=seam_map)


if __name__ == "__main__":
    import sys

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            test_connection()
        elif len(sys.argv) > 1 and sys.argv[1] == "status":
            print(json.dumps(CLORestClient().get_status(), indent=2))
        else:
            example_workflow()
    except KeyboardInterrupt:
        print("\n\nPipeline cancelled by user")
        sys.exit(130)
