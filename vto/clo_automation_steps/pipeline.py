"""Pipeline orchestrator for modular CLO automation steps."""

import json
from datetime import datetime, timezone
from pathlib import Path

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


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_report(ctx, overall_ok, step_results):
    return {
        "status": "completed" if overall_ok else "failed",
        "created_at": _utc_now_iso_z(),
        "steps": step_results,
        "diagnostics": {
            "loaded_patterns": ctx.loaded_patterns,
            "piece_to_index": ctx.piece_to_index,
            "index_to_piece": {str(k): v for k, v in ctx.index_to_piece.items()},
            "pattern_import_scale": ctx.pattern_import_scale,
            "pattern_import_scales": ctx.pattern_import_scales,
            "pattern_geometry_hash": ctx.pattern_geometry_hash,
            "pattern_hashes": ctx.pattern_hashes,
            "sdk_pattern_names": ctx.imported_pattern_names,
            "slot_map": ctx.slot_map,
            "slot_candidates": ctx.slot_candidates,
            "slot_fallback_mode": ctx.slot_fallback_mode,
            "edge_counts": ctx.edge_counts,
            "edge_sources": ctx.edge_sources,
            "sdk_capabilities": ctx.sdk_capabilities,
            "avatar_debug": ctx.avatar_debug,
            "import_scale_debug": ctx.import_scale_debug,
            "slot_diagnostics": ctx.slot_diagnostics,
            "scale_metrics": ctx.scale_metrics,
            "seam_results": ctx.seam_results,
            "arrangement_ok": ctx.arrangement_ok,
            "ready_for_sewing": ctx.ready_for_sewing,
        },
    }


def run_pipeline(
    seam_map=None,
    avatar_path: str | None = None,
    patterns_dir: str | None = None,
    report_path: str | None = None,
):
    """Run full CLO automation pipeline by executing all step modules.

    Optional `avatar_path` and `patterns_dir` may be provided to override
    the default discovery logic and use a chosen `vto/input` run.
    """
    ctx = create_context(seam_map=seam_map, avatar_path=avatar_path, patterns_dir=patterns_dir)

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

    step_results = []
    overall_ok = True
    for step in steps:
        step_name = getattr(step, "__module__", "step").split(".")[-1]
        try:
            ok = bool(step(ctx))
        except Exception as exc:
            ok = False
            step_results.append({"step": step_name, "success": False, "error": str(exc)})
            overall_ok = False
            break

        step_results.append({"step": step_name, "success": ok})
        if not ok:
            overall_ok = False
            break

    print("\n" + "=" * 64)
    try:
        final = ctx.client.get_status()
        succeeded = sum(1 for r in final.get("last_results", []) if r.get("success"))
        total = len(final.get("last_results", []))
    except Exception:
        succeeded, total = 0, 0

    if overall_ok:
        print("Simulation complete.")
    else:
        print("Pipeline ended before completion due to a failed gate/step.")
    print(f"Last batch: {succeeded}/{total} commands succeeded.")
    print("=" * 64)

    report = _build_report(ctx, overall_ok, step_results)
    if report_path:
        try:
            p = Path(report_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"Pipeline report written: {p}")
        except Exception as exc:
            print(f"Warning: failed to write pipeline report: {exc}")

    return overall_ok
