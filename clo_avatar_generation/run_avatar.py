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

DEFAULT_APPLY_MODE = "avt_patch"
LEGACY_APPLY_MODES = {"csv", "avatar_properties"}
LEGACY_ROUTES_DOC = "clo_avatar_generation/schema/legacy_routes.md"


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
    parser.add_argument("--measurement-file", default=None, help="Optional override for the JSON measurement source.")
    parser.add_argument(
        "--apply-mode",
        choices=("auto", "csv", "avatar_properties", "avt_patch"),
        default=None,
        help=(
            "Measurement apply mode. avt_patch (the default) is the only supported route. "
            "csv and avatar_properties are legacy/experimental routes that require --enable-legacy-route; "
            "see clo_avatar_generation/schema/legacy_routes.md."
        ),
    )
    parser.add_argument(
        "--enable-legacy-route",
        action="store_true",
        help="Required alongside --apply-mode csv or --apply-mode avatar_properties to actually run them.",
    )
    parser.add_argument(
        "--active-field",
        action="append",
        default=None,
        help="Optional CLO target or source field name to isolate for this run. Repeat to pass multiple values.",
    )
    parser.add_argument("--non-interactive", action="store_true", help="Use provided/default values without prompts.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    print("\nCLO Avatar Generation Pipeline")
    print("-" * 50)

    try:
        latest_user_id = get_latest_user_id()
        default_user_id = args.user_id or latest_user_id
        default_apply_mode = args.apply_mode or DEFAULT_APPLY_MODE

        if args.non_interactive:
            user_id = default_user_id
            if not user_id:
                print("Error: --user-id is required in non-interactive mode when no previous run exists.")
                return 1
            run_number = args.run_number or get_next_run_number(user_id)
            base_avatar = args.base_avatar or _resolve_default_base_avatar()
            measurement_file = args.measurement_file
            apply_mode = default_apply_mode
            active_fields = list(args.active_field or [])
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

            measurement_file = args.measurement_file
            apply_mode = default_apply_mode
            active_fields = list(args.active_field or [])

        if apply_mode in LEGACY_APPLY_MODES and not args.enable_legacy_route:
            print(
                f"Error: --apply-mode {apply_mode} is a legacy route and requires --enable-legacy-route. "
                f"See {LEGACY_ROUTES_DOC}."
            )
            return 1

        ctx = Step1Context(
            user_id=user_id,
            requested_run_number=run_number,
            base_avatar_path_input=base_avatar,
            measurement_file_input=measurement_file,
            measurement_apply_mode_input=apply_mode,
            enable_legacy_route=args.enable_legacy_route,
            active_field_filters=active_fields,
            interactive=not args.non_interactive,
        )
        ctx = run_pipeline(ctx)

        if ctx.status == "completed":
            return 0
        return 1

    except KeyboardInterrupt:
        print("\n\nPipeline cancelled by user")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
