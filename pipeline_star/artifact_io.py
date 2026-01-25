"""Write pipeline artifacts to JSON files with deterministic formatting."""

import json
import os
from typing import Dict, Any
from datetime import datetime

from pipeline_star.run_manifest import RunIdentity, get_inputs_json_path, get_values_json_path, get_generated_dir
from pipeline_star.artifact_schema import InputsSchema, ValuesSchema


# Write inputs JSON artifact to pipeline_star/generated/
def write_inputs_json(run_id: RunIdentity, inputs_data: InputsSchema) -> str:
    os.makedirs(get_generated_dir(), exist_ok=True)
    
    file_path = get_inputs_json_path(run_id)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(inputs_data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write('\n')
    
    return file_path


# Write values JSON artifact to pipeline_star/generated/
def write_values_json(run_id: RunIdentity, values_data: ValuesSchema) -> str:
    os.makedirs(get_generated_dir(), exist_ok=True)
    
    if values_data['status'] not in ['passed', 'failed']:
        raise ValueError(f"Invalid status: {values_data['status']}. Must be 'passed' or 'failed'.")
    
    file_path = get_values_json_path(run_id)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(values_data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write('\n')
    
    return file_path


# Get current timestamp in ISO 8601 format
def get_timestamp() -> str:
    return datetime.utcnow().isoformat() + 'Z'
