"""Run identity helpers for the Step-1 CLO avatar workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PACKAGE_ROOT / "output"


@dataclass(frozen=True)
class RunIdentity:
    """Canonical run identity in the form <user_id>-<run_number>."""

    user_id: str
    number: int

    @property
    def run_id(self) -> str:
        return f"{self.user_id}-{self.number:03d}"


def get_output_root() -> Path:
    return OUTPUT_ROOT


def get_run_dir(run_id: RunIdentity) -> Path:
    return get_output_root() / run_id.run_id


def parse_run_dir_name(name: str) -> Optional[RunIdentity]:
    if "-" not in name:
        return None

    user_id, run_number_text = name.rsplit("-", 1)
    if not user_id or not run_number_text.isdigit():
        return None

    return RunIdentity(user_id=user_id, number=int(run_number_text))


def list_run_dirs(user_id: str | None = None) -> list[Path]:
    output_root = get_output_root()
    if not output_root.exists():
        return []

    run_dirs: list[Path] = []
    for path in output_root.iterdir():
        if not path.is_dir():
            continue
        parsed = parse_run_dir_name(path.name)
        if parsed is None:
            continue
        if user_id is not None and parsed.user_id != user_id:
            continue
        run_dirs.append(path)
    return sorted(run_dirs)


def get_next_run_number(user_id: str) -> int:
    max_number = 0
    for path in list_run_dirs(user_id):
        parsed = parse_run_dir_name(path.name)
        if parsed is None:
            continue
        max_number = max(max_number, parsed.number)
    return max_number + 1


def get_latest_user_id() -> str | None:
    latest_identity: RunIdentity | None = None
    for path in list_run_dirs():
        parsed = parse_run_dir_name(path.name)
        if parsed is None:
            continue
        if latest_identity is None or parsed.number > latest_identity.number:
            latest_identity = parsed
    return latest_identity.user_id if latest_identity else None
