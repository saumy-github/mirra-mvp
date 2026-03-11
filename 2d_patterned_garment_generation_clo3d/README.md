# 2D Garment Pattern Generator

Takes body measurements and produces **ready-to-import T-shirt pattern files** for CLO3D — the same way a garment pattern cutter would draft pieces on paper, just automated.

Each run creates a numbered output folder so you never overwrite previous garments.

---

## What it does

1. Takes body measurements (height, chest, shoulder, waist, hip)
2. Calculates garment dimensions with proper ease (extra room for movement)
3. Draws 4 pattern pieces with correct curves: front panel, back panel, left sleeve, right sleeve
4. Exports them as `.dxf` files (for CLO3D import) and `.svg` files (for visual preview)

---

## Requirements

Python 3.8+ and one library:

```bash
pip install ezdxf
```

---

## Running the pipeline

Run from the **repo root** (`mirra-mvp/`):

### Option A — Manual measurements

```bash
# Mac/Linuxpython 2d_patterned_garment_generation_clo3d/generate_patterns_clo3d.py \
  --manual --height 178 --chest 100 --shoulder 45 --waist 85 --hip 98 --gender male \
  -o 2d_patterned_garment_generation_clo3d/output
```

```powershell
# Windows
.\.venv\Scripts\python.exe 2d_patterned_garment_generation_clo3d\generate_patterns_clo3d.py --manual --height 178 --chest 100 --shoulder 45 --waist 85 --hip 98 --gender male -o 2d_patterned_garment_generation_clo3d\output
```

### Option B — From avatar measurements JSON

If you have a measurements file from the avatar pipeline:

```bash
python 2d_patterned_garment_generation_clo3d/generate_patterns_clo3d.py \
  --avatar pipeline_star/generated/clo_avatars/<measurements_file>.json \
  -o 2d_patterned_garment_generation_clo3d/output
```

### Fit options

Add `--fit slim`, `--fit regular` (default), or `--fit relaxed` to control how much ease is added.

---

## All flags

| Flag | Description | Default |
|------|-------------|---------|
| `--height` | Body height in cm | 175 |
| `--chest` | Chest circumference in cm | 100 |
| `--shoulder` | Shoulder width in cm | 45 |
| `--waist` | Waist circumference in cm | 85 |
| `--hip` | Hip circumference in cm | 98 |
| `--gender` | `male` or `female` | male |
| `--fit` | `slim`, `regular`, `relaxed` | regular |
| `--avatar` | Path to avatar measurements JSON | — |
| `-o` | Base output folder | `output` |

---

## Output

Each run creates a new numbered subfolder — previous runs are never overwritten:

```
2d_patterned_garment_generation_clo3d/output/
├── run_001/
│   ├── patterns_dxf/          ← import these into CLO3D
│   │   ├── front_panel.dxf
│   │   ├── back_panel.dxf
│   │   ├── sleeve_left.dxf
│   │   └── sleeve_right.dxf
│   └── patterns_svg/          ← open these to visually check shapes
│       ├── front_panel.svg
│       ├── back_panel.svg
│       ├── sleeve_left.svg
│       └── sleeve_right.svg
├── run_002/
│   └── ...
```

---

## Using the output in CLO3D

1. Open CLO3D
2. Import avatar: **Avatar → Import Avatar**
3. Import patterns: **File → Import → DXF/AAMA** → select all 4 `.dxf` files from `run_NNN/patterns_dxf/`
4. Use the **Segment Sewing** tool to connect:
   - Front ↔ Back at both shoulders
   - Front ↔ Back at both sides
   - Each sleeve cap ↔ its armhole
   - Close each sleeve along the underarm
5. Assign fabric (Cotton Knit works well) → **Simulate**
