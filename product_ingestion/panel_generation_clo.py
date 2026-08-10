"""Canonical Step 2 panel generation, backed by the CLO reference block.

Drop-in replacement for `panel_generation.generate_panels`: same signature,
same `PanelGenerationResult`, same output layout under `panels_dir`.  Swapping
it in is a one-line import change in `run_product_ingestion.py`.

Units
-----
This is the part that needs care.  Three different unit conventions meet here:

    sizes collection   centimetres
    CloTShirtDraft     millimetres  (the fitted constants are in mm)
    texture_projection centimetres  (PX_PER_CM = 10)
    DXF for CLO        millimetres  ($INSUNITS = 4, CLO imports at scale 0.1)

So the draft is built in mm, exported to DXF in mm, and a scaled copy of the
layouts is handed to the SVG exporter and to `texture_projection` in cm.  The
`PanelGenerationResult.layouts` returned to the caller are the **cm** copies,
matching what the old generator returned, so `texture_projection` needs no
change at all.

Measurement conventions
-----------------------
`GarmentMeasurements`' docstrings do not describe what `panels.py` actually
does with the fields.  The docstring claims `shoulder_width` is a half span;
`panels.py` line 287 computes `center_x + shoulder_width / 2`, so it is the
FULL span.  Likewise `half_chest_width` is used as the full flat panel width,
not a half.  The mapping below follows the code, which is what the seeded
sizes in `mirra_measurements/seed_sizes.py` were authored against.

Two fields the sizes collection does not carry are derived from the CLO
reference block's own proportions:

    hem_half_width    0.930697 x half_chest_width   (the side seam taper)
    wrist_full_width  0.783952 x bicep_full_width   (the sleeve taper)

Add `hem_width_cm` and `wrist_width_cm` to the sizes documents and they will
be used instead.  Until then a straight-sided tee is impossible to express,
which is why the old panels came out boxy.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .garment_measurements import GarmentMeasurements
    from .curve_segment import CubicBezierSegment, PieceEdge, PieceLayout
    from .panel_export_svg import export_panels_svg
    from .clo_block.clo_draft import CloTShirtDraft
    from .clo_block.clo_draft_config import CloBlockMeasurements, CloDraftConfig
    from .clo_block.clo_dxf_writer import write_pattern_set
except ImportError:  # pragma: no cover - direct script use
    from garment_measurements import GarmentMeasurements  # type: ignore
    from curve_segment import CubicBezierSegment, PieceEdge, PieceLayout  # type: ignore
    from panel_export_svg import export_panels_svg  # type: ignore
    from clo_block.clo_draft import CloTShirtDraft  # type: ignore
    from clo_block.clo_draft_config import CloBlockMeasurements, CloDraftConfig  # type: ignore
    from clo_block.clo_dxf_writer import write_pattern_set  # type: ignore


# Ratios taken from the CLO reference block; used only when the sizes document
# does not carry the field.
HEM_TO_CHEST_RATIO = 269.9999 / 290.0975      # 0.930697
WRIST_TO_BICEP_RATIO = 384.3506 / 490.2734    # 0.783952

MM_PER_CM = 10.0


@dataclass
class PanelGenerationResult:
    """Paths and metadata for generated panel outputs.

    Field-for-field identical to the old `panel_generation.PanelGenerationResult`
    so callers do not change.  `layouts` are in CENTIMETRES.
    """

    panels_dir: Path
    dxf_dir: Path
    svg_dir: Path
    metadata_path: Path
    manifest_path: Path
    panel_names: List[str]
    layouts: Optional[dict] = None
    draft: Optional[CloTShirtDraft] = None   # mm-space draft, for diagnostics


# --------------------------------------------------------------------------- #
# Measurement translation                                                       #
# --------------------------------------------------------------------------- #

def garment_to_clo_block(
    m: GarmentMeasurements,
    *,
    hem_width_cm: Optional[float] = None,
    wrist_width_cm: Optional[float] = None,
    label: str = "M",
) -> CloBlockMeasurements:
    """Translate a `GarmentMeasurements` (cm) into a `CloBlockMeasurements` (mm).

    `hem_width_cm` and `wrist_width_cm` are the full flat widths.  Pass them
    when the sizes document has them; otherwise the CLO reference ratios apply.
    """
    half_chest = m.half_chest_width * MM_PER_CM / 2.0
    shoulder_half = m.shoulder_width * MM_PER_CM / 2.0

    # panels.py clamps the neck opening to 60% of the shoulder span; keep the
    # same guard so existing size rows that violate it still generate.
    neck_full_cm = min(float(m.neck_width), m.shoulder_width * 0.60)
    neck_half = neck_full_cm * MM_PER_CM / 2.0

    bicep_full = m.bicep_width * 2.0 * MM_PER_CM

    hem_half = (hem_width_cm * MM_PER_CM / 2.0 if hem_width_cm is not None
                else half_chest * HEM_TO_CHEST_RATIO)
    wrist_full = (wrist_width_cm * MM_PER_CM if wrist_width_cm is not None
                  else bicep_full * WRIST_TO_BICEP_RATIO)

    block = CloBlockMeasurements(
        half_chest_width=half_chest,
        hem_half_width=hem_half,
        garment_length=m.garment_length * MM_PER_CM,
        shoulder_half_width=shoulder_half,
        neck_half_width=neck_half,
        neck_depth_front=m.neck_depth_front * MM_PER_CM,
        neck_depth_back=m.neck_depth_back * MM_PER_CM,
        armhole_depth=m.armhole_depth * MM_PER_CM,
        bicep_full_width=bicep_full,
        wrist_full_width=wrist_full,
        underarm_to_wrist=m.sleeve_length * MM_PER_CM,
        label=label,
    )
    block.validate()
    return block


def clo_block_from_size_doc(doc: dict, label: str = "M") -> CloBlockMeasurements:
    """Build directly from a sizes-collection document, skipping the old dataclass."""
    return garment_to_clo_block(
        GarmentMeasurements(
            body_height=175.0, body_chest=0.0,
            body_shoulder=doc["shoulder_width_cm"],
            half_chest_width=doc["half_chest_width_cm"],
            garment_length=doc["garment_length_cm"],
            shoulder_width=doc["shoulder_width_cm"],
            neck_width=doc["neck_width_cm"],
            neck_depth_front=doc["neck_depth_front_cm"],
            neck_depth_back=doc["neck_depth_back_cm"],
            sleeve_length=doc["sleeve_length_cm"],
            bicep_width=doc["bicep_width_cm"],
            armhole_depth=doc["armhole_depth_cm"],
            seam_allowance=doc.get("seam_allowance_cm", 1.0),
            fit_type=doc.get("fit_type", "regular"),
        ),
        hem_width_cm=doc.get("hem_width_cm"),
        wrist_width_cm=doc.get("wrist_width_cm"),
        label=label,
    )


# --------------------------------------------------------------------------- #
# Proportion diagnostics                                                        #
# --------------------------------------------------------------------------- #

# On the CLO reference block the total cap arc is 1.1242 x the unfolded bicep
# width. That ratio is what makes the cap height land at a wearable 0.244 of
# the bicep instead of spiking.
CAP_ARC_OVER_BICEP = 551.1767 / 490.2734


def recommend_bicep_width_cm(measurements: GarmentMeasurements) -> dict:
    """Check whether a size row can produce a wearable sleeve, and say how to fix it.

    A sleeve cap has to be long enough to fill the armhole. If the bicep is too
    narrow for the armhole it has to fill, the solver still converges — but only
    by making the cap absurdly tall, which produces a spiked sleeve rather than
    a t-shirt one.

    Returns the current armhole length, the `bicep_width_cm` that would put the
    cap at the CLO reference proportion, and the `armhole_depth_cm` that would
    instead suit the bicep already recorded. Pick whichever is easier to change.
    """
    block = garment_to_clo_block(measurements)
    draft = CloTShirtDraft(block)
    draft.layouts["front_panel"] = draft._build_body_panel(is_front=True)
    draft.layouts["back_panel"] = draft._build_body_panel(is_front=False)

    try:
        from .clo_block.clo_draft import _arc_length as _al
    except ImportError:  # pragma: no cover
        from clo_block.clo_draft import _arc_length as _al  # type: ignore
    armhole = _al(draft.layouts["front_panel"].edges[2]) + \
        _al(draft.layouts["back_panel"].edges[2])

    cfg = draft.cfg
    mean_ease = (cfg.cap_ease_front_frac + cfg.cap_ease_back_frac) / 2.0
    needed_full = armhole * (1.0 + mean_ease) / CAP_ARC_OVER_BICEP

    return {
        "armhole_total_cm": round(armhole / MM_PER_CM, 2),
        "bicep_width_cm_now": measurements.bicep_width,
        "bicep_width_cm_recommended": round(needed_full / (2 * MM_PER_CM), 1),
        "armhole_depth_cm_now": measurements.armhole_depth,
        "armhole_depth_cm_alternative": round(
            measurements.armhole_depth * block.bicep_full_width / needed_full, 1
        ),
        "ok": abs(needed_full - block.bicep_full_width) / needed_full < 0.08,
    }


# --------------------------------------------------------------------------- #
# Unit scaling of layouts                                                       #
# --------------------------------------------------------------------------- #

def _scale_point(p, k: float):
    return (p[0] * k, p[1] * k)


def scale_layout(layout: PieceLayout, k: float) -> PieceLayout:
    """Return a copy of a PieceLayout with every coordinate multiplied by k."""
    edges: List[PieceEdge] = []
    for e in layout.edges:
        segs = [
            CubicBezierSegment(
                _scale_point(s.p0, k), _scale_point(s.p1, k),
                _scale_point(s.p2, k), _scale_point(s.p3, k),
            )
            for s in e.segments
        ]
        edges.append(PieceEdge(
            name=e.name, edge_type=e.edge_type,
            start=_scale_point(e.start, k), end=_scale_point(e.end, k),
            segments=segs,
        ))
    return PieceLayout(name=layout.name, edges=edges)


def scale_layouts(layouts: Dict[str, PieceLayout], k: float) -> Dict[str, PieceLayout]:
    return {name: scale_layout(lay, k) for name, lay in layouts.items()}


# --------------------------------------------------------------------------- #
# Metadata                                                                      #
# --------------------------------------------------------------------------- #

def write_panel_metadata(
    draft: CloTShirtDraft,
    measurements: GarmentMeasurements,
    output_path: Path,
) -> Path:
    """Write panel_metadata.json describing the generated block.

    Version 4.0.  The seam-matching block now reports the real relationship:
    negative cap ease, and the below/above-notch split that the old metadata
    had no way to express.
    """
    r = draft.seam_report()
    b, cfg = draft.m, draft.cfg

    metadata = {
        "garment_type": "tshirt",
        "version": "4.0",
        "generation_type": "clo-reference-block",
        "source": (
            "Shape constants fitted to the CLO Standalone 2026.0.300 default "
            "t-shirt DXF export (AAMA R12), size M."
        ),
        "units": {
            "block_mm": True,
            "layouts_returned_cm": True,
            "dxf_mm": True,
            "clo_import_scale": 0.1,
        },
        "garment_measurements_cm": {
            "half_chest_width": measurements.half_chest_width,
            "garment_length": measurements.garment_length,
            "shoulder_width": measurements.shoulder_width,
            "neck_width": measurements.neck_width,
            "neck_depth_front": measurements.neck_depth_front,
            "neck_depth_back": measurements.neck_depth_back,
            "sleeve_length": measurements.sleeve_length,
            "bicep_width": measurements.bicep_width,
            "armhole_depth": measurements.armhole_depth,
        },
        "block_measurements_mm": {
            "half_chest_width": round(b.half_chest_width, 3),
            "hem_half_width": round(b.hem_half_width, 3),
            "garment_length": round(b.garment_length, 3),
            "shoulder_half_width": round(b.shoulder_half_width, 3),
            "neck_half_width": round(b.neck_half_width, 3),
            "neck_depth_front": round(b.neck_depth_front, 3),
            "neck_depth_back": round(b.neck_depth_back, 3),
            "armhole_depth": round(b.armhole_depth, 3),
            "bicep_full_width": round(b.bicep_full_width, 3),
            "wrist_full_width": round(b.wrist_full_width, 3),
            "underarm_to_wrist": round(b.underarm_to_wrist, 3),
        },
        "derived_mm": {
            "shoulder_drop": round(draft.shoulder_drop, 3),
            "cap_height": r["cap_height_mm"],
            "cap_height_over_bicep": r["cap_height_over_bicep"],
            "peak_offset_toward_back": r["peak_offset_mm"],
            "back_neck_half_width": round(draft._back_neck_half(), 3),
            "back_shoulder_half_width": round(draft._back_shoulder_half(), 3),
        },
        "fit_details": {
            "fit_type": measurements.fit_type,
            "shoulder_slope": cfg.shoulder_slope,
            "underarm_seams_straight": cfg.underarm_straight,
            "side_seam": "straight taper (no waist suppression)",
            "shoulder_seam": "straight (no crown)",
            "hem": "straight",
        },
        "seam_matching_mm": {
            "front_armhole": r["front_armhole_mm"],
            "back_armhole": r["back_armhole_mm"],
            "armhole_total": r["armhole_total_mm"],
            "cap_front": r["cap_front_mm"],
            "cap_back": r["cap_back_mm"],
            "cap_total": r["cap_total_mm"],
            "ease": r["ease_mm"],
            "ease_pct": r["ease_pct"],
            "notch_from_underarm": r["notch_from_underarm_mm"],
            "below_notch_mismatch_front": r["below_notch_mismatch_front_mm"],
            "below_notch_mismatch_back": r["below_notch_mismatch_back_mm"],
            "above_notch_mismatch_front": r["above_notch_mismatch_front_mm"],
            "above_notch_mismatch_back": r["above_notch_mismatch_back_mm"],
            "solver_iterations": r["solver_iterations"],
            "note": (
                "Cap ease is negative by design: a jersey tee cap is cut short "
                "and stretched into the armhole. All of the mismatch sits above "
                "the notches; below them the seams match exactly."
            ),
        },
        "body_seams_mm": {
            "shoulder_front": r["shoulder_seam_mm"],
            "shoulder_back": r["back_shoulder_seam_mm"],
            "side": r["side_seam_mm"],
            "sleeve_tube_front": r["sleeve_tube_front_mm"],
            "sleeve_tube_back": r["sleeve_tube_back_mm"],
        },
        "panel_info": {
            "coordinates": "seam_line",
            "seam_allowances_included": cfg.seam_allowance_mm > 0,
            "seam_allowance_mm": cfg.seam_allowance_mm,
            "dxf_entities": "POLYLINE (R12 / AC1009)",
            "dxf_layers": {
                "1": "boundary (sewing line)",
                "2": "turn points",
                "3": "curve points",
                "4": "notches (Z=7.0, code 50 = inward normal angle)",
                "7": "grainline",
                "8": "internal construction lines",
            },
        },
        "panel_pieces": list(draft.layouts.keys()),
        "edge_counts": {p: len(draft.layouts[p].edges) for p in draft.layouts},
        "notch_counts": {p: len(draft.notches.get(p, [])) for p in draft.layouts},
        "clo_import_notes": [
            "DXF units millimetres ($INSUNITS = 4). CLO import scale 0.1.",
            "Front and back are 10 edges; sleeves are 5.",
            "Edge indices are 0-based and match edge_manifest.json.",
            "Sleeve cap arc is SHORTER than the armhole by ~2.3 percent.",
        ],
    }

    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"  Wrote panel metadata: {output_path.name}")
    return output_path


def write_edge_manifest(draft: CloTShirtDraft, output_path: Path) -> Path:
    """Write edge_manifest.json in the shape seams.py expects.

    `load_seams_from_manifest` looks up `{"name": ..., "index": ...}` per piece,
    so the extra `type`, `length_mm` and `role` keys are ignored by it and are
    there for humans and for step_06's edge-count validation.
    """
    output_path.write_text(json.dumps(draft.edge_manifest(), indent=2), encoding="utf-8")
    print(f"  Wrote edge manifest: {output_path.name}")
    return output_path


# --------------------------------------------------------------------------- #
# Entry point                                                                   #
# --------------------------------------------------------------------------- #

def generate_panels(
    measurements: GarmentMeasurements,
    panels_dir: Path,
    *,
    config: Optional[CloDraftConfig] = None,
    size_label: str = "M",
    hem_width_cm: Optional[float] = None,
    wrist_width_cm: Optional[float] = None,
) -> PanelGenerationResult:
    """Generate panels and export DXF/SVG/manifest artifacts.

    Signature-compatible with the old `panel_generation.generate_panels`.
    """
    panels_dir = Path(panels_dir)
    panels_dir.mkdir(parents=True, exist_ok=True)
    dxf_dir = panels_dir / "dxf"
    svg_dir = panels_dir / "svg"
    dxf_dir.mkdir(parents=True, exist_ok=True)
    svg_dir.mkdir(parents=True, exist_ok=True)

    block = garment_to_clo_block(
        measurements, hem_width_cm=hem_width_cm,
        wrist_width_cm=wrist_width_cm, label=size_label,
    )
    draft = CloTShirtDraft(block, config or CloDraftConfig())
    draft.build()

    # DXF in millimetres, straight from the draft.
    write_pattern_set(draft, dxf_dir, size_label=size_label)

    # Everything downstream of here expects centimetres.
    layouts_cm = scale_layouts(draft.layouts, 1.0 / MM_PER_CM)
    export_panels_svg(layouts_cm, svg_dir)

    metadata_path = write_panel_metadata(
        draft, measurements, panels_dir / "panel_metadata.json"
    )
    manifest_path = write_edge_manifest(draft, panels_dir / "edge_manifest.json")

    r = draft.seam_report()
    print(f"  Cap solved in {r['solver_iterations']} iterations: "
          f"height {r['cap_height_mm']:.2f} mm, ease {r['ease_mm']:+.2f} mm "
          f"({r['ease_pct']:+.2f}%)")

    return PanelGenerationResult(
        panels_dir=panels_dir,
        dxf_dir=dxf_dir,
        svg_dir=svg_dir,
        metadata_path=metadata_path,
        manifest_path=manifest_path,
        panel_names=list(draft.layouts.keys()),
        layouts=layouts_cm,
        draft=draft,
    )
