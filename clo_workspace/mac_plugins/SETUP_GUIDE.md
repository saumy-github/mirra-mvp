# macOS CLO REST Plugin — Setup Guide

A step-by-step guide to build, install, and use the REST plugin on macOS (Apple Silicon).

---

## Prerequisites

Install these once:

```bash
# Xcode Command Line Tools (compiler + linker only — full Xcode IDE not needed)
xcode-select --install

# Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Build tools + Qt 5.15
brew install cmake qt@5
```

You also need:
- **CLO 3D** installed (tested with CLO 2025.2)
- **CLO SDK** — obtain from your team lead and place it somewhere accessible (e.g. `~/CLO_SDK`)

---

## 1. Build the Plugin

```bash
cd /path/to/mirra-mvp/clo_workspace/mac_plugins

cmake -B build \
  -DCLO_SDK_PATH=~/CLO_SDK \
  -DCMAKE_BUILD_TYPE=Release \
  -DQt5_DIR=$(brew --prefix qt@5)/lib/cmake/Qt5

cmake --build build --config Release
```

On success you will see:
```
Build complete: .../build/Release/libRestPlugin.dylib
```

---

## 2. Install the Plugin

```bash
cmake --install build
```

This copies `libRestPlugin.dylib` to `~/Documents/CLO/Plugins/`.

Verify it's there:
```bash
ls ~/Documents/CLO/Plugins/libRestPlugin.dylib
```

---

## 3. Configure CLO Plugin Search Path

CLO reads a text file to know where to look for plugins. This file often ships with Windows placeholder paths and must be fixed once.

**File location:**
```
~/Documents/CLO/Configuration/API_Plug_in/defaultPlugInFolders.txt
```

**Set its content to your plugins folder:**
```bash
echo "$HOME/Documents/CLO/Plugins" > "$HOME/Documents/CLO/Configuration/API_Plug_in/defaultPlugInFolders.txt"
```

Verify:
```bash
cat ~/Documents/CLO/Configuration/API_Plug_in/defaultPlugInFolders.txt
# Should print: /Users/<your-username>/Documents/CLO/Plugins
```

> **Why this matters:** If this file contains Windows paths like `C:\default_plugin_folder1`, CLO will never find your plugin and the Plug-in menu will be empty.

---

## 4. Activate the Plugin in CLO

1. Open **CLO 3D**
2. In the menu bar click **Plug-in**
3. Click **REST Server**
4. The plugin starts an HTTP server on `127.0.0.1:50505`

Confirm it's running from Terminal:
```bash
curl http://127.0.0.1:50505/health
# Expected: {"status":"ok","plugin":"RestPlugin","version":"1.0"}
```

> The plugin must be clicked **every time CLO is opened** — it does not auto-start.

---

## 5. Run the VTO Pipeline

Make sure CLO is open and REST Server is active (step 4), then:

```bash
cd /path/to/mirra-mvp
source .venv/bin/activate
PYTHONPATH=/path/to/mirra-mvp python vto/run_vto.py
```

When prompted:
- **Avatar run** — pick from `avatar_generation/output/` (e.g. `u_001-007`)
- **Product run** — pick from `product_ingestion/output/` (e.g. `c_001-s_002-001`)

Confirm with `y` and the pipeline runs all 11 CLO automation steps automatically.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Plug-in menu is empty | `defaultPlugInFolders.txt` has wrong paths | Run the `echo` command in Step 3 |
| Plugin visible but nothing happens on click | Plugin failed to bind port | Check CLO console for errors |
| `curl: Connection refused` | REST Server not activated | Click Plug-in → REST Server in CLO |
| Pipeline step 1 fails (health check) | CLO not open or plugin not activated | Open CLO and activate REST Server |
| `dylib rejected` on load | Code signing issue | Run `codesign --force --sign - ~/Documents/CLO/Plugins/libRestPlugin.dylib` |

---

## Notes

- Plugin is built for **arm64** (Apple Silicon). If you are on Intel Mac, change `CMAKE_OSX_ARCHITECTURES` to `x86_64` in `CMakeLists.txt`.
- Qt symbols are resolved from CLO's own Qt5 at runtime — do **not** link against a separate Qt5 installation.
- The plugin must be **re-built** any time `RestPlugin_macOS.cpp` is changed, then re-installed with `cmake --install build`.
