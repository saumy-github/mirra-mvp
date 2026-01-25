"""Canonical JSON structure for pipeline artifacts."""

from typing import Dict, Any, List, TypedDict, Optional


# MVP measurement fields used for fitting (2% tolerance gate)
FITTING_MEASUREMENT_FIELDS = [
    'height_cm',
    'shoulder_width_cm',
    'chest_circumference_cm',
    'waist_circumference_cm',
    'hip_circumference_cm',
]

# Validate-only fields (not used in optimization)
VALIDATE_ONLY_FIELDS = [
    'leg_length_cm',
]

# Skipped fields for MVP (bust measurements not used)
SKIPPED_FIELDS = [
    'bust_circumference_cm',
    'under_bust_circumference_cm',
]

# Tolerance threshold for fitness gate (2%)
FITNESS_TOLERANCE_PERCENT = 2.0


# Schema for inputs JSON (raw Mongo snapshot + derived targets + config)
class InputsSchema(TypedDict):
    run_id: str
    created_at: str
    user_id: str
    mongo_snapshot: Dict[str, Any]
    derived_targets: Dict[str, float]
    config: Dict[str, Any]


# Schema for fit report in values JSON
class FitReport(TypedDict):
    predicted_measurements: Dict[str, float]
    errors_percent: Dict[str, float]
    loss: float
    iterations: int
    max_error_percent: float
    passed_gate: bool


# Schema for values JSON (status + betas/thetas/scale + fit report + pointer to inputs)
class ValuesSchema(TypedDict):
    run_id: str
    created_at: str
    status: str
    inputs_file: str
    betas: List[float]
    thetas: List[float]
    scale: float
    pose_metadata: Dict[str, str]
    fit_report: FitReport


# Create empty inputs schema template
def create_inputs_schema(
    run_id: str,
    created_at: str,
    user_id: str,
    mongo_snapshot: Dict[str, Any],
    derived_targets: Dict[str, float],
    config: Dict[str, Any]
) -> InputsSchema:
    return {
        'run_id': run_id,
        'created_at': created_at,
        'user_id': user_id,
        'mongo_snapshot': mongo_snapshot,
        'derived_targets': derived_targets,
        'config': config,
    }


# Create empty values schema template
def create_values_schema(
    run_id: str,
    created_at: str,
    status: str,
    inputs_file: str,
    betas: List[float],
    thetas: List[float],
    scale: float,
    pose_metadata: Dict[str, str],
    fit_report: FitReport
) -> ValuesSchema:
    return {
        'run_id': run_id,
        'created_at': created_at,
        'status': status,
        'inputs_file': inputs_file,
        'betas': betas,
        'thetas': thetas,
        'scale': scale,
        'pose_metadata': pose_metadata,
        'fit_report': fit_report,
    }
