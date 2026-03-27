"""Stable test fixtures for development and regression testing."""

# Golden user IDs in priority order (highest to lowest)
GOLDEN_USER_IDS = [
    'u_001',
    'u_002',
    'u_006',
    'u_007',
]

# Mapping of user_id to priority integer (lower number = higher priority)
GOLDEN_USER_PRIORITY = {
    'u_001': 1,
    'u_002': 2,
    'u_006': 3,
    'u_007': 4,
}
