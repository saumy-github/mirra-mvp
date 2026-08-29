"""Main runner for the isolated CLO-native VTO lane."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = PACKAGE_ROOT / "output"
DEFAULT_AVT_NAME = "clo_test.avt"
DEFAULT_CSV_PATH = REPO_ROOT / "clo_avatar_generation" / "schema" / "measurement_template_unconfirmed.csv"
DEFAULT_BASE_AVATAR = REPO_ROOT / "clo_avatar_generation" / "input" / "base-1.avt"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _discover_default_avt() -> Path:
    preferred = DEFAULT_OUTPUT_ROOT / DEFAULT_AVT_NAME
    if preferred.exists():
        return preferred

    output_candidates = sorted(DEFAULT_OUTPUT_ROOT.glob("*.avt"))
    if len(output_candidates) == 1:
        return output_candidates[0]

    template_root = PACKAGE_ROOT / "avt_templates"
    template_candidates = sorted(template_root.glob("*.avt"))
    if len(template_candidates) == 1:
        return template_candidates[0]

    if DEFAULT_BASE_AVATAR.exists():
        return DEFAULT_BASE_AVATAR

    if not output_candidates and not template_candidates:
        raise FileNotFoundError(
            f"No .avt file found in {DEFAULT_OUTPUT_ROOT}, {template_root}, or {DEFAULT_BASE_AVATAR}."
        )

    if output_candidates:
        return output_candidates[0]
    return template_candidates[0]


def _default_report_path(avt_path: Path) -> Path:
    return DEFAULT_OUTPUT_ROOT / f"{avt_path.stem}__native_vto_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated CLO-native VTO pipeline.")
    parser.add_argument("--avt-path", default=None)
    parser.add_argument("--csv-path", default=None)
    parser.add_argument("--patterns-dir", default=None)
    parser.add_argument("--use-default-csv", action="store_true")
    parser.add_argument("--report-path", default=None)
    parser.add_argument(
        "--use-default-panels",
        action="store_true",
        help="Use pre-built DXF panels from clo_vto/default_panels/dxf/ "
             "instead of generated panels. Decouples VTO from panel generation.",
    )
    parser.add_argument(
        "--ingestion-output-dir",
        default=None,
        help="Root of a product_ingestion run output directory (contains "
             "image_info/ and panels/). Required with --use-default-panels "
             "to locate colors.json and texture atlases.",
    )
    # Run identity — decides the output directory. Given explicitly rather
    # than derived from paths; path-sniffing is how avatar discovery got loose.
    parser.add_argument("--user-id", default=None, help="For example u_011.")
    parser.add_argument("--cloth-id", default=None, help="For example c_001.")
    parser.add_argument("--size-id", default=None, help="For example s_001.")
    # Strict modes exist on create_context but had no way in until now.
    parser.add_argument(
        "--strict-seams",
        action="store_true",
        help="Abort instead of falling back to DEFAULT_SEAMS when the edge manifest is missing.",
    )
    parser.add_argument(
        "--strict-dxf-units",
        action="store_true",
        help="Abort when DXF units cannot be determined instead of assuming scale 1.0.",
    )
    parser.add_argument(
        "--strict-seam-hash",
        action="store_true",
        help="Require a non-empty geometry hash baseline in step 9.",
    )
    args = parser.parse_args()

    from clo_vto.native_vto.pipeline import run_pipeline

    avt_path = Path(args.avt_path) if args.avt_path else _discover_default_avt()

    csv_path = None
    if args.csv_path:
        csv_path = str(Path(args.csv_path))
    elif args.use_default_csv and DEFAULT_CSV_PATH.exists():
        csv_path = str(DEFAULT_CSV_PATH)

    report_path = args.report_path or str(_default_report_path(avt_path))

    ok = run_pipeline(
        avatar_path=str(avt_path),
        patterns_dir=str(Path(args.patterns_dir)) if args.patterns_dir else None,
        csv_path=csv_path,
        report_path=report_path,
        use_default_panels=args.use_default_panels,
        ingestion_output_dir=args.ingestion_output_dir,
        user_id=args.user_id,
        cloth_id=args.cloth_id,
        size_id=args.size_id,
        allow_seam_fallback=not args.strict_seams,
        strict_dxf_units=args.strict_dxf_units,
        strict_seam_hash=args.strict_seam_hash,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
