# Mirra Measurements DB

Standalone Python module for storing avatar body measurements and size templates in MongoDB.

## Overview

- Database: `mirratest`
- Collections:
  - `measurements`
  - `sizes`

## Measurements Collection

Required fields:

- `user_id` (for example `u_001`)
- `gender`
- `accuracy`
- `created_at`
- `updated_at`

Optional shared fields:

- `height_cm`
- `weight_kg`
- `shoulder_width_cm`
- `waist_circumference_cm`
- `hip_circumference_cm`
- `leg_length_cm`
- `body_shape_type`
- `skin_tone_hex`

Optional male field:

- `chest_circumference_cm`

Optional female fields:

- `bust_circumference_cm`
- `under_bust_circumference_cm`

## Sizes Collection

Required fields:

- `size_id` (for example `s_001`)
- `fit_type`
- `half_chest_width_cm`
- `garment_length_cm`
- `shoulder_width_cm`
- `neck_width_cm`
- `neck_depth_front_cm`
- `neck_depth_back_cm`
- `sleeve_length_cm`
- `bicep_width_cm`
- `armhole_depth_cm`
- `seam_allowance_cm`
- `created_at`
- `updated_at`

Optional cloth metadata:

- `cloth_id` (for example `c_001`)
- `cloth_label`
- `category`

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example` and set:

```bash
MONGODB_URI=mongodb://localhost:27017
```

## Seed Data

Seed measurements:

```bash
python -m mirra_measurements.seed_measurements
```

Seed sizes:

```bash
python -m mirra_measurements.seed_sizes
```

## Usage

Measurements collection:

```python
from mirra_measurements.db import get_measurements_collection

measurements = get_measurements_collection()
user_data = measurements.find_one({"user_id": "u_001"})
```

Sizes collection:

```python
from mirra_measurements.db import get_sizes_collection

sizes = get_sizes_collection()
size_data = sizes.find_one({"size_id": "s_001"})
```

Create measurement docs:

```python
from mirra_measurements import create_measurement_doc, validate_measurement_doc
```

Create size docs:

```python
from mirra_measurements import create_size_doc, validate_size_doc
```

## Architecture

```plain
mirra_measurements/
|-- __init__.py
|-- db.py
|-- avatar_model.py
|-- size_model.py
|-- seed_measurements.py
|-- seed_sizes.py
|-- .env.example
`-- README.md
```
