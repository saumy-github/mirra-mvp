# Mirra Measurements DB

Standalone Python module for storing and retrieving user body measurements in MongoDB.

## Overview

- **Database**: `mirratest`
- **Collection**: `measurements`
- **Indexes**:
  - `user_id` (unique)
  - `gender` (non-unique)

## Data Model

Each measurement document contains:

### Required Fields

- `user_id`: string (e.g., "user_m_001")
- `gender`: string, one of: "male" | "female"
- `accuracy`: string, one of: "accurate" | "approx"
- `created_at`: datetime (UTC)
- `updated_at`: datetime (UTC)

### Optional Shared Fields

- `height_cm`: number
- `weight_kg`: number
- `shoulder_width_cm`: number
- `waist_circumference_cm`: number
- `hip_circumference_cm`: number
- `leg_length_cm`: number
- `body_shape_type`: string (e.g., "rectangle", "hourglass", "inverted_triangle")
- `skin_tone_hex`: string (e.g., "#1A1A1A")

### Male-Specific Optional Field

- `chest_circumference_cm`: number

### Female-Specific Optional Fields

- `bust_circumference_cm`: number
- `under_bust_circumference_cm`: number

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure MongoDB Connection

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and set your MongoDB connection string:

```bash
MONGODB_URI=mongodb://localhost:27017
```

For MongoDB Atlas or remote servers:

```bash
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

### 3. Seed the Database

Run the seed script to populate test data (10 documents: 5 male + 5 female):

```bash
# From the repo root (mirra-mvp/)
python -m mirra_measurements.seed_measurements
```

Or if you're inside the `mirra_measurements/` directory:

```bash
cd mirra_measurements_db
python seed_measurements.py
```

The seed script will:

- Insert or update 10 measurement documents
- Use deterministic user IDs (`user_m_001` to `user_m_005`, `user_f_001` to `user_f_005`)
- Include fully-filled records and records with missing optional fields
- Include both "accurate" and "approx" accuracy examples
- Avoid duplicates on re-run (upsert by `user_id`)

## Usage

### Connect to Database

```python
from mirra_measurements.db import get_db, get_measurements_collection

# Get database
db = get_db()

# Get measurements collection (with indexes)
collection = get_measurements_collection()
```

### Create and Validate Documents

```python
from mirra_measurements import create_measurement_doc, validate_measurement_doc

# Create a measurement document
doc = create_measurement_doc(
    user_id="user_m_100",
    gender="male",
    accuracy="accurate",
    height_cm=180.0,
    weight_kg=75.0,
    chest_circumference_cm=100.0
)

# Validate before inserting
is_valid, error = validate_measurement_doc(doc)
if is_valid:
    collection = get_measurements_collection()
    collection.insert_one(doc)
else:
    print(f"Validation error: {error}")
```

### Query Measurements

```python
from mirra_measurements.db import get_measurements_collection

collection = get_measurements_collection()

# Find by user_id
user_data = collection.find_one({"user_id": "user_m_001"})

# Find all males
males = collection.find({"gender": "male"})

# Find accurate measurements only
accurate = collection.find({"accuracy": "accurate"})
```

## Validation Rules

The `validate_measurement_doc()` function enforces:

1. **Required fields** must exist: `user_id`, `gender`, `accuracy`, `created_at`, `updated_at`
2. **Enums** must be valid:
   - `gender` ∈ {"male", "female"}
   - `accuracy` ∈ {"accurate", "approx"}
3. **Optional fields** are allowed to be missing or `None`
4. **Numeric fields** (if present) must be numbers > 0
5. **String fields** (if present) must be strings

## Architecture

```plain
mirra_measurements/
├── __init__.py           # Package initialization
├── db.py                 # MongoDB connection and collection access
├── avatar_model.py       # Avatar body measurement model and validation
├── garment_model.py      # Garment pattern model and validation
├── seed_measurements.py  # Seeding script with test data
├── seed_garments.py      # Seeding script for garment templates
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables
└── README.md             # This file
```

## Requirements

- Python 3.10+
- MongoDB (local or remote)
- Dependencies: `pymongo`, `python-dotenv`

## Future Extensions

This module is designed to be reusable across different technologies. Potential additions:

- REST API endpoints (FastAPI/Flask)
- GraphQL API
- Additional measurement types
- Data export/import utilities
- Analytics and aggregation queries
- User authentication integration

## License

(Add your license information here)
