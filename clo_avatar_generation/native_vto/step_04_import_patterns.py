"""Step 4: Import DXF pattern pieces."""

import hashlib
from pathlib import Path

try:
    import ezdxf
    from ezdxf import units as ezdxf_units
except Exception:
    ezdxf = None
    ezdxf_units = None

from .helpers import print_result


def _read_dxf_bbox(dxf_path: Path):
    """Return (min_x, min_y, max_x, max_y) from polyline-like entities."""
    if ezdxf is None:
        return None

    try:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
        points = []

        for entity in msp:
            dtype = entity.dxftype()
            layer = str(getattr(entity.dxf, "layer", "")).lower()
            cutline = layer in ("cutline", "0")

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
                if not cutline:
                    continue
                try:
                    s = entity.dxf.start
                    e = entity.dxf.end
                    points.append((float(s[0]), float(s[1])))
                    points.append((float(e[0]), float(e[1])))
                except Exception:
                    pass
            elif dtype == "SPLINE":
                # New format: SPLINE entities on CutLine layer.
                # We export using add_spline(fit_points=...) so ezdxf stores
                # data in fit_points, not control_points.  Try fit_points
                # first; only fall back to control_points if fit_points empty.
                if not cutline:
                    continue
                try:
                    collected = []
                    try:
                        for fp in entity.fit_points:
                            collected.append((float(fp[0]), float(fp[1])))
                    except Exception:
                        pass
                    if not collected:
                        for cp in entity.control_points:
                            collected.append((float(cp[0]), float(cp[1])))
                    points.extend(collected)
                except Exception:
                    pass

        if not points:
            return None

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (min(xs), min(ys), max(xs), max(ys))
    except Exception:
        return None


def _bbox_ok(dxf_path: Path):
    """Basic garment panel dimension guard in cm-like units.

    Typical tshirt panel dimensions should not be near-zero or multi-meter scale.
    """
    bbox = _read_dxf_bbox(dxf_path)
    if bbox is None:
        return True, None
    min_x, min_y, max_x, max_y = bbox
    width = max_x - min_x
    height = max_y - min_y
    # Accept either cm-like coordinates or mm-like coordinates.
    cm_ok = 5.0 <= width <= 300.0 and 5.0 <= height <= 300.0
    mm_ok = 50.0 <= width <= 3000.0 and 50.0 <= height <= 3000.0
    ok = cm_ok or mm_ok
    return ok, (width, height)


def _recommended_import_scale(dxf_path: Path) -> float:
    """Return CLO import scale from DXF units.

    Contract used by this pipeline:
    - DXF exported in millimeters -> CLO scene centimeters => scale 0.1
    - Otherwise fallback to 1.0
    """
    if ezdxf is None:
        return 1.0
    try:
        doc = ezdxf.readfile(str(dxf_path))
        if ezdxf_units is not None and int(getattr(doc, "units", 0)) == int(ezdxf_units.MM):
            return 0.1
    except Exception:
        pass
    return 1.0


def run(ctx):
    print("\n[4] Importing patterns ...")
    ctx.imported_files = []
    ctx.imported_pieces = []
    ctx.piece_to_index = {}
    ctx.index_to_piece = {}
    ctx.pattern_import_scales = {}
    ctx.pattern_hashes = {}
    ctx.pattern_geometry_hash = ""

    before_count_resp = ctx.client.get_pattern_count()
    before_count = int(before_count_resp.get("count", 0)) if before_count_resp.get("success", True) else 0
    print(f"  Patterns before import: {before_count}")

    for fname in ctx.pattern_files:
        path = ctx.patterns_dir / fname
        if not path.exists():
            print(f"  ! Pattern not found: {path}")
            continue

        logical_piece = fname.replace(".dxf", "")
        try:
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            ctx.pattern_hashes[logical_piece] = file_hash
        except Exception:
            pass

        size_ok, dims = _bbox_ok(path)
        if dims is not None:
            w, h = dims
            print(f"  DXF bbox {fname}: width={w:.2f} height={h:.2f}")
        if not size_ok:
            print(f"  ! Size sanity failed for {fname} - likely wrong units/scale. Aborting import stage.")
            return False

        import_scale = _recommended_import_scale(path)
        ctx.pattern_import_scale = import_scale
        ctx.pattern_import_scales[logical_piece] = import_scale

        result = ctx.client.import_pattern(str(path), scale=import_scale)
        if print_result(result, fname):
            ctx.imported_files.append(fname)
            ctx.imported_pieces.append(logical_piece)

    print("     Waiting for CLO to finish imports ...")
    ctx.client.wait_for_queue(timeout=60)

    status = ctx.client.get_status()
    last_results = status.get("last_results", [])
    import_failures = [
        r for r in last_results
        if r.get("type") == "import-pattern" and not r.get("success", False)
    ]
    if import_failures:
        print("  CLO reported pattern import failures:")
        for r in import_failures:
            print(f"    - {r.get('message', 'Unknown import failure')}")
        return False

    after_count_resp = ctx.client.get_pattern_count()
    after_count = int(after_count_resp.get("count", 0)) if after_count_resp.get("success", True) else 0
    expected_new = len(ctx.imported_pieces)
    print(f"  Patterns after import: {after_count}")

    if after_count - before_count != expected_new:
        print(
            "  Import identity mapping failed - expected "
            f"{expected_new} new patterns, got {after_count - before_count}."
        )
        return False

    for offset, piece in enumerate(ctx.imported_pieces):
        idx = before_count + offset
        ctx.piece_to_index[piece] = idx
        ctx.index_to_piece[idx] = piece

    if ctx.pattern_hashes:
        ordered = [ctx.pattern_hashes[p] for p in sorted(ctx.pattern_hashes.keys())]
        ctx.pattern_geometry_hash = hashlib.sha256("|".join(ordered).encode("utf-8")).hexdigest()

    print(f"  Piece to index mapping: {ctx.piece_to_index}")
    if ctx.pattern_geometry_hash:
        print(f"  Pattern geometry hash: {ctx.pattern_geometry_hash[:12]}...")

    if len(ctx.imported_files) != len(ctx.pattern_files):
        print(
            "  Import stage failed - imported "
            f"{len(ctx.imported_files)}/{len(ctx.pattern_files)} expected pieces."
        )
        return False

    return True
