#!/usr/bin/env python3
"""Inspect the currently installed CLO plugin artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
ENV_PATH = WORKSPACE_DIR / ".env"
PLUGIN_NAMES = (
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


def default_plugin_dir(platform_name: str, env_values: dict[str, str]) -> Path | None:
    configured = env_values.get("CLO_PLUGINS_DIR", "").strip()
    if configured:
        return Path(configured)
    return None


def find_plugin_artifact(plugin_dir: Path) -> Path | None:
    for name in PLUGIN_NAMES:
        candidate = plugin_dir / name
        if candidate.exists():
            return candidate
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the installed CLO plugin artifact")
    parser.add_argument("--plugin-dir", help="Override the plugin install directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_values = load_env_file(ENV_PATH)
    platform_name = detect_platform(env_values)
    plugin_dir = Path(args.plugin_dir) if args.plugin_dir else default_plugin_dir(platform_name, env_values)

    if plugin_dir is None:
        raise SystemExit(
            "Could not determine the plugin directory for platform "
            f"{platform_name}. Set CLO_PLUGINS_DIR in {ENV_PATH} or pass --plugin-dir explicitly."
        )

    artifact = find_plugin_artifact(plugin_dir)
    payload = {
        "platform": platform_name,
        "plugin_dir": str(plugin_dir),
        "artifact_found": artifact is not None,
        "artifact_path": str(artifact) if artifact is not None else "",
    }

    if artifact is not None:
        stat = artifact.stat()
        payload["size_bytes"] = stat.st_size
        payload["modified_at_epoch"] = stat.st_mtime

    print(json.dumps(payload, indent=2))
    return 0 if artifact is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
