"""Phase 4 input schema definitions for the isolated CLO-native path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NativeAvatarInputSchema:
    """High-level input contract for one CLO-native experimental run."""

    user_id: str
    family: str
    template_id: str
    source_measurements: dict[str, Any] = field(default_factory=dict)

