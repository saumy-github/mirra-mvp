"""Phase 4 output schema definitions for the isolated CLO-native path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NativeAvatarOutputSchema:
    """High-level output contract for one CLO-native experimental run."""

    run_id: str
    status: str
    planned_outputs: dict[str, Any] = field(default_factory=dict)

