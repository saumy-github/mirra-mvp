# Setup Guide

## Step 1 — Python Environment & Dependencies

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

2. Activate it:

   ```bash
   # On Linux / macOS:
   source .venv/bin/activate

   # On Windows:
   .venv\Scripts\activate
   ```

3. Install all dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Print all installed packages:

   ```bash
   pip list
   ```

---

## Step 2 — MongoDB Connection & Seeding

To use the measurements database, set up your MongoDB connection and seed test data:

1. Go to the `mirra_measurements` folder:

   ```bash
   cd mirra_measurements
   ```

2. Copy the example environment file and edit it:

   ```bash
   cp .env.example .env
   # Edit .env and set your MongoDB connection string
   ```

3. Seed the database with test data (10 documents: 5 male + 5 female):

   From the repo root:

   ```bash
   python -m mirra_measurements.seed_measurements
   ```

   Or from inside `mirra_measurements/`:

   ```bash
   python seed_measurements.py
   ```

---

## Step 3 - Pipeline & Technology Setup

Each pipeline or technology has its own setup guide in its respective folder:

| Pipeline / Technology | Setup Guide                                      |
| --------------------- | ------------------------------------------------ |
| STAR Avatar Pipeline  | [pipeline_star/SETUP.md](pipeline_star/SETUP.md) |

---
