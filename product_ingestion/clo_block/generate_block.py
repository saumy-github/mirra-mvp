"""Generate a CLO-compatible t-shirt block from measurements.

Examples
--------
Reproduce the CLO reference size M:
    python generate_block.py --out ./out/M

From explicit pattern measurements (millimetres):
    python generate_block.py --out ./out/L \\
        --half-chest 310 --hem-half 289 --length 745 \\
        --shoulder-half 245 --neck-half 101 \\
        --neck-front 104 --neck-back 38 --armhole-depth 262 \\
        --bicep 520 --wrist 408 --underarm-to-wrist 132 --label L

From body measurements, using the reference block's own proportions:
    python generate_block.py --out ./out/body --from-body \\
        --chest-girth 1000 --shoulder-span 470 --back-length 720

Outputs written to --out:
    dxf/{front_panel,back_panel,sleeve_left,sleeve_right}.dxf
    preview.svg
    edge_manifest.json
    seam_report.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .clo_draft import CloTShirtDraft
    from .clo_draft_config import CloBlockMeasurements, CloDraftConfig, relaxed_tee, woven_tee
    from .clo_dxf_writer import write_pattern_set, write_svg
except ImportError:  # pragma: no cover
    from clo_draft import CloTShirtDraft  # type: ignore
    from clo_draft_config import (  # type: ignore
        CloBlockMeasurements, CloDraftConfig, relaxed_tee, woven_tee,
    )
    from clo_dxf_writer import write_pattern_set, write_svg  # type: ignore

PRESETS = {"clo": CloDraftConfig, "relaxed": relaxed_tee, "woven": woven_tee}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--label", default="M", help="size label used in DXF block names")
    p.add_argument("--preset", choices=sorted(PRESETS), default="clo")
    p.add_argument("--n-fit", type=int, default=None,
                   help="points sampled per Bezier segment (default 24)")
    p.add_argument("--seam-allowance", type=float, default=0.0,
                   help="mm; 0 matches CLO, which exports none")
    p.add_argument("--no-internal-lines", action="store_true",
                   help="omit layer-8 construction lines")
    p.add_argument("--notch-absolute", type=float, default=None,
                   help="fix notch distance from underarm in mm instead of "
                        "scaling it with armhole depth")

    g = p.add_argument_group("pattern measurements (mm)")
    for flag, dest in [
        ("--half-chest", "half_chest_width"), ("--hem-half", "hem_half_width"),
        ("--length", "garment_length"), ("--shoulder-half", "shoulder_half_width"),
        ("--neck-half", "neck_half_width"), ("--neck-front", "neck_depth_front"),
        ("--neck-back", "neck_depth_back"), ("--armhole-depth", "armhole_depth"),
        ("--bicep", "bicep_full_width"), ("--wrist", "wrist_full_width"),
        ("--underarm-to-wrist", "underarm_to_wrist"),
    ]:
        g.add_argument(flag, dest=dest, type=float, default=None)

    b = p.add_argument_group("body-driven mode")
    b.add_argument("--from-body", action="store_true")
    b.add_argument("--chest-girth", type=float)
    b.add_argument("--shoulder-span", type=float)
    b.add_argument("--back-length", type=float)
    b.add_argument("--chest-ease", type=float, default=160.0)
    b.add_argument("--fit", choices=("slim", "regular", "relaxed"), default="regular")
    return p


def measurements_from_args(a) -> CloBlockMeasurements:
    if a.from_body:
        missing = [n for n in ("chest_girth", "shoulder_span", "back_length")
                   if getattr(a, n) is None]
        if missing:
            raise SystemExit("--from-body requires " + ", ".join("--" + m.replace("_", "-")
                                                                for m in missing))
        m = CloBlockMeasurements.from_body(
            a.chest_girth, a.shoulder_span, a.back_length,
            chest_ease=a.chest_ease, fit=a.fit,
        )
        m.label = a.label
        return m

    m = CloBlockMeasurements.clo_default_M()
    m.label = a.label
    for field_name in (
        "half_chest_width", "hem_half_width", "garment_length",
        "shoulder_half_width", "neck_half_width", "neck_depth_front",
        "neck_depth_back", "armhole_depth", "bicep_full_width",
        "wrist_full_width", "underarm_to_wrist",
    ):
        v = getattr(a, field_name)
        if v is not None:
            setattr(m, field_name, v)
    return m


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)

    cfg = PRESETS[a.preset]()
    cfg.seam_allowance_mm = a.seam_allowance
    cfg.emit_internal_lines = not a.no_internal_lines
    if a.n_fit:
        cfg.n_fit = a.n_fit
    if a.notch_absolute is not None:
        cfg.notch_absolute_mm = a.notch_absolute

    draft = CloTShirtDraft(measurements_from_args(a), cfg)
    draft.build()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_pattern_set(draft, out / "dxf", size_label=a.label)
    write_svg(draft, out / "preview.svg")
    (out / "edge_manifest.json").write_text(json.dumps(draft.edge_manifest(), indent=1))
    report = draft.seam_report()
    (out / "seam_report.json").write_text(json.dumps(report, indent=1))

    print(f"wrote {out}/dxf/*.dxf, preview.svg, edge_manifest.json, seam_report.json")
    print(f"  cap height        {report['cap_height_mm']:.2f} mm "
          f"({report['cap_height_over_bicep']:.3f} of bicep)")
    print(f"  peak offset       {report['peak_offset_mm']:+.2f} mm toward the back")
    print(f"  armhole total     {report['armhole_total_mm']:.2f} mm")
    print(f"  cap total         {report['cap_total_mm']:.2f} mm")
    print(f"  ease              {report['ease_mm']:+.2f} mm "
          f"({report['ease_pct']:+.3f} %)")
    print(f"  notch from underarm {report['notch_from_underarm_mm']:.2f} mm "
          f"(matched exactly on panel and sleeve)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
