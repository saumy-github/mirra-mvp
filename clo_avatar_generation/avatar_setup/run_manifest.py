"""Run identity and output layout for the isolated CLO-native experiment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PACKAGE_ROOT / "output"


@dataclass(frozen=True)
class CLONativeRunIdentity:
    """Run naming contract for the CLO-native experiment."""

    user_id: str
    family: str
    number: int

    @property
    def run_id(self) -> str:
        return f"{self.user_id}__{self.family}__{self.number:03d}"


def get_output_root() -> Path:
    """Return the output root for the CLO-native experiment."""

    return OUTPUT_ROOT


def get_run_dir(run_id: CLONativeRunIdentity) -> str:
    """Return the full run directory path."""

    return str(get_output_root() / run_id.run_id)
