# Movement Plan: clo_avatar_generation → clo_avatar_generation + clo_vto

## Goal

Split the current `clo_avatar_generation/` folder into two separate top-level folders:
- `clo_avatar_generation/` — Step 1 only (avatar generation)
- `clo_vto/` — Step 3 only (virtual try-on)

**Rule: Move files using the move command. Do not rewrite or recreate files.**

---

## What Gets Created

One new top-level folder at the repo root:
```
clo_vto/
```

Two new files must be created in `clo_vto/` (they are package boilerplate, not code files):
```
clo_vto/__init__.py          (empty, makes it a Python package)
clo_vto/output/              (empty folder, VTO run outputs will go here)
```

---

## Files and Folders to Move

### Move 1: The VTO pipeline package

```
MOVE:
  clo_avatar_generation/native_vto/
TO:
  clo_vto/native_vto/
```

All files inside move as-is — no renames:
```
native_vto/__init__.py
native_vto/client.py
native_vto/context.py
native_vto/helpers.py
native_vto/pipeline.py
native_vto/seams.py
native_vto/step_01_health.py
native_vto/step_02_new_project.py
native_vto/step_03_import_avatar.py
native_vto/step_04_import_patterns.py
native_vto/step_05_verify_patterns.py
native_vto/step_06_read_edges_and_slots.py
native_vto/step_07_arrange_patterns.py
native_vto/step_08_apply_fabric.py
native_vto/step_09_create_seams.py
native_vto/step_10_simulate.py
native_vto/step_11_export_note.py
```

### Move 2: The VTO entry point

```
MOVE:
  clo_avatar_generation/run_clo_vto.py
TO:
  clo_vto/run_clo_vto.py
```

---

## Everything That Stays in clo_avatar_generation/

No changes to any of these:
```
clo_avatar_generation/
├── avatar_runtime/          (Step 1 pipeline — untouched)
├── schema/                  (Step 1 field contract — untouched)
├── input/                   (base-1.avt + measurements — untouched)
├── output/                  (Step 1 run outputs — untouched)
├── avt_templates/           (avatar templates — untouched)
├── adapters/                (used by resize_avatar.py — untouched)
├── research-2/              (Step 1 measurement research docs — untouched)
├── research/                (old, stays, delete later)
├── research_files/          (old artifacts, stays, delete later)
├── avatar_setup/            (dead code, stays, delete later)
├── run_avatar.py            (Step 1 entry point — untouched)
├── resize_avatar.py         (Step 1 helper — untouched)
├── reporting.py             (unused, stays, delete later)
├── summary.md               (untouched)
├── README.md                (untouched)
├── __init__.py              (untouched)
└── .gitignore               (untouched)
```

---

## Import and Path Changes After the Move

After moving, exactly **4 lines** across **2 files** need to be updated.
No other files are affected — all internal imports inside `native_vto/` use relative imports (`.helpers`, `.seams`, etc.) and will work correctly after the folder moves.

---

### File 1: `clo_vto/run_clo_vto.py`

**Change 1 — import: `native_vto.helpers`**
```python
# BEFORE
from clo_avatar_generation.native_vto.helpers import resolve_patterns_dir

# AFTER
from clo_vto.native_vto.helpers import resolve_patterns_dir
```

**Change 2 — import: `native_vto.pipeline`**
```python
# BEFORE
from clo_avatar_generation.native_vto.pipeline import run_pipeline

# AFTER
from clo_vto.native_vto.pipeline import run_pipeline
```

**Change 3 — path: `DEFAULT_CSV_PATH`**

Currently points to `clo_avatar_generation/schema/measurement_template_unconfirmed.csv` via `PACKAGE_ROOT / "schema" / ...`. After the move, `PACKAGE_ROOT` will point to `clo_vto/` and that path won't exist.

```python
# BEFORE
PACKAGE_ROOT = Path(__file__).resolve().parent          # was clo_avatar_generation/
DEFAULT_CSV_PATH = PACKAGE_ROOT / "schema" / "measurement_template_unconfirmed.csv"

# AFTER
REPO_ROOT = Path(__file__).resolve().parents[1]         # one level up from clo_vto/
DEFAULT_CSV_PATH = REPO_ROOT / "clo_avatar_generation" / "schema" / "measurement_template_unconfirmed.csv"
```

**Change 4 — path: `DEFAULT_BASE_AVATAR`**

Currently points to `clo_avatar_generation/input/base-1.avt` via `PACKAGE_ROOT / "input" / ...`. Same issue.

```python
# BEFORE
DEFAULT_BASE_AVATAR = PACKAGE_ROOT / "input" / "base-1.avt"

# AFTER
DEFAULT_BASE_AVATAR = REPO_ROOT / "clo_avatar_generation" / "input" / "base-1.avt"
```

> Note: `REPO_ROOT` is already defined at the top of `run_clo_vto.py` as `Path(__file__).resolve().parents[1]`. After the move this still correctly resolves to the repo root since `run_clo_vto.py` will be one level deep inside `clo_vto/`.

---

### File 2: `clo_vto/native_vto/context.py`

**Change 5 — path: `_discover_default_native_avatar` fallback**

`context.py` uses `package_root = Path(__file__).resolve().parents[1]` to compute `output_dir` and `project_dir`. After the move, `package_root` will correctly point to `clo_vto/` — this is the right place for VTO output. No change needed for `output_dir` or `project_dir`.

However the final fallback in `_discover_default_native_avatar()` is:
```python
default_input_avatar = package_root / "input" / "base-1.avt"
```
After the move this will look for `clo_vto/input/base-1.avt` which does not exist. The base avatar lives in `clo_avatar_generation/input/`.

```python
# BEFORE
workspace_root = Path(__file__).resolve().parents[2]   # repo root
package_root = Path(__file__).resolve().parents[1]     # clo_avatar_generation/

default_input_avatar = package_root / "input" / "base-1.avt"

# AFTER
workspace_root = Path(__file__).resolve().parents[2]   # repo root (unchanged)
package_root = Path(__file__).resolve().parents[1]     # clo_vto/ (correct for output)

default_input_avatar = workspace_root / "clo_avatar_generation" / "input" / "base-1.avt"
```

---

## Summary: Complete Change List

| File | Line(s) | Change |
|---|---|---|
| `clo_vto/run_clo_vto.py` | import of `helpers` | `clo_avatar_generation.native_vto` → `clo_vto.native_vto` |
| `clo_vto/run_clo_vto.py` | import of `pipeline` | `clo_avatar_generation.native_vto` → `clo_vto.native_vto` |
| `clo_vto/run_clo_vto.py` | `DEFAULT_CSV_PATH` | `PACKAGE_ROOT / "schema" / ...` → `REPO_ROOT / "clo_avatar_generation" / "schema" / ...` |
| `clo_vto/run_clo_vto.py` | `DEFAULT_BASE_AVATAR` | `PACKAGE_ROOT / "input" / ...` → `REPO_ROOT / "clo_avatar_generation" / "input" / ...` |
| `clo_vto/native_vto/context.py` | `default_input_avatar` | `package_root / "input" / ...` → `workspace_root / "clo_avatar_generation" / "input" / ...` |

**No changes needed in:**
- All `native_vto/step_*.py` files (only use relative imports within the package)
- `native_vto/seams.py`, `native_vto/client.py` (no cross-package imports)
- `native_vto/helpers.py` (imports `product_ingestion.run_manifest` — absolute, still works)
- `native_vto/pipeline.py` (only relative imports)
- Anything in `clo_avatar_generation/` (nothing there imports from `native_vto`)

---

## New Command to Run After the Move

The VTO command will change from:
```
python clo_avatar_generation/run_clo_vto.py
```
to:
```
python clo_vto/run_clo_vto.py
```

The Step 1 command is unchanged:
```
python clo_avatar_generation/run_avatar.py
```

---

## Output Folder After Split

| Pipeline | Output folder |
|---|---|
| Step 1 (avatar generation) | `clo_avatar_generation/output/` |
| Step 3 (VTO) | `clo_vto/output/` |

The existing `clo_avatar_generation/output/base-1__native_vto_report.json` is an old VTO artifact that landed in the wrong place. It stays there and will be cleaned up with the other old files later.
