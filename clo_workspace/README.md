# CLO3D REST Automation Plugin

This folder contains a C++ plugin that runs a local REST server inside CLO3D, letting you control CLO3D from Python — import patterns, import avatars, simulate, and export — without touching the GUI.

---

## How it works

```
Python script  →  HTTP request  →  REST server (inside CLO)  →  CLO3D does the action
```

The plugin starts a server on `http://localhost:50505`. Your Python script calls endpoints like `/import-pattern` or `/simulate`. CLO3D executes them on the next menu click.

---

## Prerequisites — install these first

### 1. CLO3D
- CLO Standalone (trial or licensed) installed at the default location:
  `C:\Program Files\CLO Standalone OnlineAuth\`

### 2. CLO SDK
- Download CLO SDK v2025.2.236 and extract to:
  `C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\`

### 3. Visual Studio 2022
- Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/)
- During install, select the **"Desktop development with C++"** workload

### 4. CMake
- Comes bundled with Visual Studio. No separate install needed.

### 5. Python `requests` library
```powershell
pip install requests
```

---

## Step 1 — Build the plugin DLL

Run this from the repo root. It copies source files into the SDK, compiles, and opens the output folder:

```powershell
clo_workspace\plugins\build_rest_plugin.bat
```

The built DLL will be at:
```
C:\setup\CLO_SDK_v2025.2.236_WIN\...\Samples\RestPlugin\build\Release\RestPlugin.dll
```

> If the bat file fails, see the manual build steps at the bottom of this file.

---

## Step 2 — Install the DLL into CLO3D

**CLO must be closed for this step.**

```powershell
Copy-Item "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\Samples\RestPlugin\build\Release\RestPlugin.dll" `
          -Destination "C:\Program Files\CLO Standalone OnlineAuth\plugins\" -Force
```

---

## Step 3 — Load the plugin in CLO3D (GUI)

1. Open CLO3D
2. Go to **Preferences → Plug-in Manager** (or **Edit → Preferences → Plug-in Manager** depending on version)
3. In the plugin list, find **RestPlugin** and make sure it is **checked/enabled**
4. Click **OK**
5. Restart CLO3D if prompted

After restart, you should see a new menu item:
**Plugins → REST Server & Execute**

---

## Step 4 — Start the REST server

In CLO3D, click:

**Plugins → REST Server & Execute**

A message box will appear confirming the server started on port 50505. Click OK.

> You need to click this menu item **once to start the server**, then **again each time** to process queued commands.

---

## Step 5 — Run Python automation

From the repo root, run the test import script to verify everything works:

```powershell
.\.venv\Scripts\python.exe test_clo_import.py
```

This will:
1. Check the REST server is running
2. Queue all 4 DXF pattern files from the latest `output/run_NNN/` folder
3. Print instructions to click the CLO menu to execute

Then click **Plugins → REST Server & Execute** in CLO3D to actually import the patterns.

---

## Available REST endpoints

| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | `/health` | Check server is running |
| GET | `/patterns/count` | Number of patterns loaded in CLO |
| POST | `/import-pattern` | Queue a DXF pattern file for import |
| POST | `/import-avatar` | Queue an OBJ avatar for import |
| POST | `/simulate` | Queue a simulation run |
| POST | `/export` | Queue a GLB/OBJ export |
| POST | `/create-seam` | Queue a seam between two pattern edges |
| POST | `/save-project` | Queue saving as `.zprj` |
| POST | `/execute` | Run any arbitrary CLO command |

### Example Python usage

```python
import sys
sys.path.insert(0, r"C:\Users\Anant\mirra-mvp\clo_workspace\plugins")
from clo_automation_client import CLORestClient

client = CLORestClient()

# Check server
print(client.health_check())

# Queue a pattern import
client.import_pattern(r"C:\Users\Anant\mirra-mvp\2d_patterned_garment_generation_clo3d\output\run_003\patterns_dxf\front_panel.dxf")

# Then click Plugins → REST Server & Execute in CLO3D
```

---

## Folder structure

```
clo_workspace/
├── plugins/
│   ├── RestPlugin.cpp          ← main plugin source (copy of RestPlugin_clean.cpp)
│   ├── RestPlugin_clean.cpp    ← source of truth for the plugin
│   ├── CMakeLists.txt          ← build config
│   ├── build_rest_plugin.bat   ← one-click build + install script
│   ├── httplib.h               ← embedded HTTP server library
│   ├── json.hpp                ← embedded JSON library
│   ├── dllmain.cpp             ← DLL entry point
│   ├── stdafx.h / targetver.h  ← Windows headers
│   ├── clo_automation_client.py ← Python client library
│   └── test_clo_import.py      ← quick test script
├── exports/                    ← GLB/OBJ files exported by CLO land here
├── projects/                   ← saved CLO .zprj project files
└── temp/                       ← scratch space
```

---

## Manual build steps (if the .bat fails)

```powershell
# 1. Copy source files to SDK
$SDK = "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\Samples\RestPlugin"
New-Item -ItemType Directory -Force $SDK
Copy-Item "clo_workspace\plugins\RestPlugin_clean.cpp" "$SDK\RestPlugin.cpp" -Force
Copy-Item "clo_workspace\plugins\dllmain.cpp", "clo_workspace\plugins\CMakeLists.txt", `
          "clo_workspace\plugins\stdafx.h", "clo_workspace\plugins\targetver.h", `
          "clo_workspace\plugins\httplib.h", "clo_workspace\plugins\json.hpp" "$SDK\" -Force

# 2. Configure with CMake
$CMAKE = "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
New-Item -ItemType Directory -Force "$SDK\build"
cd "$SDK\build"
& $CMAKE .. -G "Visual Studio 17 2022" -A x64

# 3. Build
& $CMAKE --build . --config Release

# 4. Install (close CLO first)
Copy-Item "$SDK\build\Release\RestPlugin.dll" "C:\Program Files\CLO Standalone OnlineAuth\plugins\" -Force
```
