"""Interactive Step-1 CLO avatar-generation runner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clo_avatar_generation.avatar_runtime.context import Step1Context
from clo_avatar_generation.avatar_runtime.field_contract import get_default_base_avatar
from clo_avatar_generation.avatar_runtime.pipeline import run_pipeline
from clo_avatar_generation.avatar_runtime.run_manifest import get_latest_user_id, get_next_run_number


def _prompt_with_default(prompt: str, default: str | None) -> str:
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default
    return input(f"{prompt}: ").strip()


def _prompt_yes_no(prompt: str, default_yes: bool = True) -> bool:
    suffix = "(Y/n)" if default_yes else "(y/N)"
    response = input(f"{prompt} {suffix}: ").strip().lower()
    if not response:
        return default_yes
    return response in {"y", "yes"}


def _resolve_default_base_avatar() -> str:
    default_relative = get_default_base_avatar()
    default_path = default_relative if default_relative.is_absolute() else (REPO_ROOT / default_relative)
    return str(default_path.resolve())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Step-1 CLO avatar-generation workflow.")
    parser.add_argument("--user-id", default=None, help="Measurement user_id (for example u_001).")
    parser.add_argument("--run-number", type=int, default=None, help="Optional explicit run number.")
    parser.add_argument("--base-avatar", default=None, help="Optional override for the base .avt path.")
    parser.add_argument("--non-interactive", action="store_true", help="Use provided/default values without prompts.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    print("\nCLO Avatar Generation Pipeline")
    print("-" * 50)

    try:
        latest_user_id = get_latest_user_id()
        default_user_id = args.user_id or latest_user_id

        if args.non_interactive:
            user_id = default_user_id
            if not user_id:
                print("Error: --user-id is required in non-interactive mode when no previous run exists.")
                return 1
            run_number = args.run_number or get_next_run_number(user_id)
            base_avatar = args.base_avatar or _resolve_default_base_avatar()
        else:
            user_id = _prompt_with_default("Enter user_id", default_user_id).strip()
            if not user_id:
                print("Error: user_id cannot be empty")
                return 1

            suggested_run_number = args.run_number or get_next_run_number(user_id)
            if args.run_number is None:
                use_default = _prompt_yes_no(
                    f"Use run number {suggested_run_number:03d}?",
                    default_yes=True,
                )
                if use_default:
                    run_number = suggested_run_number
                else:
                    custom_number = input("Enter custom run number: ").strip()
                    try:
                        run_number = int(custom_number)
                    except ValueError:
                        print("Error: invalid run number")
                        return 1
            else:
                run_number = args.run_number

            base_avatar = _prompt_with_default(
                "Base avatar path",
                args.base_avatar or _resolve_default_base_avatar(),
            ).strip()

        ctx = Step1Context(
            user_id=user_id,
            requested_run_number=run_number,
            base_avatar_path_input=base_avatar,
            interactive=not args.non_interactive,
        )
        ctx = run_pipeline(ctx)

        if ctx.run_dir is not None:
            print(f"\nRun folder: {ctx.run_dir}")
            print(f"run_summary.json: {ctx.run_dir / 'run_summary.json'}")
            print(f"output.json: {ctx.run_dir / 'output.json'}")

        if ctx.status == "completed":
            print("CLO avatar-generation pipeline completed.")
            return 0

        failed_steps = [step for step in ctx.step_results if not step.get("success")]
        if failed_steps:
            last_failed = failed_steps[-1]
            if last_failed.get("error"):
                print(f"Failure detail: {last_failed['step']} -> {last_failed['error']}")
        print("CLO avatar-generation pipeline failed.")
        return 1

    except KeyboardInterrupt:
        print("\n\nPipeline cancelled by user")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
