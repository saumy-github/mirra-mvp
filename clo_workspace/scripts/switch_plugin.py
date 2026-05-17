#!/usr/bin/env python3
"""Switch the active CLO plugin version from the mirra-vault."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
ENV_PATH = WORKSPACE_DIR / ".env"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def detect_platform(env: dict[str, str]) -> str:
    configured = env.get("PLUGIN_PLATFORM", "").strip().lower()
    if configured:
        return configured
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return sys.platform.lower()


def versioned_artifact_name(version: str, platform: str) -> str:
    if platform == "windows":
        return f"RestPlugin_v{version}.dll"
    return f"libRestPlugin_v{version}.dylib"


def versioned_plugin_glob(platform: str) -> str:
    if platform == "windows":
        return "RestPlugin_v*.dll"
    return "libRestPlugin_v*.dylib"


def is_clo_running(platform: str) -> bool:
    try:
        if platform == "windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq CLO Standalone OnlineAuth.exe"],
                capture_output=True, text=True
            )
            return "CLO Standalone OnlineAuth.exe" in result.stdout
        if platform == "mac":
            result = subprocess.run(["pgrep", "-ix", "clo"], capture_output=True)
            return result.returncode == 0
    except Exception:
        pass
    return False


def list_versions(plugins_dir: Path, vault_dir: Path, platform: str) -> None:
    glob = versioned_plugin_glob(platform)

    active = list(plugins_dir.glob(glob))
    if active:
        print(f"Active ({plugins_dir}):")
        for f in sorted(active):
            print(f"  {f.name}")
    else:
        print(f"Active ({plugins_dir}): none")

    if vault_dir.exists():
        vault_files = sorted(vault_dir.glob(glob))
        print(f"\nVault ({vault_dir}):")
        if vault_files:
            for f in vault_files:
                print(f"  {f.name}")
        else:
            print("  (empty)")
    else:
        print(f"\nVault ({vault_dir}): directory does not exist yet")


def activate_version(version: str, plugins_dir: Path, vault_dir: Path, platform: str) -> None:
    target_name = versioned_artifact_name(version, platform)
    vault_source = vault_dir / target_name

    if not vault_source.exists():
        raise SystemExit(
            f"Version '{version}' not found in vault.\n"
            f"  Expected: {vault_source}\n"
            f"  Run 'switch_plugin.py --list' to see available versions."
        )

    if is_clo_running(platform):
        raise SystemExit(
            "CLO is running. Close CLO before switching the plugin, "
            "then run this command again."
        )

    active_dest = plugins_dir / target_name
    import shutil
    shutil.copy2(vault_source, active_dest)
    print(f"Copied: {vault_source}")
    print(f"    to: {active_dest}")

    glob = versioned_plugin_glob(platform)
    for old in plugins_dir.glob(glob):
        if old != active_dest:
            old.unlink()
            print(f"Removed old version: {old.name}")

    print(f"\nActive plugin is now: {target_name}")
    print("Restart CLO to apply the change.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Switch the active CLO plugin version from the mirra-vault."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List active and vault versions")
    group.add_argument("--activate", metavar="VERSION", help="Activate a vault version (e.g. 1.1.0)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = load_env_file(ENV_PATH)
    platform = detect_platform(env)

    plugins_dir_str = env.get("CLO_PLUGINS_DIR", "").strip()
    vault_dir_str = env.get("CLO_PLUGIN_VAULT_DIR", "").strip()

    if not plugins_dir_str:
        raise SystemExit(
            f"CLO_PLUGINS_DIR is not set. Add it to {ENV_PATH}."
        )
    if not vault_dir_str:
        raise SystemExit(
            f"CLO_PLUGIN_VAULT_DIR is not set. Add it to {ENV_PATH}."
        )

    plugins_dir = Path(plugins_dir_str)
    vault_dir = Path(vault_dir_str)

    if not plugins_dir.exists():
        raise SystemExit(f"CLO plugins directory does not exist: {plugins_dir}")

    if args.list:
        list_versions(plugins_dir, vault_dir, platform)
    else:
        activate_version(args.activate, plugins_dir, vault_dir, platform)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
