"""
MIRAAA Pipeline Package

Garment Design Automation Pipeline v2.0
All measurements in centimeters (cm).
"""

from .pipeline import (
    MIRAAPipeline,
    PipelineResult,
    run_pipeline
)

from .config import (
    PipelineConfig,
    Measurements,
    DEFAULT_CONFIG
)

__version__ = "2.0.0"
__all__ = [
    'MIRAAPipeline',
    'PipelineResult',
    'run_pipeline',
    'PipelineConfig',
    'Measurements',
    'DEFAULT_CONFIG'
]
