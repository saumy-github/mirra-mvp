"""Simple entrypoint for the isolated CLO-native avatar lane.

This command is meant to be easier to use than manually calling raw REST
endpoints. It can:

1. reset the current CLO project
2. import a native CLO avatar (.avt)
3. optionally import avatar measurements (.csv)
4. optionally write a local JSON report

By default it uses the repo-local starter measurement CSV:
`clo_avatar_generation/schema/measurement_template_unconfirmed.csv`
"""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

from ..adapters.clo_native_client import CLONativeClient
from ..adapters.clo_native_importer import CLONativeImporter
from ..reporting import write_json_report


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AVT_DIR = PACKAGE_ROOT / "avt_templates"
DEFAULT_CSV_PATH = (
    PACKAGE_ROOT / "schema" / "measurement_template_unconfirmed.csv"
)


def _default_report_path(avt_path: str | Path) -> Path:
    avt = Path(avt_path)
    return avt.with_name(f"{avt.stem}__avatar_run_report.json")


def _discover_default_avt_path() -> Path | None:
    avt_files = sorted(DEFAULT_AVT_DIR.glob("*.avt"))
    if len(avt_files) == 1:
        return avt_files[0]
    return None


def _validate_avt_path(avt_path: str | Path) -> Path:
    path = Path(avt_path).expanduser().resolve()
    if not path.exists():
        default_note = ""
        discovered = _discover_default_avt_path()
        if discovered is not None:
            default_note = f" One repo-local candidate exists at: {discovered}"
        raise FileNotFoundError(
            f"Avatar file not found: {path}. Pass a real CLO .avt file path.{default_note}"
        )
    if path.suffix.lower() != ".avt":
        raise ValueError(f"Avatar file must use the .avt extension: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Avatar file is empty: {path}")
    if not zipfile.is_zipfile(path):
        raise ValueError(
            f"Avatar file is not a valid CLO avatar package: {path}. "
            "CLO reported an unzip error for this kind of input."
        )
    return path


def _validate_csv_path(csv_path: str | Path) -> Path:
    path = Path(csv_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Measurement CSV not found: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Measurement file must use the .csv extension: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Measurement CSV is empty: {path}")
    return path


def run_avatar_command(
    avt_path: str | None,
    csv_path: str | None = None,
    report_path: str | None = None,
    reset_project: bool = True,
) -> Path:
    """Run the simplest possible native-avatar import flow."""

    resolved_avt_path = avt_path
    if resolved_avt_path is None:
        discovered = _discover_default_avt_path()
        if discovered is None:
            raise FileNotFoundError(
                "No --avt-path was provided and no single default .avt file was found in "
                f"{DEFAULT_AVT_DIR}. Put one real .avt there or pass --avt-path explicitly."
            )
        resolved_avt_path = str(discovered)

    validated_avt_path = _validate_avt_path(resolved_avt_path)

    client = CLONativeClient()
    importer = CLONativeImporter(client=client)

    resolved_csv_path = csv_path
    if resolved_csv_path is None and DEFAULT_CSV_PATH.exists():
        resolved_csv_path = str(DEFAULT_CSV_PATH)
    validated_csv_path = _validate_csv_path(resolved_csv_path) if resolved_csv_path else None

    if validated_csv_path:
        import_result = importer.import_template_and_measurements(
            avt_path=validated_avt_path,
            csv_path=validated_csv_path,
            reset_project=reset_project,
        )
    else:
        if reset_project:
            client.new_project()
            client.wait_for_queue()

        avatar_result = client.import_avatar_avt(validated_avt_path)
        client.wait_for_queue()
        import_result = {
            "avatar_result": avatar_result,
            "measurement_result": None,
        }

    native_debug = client.get_native_avatar_debug()
    status = client.get_status()
    capabilities = client.get_capabilities()

    final_report_path = (
        Path(report_path) if report_path else _default_report_path(validated_avt_path)
    )
    return write_json_report(
        final_report_path,
        {
            "phase": "run-avatar",
            "inputs": {
                "avt_path": str(validated_avt_path),
                "csv_path": str(validated_csv_path) if validated_csv_path else None,
                "reset_project": reset_project,
            },
            "import_result": import_result,
            "native_debug": native_debug,
            "status": status,
            "capabilities": capabilities,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple CLO-native avatar import runner.")
    parser.add_argument(
        "--avt-path",
        required=False,
        help="Path to a real CLO avatar .avt file. If omitted, the runner will use the single .avt in clo_avatar_generation/avt_templates if exactly one exists.",
    )
    parser.add_argument(
        "--csv-path",
        default=None,
        help="Optional path to a CLO avatar measurement CSV. Defaults to the repo-local starter CSV.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional output path for the JSON report",
    )
    parser.add_argument(
        "--no-reset-project",
        action="store_true",
        help="Do not create a new CLO project before importing",
    )
    parser.add_argument(
        "--avatar-only",
        action="store_true",
        help="Import only the avatar and skip CSV import even if the default CSV exists",
    )
    args = parser.parse_args()

    report_path = run_avatar_command(
        avt_path=args.avt_path,
        csv_path=None if args.avatar_only else args.csv_path,
        report_path=args.report_path,
        reset_project=not args.no_reset_project,
    )
    print(f"Wrote avatar run report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
