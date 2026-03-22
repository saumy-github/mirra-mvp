"""Canonical run identity and output file paths."""

import os
from pathlib import Path
from typing import NamedTuple, Optional


class RunIdentity(NamedTuple):
    """Run identity: user_id + per-user counter (e.g. u_001-001)."""

    user_id: str
    number: int

    @property
    def run_id(self) -> str:
        return f"{self.user_id}-{self.number:03d}"


# Run folder naming formula: <user_id>-<run number>
def get_output_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "output")


def get_run_dir(run_id: RunIdentity) -> str:
    return os.path.join(get_output_dir(), run_id.run_id)


def get_inputs_json_path(run_id: RunIdentity) -> str:
    return os.path.join(get_run_dir(run_id), "input.json")


def get_values_json_path(run_id: RunIdentity) -> str:
    return os.path.join(get_run_dir(run_id), "output.json")


def get_avatar_glb_path(run_id: RunIdentity) -> str:
    return os.path.join(get_run_dir(run_id), "avatar.glb")


def get_avatar_obj_path(run_id: RunIdentity) -> str:
    return os.path.join(get_run_dir(run_id), "avatar.obj")


def get_measurements_json_path(run_id: RunIdentity) -> str:
    return os.path.join(get_run_dir(run_id), "measurements.json")


def _parse_run_dir_name(name: str) -> Optional[tuple[str, int]]:
    """Parse a run directory name in the form <user_id>-<run_number>."""
    if "-" not in name:
        return None

    user_id, run_number_text = name.rsplit("-", 1)
    if not user_id or not run_number_text.isdigit():
        return None

    return user_id, int(run_number_text)


def _list_run_dirs(user_id: Optional[str] = None) -> list[tuple[Path, str, int]]:
    """Return all valid run directories, optionally filtered by user_id."""
    output_dir = Path(get_output_dir())
    if not output_dir.exists():
        return []

    run_dirs: list[tuple[Path, str, int]] = []
    for path in output_dir.iterdir():
        if not path.is_dir():
            continue

        parsed = _parse_run_dir_name(path.name)
        if parsed is None:
            continue

        parsed_user_id, run_number = parsed
        if user_id is not None and parsed_user_id != user_id:
            continue

        run_dirs.append((path, parsed_user_id, run_number))

    return run_dirs


def get_latest_run_dir(user_id: Optional[str] = None) -> str:
    """Return the latest run directory path."""
    run_dirs = _list_run_dirs(user_id)
    if not run_dirs:
        if user_id is None:
            raise FileNotFoundError(f"No avatar runs found in {get_output_dir()}")
        raise FileNotFoundError(
            f"No avatar runs found for user_id '{user_id}' in {get_output_dir()}"
        )

    if user_id is None:
        latest_path = max(run_dirs, key=lambda item: item[0].stat().st_mtime)[0]
    else:
        latest_path = max(run_dirs, key=lambda item: item[2])[0]

    return str(latest_path)


def _get_existing_artifact_path(
    artifact_name: str,
    user_id: Optional[str] = None,
) -> str:
    """Return an artifact from the latest run, raising if it is missing."""
    run_dir = Path(get_latest_run_dir(user_id))
    artifact_path = run_dir / artifact_name
    if not artifact_path.exists():
        raise FileNotFoundError(f"Expected artifact not found: {artifact_path}")
    return str(artifact_path)


def get_latest_avatar_obj_path(user_id: Optional[str] = None) -> str:
    """Return the avatar.obj path from the latest run."""
    return _get_existing_artifact_path("avatar.obj", user_id)


def get_latest_measurements_json_path(user_id: Optional[str] = None) -> str:
    """Return the measurements.json path from the latest run."""
    return _get_existing_artifact_path("measurements.json", user_id)
