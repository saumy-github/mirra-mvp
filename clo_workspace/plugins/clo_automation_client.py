"""CLO REST Automation Client.

This file is now a thin orchestrator that imports modular step files from
clo_automation_steps and runs the full pipeline.
"""

import json

from clo_automation_steps.client import CLORestClient
from clo_automation_steps.helpers import print_result as _ok
from clo_automation_steps.helpers import resolve_patterns_dir as _resolve_patterns_dir
from clo_automation_steps.pipeline import run_pipeline


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
    return run_pipeline(seam_map=seam_map)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_connection()
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(CLORestClient().get_status(), indent=2))
    else:
        example_workflow()
