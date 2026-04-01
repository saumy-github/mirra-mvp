"""Phase 7 CLI for deciding the role of the CLO-native avatar."""

from __future__ import annotations

import argparse
from pathlib import Path

from .decision_matrix import RoleDecisionInput, decide_avatar_role
from ..reporting import write_json_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the role of the CLO-native avatar.")
    parser.add_argument("--body-fidelity", type=float, required=True)
    parser.add_argument("--arrangement-reliability", type=float, required=True)
    parser.add_argument("--placement-quality", type=float, required=True)
    parser.add_argument("--simulation-cleanliness", type=float, required=True)
    parser.add_argument("--implementation-cost", type=float, required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--report-path", required=True)
    args = parser.parse_args()

    decision_input = RoleDecisionInput(
        body_fidelity_score=args.body_fidelity,
        arrangement_reliability_score=args.arrangement_reliability,
        placement_quality_score=args.placement_quality,
        simulation_cleanliness_score=args.simulation_cleanliness,
        implementation_cost_score=args.implementation_cost,
        notes=args.notes,
    )
    outcome = decide_avatar_role(decision_input)

    payload = {
        "phase": "phase-7-avatar-role-decision",
        "input": {
            "body_fidelity_score": decision_input.body_fidelity_score,
            "arrangement_reliability_score": decision_input.arrangement_reliability_score,
            "placement_quality_score": decision_input.placement_quality_score,
            "simulation_cleanliness_score": decision_input.simulation_cleanliness_score,
            "implementation_cost_score": decision_input.implementation_cost_score,
            "notes": decision_input.notes,
        },
        "outcome": outcome.to_dict(),
    }
    report_path = write_json_report(Path(args.report_path), payload)
    print(f"Wrote avatar-role decision report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
