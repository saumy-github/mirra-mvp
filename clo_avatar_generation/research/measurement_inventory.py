"""Phase 2 measurement inventory contracts for the CLO-native path.

This module stores what we currently know about CLO-editable measurements and
what still needs to be manually confirmed from a real avatar template and CSV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..avatar_setup.contracts import AvatarFamily


FieldStatus = Literal[
    "documented_publicly",
    "visible_in_guide",
    "needs_template_confirmation",
    "unknown_csv_name",
]

FieldCategory = Literal[
    "width_basis",
    "height_basis",
    "circumference",
    "height",
    "length",
    "shape",
    "region_control",
]

ValueSource = Literal[
    "user_input_direct",
    "derived_from_user_input",
    "approx_from_prior",
    "unknown",
]


@dataclass(frozen=True)
class CLOMeasurementField:
    """One candidate editable CLO measurement field."""

    public_name: str
    category: FieldCategory
    status: FieldStatus
    likely_source: ValueSource
    notes: str = ""


@dataclass(frozen=True)
class TemplateMeasurementInventory:
    """Inventory of known or expected fields for one avatar family."""

    family: AvatarFamily
    template_mode: str
    fields: tuple[CLOMeasurementField, ...] = field(default_factory=tuple)
    unresolved_questions: tuple[str, ...] = field(default_factory=tuple)


COMMON_DOCUMENTED_FIELDS: tuple[CLOMeasurementField, ...] = (
    CLOMeasurementField(
        public_name="Total Height",
        category="height_basis",
        status="documented_publicly",
        likely_source="user_input_direct",
        notes="Explicitly documented as a height basis in CLO Avatar Editor docs.",
    ),
    CLOMeasurementField(
        public_name="HPS Height",
        category="height_basis",
        status="documented_publicly",
        likely_source="derived_from_user_input",
        notes="Documented by CLO as an alternate height basis; exact mapping needs template confirmation.",
    ),
    CLOMeasurementField(
        public_name="Inseam",
        category="height_basis",
        status="documented_publicly",
        likely_source="derived_from_user_input",
        notes="Documented by CLO as an alternate height basis.",
    ),
    CLOMeasurementField(
        public_name="Bust",
        category="width_basis",
        status="documented_publicly",
        likely_source="user_input_direct",
        notes="Used directly for female width control and generally visible in Avatar Editor guides.",
    ),
    CLOMeasurementField(
        public_name="Under Bust",
        category="width_basis",
        status="documented_publicly",
        likely_source="user_input_direct",
        notes="Documented width basis and movable region.",
    ),
    CLOMeasurementField(
        public_name="Weight",
        category="width_basis",
        status="documented_publicly",
        likely_source="user_input_direct",
        notes="Documented width basis option in Avatar Editor.",
    ),
    CLOMeasurementField(
        public_name="Waist",
        category="region_control",
        status="documented_publicly",
        likely_source="user_input_direct",
        notes="Documented movable circumference region.",
    ),
    CLOMeasurementField(
        public_name="High Hip",
        category="region_control",
        status="documented_publicly",
        likely_source="derived_from_user_input",
        notes="Documented movable circumference region; exact source in Mirra still needs mapping.",
    ),
    CLOMeasurementField(
        public_name="Low Hip",
        category="region_control",
        status="documented_publicly",
        likely_source="user_input_direct",
        notes="Documented movable circumference region.",
    ),
    CLOMeasurementField(
        public_name="Thigh",
        category="region_control",
        status="documented_publicly",
        likely_source="approx_from_prior",
        notes="Documented movable circumference region but not currently part of Mirra user input.",
    ),
    CLOMeasurementField(
        public_name="Neck Base",
        category="circumference",
        status="visible_in_guide",
        likely_source="approx_from_prior",
        notes="Seen in official guide screenshots; exact editability and CSV naming still need template confirmation.",
    ),
    CLOMeasurementField(
        public_name="Bicep",
        category="circumference",
        status="visible_in_guide",
        likely_source="approx_from_prior",
        notes="Seen in official guide screenshots; exact template availability needs confirmation.",
    ),
    CLOMeasurementField(
        public_name="Across Shoulder (Curvilinear)",
        category="length",
        status="visible_in_guide",
        likely_source="derived_from_user_input",
        notes="Potential target for shoulder mapping; exact CSV naming unknown.",
    ),
    CLOMeasurementField(
        public_name="Arm",
        category="length",
        status="visible_in_guide",
        likely_source="approx_from_prior",
        notes="Seen in guide screenshots; exact definition needs template confirmation.",
    ),
)


MALE_TEMPLATE_INVENTORY = TemplateMeasurementInventory(
    family="male",
    template_mode="default_clo_avatar",
    fields=COMMON_DOCUMENTED_FIELDS
    + (
        CLOMeasurementField(
            public_name="Crotch Volume",
            category="shape",
            status="documented_publicly",
            likely_source="approx_from_prior",
            notes="Documented as a male shape-control option.",
        ),
    ),
    unresolved_questions=(
        "Which male default avatar fields are editable versus greyed out in the chosen template?",
        "What are the exact CSV column names for male shoulder and arm-related controls?",
        "Which documented controls appear in the exact installed CLO version we will test?",
    ),
)


FEMALE_TEMPLATE_INVENTORY = TemplateMeasurementInventory(
    family="female",
    template_mode="default_clo_avatar",
    fields=COMMON_DOCUMENTED_FIELDS
    + (
        CLOMeasurementField(
            public_name="Cup Size",
            category="shape",
            status="documented_publicly",
            likely_source="derived_from_user_input",
            notes="Documented for Under Bust width mode.",
        ),
        CLOMeasurementField(
            public_name="Breast Shape",
            category="shape",
            status="documented_publicly",
            likely_source="approx_from_prior",
            notes="Documented female-specific shape control.",
        ),
        CLOMeasurementField(
            public_name="Breast Space",
            category="shape",
            status="documented_publicly",
            likely_source="approx_from_prior",
            notes="Documented female-specific shape control.",
        ),
        CLOMeasurementField(
            public_name="Breast Height",
            category="shape",
            status="documented_publicly",
            likely_source="approx_from_prior",
            notes="Documented female-specific shape control.",
        ),
    ),
    unresolved_questions=(
        "Which female default avatar fields are editable versus greyed out in the chosen template?",
        "What are the exact CSV column names for bust, under bust, and shoulder-related controls?",
        "How does CLO represent cup-related data in the import CSV, if at all?",
    ),
)


def get_phase2_inventory(family: AvatarFamily) -> TemplateMeasurementInventory:
    """Return the current Phase 2 inventory stub for one avatar family."""

    if family == "male":
        return MALE_TEMPLATE_INVENTORY
    return FEMALE_TEMPLATE_INVENTORY
