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
    args = parser.parse_args()

    from clo_vto.native_vto.helpers import resolve_patterns_dir
    from clo_vto.native_vto.pipeline import run_pipeline

    avt_path = Path(args.avt_path) if args.avt_path else _discover_default_avt()
    patterns_dir = Path(args.patterns_dir) if args.patterns_dir else Path(resolve_patterns_dir())

    csv_path = None
    if args.csv_path:
        csv_path = str(Path(args.csv_path))
    elif args.use_default_csv and DEFAULT_CSV_PATH.exists():
        csv_path = str(DEFAULT_CSV_PATH)

    report_path = args.report_path or str(_default_report_path(avt_path))

    ok = run_pipeline(
        avatar_path=str(avt_path),
        patterns_dir=str(patterns_dir),
        csv_path=csv_path,
        report_path=report_path,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
