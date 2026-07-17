"""Pipeline orchestrator for modular CLO automation steps."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .context import create_context
from .helpers import step_header, step_footer
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
from .step_11_export_note import run as step_11_export_glb
from .step_12_texture_glb import run as step_12_texture_glb


# Human-readable name for each step module.
_STEP_NAMES = {
    "step_01_health":             "Health Check",
    "step_02_new_project":        "New Project",
    "step_03_import_avatar":      "Import Avatar",
    "step_04_import_patterns":    "Import Patterns",
    "step_05_verify_patterns":    "Verify Patterns",
    "step_06_read_edges_and_slots": "Read Edges & Slots",
    "step_07_arrange_patterns":   "Arrange Patterns",
    "step_08_apply_fabric":       "Apply Fabric",
    "step_09_create_seams":       "Create Seams",
    "step_10_simulate":           "Simulate",
    "step_11_export_note":         "Export GLB",
    "step_12_texture_glb":         "GLB Texture Inject",
}


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_report(ctx, overall_ok, step_results):
    return {
        "status": "completed" if overall_ok else "failed",
        "created_at": _utc_now_iso_z(),
        "mode": "default_panels" if ctx.use_default_panels else "generated_panels",
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


def _resolve_texture_paths(patterns_dir: Path) -> dict:
    """Resolve texture artifact paths from a generated panels_dir.

    patterns_dir is typically …/panels/dxf so:
      colors.json     → …/image_info/colors.json   (two levels up)
      textures_dir    → …/panels/textures           (sibling of dxf)
      graphic_diffuse → …/image_info/graphic_diffuse.png
    """
    run_dir = patterns_dir.parent.parent  # panels/dxf → panels → run_dir
    image_info = run_dir / "image_info"
    return {
        "colors_json_path":     image_info / "colors.json",
        "textures_dir":         patterns_dir.parent / "textures",
        "graphic_diffuse_path": image_info / "graphic_diffuse.png",
    }


def _resolve_texture_paths_from_ingestion(ingestion_output_dir: Path) -> dict:
    """Resolve texture artifact paths from an explicit ingestion output dir.

    Used when use_default_panels=True — the panels_dir is the default_panels
    folder, so texture artifacts must come from the product ingestion run.

    ingestion_output_dir is the root run dir (contains image_info/ and panels/).
    """
    image_info = ingestion_output_dir / "image_info"
    return {
        "colors_json_path":     image_info / "colors.json",
        "textures_dir":         ingestion_output_dir / "panels" / "textures",
        "graphic_diffuse_path": image_info / "graphic_diffuse.png",
    }


def _step_extras(step_num: int, ctx) -> dict:
    """Return a {label: value} dict of key paths/state for the step header.

    Values are pre-formatted strings so step_header just prints them.  Each
    step shows only the fields relevant to its own work, with EXISTS checks
    so problems are visible before the step runs.
    """
    def _ep(path) -> str:
        p = Path(path)
        return f"{p}  ({'EXISTS' if p.exists() else 'MISSING'})"

    if step_num == 1:
        return {"CLO URL": "http://127.0.0.1:50600"}

    if step_num == 2:
        return {"output_dir": str(ctx.output_dir)}

    if step_num == 3:
        return {"avatar": _ep(ctx.avatar_path)}

    if step_num == 4:
        dxf_count = len(list(ctx.patterns_dir.glob("*.dxf"))) if ctx.patterns_dir.exists() else 0
        return {
            "patterns_dir": (
                f"{ctx.patterns_dir}  "
                f"({'EXISTS' if ctx.patterns_dir.exists() else 'MISSING'}, {dxf_count} DXF)"
            ),
            "mode": "default_panels" if ctx.use_default_panels else "generated_panels",
        }

    if step_num == 5:
        return {"patterns_dir": _ep(ctx.patterns_dir)}

    if step_num == 6:
        manifest = ctx.patterns_dir.parent / "edge_manifest.json"
        return {
            "patterns_dir":  str(ctx.patterns_dir),
            "edge_manifest": _ep(manifest),
        }

    if step_num == 8:
        colors   = ctx.colors_json_path    or (ctx.patterns_dir.parent.parent / "image_info" / "colors.json")
        textures = ctx.textures_dir        or (ctx.patterns_dir.parent / "textures")
        graphic  = ctx.graphic_diffuse_path or (ctx.patterns_dir.parent.parent / "image_info" / "graphic_diffuse.png")
        tex_exists = Path(textures).exists()
        tex_count  = len(list(Path(textures).glob("*.png"))) if tex_exists else 0
        return {
            "colors_json"    : _ep(colors),
            "textures_dir"   : (
                f"{textures}  "
                f"({'EXISTS' if tex_exists else 'MISSING'}"
                f"{f', {tex_count} PNGs' if tex_exists else ''})"
            ),
            "graphic_diffuse": _ep(graphic),
        }

    if step_num == 9:
        return {"seams": f"{len(ctx.seams)} defined"}

    if step_num == 11:
        return {"output_dir": str(ctx.output_dir)}

    if step_num == 12:
        def _ep(path) -> str:
            p = Path(path)
            return f"{p}  ({'EXISTS' if p.exists() else 'MISSING'})"
        glb      = getattr(ctx, "glb_path", None)
        colors   = getattr(ctx, "colors_json_path", None)
        textures = getattr(ctx, "textures_dir", None)
        tex_exists = textures and Path(textures).exists()
        tex_count  = len(list(Path(textures).glob("*.png"))) if tex_exists else 0
        return {
            "source_glb":  _ep(glb) if glb else "not set — step 11 may not have run",
            "colors_json": _ep(colors) if colors else "not set",
            "textures_dir": (
                f"{textures}  "
                f"({'EXISTS' if tex_exists else 'MISSING'}"
                f"{f', {tex_count} PNGs' if tex_exists else ''})"
            ) if textures else "not set",
            "skip_postprocess": str(getattr(ctx, "skip_glb_postprocess", False)),
        }

    return {}


def run_pipeline(
    seam_map=None,
    avatar_path: str | None = None,
    patterns_dir: str | None = None,
    csv_path: str | None = None,
    report_path: str | None = None,
    use_default_panels: bool = False,
    ingestion_output_dir: str | None = None,
):
    """Run the isolated CLO-native VTO pipeline.

    Parameters
    ----------
    use_default_panels : bool
        When True, the pipeline imports DXF panels from
        clo_vto/default_panels/dxf/ instead of running panel generation.
        Texture artifact paths are taken from ingestion_output_dir.
    ingestion_output_dir : str | None
        Root of the product ingestion run output (the directory that contains
        image_info/ and panels/). Required when use_default_panels=True to
        locate colors.json and the texture atlases.
    """
    pipeline_start = time.monotonic()

    ctx = create_context(
        seam_map=seam_map,
        avatar_path=avatar_path,
        patterns_dir=patterns_dir,
        use_default_panels=use_default_panels,
        ingestion_output_dir=ingestion_output_dir,
    )
    setattr(ctx, "native_measurement_csv", Path(csv_path) if csv_path else None)

    # Resolve texture artifact paths.
    if use_default_panels and ingestion_output_dir:
        texture_paths = _resolve_texture_paths_from_ingestion(
            Path(ingestion_output_dir).resolve()
        )
    else:
        texture_paths = _resolve_texture_paths(ctx.patterns_dir)

    for attr, val in texture_paths.items():
        setattr(ctx, attr, val)

    # ── Pipeline header ──────────────────────────────────────────────────────
    print("\n" + "═" * 64)
    print("  CLO Native-Avatar Virtual Try-On Pipeline")
    print("═" * 64)
    mode_label = "DEFAULT PANELS" if use_default_panels else "GENERATED PANELS"
    print(f"  Mode          : {mode_label}")
    print(f"  Avatar        : {ctx.avatar_path}")
    print(f"  Patterns dir  : {ctx.patterns_dir}")
    print(f"  colors.json   : {ctx.colors_json_path}  (exists={Path(ctx.colors_json_path).exists() if ctx.colors_json_path else False})")
    print(f"  Textures dir  : {ctx.textures_dir}  (exists={Path(ctx.textures_dir).exists() if ctx.textures_dir else False})")
    if csv_path:
        print(f"  Measurement   : {csv_path}")
    if use_default_panels and not ingestion_output_dir:
        print("  [WARN] use_default_panels=True but no ingestion_output_dir given.")
        print("         Texture/color steps will skip gracefully (no artifacts found).")
    print("═" * 64)

    steps = [
        (1,  step_01_health),
        (2,  step_02_new_project),
        (3,  step_03_import_avatar),
        (4,  step_04_import_patterns),
        (5,  step_05_verify_patterns),
        (6,  step_06_read_edges_and_slots),
        (7,  step_07_arrange_patterns),
        (8,  step_08_apply_fabric),
        (9,  step_09_create_seams),
        (10, step_10_simulate),
        (11, step_11_export_glb),
        (12, step_12_texture_glb),
    ]

    step_results = []
    overall_ok = True

    for step_num, step_fn in steps:
        module_name = getattr(step_fn, "__module__", "").split(".")[-1]
        step_name = _STEP_NAMES.get(module_name, module_name)
        t0 = step_header(step_num, step_name, extras=_step_extras(step_num, ctx))

        try:
            ok = bool(step_fn(ctx))
        except Exception as exc:
            ok = False
            step_footer(step_num, t0, ok=False, reason=str(exc))
            step_results.append({"step": module_name, "name": step_name, "success": False, "error": str(exc)})
            overall_ok = False
            break

        elapsed = time.monotonic() - t0
        step_footer(step_num, t0, ok=ok)
        step_results.append({"step": module_name, "name": step_name, "success": ok, "duration_s": round(elapsed, 2)})

        if not ok:
            overall_ok = False
            break

    # ── Pipeline footer ──────────────────────────────────────────────────────
    total_elapsed = time.monotonic() - pipeline_start
    print("\n" + "═" * 64)
    try:
        final = ctx.client.get_status()
        succeeded = sum(1 for r in final.get("last_results", []) if r.get("success"))
        total = len(final.get("last_results", []))
    except Exception:
        succeeded, total = 0, 0

    if overall_ok:
        print(f"  Pipeline complete ✓  ({total_elapsed:.1f}s total)")
    else:
        failed_step = next((r for r in step_results if not r["success"]), {})
        print(f"  Pipeline FAILED ✗  at [{failed_step.get('name', '?')}]  ({total_elapsed:.1f}s total)")
    print(f"  CLO queue results: {succeeded}/{total} succeeded")
    print("═" * 64)

    report = _build_report(ctx, overall_ok, step_results)
    if report_path:
        try:
            p = Path(report_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"  Report → {p}")
        except Exception as exc:
            print(f"  [WARN] Failed to write pipeline report: {exc}")

    return overall_ok
