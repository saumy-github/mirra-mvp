# CLO REST Plugin — macOS Build, Install & Troubleshooting

Written after the **first successful macOS build** of `mac/RestPlugin_macOS.cpp`
(2026-08-04). Before this the Mac source had never been compiled on a real Mac —
it was source-reviewed only, and `versions/v_1.3.0.json` still marks mac as
`"pending"`. Everything below is what actually happened, verified on hardware,
not what the older handoff doc assumed.

If you are rebuilding this plugin, read §2 and §3, then run §4. If the plugin is
installed but misbehaving, jump to §8.

---

## 1. Verified working configuration

This exact combination produced a working plugin. Deviating from it is fine, but
§8 explains which deviations bite.

| Component | Version | Notes |
|---|---|---|
| macOS | 26.5.2 (Darwin 25.5.0), arm64 Apple Silicon | |
| CLO | **2026.0.374** | `/Applications/CLO.app` |
| CLO's bundled Qt | **6.10.3** | ← the number that matters most |
| CLO SDK | 2026.0.262 (Mac) | `~/Downloads/CLO_SDK_v2026.0.262_Mac` |
| Homebrew Qt | **qt 6.11.1** | Qt**6**, not qt@5 |
| CMake | 4.1.1 | Homebrew |
| Compiler | AppleClang 17.0.0 | Xcode Command Line Tools |
| Plugin version built | **1.3.0** | not 1.1.1 — see §7 |

Two version numbers are *deliberately mismatched* and it is fine:

- **SDK 2026.0.262 vs CLO 2026.0.374.** The SDK is only used for headers. The
  actual `libCLOAPIInterface.dylib` we link comes from the installed CLO app, so
  the binary side is exactly version-matched. See §3.2.
- **Homebrew Qt 6.11.1 vs CLO's Qt 6.10.3.** Handled by `QT_NO_VERSION_TAGGING`.
  See §3.4. Do not go hunting for an exact-6.10 Qt; it isn't needed.

**How to re-check these on any machine:**

```bash
# CLO version
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" \
    /Applications/CLO.app/Contents/Info.plist

# CLO's Qt version  ← check this first on any new CLO release
otool -L /Applications/CLO.app/Contents/MacOS/CLO_Standalone_OnlineAuth \
    | grep -i qtcore
```

---

## 2. Prerequisites

```bash
xcode-select --install          # Xcode Command Line Tools
brew install cmake
brew install qt                 # Qt6. NOT qt@5 — see §3.1
```

### qt@5 conflict

If `qt@5` is installed, `brew install qt` fails with:

```
Error: Cannot install qtbase because conflicting formulae are installed.
  qt@5: because both link conflicting binaries
```

Fix — unlinking is safe, it only removes symlinks from `/opt/homebrew/bin`; the
keg stays and `/opt/homebrew/opt/qt@5` still resolves:

```bash
brew unlink qt@5
brew install qt
```

If something else on the machine needs qt@5 linked, `brew link qt@5` afterwards.
This plugin build does **not** need it linked — the path comes from `.env`.

### CLO SDK

Download the macOS SDK from the CLO developer portal and extract it somewhere
stable. Exact version match to CLO is **not** required (see §3.2), but stay on
the same major release year.

---

## 3. The four problems that had to be solved

Each of these cost real time. They are listed in the order you will hit them.

### 3.1 CLO 2026 uses Qt6, not Qt5

**Symptom:** build succeeds, then CLO shows *"The plug-in has a problem. Do you
want to remove the plug-in?"*

**Cause:** `mac/CMakeLists.txt` originally did `find_package(Qt5 COMPONENTS Core
REQUIRED)`. The plugin does not link Qt — it uses `-undefined dynamic_lookup` and
expects Qt symbols to resolve from CLO's already-loaded Qt at runtime. CLO 2026
ships **Qt 6.10.3 and no Qt5 at all**, so Qt5-header symbols cannot resolve.

Three symbols a Qt5 build needs that Qt6 does not have:

| symbol | fate in Qt6 |
|---|---|
| `QArrayData::shared_null` | removed |
| `QArrayData::deallocate(QArrayData*, ulong, ulong)` | resigned (`x` → `qsizetype`) |
| `QString::fromUtf8_helper(const char*, int)` | resigned (`int` → `qsizetype`) |

**Fix (already applied to `mac/CMakeLists.txt`):** `Qt5` → `Qt6` in three places
— `find_package`, the `TARGET_PROPERTY` include-dirs generator expression, and
the comments.

### 3.2 The SDK ships an empty `Lib/` folder

**Symptom:**

```
CMake Error at CMakeLists.txt:57 (find_library):
  Could not find CLO_API_LIB using the following names: CLOAPIInterface
```

**Cause:** `<SDK>/CLOAPIInterface/Lib/` is **empty** in the downloaded SDK. This
is not a bug in our CMakeLists — CLO's own bundled samples
(`Samples/ExportPlugin/CMakeLists.txt`) use an identical
`find_library(... HINTS ../../CLOAPIInterface/Lib REQUIRED)` and cannot build
either.

**Fix — copy the library out of the installed CLO app:**

```bash
cp /Applications/CLO.app/Contents/Frameworks/libCLOAPIInterface.dylib \
   "$CLO_SDK_PATH/CLOAPIInterface/Lib/"
```

This is *better* than whatever the SDK would have shipped: it comes from the CLO
build you actually run, so it is exactly version-matched, which cancels out the
SDK-vs-CLO version gap. It is universal arm64+x86_64, and its install name is
`@executable_path/../Frameworks/libCLOAPIInterface.dylib` — meaning that when
CLO loads the plugin, it resolves to CLO's own already-loaded copy rather than
loading a second instance. Verify with `otool -L` on the built plugin.

**Re-do this step after every SDK re-extract.**

### 3.3 macOS plugins must be *registered*, not just dropped in

**Symptom:** dylib sits in `~/Documents/CLO/Plugins/`, CLO restarts, nothing
appears in the Plugins menu, port 50505 dead, and `api_plugin_log.txt` never
mentions the file.

**Cause:** CLO 2026 uses a v2 plugin system. `pluginSettings.json` is the source
of truth for registered plugins, and a native dylib has to be added through the
Plug-in Manager UI. Copying the file into the folder does nothing on its own.

**Fix:** see §6. This is a *procedure* problem, not a build problem.

### 3.4 Qt version-tag symbol mismatch

**Symptom:** identical to 3.1 — *"The plug-in has a problem."* — even after
switching to Qt6. This is the one that looks like 3.1 came back.

**Cause:** Qt headers emit a reference to `qt_version_tag_<major>_<minor>`
matching the headers you compiled against. Homebrew's Qt is 6.11, CLO's is 6.10,
so the plugin demands `_qt_version_tag_6_11`, which CLO cannot provide:

```
dlopen(.../libRestPlugin.dylib, 0x0006):
    symbol not found in flat namespace '_qt_version_tag_6_11'
```

**Fix (already applied):** `QT_NO_VERSION_TAGGING` added to
`target_compile_definitions` in `mac/CMakeLists.txt`. This is Qt's own supported
macro for exactly this situation. The plugin only uses long-stable QtCore API
(`QTimer`, `QObject`, `QMetaObject::invokeMethod`, `QString`), so exact-minor
matching buys nothing.

> **Note:** CLO reports *every* dylib load failure with the same generic "The
> plug-in has a problem" dialog. It never tells you which symbol. Use the probe
> in §8.1 to get the real error.

---

## 4. Build

### 4.1 `.env`

`clo_workspace/.env` is gitignored and machine-local. Working contents:

```
PLUGIN_PLATFORM=mac
BUILD_CONFIG=Release
CMAKE_EXE=

CLO_SDK_PATH=/Users/<you>/Downloads/CLO_SDK_v2026.0.262_Mac
CLO_PLUGINS_DIR=/Users/<you>/Documents/CLO/Plugins
CLO_PLUGIN_VAULT_DIR=/Users/<you>/Documents/CLO/Plugins/mirra-vault

CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt
Qt6_DIR=/opt/homebrew/opt/qt/lib/cmake/Qt6
CMAKE_OSX_ARCHITECTURES=arm64
```

Notes:

- `CMAKE_PREFIX_PATH` points at Homebrew's **qt** (Qt6), not `qt@5`.
- `Qt6_DIR` is documentation only — `build_plugin.py` reads a `Qt5_DIR` key and
  passes `-DQt5_DIR`. With the key renamed, it passes nothing, and
  `CMAKE_PREFIX_PATH` alone is enough for `find_package(Qt6)`. Harmless, but if
  you ever want the flag plumbed properly, that is the line to change in
  `build_plugin.py`.
- `CMAKE_OSX_ARCHITECTURES`: `arm64` on Apple Silicon, `x86_64` on Intel.
- `CLO_PLUGIN_VAULT_DIR` must resolve **outside** the repo — `build_plugin.py`
  hard-refuses otherwise.

### 4.2 Run it

```bash
cd /path/to/mirra-mvp

# One-time per SDK extract (see §3.2)
cp /Applications/CLO.app/Contents/Frameworks/libCLOAPIInterface.dylib \
   "$CLO_SDK_PATH/CLOAPIInterface/Lib/"

# Always wipe the SDK sample build dir — stale CMakeCache.txt keeps old Qt paths
rm -rf "$CLO_SDK_PATH/Samples/RestPlugin/build"

python3 clo_workspace/build_plugin.py
```

Expected tail:

```
[100%] Built target RestPlugin
Built plugin artifact: <SDK>/Samples/RestPlugin/build/Release/libRestPlugin.dylib
Vault copy: ~/Documents/CLO/Plugins/mirra-vault/libRestPlugin_v1.3.0.dylib
```

Full log at `clo_workspace/logs/build_plugin_mac_<timestamp>.log`. Attach it to
any bug report — it names the exact failing stage.

`--sync-only` copies sources into the SDK sample folder without compiling, for
sanity-checking paths.

---

## 5. Verify the binary *before* touching CLO

Do this every build. It takes seconds and prevents a pointless
restart-and-pray loop.

```bash
DY=~/Documents/CLO/Plugins/mirra-vault/libRestPlugin_v1.3.0.dylib

# 1. Architecture must match your Mac
lipo -archs "$DY"                       # → arm64

# 2. Required CLO entry points must be exported (expect 6)
nm -gU "$DY" | grep -E "DoFunction|GetActionName|GetObjectNameTree|GetPositionIndex"

# 3. Every Qt symbol must exist in CLO's Qt. Zero misses required.
QT6=/Applications/CLO.app/Contents/Frameworks/QtCore.framework/Versions/A/QtCore
nm -gU "$QT6" | awk '{print $NF}' | sort -u > /tmp/qt6syms.txt
for s in $(nm -u "$DY" | grep -E "Q[A-Za-z]" | tr -d ' '); do
  grep -qx "$s" /tmp/qt6syms.txt || echo "MISSING $s"
done
```

The six exports CLO requires (matching `Samples/ExportPlugin/ExportPlugin.h`):
`DoFunction`, `DoFunctionAfterLoadingCLOFile`, `DoFunctionContinuously`,
`GetActionName`, `GetObjectNameTreeToAddAction`, `GetPositionIndexToAddAction`.

Then the definitive test — §8.1's `dlopen` probe. If that prints
`PLUGIN : loaded OK`, CLO will load it.

---

## 6. Install & register

Registration is a UI step. There is no file you can write to skip it.

1. **Quit CLO completely** (⌘Q).
2. Copy the built dylib into the plugins folder. Use a **plain name** matching
   CLO's own sample convention:
   ```bash
   cp ~/Documents/CLO/Plugins/mirra-vault/libRestPlugin_v1.3.0.dylib \
      ~/Documents/CLO/Plugins/libRestPlugin.dylib
   ```
3. **Ensure exactly one `.dylib` is in that folder.** Two copies both start HTTP
   servers and fight over port 50505. Delete the versioned one from
   `CLO_PLUGINS_DIR` — the vault keeps it for rollback.
   ```bash
   ls ~/Documents/CLO/Plugins/*.dylib     # must print exactly one line
   ```
4. Launch CLO.
5. **Plugins → Plug-in Manager → Add Plug-in**, select
   `~/Documents/CLO/Plugins/libRestPlugin.dylib`.
   Expect: *"The plug-in file is loaded into the plug-in manager successfully."*
   If an old broken entry is listed, remove it first.
6. **Plugins → REST Server & Execute** — click **once**.

**Clicking it shows no dialog, no progress bar, nothing. That is correct.** The
Mac plugin starts its HTTP server silently (Windows shows a message box; Mac
does not). Do not click repeatedly. Verify with §7 instead.

After the first click the server runs on its own, drained by a 200 ms Qt timer.

### About `defaultPlugInFolders.txt` and the legacy folder

- `~/Documents/clo/Configuration/API_Plug_in/` is **legacy**. CLO shows a
  deprecation dialog if it exists. It is no longer used for discovery or
  persistence and is safe to delete.
- The current-generation equivalent is
  `~/Documents/CLO/Plugins/defaultPlugInFolders.txt`, one folder path per line.
  It lists *additional* folders to scan. It is **not** what registers a native
  dylib — that is the Plug-in Manager (§6.5). Creating it does not substitute
  for registration.

---

## 7. Verify the running plugin

```bash
curl -s http://127.0.0.1:50505/health | python3 -m json.tool
```

Expected (`plugin_built_at` should match your build time — if it doesn't, CLO is
running a stale dylib):

```json
{
  "status": "ok",
  "platform": "mac",
  "version": "1.3.0",
  "release_status": "unstable",
  "plugin_built_at": "2026-08-03T21:16:46Z"
}
```

```bash
curl -s http://127.0.0.1:50505/capabilities | python3 -m json.tool
```

These two **must** be `true` on Mac — they are the whole point of building on
real macOS, and are stubbed off on Windows due to a Windows-only SEH crash:

```json
"has_avatar_state_readback": true,
"has_avatar_avt_export": true
```

Health alone is not proof. Exercise a write endpoint too, since the queue is a
separate mechanism from the read path:

```bash
curl -s -X POST http://127.0.0.1:50505/new-project    # → "New project queued"
sleep 3
curl -s http://127.0.0.1:50505/status                 # → "New project created"
curl -s http://127.0.0.1:50505/patterns/count         # → {"count":0}
```

Confirm CLO itself owns the port:

```bash
lsof -nP -iTCP:50505     # → CLO_Stand ... (LISTEN)
```

### Which version gets built

`build_plugin.py:find_current_version_path()` globs `versions/v_*.json` and takes
the **highest** version number. It currently builds **1.3.0**, not the 1.1.1 that
older docs mention. To build a specific version, that function is the place to
look. A version file with `"status": "blocked"` refuses to build without
`--allow-blocked`.

---

## 8. Troubleshooting

### 8.1 The `dlopen` probe — use this first, always

CLO's "The plug-in has a problem" dialog never names the real error. This probe
loads the plugin exactly the way CLO does (CLO's own QtCore and
`libCLOAPIInterface` first, then the plugin) and prints the true `dlerror()`.
It found the `qt_version_tag_6_11` bug in one run after an hour of guessing.

The `MacOS/` + `Frameworks/` layout is **not decoration**. The plugin's load
command is `@executable_path/../Frameworks/libCLOAPIInterface.dylib`, so the
probe binary must sit one level below a `Frameworks/` directory containing that
library. Skip the symlink and the probe reports

```
PLUGIN : FAILED
  Library not loaded: @executable_path/../Frameworks/libCLOAPIInterface.dylib
```

on a perfectly good plugin — a false negative that sends you chasing a
nonexistent bug. (Loading the library by absolute path first is *not* enough;
dyld still resolves the plugin's dependency relative to the probe binary.)

```bash
D=/tmp/clotest && mkdir -p "$D/MacOS" "$D/Frameworks"
ln -sf /Applications/CLO.app/Contents/Frameworks/libCLOAPIInterface.dylib "$D/Frameworks/"
cat > "$D/probe.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int main(int argc, char** argv) {
    void* qt = dlopen("/Applications/CLO.app/Contents/Frameworks/QtCore.framework/Versions/A/QtCore", RTLD_NOW|RTLD_GLOBAL);
    printf("QtCore : %s\n", qt ? "loaded" : dlerror());
    void* api = dlopen("/Applications/CLO.app/Contents/Frameworks/libCLOAPIInterface.dylib", RTLD_NOW|RTLD_GLOBAL);
    printf("CLOAPI : %s\n", api ? "loaded" : dlerror());
    void* p = dlopen(argv[1], RTLD_NOW|RTLD_LOCAL);
    if (p) { printf("PLUGIN : loaded OK\n");
             printf("GetActionName: %s\n", dlsym(p, "GetActionName") ? "found" : "MISSING"); }
    else   { printf("PLUGIN : FAILED\n  %s\n", dlerror()); }
    return 0;
}
EOF
cc -o "$D/MacOS/probe" "$D/probe.c"
"$D/MacOS/probe" ~/Documents/CLO/Plugins/libRestPlugin.dylib
```

Success looks like:

```
QtCore : loaded
CLOAPI : loaded
PLUGIN : loaded OK
GetActionName: found
```

### 8.2 Symptom index

| Symptom | Cause | Fix |
|---|---|---|
| *"The plug-in has a problem. Do you want to remove the plug-in?"* | `dlopen` failed — CLO never says why | Click **No**. Run §8.1 probe for the real error. |
| Probe says `symbol not found ... _qt_version_tag_6_XX` | Homebrew Qt minor ≠ CLO Qt minor | `QT_NO_VERSION_TAGGING` (§3.4) — already applied |
| Probe says missing `QArrayData` / `QString::fromUtf8_helper` symbols | Built against Qt5 headers | Switch to Qt6 (§3.1) |
| `find_library ... Could not find CLO_API_LIB` | SDK `Lib/` empty | Copy dylib from CLO.app (§3.2) |
| Build OK, dylib in folder, nothing in Plugins menu | Not registered | Plug-in Manager → Add Plug-in (§6.5) |
| Clicking *REST Server & Execute* does nothing visible | Correct behavior — Mac starts silently | Verify with `curl /health` (§7) |
| `curl` → `http 000` / connection refused | Server not started, or CLO not running | Click *REST Server & Execute* once; check `lsof -nP -iTCP:50505` |
| Port 50505 in use / two servers fighting | Two dylibs in `CLO_PLUGINS_DIR` | Keep exactly one (§6.3) |
| `/health` shows an old `plugin_built_at` | CLO running a stale dylib | Quit CLO fully, reinstall, relaunch |
| CMake picks up old Qt paths after switching Qt5→Qt6 | Stale `CMakeCache.txt` | `rm -rf "$CLO_SDK_PATH/Samples/RestPlugin/build"` |
| `brew install qt` → conflicting formulae | qt@5 linked | `brew unlink qt@5` (§2) |
| Deprecation dialog about `Configuration/API_Plug_in` | Legacy folder exists | Safe to delete (§6) |

### 8.3 Useful paths

```
~/Documents/CLO/Plugins/                        installed plugins (one dylib!)
~/Documents/CLO/Plugins/pluginSettings.json     v2 registration, source of truth
~/Documents/CLO/Plugins/defaultPlugInFolders.txt  extra scan folders (optional)
~/Documents/CLO/Plugins/mirra-vault/            versioned builds, for rollback
~/Documents/clo/CLO Assets/api_plugin_log.txt   CLO's plugin log
clo_workspace/logs/build_plugin_mac_*.log       build logs
<SDK>/Samples/RestPlugin/                       where sources are synced+compiled
```

`api_plugin_log.txt` logs Python folder registration and plugin-folder skips. It
does **not** log native dylib load failures — silence there is not proof of
success.

### 8.4 Rollback

```bash
python3 clo_workspace/scripts/get_installed_plugin_info.py   # installed vs vault
python3 clo_workspace/scripts/switch_plugin.py --activate 1.1.0
```

Both require CLO closed. `switch_plugin.py` removes competing versioned plugins
from `CLO_PLUGINS_DIR` automatically.

---

## 9. Changes made to the repo

Both are in `clo_workspace/mac/CMakeLists.txt`. An older handoff doc said not to
edit anything under `mac/` — that instruction predates any Mac build ever having
been attempted, and both changes are genuine fixes to stale assumptions about
CLO's Qt version. They must be carried forward, not reverted.

1. **`find_package(Qt5 ...)` → `find_package(Qt6 ...)`**, plus `Qt5::Core` →
   `Qt6::Core` in the include-dirs generator expression and comments. (§3.1)
2. **`QT_NO_VERSION_TAGGING`** added to `target_compile_definitions`. (§3.4)

Both carry inline comments explaining why, so nobody "tidies" them back.

Not committed / machine-local, recreate per machine:

- `clo_workspace/.env` (gitignored)
- `libCLOAPIInterface.dylib` copied into `<SDK>/CLOAPIInterface/Lib/`

System changes made outside the repo:

- `brew unlink qt@5` then `brew install qt` (Qt 6.11.1)
- Deleted legacy `~/Documents/clo/Configuration/API_Plug_in/`

---

## 10. Still open

- **`versions/v_1.3.0.json` marks mac as `"pending"`.** Now that it builds,
  loads, and answers `/health`, `/capabilities` and `POST /new-project` on real
  hardware, that should move to `in_sync` — after a full
  `clo_vto/run_clo_vto.py` run confirms the write endpoints behave under load.
- **No `TraceLog` on Mac.** Windows has a crash-forensic file logger; Mac does
  not. Deferred, tracked in
  `.agent/clo-avatar-vto/merge-followup-clo-workspace.md` §5.
- **`build_plugin.py` still reads a `Qt5_DIR` env key** and passes `-DQt5_DIR`.
  Inert now, but misleading — worth renaming to `Qt6_DIR`.
- **Qt6 headers are only tested at 6.11.1 against CLO 6.10.3.** If CLO ships a
  Qt7 or Homebrew moves to Qt 7, re-run §1's check and §5's symbol diff before
  assuming anything.
