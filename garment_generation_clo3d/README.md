# 3D T-Shirt Mesh Generator (Blender)

Generates a **3D T-shirt mesh** directly using Blender's Python API. This is the older, simpler approach — it sculpts a T-shirt shape as a mesh rather than drafting sewing patterns.

> **Note:** For CLO3D work, prefer `2d_patterned_garment_generation_clo3d/` instead. That pipeline generates proper 2D sewing patterns which CLO3D simulates with real fabric physics. This folder just produces a raw mesh.

---

## What it does

Runs inside Blender and creates a T-shirt mesh with:
- Body tube (with waist taper and hem)
- Two sleeves attached at the armholes
- Neckband ring
- Exports as `.obj` and `.glb`

All dimensions are hardcoded in centimeters at the top of the script.

---

## Requirements

- **Blender 3.0+** — download from [blender.org](https://www.blender.org/download/)
- No extra Python packages — uses Blender's built-in `bpy` and `bmesh`

---

## How to run

### Option A — Inside Blender (interactive)

1. Open Blender
2. Switch to the **Scripting** workspace (tab at the top)
3. Click **Open** and select `generate_tshirt_clo3d.py`
4. Click **Run Script**
5. Output files (`tshirt_clo3d.obj`, `tshirt_clo3d.glb`) are saved to this folder

### Option B — Command line (headless)

```powershell
& "C:\Program Files\Blender Foundation\Blender 3.x\blender.exe" --background --python garment_generation_clo3d\generate_tshirt_clo3d.py
```

Replace `3.x` with your installed Blender version.

---

## Output

| File | Description |
|------|-------------|
| `tshirt_clo3d.obj` | Mesh in OBJ format |
| `tshirt_clo3d.glb` | Mesh in GLB format (for web/3D viewers) |
| `tshirt_clo3d.mtl` | Material file (auto-generated alongside OBJ) |

To change the T-shirt dimensions, edit the measurement variables at the top of `generate_tshirt_clo3d.py` (e.g. `body_width`, `sleeve_length`, `shoulder_width`).
