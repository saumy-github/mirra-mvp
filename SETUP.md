# Setup Guide

---

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

---

## Step 2 — STAR Body Model

The avatar pipeline uses the **STAR** (Sparse Trained Articulated Human Body Regressor) model.

### 2a. Install the STAR library

From the project root, run:

```bash
pip install -e libs/star/
```

### 2b. Download the STAR model files

1. Register and download the model files from the official website:
   👉 <https://star.is.tue.mpg.de/>

2. After downloading, place the model files in the following structure inside the project root:

   ```plain
   models/
   └── star_1_1/
       ├── male/
       │   └── model.npz
       ├── female/
       │   └── model.npz
       └── neutral/
           └── model.npz
   ```

   > The model paths are already pre-configured in `libs/star/star/config.py` to point to this exact location. No changes needed.

---

## Step 3 — Additional External Files

Nothing to download here yet.

---
