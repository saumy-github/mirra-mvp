"""vto/run_vto.py

Interactive runner for Phase 4 VTO flow.

This script selects a Step 1 avatar run and a Step 2 product run,
creates a VTO run folder using the locked naming format
`<avatar_run>__<product_run>__<vto_run_number>` and writes `input.json`
and an initial `run_summary.json`.

Run from the repository root or from within `vto/`.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "vto" / "output"
AVATAR_OUTPUT_ROOT = REPO_ROOT / "avatar_generation" / "output"
PRODUCT_OUTPUT_ROOT = REPO_ROOT / "product_ingestion" / "output"

# Ensure absolute imports like `from vto...` work even when launched from `vto/`.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_avatar_run() -> Optional[Path]:
    if not AVATAR_OUTPUT_ROOT.exists():
        return None
    runs = sorted([p for p in AVATAR_OUTPUT_ROOT.iterdir() if p.is_dir() and p.name.startswith("u_")])
    return runs[-1] if runs else None


def find_latest_product_run() -> Optional[Path]:
    if not PRODUCT_OUTPUT_ROOT.exists():
        return None
    runs = sorted([p for p in PRODUCT_OUTPUT_ROOT.iterdir() if p.is_dir() and p.name.startswith("c_")])
    return runs[-1] if runs else None


def prompt_with_default(prompt: str, default: Optional[str]) -> str:
    if default:
        resp = input(f"{prompt} [{default}]: ").strip()
        return resp if resp else default
    return input(f"{prompt}: ").strip()


def next_vto_run_number(avatar_run: str, product_run: str) -> str:
    pattern = f"{avatar_run}__{product_run}__"
    if not OUTPUT_ROOT.exists():
        return "001"
    matches = [p for p in OUTPUT_ROOT.iterdir() if p.is_dir() and p.name.startswith(pattern)]
    if not matches:
        return "001"
    nums = []
    for p in matches:
        parts = p.name.split("__")
        if len(parts) >= 3:
            try:
                nums.append(int(parts[2]))
            except Exception:
                pass
    return f"{(max(nums) + 1):03d}" if nums else "001"


def create_run_folder(avatar_run: str, product_run: str, vto_run_number: str) -> Path:
    out = OUTPUT_ROOT / f"{avatar_run}__{product_run}__{vto_run_number}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_input_json(run_dir: Path, avatar_run: str, product_run: str, resolved: dict) -> None:
    payload = {
        "avatar_run": avatar_run,
        "product_run": product_run,
        "resolved_paths": resolved,
        "created_at": utc_now_iso_z(),
    }
    with (run_dir / "input.json").open("w", encoding="utf8") as f:
        json.dump(payload, f, indent=2)


def write_run_summary(run_dir: Path, status: str = "initialized") -> None:
    summary = {
        "status": status,
        "steps": [],
        "created_at": utc_now_iso_z(),
    }
    with (run_dir / "run_summary.json").open("w", encoding="utf8") as f:
        json.dump(summary, f, indent=2)


def resolve_paths(avatar_run_path: Path, product_run_path: Path) -> dict:
    return {
        "avatar_obj": str((avatar_run_path / "avatar.obj")) if (avatar_run_path / "avatar.obj").exists() else None,
        "avatar_glb": str((avatar_run_path / "avatar.glb")) if (avatar_run_path / "avatar.glb").exists() else None,
        "measurements": str((avatar_run_path / "measurements.json")) if (avatar_run_path / "measurements.json").exists() else None,
        "panels_dxf_dir": str((product_run_path / "panels" / "dxf")) if (product_run_path / "panels" / "dxf").exists() else None,
        "panels_svg_dir": str((product_run_path / "panels" / "svg")) if (product_run_path / "panels" / "svg").exists() else None,
        "run_summary_product": str((product_run_path / "run_summary.json")) if (product_run_path / "run_summary.json").exists() else None,
    }


def main():
    print("vto/run_vto.py — Interactive VTO runner")

    latest_avatar = find_latest_avatar_run()
    default_avatar = latest_avatar.name if latest_avatar else None
    avatar_run = prompt_with_default("Select avatar run (folder name)", default_avatar)
    if not avatar_run:
        print("No avatar run provided — aborting")
        sys.exit(1)
    avatar_run_path = AVATAR_OUTPUT_ROOT / avatar_run
    if not avatar_run_path.exists():
        print(f"Avatar run not found: {avatar_run_path}")
        sys.exit(1)

    latest_product = find_latest_product_run()
    default_product = latest_product.name if latest_product else None
    product_run = prompt_with_default("Select product run (folder name)", default_product)
    if not product_run:
        print("No product run provided — aborting")
        sys.exit(1)
    product_run_path = PRODUCT_OUTPUT_ROOT / product_run
    if not product_run_path.exists():
        print(f"Product run not found: {product_run_path}")
        sys.exit(1)

    print(f"\nSelected avatar run: {avatar_run_path}")
    print(f"Selected product run: {product_run_path}\n")
    confirm = input("Confirm selection? (y/N): ").strip().lower()
    if confirm != "y":
        print("Aborted by user")
        sys.exit(0)

    vto_num = next_vto_run_number(avatar_run, product_run)
    run_dir = create_run_folder(avatar_run, product_run, vto_num)

    resolved = resolve_paths(avatar_run_path, product_run_path)
    write_input_json(run_dir, avatar_run, product_run, resolved)
    write_run_summary(run_dir, status="initialized")

    # `run_dir` is created under `vto/output/` already; `input.json` and
    # `run_summary.json` were written into `run_dir` above. No separate
    # mirroring to `vto/input/` is performed.

    # By default run the orchestration immediately. Prompt with default Yes.
    try:
        resp = input("Run CLO orchestration now? [Y/n]: ").strip().lower()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(130)

    run_now = (resp == "" or resp in ["y", "yes"]) 
    if run_now:
        print("Starting CLO orchestration using created run...")
        # Import here to avoid module load at top-level if not needed
        try:
            from vto.clo_automation_steps.pipeline import run_pipeline

            try:
                # Prefer OBJ if present, otherwise GLB
                avatar_p = resolved.get("avatar_obj") or resolved.get("avatar_glb")
                patterns_p = resolved.get("panels_dxf_dir")

                # Sanity checks: ensure paths exist before running
                missing = []
                if not avatar_p:
                    missing.append("avatar (no avatar.obj or avatar.glb found)")
                elif not Path(avatar_p).exists():
                    missing.append(f"avatar:{avatar_p}")
                if not patterns_p:
                    missing.append("patterns (no panels/dxf directory found)")
                elif not Path(patterns_p).exists():
                    missing.append(f"patterns_dir:{patterns_p}")

                if missing:
                    print("Orchestration aborted - missing inputs:", ", ".join(missing))
                    ok = False
                else:
                    pipeline_report_path = run_dir / "pipeline_report.json"
                    ok = run_pipeline(
                        avatar_path=avatar_p,
                        patterns_dir=patterns_p,
                        report_path=str(pipeline_report_path),
                    )
            except KeyboardInterrupt:
                print("\n\nOrchestration cancelled by user")
                ok = False
            except Exception as exc:
                print(f"Orchestration failed: {exc}")
                ok = False

            # Update run_summary.json with result
            summary_path = run_dir / "run_summary.json"
            try:
                s = {
                    "status": "completed" if ok else "failed",
                    "completed_at": utc_now_iso_z(),
                    "inputs": {
                        "avatar": avatar_p,
                        "patterns_dir": patterns_p,
                    },
                    "outputs": {
                        "pipeline_report": str(run_dir / "pipeline_report.json"),
                    },
                }
                with summary_path.open("w", encoding="utf8") as f:
                    json.dump(s, f, indent=2)
            except Exception:
                pass

            if ok:
                print("CLO orchestration finished successfully.")
            else:
                print("CLO orchestration did not complete successfully.")

        except Exception as import_exc:
            print(f"Failed to start orchestration: {import_exc}")

    print(f"Created VTO run folder: {run_dir}")
    print("Wrote input.json and run_summary.json in vto/output")
    print("Next: run CLO orchestration or manual steps as required and update run_summary.json accordingly.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nRunner cancelled by user")
        raise SystemExit(130)
