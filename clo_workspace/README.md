# CLO3D REST Automation Pipeline

This folder contains everything needed to run the full virtual try-on automation pipeline: generate a 3D avatar from body measurements → generate 2D garment patterns → automatically load them into CLO3D, sew them, and run physics simulation — all without touching the CLO GUI.

---

## Pipeline overview

```
[pipeline_star]          Body measurements → STAR model → avatar OBJ (178 cm, metres)
       ↓
[2d_patterned_garment_generation_clo3d]   → 4 DXF pattern pieces (cm)
       ↓
[clo_workspace/plugins]  Python client  →  HTTP REST  →  CLO3D plugin DLL
                                                                ↓
                                          new-project → import avatar → import patterns
                                          → arrange around body → set fabric
                                          → create 26 seams → simulate → export GLB
```

The plugin runs an HTTP server on `http://localhost:50505` inside CLO3D. Python queues commands; the plugin drains them on CLO's main thread every 500 ms via a Win32 `SetTimer` callback.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| CLO Standalone | v2025 | Default install path: `C:\Program Files\CLO Standalone OnlineAuth\` |
| CLO SDK | v2025.2.236 | Extract to `C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\` |
| Visual Studio 2022 | Community or higher | Select **"Desktop development with C++"** workload |
| CMake | (bundled with VS) | No separate install needed |
| Python | 3.9+ | Must have `requests` and `ezdxf` installed |

```powershell
pip install requests ezdxf
```

---

## Full pipeline — step by step

### Stage 0 — Generate avatar (once per user)

Run the STAR body model to create an OBJ avatar from measurements:

```powershell
cd C:\Users\Anant\mirra-mvp
.\.venv\Scripts\python.exe pipeline_star\run_avatar_pipeline.py
```

Output: `pipeline_star/generated/clo_avatars/user_m_001_001_avatar.obj`

> The OBJ is in **metres**. The CLO plugin applies `scale=100` automatically at import.

---

### Stage 1 — Generate 2D patterns

```powershell
.\.venv\Scripts\python.exe 2d_patterned_garment_generation_clo3d\generate_patterns_clo3d.py
```

This produces a new `output/run_NNN/patterns_dxf/` folder with 4 DXF files (in centimetres):

```
front_panel.dxf    — 19 edges (hem, side seams, armhole curves, shoulder, neckline)
back_panel.dxf     — 18 edges (same layout, slightly wider shoulder)
sleeve_left.dxf    — 13 edges (cuff, tube seam, front cap ×5, back cap ×5)
sleeve_right.dxf   — 13 edges (mirror of sleeve_left)
```

---

### Stage 2 — (Optional) Verify seam indices

If patterns were regenerated or edge counts changed, re-run the seam index discovery tool:

```powershell
.\.venv\Scripts\python.exe clo_workspace\plugins\discover_seam_indices.py
```

This reads the DXF files directly (no CLO needed) and prints the 26-seam map used by the modular pipeline (`clo_automation_steps/seams.py`).

---

### Stage 3 — Build the CLO plugin DLL

**Only needed when `RestPlugin.cpp` source changes.**

```powershell
cd C:\Users\Anant\mirra-mvp
$env:PATH += ";C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
cd clo_workspace\plugins
.\build_rest_plugin.bat
```

Output: `C:\setup\CLO_SDK_v2025.2.236_WIN\...\Samples\RestPlugin\build\Release\RestPlugin.dll`

> Build exit code 1 is normal — it means the post-build copy step ran but had a minor issue. The DLL is still built correctly. Look for `RestPlugin.vcxproj ->` in the output to confirm success.

---

### Stage 4 — Install the DLL into CLO3D

**CLO must be closed for this step.**

```powershell
Copy-Item "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\Samples\RestPlugin\build\Release\RestPlugin.dll" `
          -Destination "C:\Program Files\CLO Standalone OnlineAuth\plugins\" -Force
```

---

### Stage 5 — Enable the plugin in CLO3D (first time only)

1. Open CLO3D
2. Go to **Edit → Preferences → Plug-in Manager**
3. Find **RestPlugin** in the list and tick the checkbox
4. Click **OK** and restart CLO3D if prompted

After restart you will have a new menu entry: **Plugins → REST Server & Execute**

---

### Stage 6 — Start the REST server

In CLO3D, click **Plugins → REST Server & Execute**.

A confirmation dialog appears: *"REST server started on port 50505"*. Click OK.

> The server stays running for the whole CLO session. **You do not need to click the menu again** — the plugin's 500 ms timer drains the command queue automatically.

---

### Stage 7 — Run the full Python automation pipeline

```powershell
cd C:\Users\Anant\mirra-mvp
.\.venv\Scripts\python.exe clo_workspace\plugins\clo_automation_client.py
```

The script runs 10 active steps and prints live status for each:

| Step | What happens |
|------|-------------|
| **[1]** Health check | Verifies HTTP server is reachable |
| **[2]** New project | Clears CLO scene |
| **[3]** Import avatar | Loads `user_m_001_001_avatar.obj` at 100× scale (metres → cm) |
| **[4]** Import patterns | Queues all 4 DXF files; waits up to 60 s for CLO to load them |
| **[5]** Verify count | Confirms 4 patterns are in the CLO scene |
| **[6]** Read edge data | Queries edge count per pattern; prints layout info |
| **[6b]** Query slots | Calls `/arrangement-list` to get live avatar body-part slot indices |
| **[7]** Arrange in 3D | Places each piece in the matching body slot, 100 mm outside avatar surface |
| **[8]** Apply fabric | Sets fabric index 0 (first CLO project fabric) on all pieces |
| **[9]** Create 26 seams | Stitches hem, side, shoulder, armhole, and sleeve-tube seams |
| **[10]** Simulate | Runs 150-step physics; cloth drapes and seams pull together |
| **[11]** Export/Save | **Currently disabled** — see note below |

Modular implementation notes:
- `clo_workspace/plugins/clo_automation_client.py` is now a thin orchestrator/entrypoint.
- Individual steps live in `clo_workspace/plugins/clo_automation_steps/step_*.py`.
- Shared state/config lives in `context.py`, helper functions in `helpers.py`, and default seam map in `seams.py`.

Useful run modes:

```powershell
# health check only
.\.venv\Scripts\python.exe clo_workspace\plugins\clo_automation_client.py test

# inspect plugin queue status
.\.venv\Scripts\python.exe clo_workspace\plugins\clo_automation_client.py status

# run full end-to-end automation
.\.venv\Scripts\python.exe clo_workspace\plugins\clo_automation_client.py
```

Expected console output:
```
================================================================
CLO Virtual Try-On Automation Pipeline
================================================================

[1] Health check ...
  ✓ Connected to CLO REST server

[2] New project ...
  ✓ new-project: new project created

[3] Importing avatar ...
  ✓ import-avatar: avatar queued for import

[4] Importing patterns ...
  ✓ front_panel.dxf: pattern queued for import
  ✓ back_panel.dxf: ...
  ✓ sleeve_left.dxf: ...
  ✓ sleeve_right.dxf: ...

[5] Verifying pattern count ...
  Patterns in CLO scene: 4 (expected 4)

...

[10] Running physics simulation (150 steps) ...
  ✓ simulate: simulation queued

================================================================
Simulation complete.
================================================================
```

---

## Export / Save (manual for now)

Steps 11 (export GLB) and 12 (save ZPRJ) are **commented out** because CLO v2025 can crash after `ExportGLTF` until the simulation has fully settled. To export manually after the simulation finishes:

- **Export GLB**: `File → Export → glTF 2.0` → save to `clo_workspace/exports/`
- **Save project**: `File → Save As` → `.zprj` → save to `clo_workspace/projects/`

To re-enable automated export, add export/save API calls as a dedicated step module (for example, `step_12_export.py`) and wire it into `run_pipeline()` in `clo_workspace/plugins/clo_automation_steps/pipeline.py`.

---

## Available REST endpoints

| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | `/health` | Check server is running |
| GET | `/status` | Queue size, processing flag, last batch results |
| GET | `/patterns/count` | Number of patterns loaded in CLO scene |
| GET | `/patterns/{index}` | Edge count and info for one pattern |
| GET | `/arrangement-list` | All avatar body-part slots with their CLO indices |
| GET | `/pattern-arrangements` | Current slot assignment for every loaded pattern |
| POST | `/new-project` | Clear scene and start fresh |
| POST | `/import-avatar` | `{"path": "...obj"}` — import OBJ avatar (100× scale) |
| POST | `/import-pattern` | `{"path": "...dxf"}` — import DXF pattern piece |
| POST | `/arrange-pattern` | Place pattern in a body slot with mm offsets |
| POST | `/set-fabric` | Assign a fabric index to a pattern piece |
| POST | `/create-seam` | Stitch two pattern edges together |
| POST | `/simulate` | `{"steps": N}` — run physics simulation |
| POST | `/export` | `{"path": "...", "format": "glb"}` — export GLTF |
| POST | `/save-project` | `{"path": "....zprj"}` — save CLO project file |
| POST | `/execute` | Nudge queue drain (fallback if timer is delayed) |

---

## Architecture notes

### Thread model
All CLO SDK calls **must** run on CLO's main thread. The HTTP server runs on a background thread and only pushes to a `std::queue`. A Win32 `SetTimer` callback fires every 500 ms on the main thread and drains the queue by calling `ProcessCommandQueue()`.

`DoFunctionContinuously()` is **not called** by CLO v2025 — the timer approach is the correct workaround.

### Units
| Data | Unit | How handled |
|------|------|-------------|
| Avatar OBJ (pipeline_star output) | metres | `scale=100.0f` in `ImportOBJ` |
| DXF pattern pieces | centimetres | `scale=1.0f` (CLO native) |
| `SetArrangementPosition` offsets | millimetres | `offset_z=100` = 10 cm from body |
| Simulation steps | unitless | 150 steps ≈ natural drape |

### Seam map (26 seams)
Derived from DXF geometry via `discover_seam_indices.py`. Pattern indices:
- `0` = front_panel (19 edges)
- `1` = back_panel (18 edges)
- `2` = sleeve_left (13 edges)
- `3` = sleeve_right (13 edges)

Key seams: side-right/left, shoulder-right/left, sleeve tube (both), 5 armhole segments × 4 sides = 20 armhole seams total.

---

## Folder structure

```
clo_workspace/
├── plugins/
│   ├── RestPlugin.cpp              ← main plugin source (built & installed)
│   ├── RestPlugin_clean.cpp        ← clean reference copy
│   ├── CMakeLists.txt              ← CMake build config
│   ├── build_rest_plugin.bat       ← one-click build script
│   ├── httplib.h                   ← embedded HTTP server (cpp-httplib)
│   ├── json.hpp                    ← embedded JSON parser (nlohmann)
│   ├── dllmain.cpp                 ← DLL entry point
│   ├── stdafx.h / targetver.h      ← Windows precompiled headers
│   ├── clo_automation_client.py    ← thin Python entrypoint/orchestrator
│   ├── clo_automation_steps/       ← modular pipeline package
│   │   ├── client.py               ← REST client class (`CLORestClient`)
│   │   ├── context.py              ← shared pipeline context/state
│   │   ├── helpers.py              ← helper utilities
│   │   ├── seams.py                ← default seam map
│   │   ├── pipeline.py             ← run_pipeline() orchestrator
│   │   └── step_01_...step_11_...  ← one file per pipeline step
│   ├── discover_seam_indices.py    ← DXF edge analyser (run offline)
│   └── mirra_pattern_importer.py   ← standalone pattern import helper
├── exports/                        ← GLB/OBJ files exported by CLO
├── projects/                       ← saved CLO .zprj project files
└── temp/                           ← scratch space
```

---

## Quick-start cheat sheet

```powershell
# 1. Generate avatar (once)
.\.venv\Scripts\python.exe pipeline_star\run_avatar_pipeline.py

# 2. Generate patterns
.\.venv\Scripts\python.exe 2d_patterned_garment_generation_clo3d\generate_patterns_clo3d.py

# 3. Build & install DLL (only when C++ source changes)
cd clo_workspace\plugins ; .\build_rest_plugin.bat
Copy-Item "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\Samples\RestPlugin\build\Release\RestPlugin.dll" `
          "C:\Program Files\CLO Standalone OnlineAuth\plugins\" -Force

# 4. In CLO3D: Plugins → REST Server & Execute  (once per CLO session)

# 5. Run full pipeline
cd C:\Users\Anant\mirra-mvp
.\.venv\Scripts\python.exe clo_workspace\plugins\clo_automation_client.py

# Optional: smoke checks
.\.venv\Scripts\python.exe clo_workspace\plugins\clo_automation_client.py test
.\.venv\Scripts\python.exe clo_workspace\plugins\clo_automation_client.py status
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Failed to connect to CLO REST server` | Plugin not started | Click **Plugins → REST Server & Execute** in CLO |
| `queue did not drain within Xs` | CLO not processing | Click the menu item once to nudge; check CLO isn't showing a modal dialog |
| `Patterns in CLO scene: 0` | Wrong DXF path | Run `generate_patterns_clo3d.py` first; check `output/run_NNN/patterns_dxf/` exists |
| Avatar is 1.78 cm tall | Wrong scale | Make sure the installed DLL is the latest build (`scale=100.0f`) |
| Patterns all stack in one spot | Arrangement slots empty | CLO may not populate slots from OBJ avatar — pipeline falls back to position-only mode (`slot=-1`) |
| CLO crashes after export | Physics still settling | Leave export disabled; export manually after simulation stabilises |

---

## Manual build steps (if the .bat fails)

```powershell
$SDK = "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\Samples\RestPlugin"
New-Item -ItemType Directory -Force $SDK
Copy-Item "clo_workspace\plugins\RestPlugin.cpp" "$SDK\RestPlugin.cpp" -Force
Copy-Item "clo_workspace\plugins\dllmain.cpp",
          "clo_workspace\plugins\CMakeLists.txt",
          "clo_workspace\plugins\stdafx.h",
          "clo_workspace\plugins\targetver.h",
          "clo_workspace\plugins\httplib.h",
          "clo_workspace\plugins\json.hpp" "$SDK\" -Force

$CMAKE = "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
New-Item -ItemType Directory -Force "$SDK\build"
Set-Location "$SDK\build"
& $CMAKE .. -G "Visual Studio 17 2022" -A x64
& $CMAKE --build . --config Release

# Close CLO first, then:
Copy-Item "$SDK\build\Release\RestPlugin.dll" `
          "C:\Program Files\CLO Standalone OnlineAuth\plugins\" -Force
```
