# Phase 5 Plugin Extension

## Goal

Add the first isolated plugin-facing support for the CLO-native avatar path without changing the current default VTO lane.

## What was added

### New plugin support file

- `clo_workspace/plugins/CloNativePluginSupport.h`

This keeps native-avatar debug-state handling separate from the main plugin file as much as possible.

### Additive plugin endpoints

Added to the existing REST plugin:

- `GET /avatar/native-debug`
- `POST /import-avatar-avt`
- `POST /import-avatar-measurements`

### Additive plugin command handling

Added new queued command types:

- `import-avatar-avt`
- `import-avatar-measurements`

### Isolated Python-side client additions

Added only inside the experimental folder:

- `clo_avatar_generation/adapters/clo_native_client.py`
- `clo_avatar_generation/adapters/clo_native_importer.py`

No existing default VTO client was modified.

## What this phase does not do

1. It does not modify the existing default VTO runner.
2. It does not modify the existing default OBJ avatar path.
3. It does not generate the real measurement CSV yet.
4. It does not verify SDK signatures against a local CLO build during this repo-only phase.

## Important note

The new measurement-import code uses the documented CLO API names:

- `ImportAvatarMeasurement(...)`
- `ImportMeasurement(...)`

This is the correct direction based on current research, but final build verification against the exact installed CLO SDK is still required in a later validation pass.

