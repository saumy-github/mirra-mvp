"""Phase 3 mapping from Mirra measurement space to CLO measurement space.

This module is intentionally conservative. It records:

1. fields that appear to map directly
2. fields that likely need approximation or derived logic
3. fields that remain blocked until a real CLO template and CSV schema are confirmed

It does not yet generate CSV files or call CLO.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .contracts import AvatarFamily


MappingStatus = Literal[
    "direct_candidate",
    "derived_candidate",
    "approximation_candidate",
    "blocked_until_template_confirmation",
    "not_currently_supported",
]

TargetConfidence = Literal["high", "medium", "low", "unknown"]


@dataclass(frozen=True)
class MeasurementMapping:
    """One mapping from a Mirra field into a CLO field or control."""

    mirra_field: str
    clo_target: str | None
    status: MappingStatus
    confidence: TargetConfidence
    notes: str = ""


@dataclass(frozen=True)
class FamilyMappingProfile:
    """Mapping profile for one avatar family."""

    family: AvatarFamily
    mappings: tuple[MeasurementMapping, ...] = field(default_factory=tuple)
    unresolved_questions: tuple[str, ...] = field(default_factory=tuple)


COMMON_MAPPINGS: tuple[MeasurementMapping, ...] = (
    MeasurementMapping(
        mirra_field="height_cm",
        clo_target="Total Height",
        status="direct_candidate",
        confidence="high",
        notes="Best current direct candidate from public CLO docs.",
    ),
    MeasurementMapping(
        mirra_field="weight_kg",
        clo_target="Weight",
        status="direct_candidate",
        confidence="high",
        notes="Documented width-basis control in CLO.",
    ),
    MeasurementMapping(
        mirra_field="waist_circumference_cm",
        clo_target="Waist",
        status="direct_candidate",
        confidence="high",
        notes="Documented movable region and strong semantic match.",
    ),
    MeasurementMapping(
        mirra_field="hip_circumference_cm",
        clo_target="Low Hip",
        status="derived_candidate",
        confidence="medium",
        notes="Closest currently documented region candidate; exact template field still needs confirmation.",
    ),
    MeasurementMapping(
        mirra_field="shoulder_width_cm",
        clo_target="Across Shoulder (Curvilinear)",
        status="blocked_until_template_confirmation",
        confidence="medium",
        notes="Promising guide-visible match, but exact editability and CSV name are unconfirmed.",
    ),
    MeasurementMapping(
        mirra_field="leg_length_cm",
        clo_target="Inseam",
        status="derived_candidate",
        confidence="medium",
        notes="Strong candidate, but Mirra leg length collection method may not match CLO inseam definition exactly.",
    ),
    MeasurementMapping(
        mirra_field="body_shape_type",
        clo_target=None,
        status="approximation_candidate",
        confidence="low",
        notes="Not a direct CLO measurement field; may later influence shape controls or priors.",
    ),
    MeasurementMapping(
        mirra_field="skin_tone_hex",
        clo_target=None,
        status="not_currently_supported",
        confidence="high",
        notes="Not part of measurement import; belongs to appearance or later rendering layers.",
    ),
)


MALE_PROFILE = FamilyMappingProfile(
    family="male",
    mappings=COMMON_MAPPINGS
    + (
        MeasurementMapping(
            mirra_field="chest_circumference_cm",
            clo_target=None,
            status="blocked_until_template_confirmation",
            confidence="unknown",
            notes="Public docs document Bust / Under Bust more clearly than male Chest. Need real male template field inventory.",
        ),
    ),
    unresolved_questions=(
        "What exact male chest-related field should Mirra chest map to in the chosen CLO template?",
        "Is shoulder width best mapped to Across Shoulder, another shoulder field, or split into multiple controls?",
        "Which male arm and neck fields are editable and importable in the real template?",
    ),
)


FEMALE_PROFILE = FamilyMappingProfile(
    family="female",
    mappings=COMMON_MAPPINGS
    + (
        MeasurementMapping(
            mirra_field="bust_circumference_cm",
            clo_target="Bust",
            status="direct_candidate",
            confidence="high",
            notes="Strong direct match from public CLO docs.",
        ),
        MeasurementMapping(
            mirra_field="under_bust_circumference_cm",
            clo_target="Under Bust",
            status="direct_candidate",
            confidence="high",
            notes="Strong direct match from public CLO docs.",
        ),
    ),
    unresolved_questions=(
        "How does CLO represent cup-related values in the import path for the selected female template?",
        "Which shoulder-related field is the correct target for Mirra shoulder width in the chosen female template?",
        "Which female arm and neck fields are editable and importable in the real template?",
    ),
)


def get_family_mapping_profile(family: AvatarFamily) -> FamilyMappingProfile:
    """Return the current mapping profile for one family."""

    if family == "male":
        return MALE_PROFILE
    return FEMALE_PROFILE


def list_direct_candidates(family: AvatarFamily) -> tuple[MeasurementMapping, ...]:
    """Return fields that are strongest direct candidates today."""

    profile = get_family_mapping_profile(family)
    return tuple(item for item in profile.mappings if item.status == "direct_candidate")

