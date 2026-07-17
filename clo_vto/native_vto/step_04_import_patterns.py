"""Step 4: Import DXF pattern pieces."""

import hashlib
import time
from pathlib import Path

try:
    import ezdxf
    from ezdxf import units as ezdxf_units
except Exception:
    ezdxf = None
    ezdxf_units = None

from .helpers import print_result


def _collect_entity_points(entity, points: list) -> None:
    """Append (x, y) points from one polyline-like entity onto points."""
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
            return
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
            return
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


def _read_dxf_bbox(dxf_path: Path):
    """Return (min_x, min_y, max_x, max_y) from polyline-like entities.

    Also resolves geometry nested inside INSERT/BLOCK references (via
    virtual_entities(), which yields the block's entities pre-transformed
    into modelspace coordinates) — CLO's own DXF export wraps each pattern
    piece's outline inside a block insert rather than placing it directly in
    modelspace, so without this the sanity check below silently no-ops
    (returns "ok, unknown size") on exactly the files it most needs to check.
    """
    if ezdxf is None:
        return None

    try:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
        points = []

        for entity in msp:
            if entity.dxftype() == "INSERT":
                try:
                    for sub_entity in entity.virtual_entities():
                        _collect_entity_points(sub_entity, points)
                except Exception:
                    pass
            else:
                _collect_entity_points(entity, points)

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


_SCALE_UNKNOWN = object()   # sentinel — units could not be determined


def _recommended_import_scale(dxf_path: Path):
    """Return CLO import scale from DXF units, or _SCALE_UNKNOWN.

    Contract used by this pipeline:
    - DXF exported in millimeters -> CLO scene centimeters => scale 0.1
    - Unknown/unreadable units => returns _SCALE_UNKNOWN sentinel (P10).
    """
    if ezdxf is None:
        return _SCALE_UNKNOWN
    try:
        doc = ezdxf.readfile(str(dxf_path))
        if ezdxf_units is not None and int(getattr(doc, "units", 0)) == int(ezdxf_units.MM):
            return 0.1
        # Units present but not MM — return unknown so caller can decide.
        return _SCALE_UNKNOWN
    except Exception:
        return _SCALE_UNKNOWN


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

    current_count = before_count
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
            print(f"  ! Size sanity failed for {fname} - likely wrong units/scale. Aborting.")
            return False

        raw_scale = _recommended_import_scale(path)
        if raw_scale is _SCALE_UNKNOWN:
            if ctx.strict_dxf_units:
                print(
                    f"  ! DXFUnitError: units unreadable in {fname} "
                    "and strict_dxf_units=True. Aborting import."
                )
                return False
            # Every DXF this pipeline produces or hand-exports is millimetres
            # (panel_export_dxf.py sets doc.units = MM explicitly; the hand-exported
            # default_panels/ files are DXF R12, which ezdxf cannot write $INSUNITS
            # into at all, so they always land here). A scale-1.0 fallback silently
            # imported every default panel at ~10x its real size (front_panel's true
            # outline is 580x718 raw units = 58x72cm at the correct 0.1 scale, vs an
            # absurd 5.8x7.2m "shirt" at the old fallback) — a very plausible trigger
            # for CLO's seam-creation crash on grossly oversized geometry. 0.1 matches
            # this pipeline's one actual convention instead of guessing cm.
            print(f"  WARNING: DXF units unreadable for {fname}; assuming mm, using scale 0.1 (debug mode).")
            import_scale = 0.1
        else:
            import_scale = raw_scale
        ctx.pattern_import_scale = import_scale
        ctx.pattern_import_scales[logical_piece] = import_scale

        # Import one pattern at a time and wait for CLO to finish before the next.
        # This avoids the last_results buffer cap (only N results kept) and the
        # race condition where queue_size drops to 0 before all results are written.
        queued_ok = print_result(ctx.client.import_pattern(str(path), scale=import_scale), fname)
        if not queued_ok:
            print(f"  ! Plugin rejected {fname}.")
            continue

        try:
            ctx.client.wait_for_queue(timeout=30)
        except Exception as exc:
            print(f"  [WARN] {fname} import drain timed out: {exc} — checking pattern count anyway.")

        # Verify via pattern count — more reliable than last_results.
        resp = ctx.client.get_pattern_count()
        new_count = int(resp.get("count", 0)) if resp.get("success", True) else current_count

        if new_count <= current_count:
            # One retry after a short pause — handles transient CLO state issues.
            print(f"  ⚠  {fname} not yet in scene, retrying in 2s …")
            time.sleep(2.0)
            print_result(ctx.client.import_pattern(str(path), scale=import_scale), f"{fname} (retry)")
            try:
                ctx.client.wait_for_queue(timeout=30)
            except Exception as exc:
                print(f"  [WARN] {fname} retry drain timed out: {exc}")
            resp = ctx.client.get_pattern_count()
            new_count = int(resp.get("count", 0)) if resp.get("success", True) else current_count

        if new_count > current_count:
            idx = new_count - 1
            ctx.piece_to_index[logical_piece] = idx
            ctx.index_to_piece[idx] = logical_piece
            ctx.imported_files.append(fname)
            ctx.imported_pieces.append(logical_piece)
            current_count = new_count
            print(f"    → piece index {idx}")
        else:
            print(f"  ! {fname} failed to import (pattern count unchanged after retry).")

    after_count = current_count
    print(f"  Patterns after import: {after_count}")

    if ctx.pattern_hashes:
        ordered = [ctx.pattern_hashes[p] for p in sorted(ctx.pattern_hashes.keys())]
        ctx.pattern_geometry_hash = hashlib.sha256("|".join(ordered).encode("utf-8")).hexdigest()

    print(f"  Piece to index mapping: {ctx.piece_to_index}")
    if ctx.pattern_geometry_hash:
        print(f"  Pattern geometry hash: {ctx.pattern_geometry_hash[:12]}...")

    if len(ctx.imported_files) != len(ctx.pattern_files):
        print(
            f"  Import stage failed - imported "
            f"{len(ctx.imported_files)}/{len(ctx.pattern_files)} expected pieces."
        )
        return False

    return True
