# CLO REST Plugin — macOS Build Handoff

For whoever is building the Mac plugin. The C++ source already exists and is
merged into the repo (`saumy` branch, commit `16fc690` — "merger complete").
**Nothing needs to be written from scratch.** The job is: pull the repo,
install the toolchain below, run one Python script, install the `.dylib`
into CLO, and verify it responds. If you hit build errors, that's useful
signal — report the exact CMake/compiler output back.

---

## 1. What you're building

`clo_workspace/` is a cross-platform CLO 3D plugin workspace. It builds a
native library that CLO loads as a plugin — `.dll` on Windows, `.dylib` on
Mac. Once loaded (user clicks **Plugins → REST Server & Execute** in CLO
once), it starts an HTTP server on `http://127.0.0.1:50505` that our Python
pipeline talks to. Windows and Mac run the **same version** (currently
`1.1.1`) and must expose the same endpoints/behavior — that's enforced by
`clo_workspace/plugin_contract.json`.

The Mac source (`clo_workspace/mac/RestPlugin_macOS.cpp`) is already at
parity with Windows on the things that matter (port 50505, 200ms queue
timer, fabric endpoints, sync-read pattern for GET routes). It has never
actually been compiled on a real Mac — that's what this build is for.

---

## 2. Get the code

```bash
git clone <repo-url> mirra-mvp
cd mirra-mvp
git checkout saumy
```

Confirm you're on commit `16fc690` or later (`git log -1`). Everything you
need lives under `clo_workspace/`:

```
clo_workspace/
├── build_plugin.py          ← you run this, nothing else
├── plugin_contract.json     ← the endpoint contract both platforms must match
├── .env.example              ← copy this to .env and fill in your paths
├── shared/                  ← headers shared by both platforms (don't edit)
├── mac/
│   ├── RestPlugin_macOS.cpp ← the plugin source (already written)
│   ├── CMakeLists.txt       ← Mac build config (already written)
│   └── build_plugin.sh      ← optional convenience wrapper
├── versions/v_1.1.1.json    ← current version metadata
└── scripts/                 ← install/rollback helpers, run after building
```

You do not need to touch anything inside `mac/` or `shared/`. If the build
fails because of missing source, that's a bug to report, not something to
patch locally.

---

## 3. Install prerequisites

- **Python 3.9+**
- **CLO SDK for macOS** — download from the CLO developer portal. **It must
  match your installed CLO version exactly** (e.g. if you're on CLO 2025,
  get the 2025 SDK, not 2024). Extract it somewhere stable.
- **Xcode Command Line Tools**: `xcode-select --install`
- **CMake**: `brew install cmake`
- **Qt 5** (headers only — the plugin does not link Qt, it borrows CLO's
  already-loaded Qt5 at runtime): `brew install qt@5`

---

## 4. Configure `.env`

```bash
cp clo_workspace/.env.example clo_workspace/.env
```

Edit `clo_workspace/.env` (this file is gitignored — it's machine-local,
never commit it). Fill in the **macOS block only**:

```
PLUGIN_PLATFORM=mac
BUILD_CONFIG=Release
CMAKE_EXE=

CLO_SDK_PATH=/Users/yourname/Downloads/CLO_SDK_vYYYY.X.XXX_Mac
CLO_PLUGINS_DIR=/Users/yourname/Documents/CLO/Plugins
CLO_PLUGIN_VAULT_DIR=/Users/yourname/Documents/CLO/Plugins/mirra-vault

CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt@5
Qt5_DIR=/opt/homebrew/opt/qt@5/lib/cmake/Qt5
CMAKE_OSX_ARCHITECTURES=arm64
```

Notes:
- `CMAKE_OSX_ARCHITECTURES`: `arm64` for Apple Silicon (M1/M2/M3/M4), `x86_64`
  for Intel.
- `CLO_PLUGIN_VAULT_DIR` **must be outside the repo** — `build_plugin.py`
  hard-refuses if it resolves inside the checkout. It's where every built
  version is kept for rollback; CLO never loads from here directly.
- Leave `CMAKE_EXE` blank if `cmake` is already on `PATH` (Homebrew puts it
  there).
- If you installed Qt via the online installer instead of Homebrew, use its
  path instead, e.g. `/Users/yourname/Qt/5.15.16/macos/...` — see
  `clo_workspace/SETUP.md` for both variants side by side.

---

## 5. Build

From the repo root:

```bash
python3 clo_workspace/build_plugin.py
```

What this does, in order: reads `.env` → detects macOS → loads
`plugin_contract.json` and the current version file (`v_1.1.1.json`) →
generates `shared/PluginBuildInfo.h` (version/build-time macros, baked into
the binary) → copies `mac/RestPlugin_macOS.cpp` + `mac/CMakeLists.txt` +
shared headers into `<CLO_SDK_PATH>/Samples/RestPlugin/` → runs `cmake`
configure + build there → copies the resulting `.dylib` into your vault with
a versioned name (`libRestPlugin_v1.1.1.dylib`) → prints the exact manual
copy command for install.

A full build log is written to `clo_workspace/logs/build_plugin_mac_<timestamp>.log`
— **attach this if the build fails.** It records exactly which stage failed
(env validation, cmake configure, cmake build).

If `find_package(Qt5 ...)` fails during configure, it means CMake can't find
Qt5 — double check `CMAKE_PREFIX_PATH` / `Qt5_DIR` in `.env`.

To just sync sources into the SDK folder without compiling (useful for
sanity-checking paths before a full build):

```bash
python3 clo_workspace/build_plugin.py --sync-only
```

---

## 6. Install into CLO

The build prints the exact copy command at the end. Manually:

1. Close CLO completely.
2. Copy the versioned file from the vault into `CLO_PLUGINS_DIR`:
   ```bash
   cp ~/Documents/CLO/Plugins/mirra-vault/libRestPlugin_v1.1.1.dylib \
      ~/Documents/CLO/Plugins/libRestPlugin_v1.1.1.dylib
   ```
3. Make sure **no other versioned plugin** is sitting in `CLO_PLUGINS_DIR` at
   the same time — CLO will load both and they'll fight over port 50505.
   (`clo_workspace/scripts/switch_plugin.py --activate 1.1.1` does this
   swap safely if you ever have an older version installed — see §8.)
4. Restart CLO.
5. In CLO: **Plugins → REST Server & Execute** (click once — after that the
   server runs automatically in the background via a 200ms Qt timer).

---

## 7. Verify it's alive

```bash
curl http://127.0.0.1:50505/health
```

Expect JSON back with `"platform": "mac"`, `"version": "1.1.1"`,
`"release_status": "unstable"`, and a `plugin_built_at` timestamp matching
roughly when you built it. Also check:

```bash
curl http://127.0.0.1:50505/capabilities
```

On Mac, these two flags should read `true` (this is the actual point of
building on real macOS — these are stubbed to `false`/broken on Windows due
to a Windows-only SEH crash, see §9):

```json
{
  "has_avatar_state_readback": true,
  "has_avatar_avt_export": true
}
```

If either is `false`, something didn't build from the intended source —
check the build log's "Synced ... plugin sources to" line points at your
`CLO_SDK_PATH`'s sample folder, and that CLO is loading the dylib you just
built (not a stale one — check `plugin_built_at` in `/health`).

For a real end-to-end smoke test, exercise a couple of write endpoints too,
not just health:

```bash
curl -X POST http://127.0.0.1:50505/new-project
curl http://127.0.0.1:50505/status
```

---

## 8. Version / rollback tooling (only needed later)

```bash
# See what's installed vs what's in the vault
python3 clo_workspace/scripts/get_installed_plugin_info.py

# Roll back to a previous version if something regresses
python3 clo_workspace/scripts/switch_plugin.py --activate 1.1.0
```

Both require CLO to be closed. `switch_plugin.py` removes any other
versioned plugin from `CLO_PLUGINS_DIR` automatically — you won't end up
with two competing DLLs.

---

## 9. Background — why any of this matters (read if curious, not required to build)

There's a documented incident (`.claude/research/step-1/POST_MORTEM_v1.1.1.md`)
where two new Windows endpoints (`/avatars/state`, `export-avatar-avt`)
called CLO SDK functions directly from the wrong thread and raised Windows
SEH exceptions that `catch(std::exception&)` can't intercept — this killed
the HTTP server (and once, CLO itself) mid-pipeline. The fix on Windows was
to stub both out rather than fix the threading, because SEH handling
(`__try/__except`) is invasive. Mac was never affected — it already routed
every read through a `dispatchSyncRead()` promise/future handoff onto the
main thread instead of calling CLO API inline from the HTTP thread, which is
exactly the safe pattern the post-mortem's "Rules for Next Time" section
prescribes. That's *why* Mac can enable `has_avatar_state_readback` and
`has_avatar_avt_export` where Windows can't (yet).

Practical implication for you: those two endpoints are new, real code paths
that only Mac exercises today. Worth actually calling them once (not just
`/health`) before calling the build "done" — see §7's smoke test and expand
it with an `/avatar/native-debug` and `/export-avatar-avt` call if you have
a spare avatar file handy, since "works in isolation" has bitten this repo
before (rule #3 in the post-mortem: test every new CLO API call end-to-end
through the real pipeline, not just standalone).

One known gap, **not a blocker**: the Windows plugin has a file-based
crash-forensic logger (`TraceLog`, writes to `clo_workspace/logs/`) that
Mac doesn't have yet. It's tracked as a deferred TODO
(`.agent/clo-avatar-vto/merge-followup-clo-workspace.md`, §5) and isn't
needed to build or ship the Mac plugin — only relevant if you're debugging a
Mac-side crash later and wish you had a trace log.

---

## 10. If something goes wrong

- **CMake can't find Qt5** → check `CMAKE_PREFIX_PATH`/`Qt5_DIR` in `.env`.
- **CMake can't find CLOAPIInterface** → double-check `CLO_SDK_PATH` points
  at the extracted SDK root (the one containing `CLOAPIInterface/`), and
  that it's the SDK version matching your installed CLO build exactly.
- **Build succeeds but CLO doesn't show the plugin** → check
  `CLO_PLUGINS_DIR` is the folder CLO actually reads from
  (`~/Documents/CLO/Plugins` by default) and that there isn't a stale
  unversioned `RestPlugin.dylib` sitting alongside it.
- **Port 50505 already in use / connection refused** → another CLO instance
  or a previous plugin load may still be holding the port; fully quit CLO
  (not just close the window) and relaunch.
- Anything else: send the `clo_workspace/logs/build_plugin_mac_*.log` file
  from the failed run — it names the exact stage that failed.
