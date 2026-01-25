"""Stable test fixtures for development and regression testing."""

# Golden user IDs in priority order (highest to lowest)
GOLDEN_USER_IDS = [
    'user_m_001',
    'user_m_002',
    'user_f_001',
    'user_f_002',
]

# Mapping of user_id to priority integer (lower number = higher priority)
GOLDEN_USER_PRIORITY = {
    'user_m_001': 1,
    'user_m_002': 2,
    'user_f_001': 3,
    'user_f_002': 4,
}
