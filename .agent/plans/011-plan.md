# 011 Plan - Shared Plugin Workspace + macOS Parity

## Goal

Restructure `clo_workspace/` into a cleaner cross-platform plugin workspace **without breaking the current code**, and bring the macOS plugin up to date with the Windows plugin.

This plan is focused on:
- making the workspace structure correct
- keeping the build/runtime working
- updating the macOS plugin so it supports the newer Windows functionality
- moving shared config/docs/build entrypoints to the root of `clo_workspace/`
- establishing the new rule that plugin updates are done for both Windows and macOS together

This plan is **not** the cleanup/delete plan.
Cleanup of unnecessary files, generated artifacts, hardcoded leftovers, and things that should not be committed belongs in `012-plan.md`.

---

## Target Workspace Structure

Use these exact names:

```text
clo_workspace/
  .env
  .env.example
  README.md
  SETUP.md
  build_plugin.py
  plugin_contract.json
  versions/
    v_1.1.0.json
  scripts/
    get_installed_plugin_info.py
  shared/
    httplib.h
    json.hpp
    CloNativePluginSupport.h
    PluginBuildInfo.h
  windows/
    RestPlugin.cpp
    CMakeLists.txt
    dllmain.cpp
    stdafx.h
    targetver.h
    build_rest_plugin.bat
  mac/
    RestPlugin_macOS.cpp
    CMakeLists.txt
    build_plugin.sh
```

Notes:
- `shared/` is only for things that are truly common to both platforms
- `windows/` is only for Windows-specific code/build files
- `mac/` is only for macOS-specific code/build files
- root `build_plugin.py` detects OS and dispatches to the correct platform-specific build path

We are **not** adding a parity file today.
That can be added later.

---

## Working Rules For This Plan

### 1. Plugin updates are now cross-platform work

From this point onward, when someone updates the plugin:
- they should update both Windows and macOS implementations
- the other OS should then be tested
- if parity issues appear, they should be fixed before the plugin work is treated as complete

### 2. Build support is only for Windows and macOS

The new root build entrypoint should:
- detect the current OS by default
- build Windows on Windows
- build macOS on macOS
- refuse to build on unsupported OSes such as Linux

It should fail clearly rather than guessing.

### 3. Shared code should stay minimal

Only move things to `shared/` when they are clearly safe and truly common.

If there is doubt about a function or implementation detail:
- keep it explicit in `windows/`
- keep it explicit in `mac/`

### 4. Root build file should only initialize and dispatch

`clo_workspace/build_plugin.py` should act as the entrypoint that:
- loads shared config
- detects OS
- loads version/contract metadata
- selects the platform-specific build path
- records build logging

After that, platform-specific build logic may stay in separate files/modules per OS.

### 5. Parity scope for this phase is minimum viable parity

For `011`, parity means:
- macOS catches up to the Windows functionality needed by the current plugin workflows
- both platforms expose the agreed minimum shared contract

This plan does **not** require every possible future helper/debug capability on day one.

### 6. Active docs should be rewritten in `011`, not deleted blindly

During `011`:
- rewrite the active root docs to match the new structure
- mark old docs that should be reviewed later

Actual deletion of stale docs belongs in `012`.

### 7. Existing generated build folders stay for now

Do not delete existing build folders during `011`.
That cleanup belongs in `012`.

---

## What Must Be Shared

These should live in `clo_workspace/shared/` because both platforms need them:
- `httplib.h`
- `json.hpp`
- `CloNativePluginSupport.h`
- generated `PluginBuildInfo.h` or equivalent shared build metadata header

The following should remain shared at the root:
- `.env`
- `.env.example`
- `README.md`
- `SETUP.md`
- `build_plugin.py`
- `plugin_contract.json`
- `versions/`
- `scripts/`

---

## What Must Stay Platform-Specific

### Windows-specific
- `RestPlugin.cpp`
- `dllmain.cpp`
- `stdafx.h`
- `targetver.h`
- Windows `CMakeLists.txt`
- Windows wrapper script if still needed

### macOS-specific
- `RestPlugin_macOS.cpp`
- macOS `CMakeLists.txt`
- macOS wrapper script if still needed

Why these must stay separate:
- plugin binary format differs (`.dll` vs `.dylib`)
- install locations differ
- timer/main-thread integration differs
- compiler/linker behavior differs
- macOS has Qt/runtime handling needs that do not match the Windows path

---

## Functional Goal For Parity

The macOS plugin should be updated until it supports the same practical REST surface and behavior as the Windows plugin.

This includes the newer Windows functionality currently missing on macOS:
- metadata-rich `/health`
- `/capabilities`
- `/debug/import-scales`
- `/avatar/debug`
- `/avatar/native-debug`
- `/avatars/state`
- `/import-avatar-avt`
- `/import-avatar-measurements`
- richer pattern inspection routes:
  - `/patterns/{index}`
  - `/patterns/{index}/bbox`
  - `/patterns/{index}/input`
  - `/patterns/{index}/line-lengths`
- `/arrangement/debug`

The goal is:
- same route names
- same request shapes
- same response shapes
- same capability flags
- same version/health semantics

Internal implementation may still differ by OS where required.

---

## Work Plan

### Phase 1 - Restructure without breaking imports/builds

Create the new root/shared/windows/mac layout.

Move files into the new structure in a controlled way.

While doing this:
- update include paths
- update build paths
- update any imports/exports or file references that break due to moved files
- keep the actual code behavior unchanged during the structure move

Success condition:
- the plugin source still builds after the move
- paths resolve correctly

### Phase 2 - Move root-level config and docs

Move:
- `.env` to `clo_workspace/.env`
- `.env.example` to `clo_workspace/.env.example`

Create/standardize:
- `clo_workspace/README.md`
- `clo_workspace/SETUP.md`
- `clo_workspace/scripts/`

They should follow the same pattern as the repo root docs:
- `README.md` explains structure, intent, and current usage
- `SETUP.md` explains exact setup/build/install workflow

`SETUP.md` should also explicitly describe:
- supported OSes
- how OS detection works
- where logs are written
- which docs are active vs marked for later cleanup

### Phase 3 - Root build entrypoint

Move the shared build dispatcher to:
- `clo_workspace/build_plugin.py`

This root build file should:
- load `.env`
- detect OS
- load `plugin_contract.json`
- load latest version from `versions/`
- generate shared build metadata
- run the Windows or macOS build path as appropriate
- log which OS was detected
- log important build phases
- record where the build failed if an error occurs

If the detected OS is neither Windows nor macOS:
- do not build
- exit with a clear unsupported-OS error

Keep platform-specific wrappers only if still useful.

### Phase 4 - Rewire Windows to the new structure

Update Windows build/config/source paths so they work from:
- `clo_workspace/windows/`
- `clo_workspace/shared/`
- root `clo_workspace/build_plugin.py`

Windows behavior should remain functionally unchanged after the move.

### Phase 5 - Rewire macOS to the new structure

Update macOS build/config/source paths so they work from:
- `clo_workspace/mac/`
- `clo_workspace/shared/`
- root `clo_workspace/build_plugin.py`

macOS should use the same shared metadata/version/contract sources as Windows.

### Phase 6 - Bring macOS feature set up to Windows level

Update the macOS plugin implementation so it includes all newer Windows plugin routes and functionality listed above.

This is the main parity phase.

### Phase 7 - Align runtime metadata

Make sure both platforms use the same shared metadata model for:
- `/health`
- `/capabilities`
- build/version reporting
- release status
- contract version

Also make sure the versioning model reflects the new working rule:
- one shared plugin version
- platform sync/tracking in the version metadata
- if one OS is broken, that becomes visible in the shared release state/process

### Phase 8 - Add root scripts for post-build checks

Create:
- `clo_workspace/scripts/get_installed_plugin_info.py`

Initial purpose:
- identify the currently installed plugin version
- identify the currently installed plugin location

This script becomes the first checked script in the root `scripts/` folder.

This plan does not need a full test-suite folder yet, but it should establish the pattern that new build-validation scripts live in:
- `clo_workspace/scripts/`

### Phase 9 - Validation

After the restructure and parity work:
- confirm Windows still builds
- confirm macOS still builds
- confirm route parity where intended
- confirm no path/import/include breakage was introduced
- confirm build logs show detected OS and failure point clearly when something goes wrong
- confirm the installed-plugin info script works

Since you are currently on Windows and have not yet built the latest plugin, one validation path for this plan should include:
- rebuilding the latest Windows plugin
- checking whether the build/install flow still works after the new structure
- using that result as part of the plan validation

This plan is not complete unless the code still works after the new structure.

---

## Env Requirements

The root env files should become the single source of machine-specific plugin-build configuration.

### `clo_workspace/.env`

Should contain all necessary local machine values required to build/install the plugin on the current OS.

### `clo_workspace/.env.example`

Should document:
- which values are shared across OSes
- which values are Windows-specific
- which values are macOS-specific

If fields differ by OS, that should be stated explicitly in the example file and setup docs rather than left implicit.

---

## Validation Checklist

Before calling this plan done:

1. `clo_workspace/` has the new root/shared/windows/mac layout
2. root `.env` and `.env.example` are in place
3. root `README.md` and `SETUP.md` are in place
4. root `build_plugin.py` is the shared entrypoint
5. Windows paths/imports/includes still work
6. macOS paths/imports/includes still work
7. macOS plugin supports the newer Windows plugin functionality
8. root `.env` and `.env.example` contain all required fields for both platforms
9. `.env.example` clearly documents which fields are shared and which are OS-specific
10. root build logs clearly show OS detection and build-stage failures
11. `clo_workspace/scripts/get_installed_plugin_info.py` exists and works
12. no runtime/build path is broken by the move
