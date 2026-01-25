"""Canonical run identity and generated file paths."""

import os
from typing import NamedTuple


# Run identity: user_id + per-user counter (e.g., user_m_001-001)
class RunIdentity(NamedTuple):
    user_id: str
    number: int
    
    @property
    def run_id(self) -> str:
        return f"{self.user_id}-{self.number:03d}"


# Get base directory for generated files
def get_generated_dir() -> str:
    return os.path.join(os.path.dirname(__file__), 'generated')


# Get canonical path for inputs JSON file
def get_inputs_json_path(run_id: RunIdentity) -> str:
    return os.path.join(get_generated_dir(), f"inputs-{run_id.run_id}.json")


# Get canonical path for values JSON file
def get_values_json_path(run_id: RunIdentity) -> str:
    return os.path.join(get_generated_dir(), f"values-{run_id.run_id}.json")


# Get canonical path for avatar GLB file
def get_avatar_glb_path(run_id: RunIdentity) -> str:
    return os.path.join(get_generated_dir(), f"{run_id.run_id}.glb")
