"""Pipeline orchestrator for modular CLO automation steps."""

from .context import create_context
from .step_01_health import run as step_01_health
from .step_02_new_project import run as step_02_new_project
from .step_03_import_avatar import run as step_03_import_avatar
from .step_04_import_patterns import run as step_04_import_patterns
from .step_05_verify_patterns import run as step_05_verify_patterns
from .step_06_read_edges_and_slots import run as step_06_read_edges_and_slots
from .step_07_arrange_patterns import run as step_07_arrange_patterns
from .step_08_apply_fabric import run as step_08_apply_fabric
from .step_09_create_seams import run as step_09_create_seams
from .step_10_simulate import run as step_10_simulate
from .step_11_export_note import run as step_11_export_note


def run_pipeline(seam_map=None):
    """Run full CLO automation pipeline by executing all step modules."""
    ctx = create_context(seam_map=seam_map)

    print("=" * 64)
    print("CLO Virtual Try-On Automation Pipeline")
    print("=" * 64)

    steps = [
        step_01_health,
        step_02_new_project,
        step_03_import_avatar,
        step_04_import_patterns,
        step_05_verify_patterns,
        step_06_read_edges_and_slots,
        step_07_arrange_patterns,
        step_08_apply_fabric,
        step_09_create_seams,
        step_10_simulate,
        step_11_export_note,
    ]

    for step in steps:
        if not step(ctx):
            return False

    print("\n" + "=" * 64)
    try:
        final = ctx.client.get_status()
        succeeded = sum(1 for r in final.get("last_results", []) if r.get("success"))
        total = len(final.get("last_results", []))
    except Exception:
        succeeded, total = 0, 0

    print("Simulation complete.")
    print(f"Last batch: {succeeded}/{total} commands succeeded.")
    print("=" * 64)
    return True
