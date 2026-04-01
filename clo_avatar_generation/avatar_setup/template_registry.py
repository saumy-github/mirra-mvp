"""Phase 1 registry for CLO avatar template candidates.

This file intentionally stores only strategy-level metadata in Phase 1.
Actual .avt files can be added later without changing existing pipelines.
"""

from __future__ import annotations

from pathlib import Path

from .contracts import Phase1Strategy, TemplateIdentity


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_ROOT = PACKAGE_ROOT / "avt_templates"


PHASE1_STRATEGY = Phase1Strategy(
    clo_version="2025.x",
    primary_families=("male", "female"),
    candidate_source_modes=(
        "default_clo_avatar",
        "converted_size_editable_avatar",
        "converted_custom_shape_avatar",
    ),
    preferred_first_test_mode="default_clo_avatar",
    required_reference_count_per_family=1,
    notes=(
        "Start with the most native CLO path first before testing converted modes.",
        "Keep one reference template per family in Phase 1.",
        "Do not assume exact .avt files exist yet; the registry can hold placeholders until Phase 2.",
    ),
)


TEMPLATE_CANDIDATES: tuple[TemplateIdentity, ...] = (
    TemplateIdentity(
        template_id="male_default_primary",
        clo_version=PHASE1_STRATEGY.clo_version,
        family="male",
        source_mode="default_clo_avatar",
        display_name="Male default CLO avatar",
        avt_path=None,
        notes="Primary first-test candidate for the male family.",
    ),
    TemplateIdentity(
        template_id="female_default_primary",
        clo_version=PHASE1_STRATEGY.clo_version,
        family="female",
        source_mode="default_clo_avatar",
        display_name="Female default CLO avatar",
        avt_path=None,
        notes="Primary first-test candidate for the female family.",
    ),
    TemplateIdentity(
        template_id="male_size_editable_candidate",
        clo_version=PHASE1_STRATEGY.clo_version,
        family="male",
        source_mode="converted_size_editable_avatar",
        display_name="Male converted size-editable avatar",
        avt_path=None,
        notes="Secondary candidate if default avatar path lacks required fidelity.",
    ),
    TemplateIdentity(
        template_id="female_size_editable_candidate",
        clo_version=PHASE1_STRATEGY.clo_version,
        family="female",
        source_mode="converted_size_editable_avatar",
        display_name="Female converted size-editable avatar",
        avt_path=None,
        notes="Secondary candidate if default avatar path lacks required fidelity.",
    ),
    TemplateIdentity(
        template_id="male_custom_shape_candidate",
        clo_version=PHASE1_STRATEGY.clo_version,
        family="male",
        source_mode="converted_custom_shape_avatar",
        display_name="Male converted custom-shape avatar",
        avt_path=None,
        notes="Reserved for later comparison against size-editable conversion.",
    ),
    TemplateIdentity(
        template_id="female_custom_shape_candidate",
        clo_version=PHASE1_STRATEGY.clo_version,
        family="female",
        source_mode="converted_custom_shape_avatar",
        display_name="Female converted custom-shape avatar",
        avt_path=None,
        notes="Reserved for later comparison against size-editable conversion.",
    ),
)


def get_phase1_strategy() -> Phase1Strategy:
    """Return the locked Phase 1 strategy."""

    return PHASE1_STRATEGY


def list_template_candidates() -> tuple[TemplateIdentity, ...]:
    """Return all Phase 1 template candidates."""

    return TEMPLATE_CANDIDATES


def get_primary_candidates() -> tuple[TemplateIdentity, ...]:
    """Return the first candidates to test in Phase 2."""

    return tuple(
        candidate
        for candidate in TEMPLATE_CANDIDATES
        if candidate.source_mode == PHASE1_STRATEGY.preferred_first_test_mode
    )
