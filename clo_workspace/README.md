# CLO Workspace

`clo_workspace/` is the cross-platform CLO plugin workspace for Mirra.

It holds the shared plugin contract, shared headers, platform-specific plugin sources, build entrypoints, and validation scripts that support the active CLO automation lanes:

- `vto/run_vto.py`
- `clo_avatar_generation/run_avatar.py`
- `clo_avatar_generation/run_clo_vto.py`

## Structure

```text
clo_workspace/
  .env
  .env.example
  README.md
  SETUP.md
  build_plugin.py
  plugin_contract.json
  versions/
  scripts/
  shared/
  windows/
  mac/
```

## Active responsibilities

- `build_plugin.py` is the shared build entrypoint.
- `shared/` contains headers and generated build metadata shared by both platforms.
- `windows/` contains the Windows plugin source and wrapper.
- `mac/` contains the macOS plugin source and wrapper.
- `scripts/` contains build and install validation helpers.
- `logs/` is kept in git with a `.gitkeep`, while local build logs are ignored.

## Current workflow surface

The plugin needs to support the combined route surface used by:

- the mesh-avatar VTO lane in `vto/`
- the native-avatar generation lane in `clo_avatar_generation/avatar_runtime/`
- the native-avatar VTO lane in `clo_avatar_generation/native_vto/`

That includes:

- metadata and queue endpoints such as `/health`, `/capabilities`, `/status`, `/execute`
- avatar import/debug/state routes
- pattern import, arrangement, inspection, seam, simulation, export, and save routes

See `plugin_contract.json` for the shared route list and `versions/` for the current release metadata.

## Checking Running Version

If CLO is open and the plugin server is running, check the live plugin version with:

```powershell
Invoke-RestMethod http://127.0.0.1:50505/health
```

This returns useful runtime metadata such as:

- `version`
- `plugin_built_at`
- `release_status`
- `platform`
- `contract_version`

Use this when you want to know which plugin version is actually running inside CLO.

The helper script:

```powershell
python clo_workspace/scripts/get_installed_plugin_info.py
```

only checks the installed plugin artifact on disk. It does not report the running plugin version by itself.

## Seams

Both seam tracks should remain visible during this phase:

- the active 10-seam mapping used by current automation flows
- the older 26-seam references and discovery path that still matter for debugging and future comparison

## Local Generated Folders

These folders are local/generated workspace output and should not be committed:

- `clo_workspace/logs/`
- `clo_workspace/exports/`
- `clo_workspace/projects/`

## Next docs

- `SETUP.md` explains local setup, build, install, and validation.
- `plugin_contract.json` defines the shared plugin surface.
- `versions/v_*.json` records release metadata and platform sync state.
