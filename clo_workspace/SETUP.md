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
- `CLO_PLUGINS_DIR` — where CLO loads plugins from (used in the manual install hint)
- `CLO_PLUGIN_VAULT_DIR` — where built plugins are saved for rollback (must be outside the repo)

macOS fields:

- `PLUGIN_PLATFORM=mac` — required
- `CLO_SDK_PATH` — path to your extracted CLO SDK folder (must match your CLO version)
- `CLO_PLUGINS_DIR` — CLO plugin folder, typically `~/Documents/CLO/Plugins` (used in the manual install hint)
- `CLO_PLUGIN_VAULT_DIR` — where built plugins are saved for rollback (must be outside the repo)
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
python clo_workspace/build_plugin.py             # build + vault copy (normal workflow)
python clo_workspace/build_plugin.py --sync-only # sync sources only, no compile
```

## Windows Build And Install

Build from repo root (no admin rights needed):

```powershell
python clo_workspace/build_plugin.py
```

This builds the DLL and saves a versioned copy to `CLO_PLUGIN_VAULT_DIR`. At the end it prints the exact copy command needed.

Manual install step (requires Administrator):

1. Close CLO.
2. Open PowerShell as Administrator (`Win+R` → `powershell` → `Ctrl+Shift+Enter`).
3. Copy the versioned DLL from the vault to the CLO plugins folder — the build output shows the exact paths.
4. Delete any old unversioned `RestPlugin.dll` from the plugins folder if present.
5. Restart CLO.

Verify the running plugin:

```powershell
Invoke-RestMethod http://127.0.0.1:50505/health
```

## macOS Build And Install

Build from repo root:

```bash
python clo_workspace/build_plugin.py
```

This builds the dylib and saves a versioned copy to `CLO_PLUGIN_VAULT_DIR`. At the end it prints the exact copy command needed.

Manual install step:

1. Close CLO.
2. Copy the versioned dylib from the vault to the CLO plugins folder — the build output shows the exact paths.
3. Restart CLO.

Useful macOS notes:

- the plugin artifact is `build/Release/libRestPlugin.dylib`
- CLO plugins normally live under `~/Documents/CLO/Plugins`
- if `find_package(Qt5 ...)` fails, set `CMAKE_PREFIX_PATH` or `Qt5_DIR` in `clo_workspace/.env`

Verify the running plugin:

```bash
curl http://127.0.0.1:50505/health
```

## Build Logs

Each root build writes a timestamped log file under:

```text
clo_workspace/logs/
```

For repo-local scratch work, use `clo_workspace/temp/`.
That is the right place for ad-hoc Windows CMake build trees such as `clo_workspace/temp/windows-build-local/`.
`clo_workspace/windows/build-local/` should be treated as a mistaken old location, not the normal workflow.

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
