# Mirra Repository Rules & Conventions

## Python Environment

**Python Version**: 3.9+ (check requirements.txt for exact version)

**Virtual Environment**: 
- Setup: Follow SETUP.md at project root
- Activation: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/Mac)

**Dependencies**:
- Install via: `pip install -r requirements.txt`
- Add new: Update requirements.txt, run pip install
- Never commit .venv/ folder

## Tech Stack Summary

### Core Technologies
- **CLO 3D SDK**: Via REST API plugin (no direct file access)
- **REST API**: 27 endpoints defined in `clo_workspace/plugin_contract.json`
- **Data Storage**: MongoDB for measurements, products, metadata
- **Web Framework**: Flask/FastAPI (if web endpoints exist)
- **Image Processing**: OpenCV, PIL/Pillow, scikit-image
- **ML Models**: RMBG-1.4 (segmentation), CLIP (view classification), scikit-learn (K-Means)

### Key Libraries
- `requests` - REST client for CLO plugin
- `opencv-python` - Image processing
- `numpy`, `scipy` - Numerical computation
- `pymongo` - MongoDB client
- `pydantic` - Data validation (schemas)

## File Organization

### Folder Meanings

**clo_workspace/**
- Purpose: REST API plugin bridge to CLO 3D
- Contains: Plugin sources (Windows, macOS), build scripts, API contract
- Entry: `build_plugin.py` (build before using other steps)
- Do NOT: Modify plugin code without deep CLO 3D knowledge

**clo_avatar_generation/**
- Purpose: Step 1 (avatar generation) + Step 3 (VTO rendering) pipelines
- Subfolders: `avatar_runtime/` (Step 1), `native_vto/` (Step 3)
- Entry: `run_avatar.py` (Step 1), `run_clo_vto.py` (Step 3)
- Key: Context and pipeline orchestrators

**product_ingestion/**
- Purpose: Step 2 (2D → 3D conversion) pipeline
- Stages: Segmentation → View selection → Color extraction → Design extraction → Pattern generation
- Entry: `run_product_ingestion.py`
- Key: Panel generation and DXF export

**mirra_measurements/**
- Purpose: Measurement data structures, utilities, validation
- Used By: All steps (Step 1: input, Step 2: sizing, Step 3: optional)
- Key: GarmentMeasurements dataclass, field validation

**utils/**
- Purpose: Shared utilities across all steps
- Examples: File I/O, JSON handling, path utilities

**output/**
- Purpose: Run artifacts and results (created automatically)
- Structure: Numbered folders per step
- Keep: All artifacts preserved for debugging/auditing
- Clean: Only if explicitly instructed

### Naming Conventions

**Files**:
- Python modules: `snake_case.py` (e.g., `panel_generation.py`)
- Configuration: `snake_case_config.py` or `config.json`
- Constants: `UPPER_SNAKE_CASE.py` (e.g., `SEGMENT_PARAMS.py`)
- Tests: `test_module_name.py` (if test folder exists)

**Directories**:
- Feature modules: `snake_case/` (e.g., `avatar_runtime/`)
- Component groups: `snake_case/` (e.g., `native_vto/`)
- Never use CamelCase for directories

**Classes**:
- `PascalCase` (e.g., `DynamicPatternGenerator`, `CLORestClient`)

**Functions & Methods**:
- `snake_case` (e.g., `apply_measurements()`, `compute_error()`)

**Constants**:
- `UPPER_SNAKE_CASE` (e.g., `MAX_ITERATIONS`, `DEFAULT_TIMEOUT`)

## Coding Style Rules

### Critical Rules (Non-Negotiable)

1. **Command Format**: Use repo-root relative paths, NEVER `python -m`
   - ✅ Correct: `python clo_avatar_generation/run_avatar.py`
   - ❌ Wrong: `python -m clo_avatar_generation.run_avatar`
   - Why: Ensures consistency across local, CI/CD, and documentation

2. **Exact Formatting Match**:
   - Keep existing spacing, indentation, line breaks
   - Don't expand compact imports into multiple lines
   - Don't add/remove extra spaces around operators
   - Match the exact style of surrounding code

3. **Quote Consistency**:
   - Do NOT change single quotes to double quotes or vice versa
   - Match existing file convention
   - If no convention exists, use single quotes (Python default)

4. **Import Organization**:
   1. External libraries first (sys, os, etc.)
   2. Third-party libraries (requests, numpy, etc.)
   3. Internal absolute imports (@-style if using)
   4. Relative imports (./module, ../module)
   5. Type imports (if separate)
   6. Keep imports compact on single lines where possible

5. **No Unnecessary Code**:
   - Don't add error handling for impossible scenarios
   - Don't add features beyond task scope
   - Don't create abstractions for 1-2 uses
   - Don't add comments explaining WHAT code does (variable names should do that)
   - Only add comments for WHY (non-obvious constraints, workarounds)

6. **No .agent/ or .claude/ Modifications**:
   - These are documentation, not code
   - Only modify with explicit instructions
   - Ask before changing

### Formatting Conventions

**Line Length**: Keep under 100 characters where practical  
**Indentation**: 4 spaces (no tabs)  
**Blank Lines**: Separate logical sections with single blank line  
**Docstrings**: One-line max (prefer good naming over docstrings)  
**Type Hints**: Use where clarity improves (not required everywhere)

## Do's and Don'ts

### DO ✅

- **Keep changes scoped**: Only modify what's needed for your task
- **Test locally**: Verify your changes work before considering done
- **Check output artifacts**: JSON files in output/ tell you what happened
- **Follow naming conventions**: Consistency helps everyone
- **Use relative paths**: For files, use repo-root relative (not absolute)
- **Preserve existing style**: Match surrounding code formatting
- **Document assumptions**: If not obvious, add a one-line comment
- **Commit often**: Small, focused commits are better than one giant commit

### DON'T ❌

- **Don't use `python -m`**: Use repo-root relative paths always
- **Don't modify .agent/ or .claude/**:  Unless explicitly told
- **Don't add unnecessary features**: Stay focused on current task
- **Don't change quote styles**: Keep existing convention
- **Don't reformat code unnecessarily**: Only change what needs changing
- **Don't create new abstractions for <3 uses**: Keep it simple
- **Don't add defensive error handling**: Trust internal code guarantees
- **Don't commit without testing**: Verify locally first

## Dependencies & Imports

### Adding New Dependencies

1. Install locally: `pip install package-name`
2. Add to requirements.txt with version pin
3. Test import works
4. Document in this file if major addition

### Import Best Practices

```python
# Good: Organized and concise
import json
import os
from pathlib import Path

import requests
import numpy as np
from pymongo import MongoClient

from mirra_measurements import GarmentMeasurements
from utils import save_json

# Avoid: Scattered, hard to scan
from utils import *
import sys, os, json
from pymongo import *
```

## Running Code

### From Repository Root

All commands run from: `c:\D-drive-data\mirra-mvp` (Windows) or equivalent Linux/Mac path

```bash
# Correct
python clo_avatar_generation/run_avatar.py --user-id 123

# Incorrect
cd clo_avatar_generation && python run_avatar.py
python -m clo_avatar_generation.run_avatar --user-id 123
```

## When to Ask Questions

1. **Quick lookup**: Check `.claude/quick-reference.md`
2. **Known issue**: Check `.claude/troubleshooting.md`
3. **Architecture question**: Check `.claude/architecture/` (your step)
4. **Convention question**: Check this file or `.claude/faq.md`
5. **Still stuck**: Ask in conversation with full context

## Legacy Folders (Do Not Modify)

At repo root, these folders are no longer maintained:
- `avatar_generation/` (superseded by `clo_avatar_generation/`)
- `vto/` (superseded by `clo_avatar_generation/native_vto/`)
- `research/` (archived learning)
- `random/` (scratch work)
- `models/` (if not actively used)

**Do NOT** make changes in these folders unless explicitly directed.
