#!/usr/bin/env python3
"""Inspect the currently installed CLO plugin artifact and vault contents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
ENV_PATH = WORKSPACE_DIR / ".env"

UNVERSIONED_PLUGIN_NAMES = (
    "RestPlugin.dll",
    "libRestPlugin.dylib",
    "RestPlugin.dylib",
)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line or line.startswith("export "):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def detect_platform(env_values: dict[str, str]) -> str:
    configured = env_values.get("PLUGIN_PLATFORM", "").strip().lower()
    if configured:
        return configured
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return sys.platform.lower()


def versioned_plugin_glob(platform: str) -> str:
    if platform == "windows":
        return "RestPlugin_v*.dll"
    return "libRestPlugin_v*.dylib"


def extract_version_from_name(filename: str) -> str:
    """Extract '1.1.1' from 'RestPlugin_v1.1.1.dll' or similar."""
    stem = Path(filename).stem  # RestPlugin_v1.1.1 or libRestPlugin_v1.1.1
    marker = "_v"
    idx = stem.rfind(marker)
    if idx == -1:
        return ""
    return stem[idx + len(marker):]


def default_plugin_dir(env_values: dict[str, str]) -> Path | None:
    configured = env_values.get("CLO_PLUGINS_DIR", "").strip()
    if configured:
        return Path(configured)
    return None


def find_plugin_artifact(plugin_dir: Path, platform: str) -> dict:
    """Return info about the active plugin. Prefers versioned; falls back to unversioned."""
    glob = versioned_plugin_glob(platform)
    versioned = sorted(plugin_dir.glob(glob))

    if len(versioned) > 1:
        return {
            "artifact_found": True,
            "conflict": True,
            "conflict_files": [str(f) for f in versioned],
            "warning": "Multiple versioned plugin DLLs found — only one should be present. "
                       "CLO will try to load all of them, causing a port conflict on 50505.",
        }

    if versioned:
        f = versioned[0]
        stat = f.stat()
        return {
            "artifact_found": True,
            "conflict": False,
            "artifact_path": str(f),
            "version_in_name": extract_version_from_name(f.name),
            "size_bytes": stat.st_size,
            "modified_at_epoch": stat.st_mtime,
        }

    # Fall back to unversioned (pre-plan-016 installs)
    for name in UNVERSIONED_PLUGIN_NAMES:
        candidate = plugin_dir / name
        if candidate.exists():
            stat = candidate.stat()
            return {
                "artifact_found": True,
                "conflict": False,
                "artifact_path": str(candidate),
                "version_in_name": "",
                "legacy_unversioned": True,
                "size_bytes": stat.st_size,
                "modified_at_epoch": stat.st_mtime,
            }

    return {"artifact_found": False}


def vault_info(vault_dir_str: str, platform: str) -> dict:
    if not vault_dir_str:
        return {"vault_dir": None, "note": "CLO_PLUGIN_VAULT_DIR not set in .env"}

    vault_dir = Path(vault_dir_str)
    if not vault_dir.exists():
        return {"vault_dir": str(vault_dir), "available_versions": [], "note": "vault directory does not exist yet"}

    glob = versioned_plugin_glob(platform)
    files = sorted(vault_dir.glob(glob))
    versions = [extract_version_from_name(f.name) for f in files]
    return {
        "vault_dir": str(vault_dir),
        "available_versions": [v for v in versions if v],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the installed CLO plugin artifact and vault")
    parser.add_argument("--plugin-dir", help="Override the plugin install directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_values = load_env_file(ENV_PATH)
    platform_name = detect_platform(env_values)
    plugin_dir = Path(args.plugin_dir) if args.plugin_dir else default_plugin_dir(env_values)

    if plugin_dir is None:
        raise SystemExit(
            "Could not determine the plugin directory for platform "
            f"{platform_name}. Set CLO_PLUGINS_DIR in {ENV_PATH} or pass --plugin-dir."
        )

    active = find_plugin_artifact(plugin_dir, platform_name)
    vault = vault_info(env_values.get("CLO_PLUGIN_VAULT_DIR", "").strip(), platform_name)

    payload = {
        "platform": platform_name,
        "plugin_dir": str(plugin_dir),
        "active": active,
        "vault": vault,
    }

    print(json.dumps(payload, indent=2))
    return 0 if active.get("artifact_found") else 1


if __name__ == "__main__":
    raise SystemExit(main())
