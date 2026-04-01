"""Contracts for the isolated CLO-native avatar experiment."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


AvatarFamily = Literal["male", "female"]
AvatarSourceMode = Literal[
    "default_clo_avatar",
    "converted_size_editable_avatar",
    "converted_custom_shape_avatar",
]


@dataclass(frozen=True)
class TemplateIdentity:
    """Stable identity for one CLO avatar template candidate."""

    template_id: str
    clo_version: str
    family: AvatarFamily
    source_mode: AvatarSourceMode
    display_name: str
    avt_path: Path | None = None
    notes: str = ""


@dataclass(frozen=True)
class Phase1Strategy:
    """Locked Phase 1 strategy for the CLO-native experiment."""

    clo_version: str
    primary_families: tuple[AvatarFamily, ...] = ("male", "female")
    candidate_source_modes: tuple[AvatarSourceMode, ...] = (
        "default_clo_avatar",
        "converted_size_editable_avatar",
        "converted_custom_shape_avatar",
    )
    preferred_first_test_mode: AvatarSourceMode = "default_clo_avatar"
    required_reference_count_per_family: int = 1
    notes: tuple[str, ...] = field(default_factory=tuple)
