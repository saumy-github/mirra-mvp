# CLO Workspace Setup

## Supported OSes

- Windows
- macOS

`clo_workspace/build_plugin.py` detects the current OS by default and only supports Windows and macOS. If it detects any other OS, it fails with a clear unsupported-platform error instead of guessing.

## Required Software

Windows:

- Python
- CLO SDK matching your CLO build
- Visual Studio with C++ toolchain (2019 or 2022 recommended)
- CMake

macOS:

- Python 3.9+
- CLO SDK matching your CLO build (download from CLO developer portal)
- Xcode Command Line Tools — install with `xcode-select --install`
- CMake — install with `brew install cmake`
- Qt 5 — install with `brew install qt@5` (Homebrew, recommended) or via the Qt online installer

## Local Config

1. Copy `clo_workspace/.env.example` to `clo_workspace/.env`.
2. Fill in the machine-specific values for your OS.

Shared fields:

- `PLUGIN_PLATFORM`
- `BUILD_CONFIG`
- `CLO_SDK_PATH`
- `CMAKE_EXE` when `cmake` is not already on `PATH`

Windows-only fields:

- `CMAKE_GENERATOR`
- `CMAKE_ARCH`
- `CLO_PLUGINS_DIR`

macOS fields:

- `PLUGIN_PLATFORM=mac` — required
- `CLO_SDK_PATH` — path to your extracted CLO SDK folder (must match your CLO version)
- `CLO_PLUGINS_DIR` — CLO plugin folder, typically `~/Documents/CLO/Plugins`
- `CMAKE_PREFIX_PATH` or `Qt5_DIR` — only needed if CMake cannot find Qt 5 automatically
- `CMAKE_OSX_ARCHITECTURES` — set to `arm64` for Apple Silicon (M1/M2/M3/M4) or `x86_64` for Intel Mac

Typical macOS values using Homebrew Qt (Apple Silicon):

```
PLUGIN_PLATFORM=mac
CLO_SDK_PATH=/Users/yourname/Downloads/CLO_SDK_vYYYY.X.XXX_Mac
CLO_PLUGINS_DIR=/Users/yourname/Documents/CLO/Plugins
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt@5
Qt5_DIR=/opt/homebrew/opt/qt@5/lib/cmake/Qt5
CMAKE_OSX_ARCHITECTURES=arm64
```

Typical macOS values using Qt online installer:

```
PLUGIN_PLATFORM=mac
CLO_SDK_PATH=/Users/yourname/Downloads/CLO_SDK_vYYYY.X.XXX_Mac
CLO_PLUGINS_DIR=/Users/yourname/Documents/CLO/Plugins
CMAKE_PREFIX_PATH=/Users/yourname/Qt/5.15.16/macos
Qt5_DIR=/Users/yourname/Qt/5.15.16/macos/lib/cmake/Qt5
CMAKE_OSX_ARCHITECTURES=arm64
```

## Build Entrypoints

Preferred entrypoint:

```powershell
python clo_workspace/build_plugin.py
```

Platform wrappers:

```powershell
clo_workspace\windows\build_rest_plugin.bat
```

```bash
clo_workspace/mac/build_plugin.sh
```

## Build Flow

`build_plugin.py` does the shared setup work:

- loads `clo_workspace/.env`
- detects the OS
- loads `plugin_contract.json`
- loads the latest version file from `versions/`
- generates `shared/PluginBuildInfo.h`
- copies the platform-specific sources plus shared headers into the CLO SDK sample plugin directory
- runs `cmake` configure/build for the detected platform

Useful modes:

```powershell
python clo_workspace/build_plugin.py --sync-only
python clo_workspace/build_plugin.py
python clo_workspace/build_plugin.py --install
```

## Windows Build And Install

Typical Windows flow from repo root:

```powershell
python clo_workspace/build_plugin.py --install
```

`--install` requires `CLO_PLUGINS_DIR` to be set in `clo_workspace/.env`.

If you want to inspect the synced SDK sample first:

```powershell
python clo_workspace/build_plugin.py --sync-only
```

After install:

1. Open CLO.
2. Make sure the plugin loads.
3. Check the running plugin metadata:

```powershell
Invoke-RestMethod http://127.0.0.1:50505/health
```

## macOS Build And Install

Typical macOS flow from repo root:

```bash
python clo_workspace/build_plugin.py --install
```

`--install` requires `CLO_PLUGINS_DIR` to be set in `clo_workspace/.env`.

Useful macOS notes:

- the plugin artifact is expected to be a `.dylib`
- the usual output shape is `build/Release/libRestPlugin.dylib`
- CLO plugins normally live under `~/Documents/CLO/Plugins`
- Plugin Manager can be used if you want to test a plugin outside the default plugin folder
- if `find_package(Qt5 ...)` fails, set `CMAKE_PREFIX_PATH` or `Qt5_DIR` in `clo_workspace/.env`

Helpful artifact checks on macOS:

```bash
file build/Release/libRestPlugin.dylib
otool -L build/Release/libRestPlugin.dylib
```

After install, start CLO and verify the running plugin with:

```bash
curl http://127.0.0.1:50505/health
```

## Build Logs

Each root build writes a timestamped log file under:

```text
clo_workspace/logs/
```

The folder is kept in git with a `.gitkeep`, but local log files are ignored and should not be committed.

The log records:

- detected OS
- chosen version and contract files
- shared metadata generation
- sync destination
- configure/build commands
- install destination when used

If the build fails, the log is the first place to inspect because it shows the stage that failed.

## Post-build Validation

Use the helper script to inspect the installed plugin artifact on disk:

```bash
python clo_workspace/scripts/get_installed_plugin_info.py
```

The helper reads `CLO_PLUGINS_DIR` from `clo_workspace/.env`, or pass `--plugin-dir` explicitly.

Windows — point at a custom install directory:

```powershell
python clo_workspace/scripts/get_installed_plugin_info.py --plugin-dir "C:/Program Files/CLO Standalone OnlineAuth/plugins"
```

macOS — point at a custom install directory:

```bash
python clo_workspace/scripts/get_installed_plugin_info.py --plugin-dir "/Users/yourname/Documents/CLO/Plugins"
```

To check the live running plugin version inside CLO:

Windows (PowerShell):
```powershell
Invoke-RestMethod http://127.0.0.1:50505/health
```

macOS (Terminal):
```bash
curl http://127.0.0.1:50505/health
```
