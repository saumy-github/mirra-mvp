"""Stable test fixtures — relocated from mirra_measurements/golden_users.py.

These fixture ids are dev/test seed data only; real accounts get u_<hex>
ids from the auth service (backend-implementation-plan.md, Phase 0 item 4).
"""

GOLDEN_USER_IDS = [
    "u_001",
    "u_002",
    "u_006",
    "u_007",
]

GOLDEN_USER_PRIORITY = {
    "u_001": 1,
    "u_002": 2,
    "u_006": 3,
    "u_007": 4,
}
