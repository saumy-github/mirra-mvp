"""
T-Shirt Appearance Extraction for CLO3D
=========================================

Four-stage pipeline that extracts appearance data from T-shirt photos
and produces CLO3D-compatible texture assets.

Stages:
  1. Segmentation       — RMBG-1.4 (or SAM fallback) isolates the garment
  2. View Selection     — CLIP zero-shot classifies front / back / side / irrelevant
  3. Colour Extraction  — K-Means in LAB colour space → HEX + palette
  4. Design Extraction  — Edge detection + contour analysis → graphic diffuse map

Each run auto-creates a new numbered folder  ext001 / ext002 / …
inside  extraction_output/.
"""

import os
import sys
import json
import math
import time
import shutil
import argparse
from pathlib import Path
from datetime import datetime

"""Compatibility shim for legacy imports from the old `tshirt_extractor`.

This module provides a tiny compatibility layer that re-exports the
canonical per-stage helpers and utilities (segmentation, view selection,
colour extraction, design extraction, and small run helpers) so legacy
scripts can continue to import from `tshirt_extractor` without changes.

Notes:
- This file intentionally avoids reintroducing the monolithic pipeline.
- The canonical implementations live in `segmentation.py`,
  `view_selection.py`, `colour_extraction.py`, `design_extraction.py`, and
  `run_manifest.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Re-export canonical helpers from the per-stage modules
from run_manifest import get_next_product_run_dir
from segmentation import (
    SegmentationResult,
    GarmentSegmentor,
    validate_transparent_bg,
)
from view_selection import ViewLabel, select_primary_image, list_cloth_images
from colour_extraction import ColourResult, ColourExtractor, validate_hex
from design_extraction import DesignResult, DesignExtractor, make_empty_graphic_like

@dataclass
class ExtractionResult:
    """Lightweight compatibility dataclass representing full pipeline output."""
    run_dir: str = ""
    segmentation: Optional[SegmentationResult] = None
    views: List[ViewLabel] = field(default_factory=list)
    colour: Optional[ColourResult] = None
    design: Optional[DesignResult] = None

def get_next_run_dir(base_dir: str, prefix: str = "ext") -> Path:
    """Create next auto-numbered `extNNN` directory under `base_dir`.

    This mirrors the old behaviour for callers that expect `get_next_run_dir`.
    """
    base = Path(base_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    existing_nums: List[int] = []
    for d in base.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            suffix = d.name[len(prefix):]
            if suffix.isdigit():
                if any(d.iterdir()):
                    existing_nums.append(int(suffix))

    next_num = (max(existing_nums) + 1) if existing_nums else 1
    run_dir = base / f"{prefix}{next_num:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

# Backwards-compatible exports
__all__ = [
    "ExtractionResult",
    "get_next_run_dir",
    "get_next_product_run_dir",
    "SegmentationResult",
    "GarmentSegmentor",
    "validate_transparent_bg",
    "ViewLabel",
    "select_primary_image",
    "list_cloth_images",
    "ColourResult",
    "ColourExtractor",
    "validate_hex",
    "DesignResult",
    "DesignExtractor",
    "make_empty_graphic_like",
]
