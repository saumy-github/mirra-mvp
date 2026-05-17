#!/usr/bin/env python3
"""Shared build entry point for the CLO REST plugin."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


WORKSPACE_DIR = Path(__file__).resolve().parent
ENV_PATH = WORKSPACE_DIR / ".env"
ENV_EXAMPLE_PATH = WORKSPACE_DIR / ".env.example"
VERSIONS_DIR = WORKSPACE_DIR / "versions"
CONTRACT_PATH = WORKSPACE_DIR / "plugin_contract.json"
SHARED_DIR = WORKSPACE_DIR / "shared"
BUILD_INFO_HEADER = SHARED_DIR / "PluginBuildInfo.h"
LOGS_DIR = WORKSPACE_DIR / "logs"
SUPPORTED_PLATFORMS = {"windows", "mac"}
ACTIVE_LOG_PATH: Path | None = None

PLATFORM_SOURCE_LAYOUT: dict[str, dict[str, object]] = {
    "windows": {
        "source_dir": WORKSPACE_DIR / "windows",
        "files": [
            ("RestPlugin_windows.cpp", "RestPlugin_windows.cpp"),
            ("dllmain.cpp", "dllmain.cpp"),
            ("CMakeLists.txt", "CMakeLists.txt"),
            ("stdafx.h", "stdafx.h"),
            ("targetver.h", "targetver.h"),
        ],
    },
    "mac": {
        "source_dir": WORKSPACE_DIR / "mac",
        "files": [
            ("RestPlugin_macOS.cpp", "RestPlugin_macOS.cpp"),
            ("CMakeLists.txt", "CMakeLists.txt"),
        ],
    },
}

SHARED_SOURCE_FILES = [
    ("httplib.h", "httplib.h"),
    ("json.hpp", "json.hpp"),
    ("CloNativePluginSupport.h", "CloNativePluginSupport.h"),
    ("PluginBuildInfo.h", "PluginBuildInfo.h"),
]


def log(message: str) -> None:
    print(message)
    if ACTIVE_LOG_PATH is not None:
        ACTIVE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ACTIVE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")


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


def merged_env() -> dict[str, str]:
    env = dict(os.environ)
    env_from_file = load_env_file(ENV_PATH)
    for key, value in env_from_file.items():
        env.setdefault(key, value)
    return env


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_version_key(path: Path) -> tuple[int, ...]:
    stem = path.stem
    version_text = stem[2:] if stem.startswith("v_") else stem
    parts: list[int] = []
    for part in version_text.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def find_current_version_path() -> Path:
    candidates = sorted(VERSIONS_DIR.glob("v_*.json"), key=parse_version_key)
    if not candidates:
        raise SystemExit(f"No version files found under {VERSIONS_DIR}")
    return candidates[-1]


def normalize_platform(value: str | None) -> str:
    if value:
        return value.strip().lower()
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return sys.platform.lower()


def validate_config(env: dict[str, str], platform_name: str) -> dict[str, str]:
    if platform_name not in SUPPORTED_PLATFORMS:
        raise SystemExit(
            "Unsupported OS for CLO plugin build: "
            f"{platform_name}. Supported platforms: windows, mac."
        )

    required = ["CLO_SDK_PATH", "BUILD_CONFIG"]

    missing = [key for key in required if not env.get(key)]
    if missing:
        raise SystemExit(
            "Missing required plugin build config values: "
            + ", ".join(missing)
            + f". Copy {ENV_EXAMPLE_PATH.name} to .env and fill them in."
        )

    vault_dir = env.get("CLO_PLUGIN_VAULT_DIR", "").strip()
    if vault_dir:
        vault_path = Path(vault_dir).resolve()
        try:
            vault_path.relative_to(WORKSPACE_DIR.parent.resolve())
            raise SystemExit(
                f"CLO_PLUGIN_VAULT_DIR must be outside the repository.\n"
                f"  '{vault_path}' is inside '{WORKSPACE_DIR.parent.resolve()}'.\n"
                f"  Set it to a path outside the repo, e.g., next to the CLO plugins folder."
            )
        except ValueError:
            pass  # not inside repo — good

    return {
        "platform": platform_name,
        "sdk_path": env["CLO_SDK_PATH"],
        "clo_plugins_dir": env.get("CLO_PLUGINS_DIR", "").strip(),
        "vault_dir": vault_dir,
        "cmake_exe": env.get("CMAKE_EXE", "").strip(),
        "cmake_generator": env.get("CMAKE_GENERATOR", "").strip(),
        "cmake_arch": env.get("CMAKE_ARCH", "").strip(),
        "cmake_prefix_path": env.get("CMAKE_PREFIX_PATH", "").strip(),
        "qt5_dir": env.get("Qt5_DIR", "").strip(),
        "cmake_osx_architectures": env.get("CMAKE_OSX_ARCHITECTURES", "").strip(),
        "build_config": env["BUILD_CONFIG"].strip() or "Release",
    }

def select_cmake_command(config: dict[str, str]) -> list[str]:
    cmake_exe = config["cmake_exe"]
    if cmake_exe:
        cmake_path = Path(cmake_exe)
        if not cmake_path.exists():
            raise SystemExit(f"CMAKE_EXE does not exist: {cmake_exe}")
        return [str(cmake_path)]
    if shutil.which("cmake"):
        return ["cmake"]
    raise SystemExit(
        "cmake was not found. Set CMAKE_EXE in .env or ensure cmake is on PATH."
    )


def generate_build_info_header(version_data: dict, contract_data: dict, config: dict[str, str]) -> None:
    platform_sync = version_data.get("platforms", {}).get(config["platform"], "untested")
    build_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    header = f"""#pragma once

// Auto-generated by build_plugin.py. Do not edit by hand.

#define MIRRA_PLUGIN_NAME "{version_data['plugin_name']}"
#define MIRRA_PLUGIN_VERSION "{version_data['plugin_version']}"
#define MIRRA_PLUGIN_API_VERSION "{version_data['api_version']}"
#define MIRRA_PLUGIN_RELEASE_DATE "{version_data['release_date']}"
#define MIRRA_PLUGIN_RELEASE_STATUS "{version_data['status']}"
#define MIRRA_PLUGIN_PLATFORM "{config['platform']}"
#define MIRRA_PLUGIN_PLATFORM_SYNC_STATE "{platform_sync}"
#define MIRRA_PLUGIN_CONTRACT_NAME "{contract_data['contract_name']}"
#define MIRRA_PLUGIN_CONTRACT_VERSION "{contract_data['api_version']}"
#define MIRRA_PLUGIN_BUILD_TIME "{build_time}"
"""
    BUILD_INFO_HEADER.parent.mkdir(parents=True, exist_ok=True)
    BUILD_INFO_HEADER.write_text(header, encoding="utf-8")


def sdk_plugin_dir(config: dict[str, str]) -> Path:
    return Path(config["sdk_path"]) / "Samples" / "RestPlugin"


def copy_sources_to_sdk_sample(dest_dir: Path, platform_name: str) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    layout = PLATFORM_SOURCE_LAYOUT[platform_name]
    source_dir = Path(layout["source_dir"])
    for source_name, dest_name in SHARED_SOURCE_FILES:
        shutil.copy2(SHARED_DIR / source_name, dest_dir / dest_name)
    for source_name, dest_name in layout["files"]:
        shutil.copy2(source_dir / source_name, dest_dir / dest_name)


def run_command(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    log("> " + " ".join(command))
    subprocess.run(command, cwd=str(cwd), env=env, check=True)


def configure_and_build(dest_dir: Path, config: dict[str, str], env: dict[str, str]) -> Path:
    build_dir = dest_dir / "build"
    build_dir.mkdir(exist_ok=True)
    cmake = select_cmake_command(config)

    configure_cmd = [*cmake, ".."]
    if config["cmake_generator"]:
        configure_cmd.extend(["-G", config["cmake_generator"]])
    if config["cmake_arch"] and config["platform"] == "windows":
        configure_cmd.extend(["-A", config["cmake_arch"]])
    if config["platform"] == "mac":
        if config["cmake_prefix_path"]:
            configure_cmd.append(f"-DCMAKE_PREFIX_PATH={config['cmake_prefix_path']}")
        if config["qt5_dir"]:
            configure_cmd.append(f"-DQt5_DIR={config['qt5_dir']}")
        if config["cmake_osx_architectures"]:
            configure_cmd.append(
                f"-DCMAKE_OSX_ARCHITECTURES={config['cmake_osx_architectures']}"
            )

    run_command(configure_cmd, cwd=build_dir, env=env)
    run_command([*cmake, "--build", ".", "--config", config["build_config"]], cwd=build_dir, env=env)

    artifact = find_build_artifact(build_dir, config["build_config"])
    if artifact is None:
        raise SystemExit(f"Build finished but plugin artifact was not found under {build_dir}")
    return artifact


def find_build_artifact(build_dir: Path, build_config: str) -> Path | None:
    candidate_dirs = [build_dir / build_config, build_dir]
    patterns = ["RestPlugin.dll", "libRestPlugin.dylib", "RestPlugin.dylib", "libRestPlugin.so", "RestPlugin.so"]
    for directory in candidate_dirs:
        for pattern in patterns:
            candidate = directory / pattern
            if candidate.exists():
                return candidate
    return None


def versioned_artifact_name(version: str, platform: str) -> str:
    if platform == "windows":
        return f"RestPlugin_v{version}.dll"
    return f"libRestPlugin_v{version}.dylib"


def versioned_plugin_glob(platform: str) -> str:
    if platform == "windows":
        return "RestPlugin_v*.dll"
    return "libRestPlugin_v*.dylib"



def copy_to_vault(artifact: Path, version_data: dict, config: dict[str, str]) -> Path | None:
    platform = config["platform"]
    version = version_data["plugin_version"]
    versioned_name = versioned_artifact_name(version, platform)
    vault_dir_str = config.get("vault_dir", "")

    if not vault_dir_str:
        log("Warning: CLO_PLUGIN_VAULT_DIR not set — skipping vault copy. "
            "Set it in .env to enable rollback support.")
        return None

    vault_dir = Path(vault_dir_str)
    vault_dir.mkdir(parents=True, exist_ok=True)
    vault_dest = vault_dir / versioned_name
    shutil.copy2(artifact, vault_dest)
    log(f"Vault copy: {vault_dest}")
    return vault_dest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the CLO REST plugin")
    parser.add_argument("--allow-blocked", action="store_true", help="Build even if the current version file marks this version as blocked")
    parser.add_argument("--sync-only", action="store_true", help="Only generate build metadata and copy files into the SDK sample folder")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = merged_env()
    version_path = find_current_version_path()
    version_data = load_json(version_path)
    contract_data = load_json(CONTRACT_PATH)

    if version_data.get("api_version") != contract_data.get("api_version"):
        raise SystemExit(f"{version_path.name} api_version does not match {CONTRACT_PATH.name} api_version")

    platform_name = normalize_platform(env.get("PLUGIN_PLATFORM"))
    config = validate_config(env, platform_name)
    global ACTIVE_LOG_PATH
    ACTIVE_LOG_PATH = LOGS_DIR / f"build_plugin_{platform_name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    release_status = version_data.get("status", "unstable")
    if release_status == "blocked" and not args.allow_blocked:
        raise SystemExit(
            "The current plugin version is marked as blocked. "
            "Fix the version status first or rebuild with --allow-blocked."
        )

    log(f"Plugin: {version_data['plugin_name']} {version_data['plugin_version']}")
    log(f"Status: {release_status}")
    log(f"Platform: {platform_name}")
    log(f"Version file: {version_path}")
    log(f"Contract file: {CONTRACT_PATH}")
    log(f"Build log: {ACTIVE_LOG_PATH}")

    generate_build_info_header(version_data, contract_data, config)
    log(f"Generated shared build metadata: {BUILD_INFO_HEADER}")

    sdk_dir = sdk_plugin_dir(config)
    copy_sources_to_sdk_sample(sdk_dir, platform_name)
    log(f"Synced {platform_name} plugin sources to: {sdk_dir}")

    if args.sync_only:
        log("Sync-only mode complete.")
        return 0

    child_env = dict(os.environ)
    child_env.update(env)
    child_env["CLO_SDK_PATH"] = config["sdk_path"]

    artifact = configure_and_build(sdk_dir, config, child_env)
    log(f"Built plugin artifact: {artifact}")

    versioned_name = versioned_artifact_name(version_data["plugin_version"], config["platform"])
    vault_dest = copy_to_vault(artifact, version_data, config)

    default_plugins_dir = {
        "windows": "C:/Program Files/CLO Standalone OnlineAuth/plugins",
        "mac": "~/Documents/CLO/Plugins",
    }
    plugins_dir = config.get("clo_plugins_dir") or default_plugins_dir.get(config["platform"], "<CLO plugins folder>")

    log("")
    log("Manual install step:")
    log(f"  1. Close CLO")
    log(f"  2. Copy: {vault_dest or artifact}")
    log(f"     To:   {plugins_dir}/{versioned_name}")
    if config["platform"] == "windows":
        log(f"  3. Requires admin rights — copy from an Administrator terminal")
    log(f"  4. Restart CLO")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
