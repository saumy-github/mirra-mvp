"""Phase 7 decision logic for the CLO-native avatar experiment.

This module helps answer one product question:

Should the CLO-native avatar become:
1. the final simulation and visible avatar
2. only the simulation proxy
3. a rejected path

The logic is intentionally lightweight and isolated so the experiment can be
evaluated without touching the current production path.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal


AvatarRoleRecommendation = Literal[
    "full_simulation_and_visible_avatar",
    "simulation_proxy_only",
    "reject_clo_native_path",
]


@dataclass(frozen=True)
class RoleDecisionInput:
    """Normalized inputs for deciding the role of the CLO-native avatar."""

    body_fidelity_score: float
    arrangement_reliability_score: float
    placement_quality_score: float
    simulation_cleanliness_score: float
    implementation_cost_score: float
    notes: str = ""


@dataclass(frozen=True)
class RoleDecisionOutcome:
    """Recommendation output for the CLO-native avatar role."""

    recommendation: AvatarRoleRecommendation
    weighted_score: float
    rationale: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp_score(value: float) -> float:
    return max(0.0, min(10.0, float(value)))


def decide_avatar_role(inputs: RoleDecisionInput) -> RoleDecisionOutcome:
    """Recommend the role the CLO-native avatar should play.

    Scoring interpretation:
    - higher body fidelity is better
    - higher arrangement reliability is better
    - higher placement quality is better
    - higher simulation cleanliness is better
    - higher implementation cost is worse
    """

    body_fidelity = _clamp_score(inputs.body_fidelity_score)
    arrangement = _clamp_score(inputs.arrangement_reliability_score)
    placement = _clamp_score(inputs.placement_quality_score)
    simulation = _clamp_score(inputs.simulation_cleanliness_score)
    implementation_cost = _clamp_score(inputs.implementation_cost_score)

    weighted_score = (
        0.30 * body_fidelity
        + 0.20 * arrangement
        + 0.20 * placement
        + 0.20 * simulation
        - 0.10 * implementation_cost
    )

    rationale: list[str] = []

    if arrangement >= 8.0 and placement >= 8.0 and simulation >= 8.0 and body_fidelity >= 7.0:
        rationale.append("CLO-native path is strong on arrangement, placement, simulation, and acceptable on body fidelity.")
        return RoleDecisionOutcome(
            recommendation="full_simulation_and_visible_avatar",
            weighted_score=weighted_score,
            rationale=tuple(rationale),
        )

    if arrangement >= 7.0 and placement >= 7.0 and simulation >= 7.0 and body_fidelity < 7.0:
        rationale.append("CLO-native path is operationally strong for cloth handling, but body fidelity is weaker than desired for the final visible twin.")
        rationale.append("This makes it a better simulation proxy than a final user-facing avatar.")
        return RoleDecisionOutcome(
            recommendation="simulation_proxy_only",
            weighted_score=weighted_score,
            rationale=tuple(rationale),
        )

    rationale.append("CLO-native path is not yet strong enough across body fidelity and cloth workflow to justify adoption.")
    return RoleDecisionOutcome(
        recommendation="reject_clo_native_path",
        weighted_score=weighted_score,
        rationale=tuple(rationale),
    )

