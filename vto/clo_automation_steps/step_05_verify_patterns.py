"""Step 5: Verify pattern count after import."""

import json
from pathlib import Path

try:
    import ezdxf
except Exception:
    ezdxf = None


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _read_dxf_bbox(dxf_path: Path):
    if ezdxf is None:
        return None
    try:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
        points = []
        for entity in msp:
            dtype = entity.dxftype()
            if dtype == "LWPOLYLINE":
                try:
                    for p in entity.get_points("xy"):
                        points.append((float(p[0]), float(p[1])))
                except Exception:
                    pass
            elif dtype == "POLYLINE":
                try:
                    for v in entity.vertices:
                        loc = v.dxf.location
                        points.append((float(loc[0]), float(loc[1])))
                except Exception:
                    pass
            elif dtype == "LINE":
                try:
                    s = entity.dxf.start
                    e = entity.dxf.end
                    points.append((float(s[0]), float(s[1])))
                    points.append((float(e[0]), float(e[1])))
                except Exception:
                    pass
        if not points:
            return None
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)
    except Exception:
        return None


def _panel_height_raw_units(ctx):
    # Prefer torso panels for calibration.
    preferred = ["front_panel.dxf", "back_panel.dxf"]
    heights = []
    for name in preferred:
        p = ctx.patterns_dir / name
        if not p.exists():
            continue
        bbox = _read_dxf_bbox(p)
        if bbox:
            heights.append(float(bbox[3] - bbox[1]))
    if not heights:
        return None
    return max(heights)


def _extract_scale_debug(ctx):
    caps = ctx.client.get_capabilities()
    if caps.get("success"):
        ctx.sdk_capabilities = caps

    debug = ctx.client.get_import_scale_debug()
    if debug.get("success"):
        ctx.import_scale_debug = debug

    avatar_scale = 1.0
    pattern_scale = ctx.pattern_import_scale or 1.0

    avatar_debug = ctx.import_scale_debug.get("avatar_import", {})
    if isinstance(avatar_debug, dict):
        avatar_scale = float(avatar_debug.get("scale", avatar_scale) or avatar_scale)

    pattern_debug = ctx.import_scale_debug.get("pattern_imports", [])
    if isinstance(pattern_debug, list) and pattern_debug:
        scales = []
        for row in pattern_debug:
            try:
                scales.append(float(row.get("scale", 0) or 0))
            except Exception:
                pass
        scales = [s for s in scales if s > 0]
        if scales:
            pattern_scale = sum(scales) / len(scales)

    return avatar_scale, pattern_scale


def _run_scale_calibration(ctx):
    """Calibrate using scene-size estimate + metadata fallback.

    Scene estimate is derived from:
    - avatar export dimensions
    - actual import scale used by plugin
    - DXF panel bbox and import scale
    """
    avatar_meta_path = ctx.avatar_path.parent / "measurements.json"
    panel_meta_path = ctx.patterns_dir.parent / "panel_metadata.json"

    avatar_meta = _load_json(avatar_meta_path)
    panel_meta = _load_json(panel_meta_path)

    if not avatar_meta or not panel_meta:
        print("  Scale calibration skipped - missing measurements or panel metadata.")
        return True

    body = avatar_meta.get("measurements", {})
    garment = panel_meta.get("garment_measurements", {})

    body_chest = float(body.get("chest_circumference_cm", 0) or 0)
    body_height = float(body.get("height_cm", 0) or 0)
    half_chest = float(garment.get("half_chest_width", 0) or 0)
    garment_length = float(garment.get("garment_length", 0) or 0)

    if body_chest <= 0 or body_height <= 0 or half_chest <= 0 or garment_length <= 0:
        print("  Scale calibration skipped - insufficient numeric fields in metadata.")
        return True

    chest_ratio = half_chest / (body_chest / 2.0)
    length_ratio = garment_length / body_height

    avatar_scale_used, pattern_scale_used = _extract_scale_debug(ctx)
    panel_height_raw = _panel_height_raw_units(ctx)

    mesh_stats = avatar_meta.get("mesh_stats", {}) if isinstance(avatar_meta, dict) else {}
    bounds_min = mesh_stats.get("bounds_min_cm", [])
    bounds_max = mesh_stats.get("bounds_max_cm", [])

    avatar_height_export_cm = body_height
    if len(bounds_min) >= 2 and len(bounds_max) >= 2:
        try:
            avatar_height_export_cm = abs(float(bounds_max[1]) - float(bounds_min[1]))
        except Exception:
            avatar_height_export_cm = body_height

    # avatar_height_export_cm is already in cm (the target body height).
    # The import scale was chosen to achieve that height in CLO (cm scene).
    # Do NOT multiply again by avatar_scale_used — that would double-count.
    scene_avatar_height_est = avatar_height_export_cm
    scene_panel_height_est = None
    scene_length_ratio_est = None
    if panel_height_raw and pattern_scale_used > 0:
        scene_panel_height_est = panel_height_raw * pattern_scale_used
        if scene_avatar_height_est > 0:
            scene_length_ratio_est = scene_panel_height_est / scene_avatar_height_est

    ctx.scale_metrics = {
        "body_chest_cm": body_chest,
        "body_height_cm": body_height,
        "garment_half_chest_cm": half_chest,
        "garment_length_cm": garment_length,
        "chest_ratio": chest_ratio,
        "length_ratio": length_ratio,
        "avatar_import_scale_used": avatar_scale_used,
        "pattern_import_scale_used": pattern_scale_used,
        "avatar_height_export_cm": avatar_height_export_cm,
        "panel_height_raw_units": panel_height_raw,
        "scene_avatar_height_est": scene_avatar_height_est,
        "scene_panel_height_est": scene_panel_height_est,
        "scene_length_ratio_est": scene_length_ratio_est,
    }

    print(
        "  Scale metrics - "
        f"chest_ratio:{chest_ratio:.3f} length_ratio:{length_ratio:.3f}"
    )
    if scene_length_ratio_est is not None:
        print(
            "  Scene-estimated scale - "
            f"panel/avatar length ratio:{scene_length_ratio_est:.3f} "
            f"(panel~{scene_panel_height_est:.1f}, avatar~{scene_avatar_height_est:.1f})"
        )

        if scene_length_ratio_est < 0.15 or scene_length_ratio_est > 0.90:
            suggested = None
            if panel_height_raw and scene_avatar_height_est > 0:
                # Target torso panel length ~= 40% of body height in scene units.
                suggested = (scene_avatar_height_est * 0.40) / panel_height_raw
                ctx.scale_metrics["suggested_pattern_import_scale"] = suggested
            ctx.scale_metrics["scene_scale_warning"] = True
            if suggested is not None:
                print(
                    "  Scene-estimated scale calibration warning - "
                    f"ratio {scene_length_ratio_est:.3f} is out of range. "
                    f"Suggested pattern import scale: {suggested:.4f}. Continuing for downstream diagnostics."
                )
            else:
                print(
                    "  Scene-estimated scale calibration warning - "
                    f"ratio {scene_length_ratio_est:.3f} is out of range. Continuing for downstream diagnostics."
                )
            return True

    # Broad, non-hardcoded guardrails to catch unit explosions.
    if chest_ratio < 0.75 or chest_ratio > 1.45:
        print(
            "  Scale calibration failed - garment/body chest ratio is out of range "
            f"({chest_ratio:.3f})."
        )
        return False

    if length_ratio < 0.25 or length_ratio > 0.65:
        print(
            "  Scale calibration failed - garment/body length ratio is out of range "
            f"({length_ratio:.3f})."
        )
        return False

    return True


def run(ctx):
    print("\n[5] Verifying pattern count ...")
    status = ctx.client.get_status()
    ctx.loaded_patterns = status.get("patterns_loaded", 0)
    print(f"  Patterns in CLO scene: {ctx.loaded_patterns} (expected {len(ctx.pattern_files)})")

    if ctx.loaded_patterns != len(ctx.pattern_files):
        print("  Pattern count mismatch - expected all 4 pieces. Aborting.")
        return False

    actual_names = []
    for idx in range(ctx.loaded_patterns):
        info = ctx.client.get_pattern_info(idx)
        name = info.get("info", {}).get("name", "")
        actual_names.append(name)

    ctx.imported_pattern_names = actual_names
    print("  SDK-reported names:", actual_names)

    # Do not gate on SDK names - they can be numeric/non-semantic in some CLO builds.
    if len(ctx.piece_to_index) != len(ctx.pattern_files):
        print(
            "  Import identity map is incomplete - expected "
            f"{len(ctx.pattern_files)} mapped pieces, got {len(ctx.piece_to_index)}."
        )
        return False

    if len(set(ctx.piece_to_index.values())) != len(ctx.pattern_files):
        print("  Import identity map has duplicate pattern indices. Aborting.")
        return False

    if not _run_scale_calibration(ctx):
        return False

    if ctx.loaded_patterns == 0:
        print("  No patterns loaded - check file paths and DXF format. Aborting.")
        return False
    return True
