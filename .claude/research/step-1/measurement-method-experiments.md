# Measurement Method Experiments

## Goal

Find a reliable way to change the measurements of a loaded CLO avatar in Step-1.

For all body-size experiments, our working unit is:

- `cm` for linear body measurements

Shape sliders that are shown as percentages in the UI should be treated as a separate control type and not mixed into the centimeter-based measurement path.

## Current Status

Status: `in_progress`

What is already proven:

- Native `.avt` avatar import works.
- The loaded avatar keeps its arrangement slots after import.
- The current CSV measurement-import route is still unverified.
- The current repo CSV template is not accepted by the live Windows plugin, even when used unchanged.

## Attempted Methods

### Method 1: CSV multi-field apply through Step-1 runtime

- Transport: JSON input on our side -> generated CSV bridge -> `POST /import-avatar-measurements`
- Plugin call:
  - `ImportAvatarMeasurement(csvPath, avtPath, options)`
- Source run:
  - [u_001-005](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-005)
- Result: `failed`

Evidence:

- [apply_result.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-005/apply_result.json)
- [clo_payload.bridge.csv](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-005/clo_payload.bridge.csv)
- [clo_payload_manifest.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-005/clo_payload_manifest.json)

What this tells us:

- Base avatar import succeeds.
- The plugin accepts the HTTP request.
- CLO rejects the measurement import itself.
- The current field mapping and/or CSV schema is not correct enough for production use.

### Method 2: CSV single-field apply through Step-1 runtime

- Transport: JSON input on our side -> generated CSV bridge with one active field -> `POST /import-avatar-measurements`
- Active field:
  - `Total Height`
- Plugin call:
  - `ImportAvatarMeasurement(csvPath, avtPath, options)`
- Source run:
  - [u_001-006](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-006)
- Result: `failed`

Evidence:

- [apply_result.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-006/apply_result.json)
- [target_measurements.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-006/target_measurements.json)
- [clo_payload.bridge.csv](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-006/clo_payload.bridge.csv)
- [clo_payload_manifest.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-006/clo_payload_manifest.json)

What this tells us:

- The failure is not just because we sent too many fields at once.
- A one-field-at-a-time CSV bridge still fails.
- This is strong evidence that the current CSV route or schema is wrong, not only the field-combination logic.

### Method 3: Exact repo CSV template with template path

- Transport: existing repo template CSV used unchanged
- CSV file:
  - [measurement_template_unconfirmed.csv](c:/D-drive-data/mirra-mvp/clo_avatar_generation/schema/measurement_template_unconfirmed.csv)
- Plugin call:
  - `ImportAvatarMeasurement(csvPath, avtPath, options)`
- Template avatar:
  - [base-1.avt](c:/D-drive-data/mirra-mvp/clo_avatar_generation/input/base-1.avt)
- Result: `failed`

Live probe summary from 2026-04-07:

- `new-project`: success
- `import-avatar-avt`: success
- `import-avatar-measurements`: request queued successfully
- queue drained successfully
- final measurement import result: failed

What this tells us:

- The current repo CSV template itself is not accepted by the SDK route we are using.
- The problem is broader than our runtime overrides.
- We should treat `measurement_template_unconfirmed.csv` as a placeholder only.

### Method 4: Exact repo CSV template without template path

- Transport: existing repo template CSV used unchanged
- CSV file:
  - [measurement_template_unconfirmed.csv](c:/D-drive-data/mirra-mvp/clo_avatar_generation/schema/measurement_template_unconfirmed.csv)
- Plugin call:
  - `ImportMeasurement(csvPath)`
- Result: `failed`

Live probe summary from 2026-04-07:

- `new-project`: success
- `import-avatar-avt`: success
- `import-avatar-measurements` request with empty `template_path`: queued successfully
- queue drained successfully
- final measurement import result: failed

What this tells us:

- Both SDK routes currently fail with the same repo CSV template:
  - `ImportAvatarMeasurement(csv, avt)`
  - `ImportMeasurement(csv)`
- So the issue is not limited to choosing the wrong one of those two routes.

### Method 5: JSON source on our side with CSV bridge underneath

- Transport: JSON source file -> runtime converts to CSV -> plugin imports CSV
- Current source file example:
  - [u_001.measurements.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/input/u_001.measurements.json)
- Result: `partially useful, not sufficient`

What this tells us:

- JSON is a good authoring and debugging format for us.
- JSON alone does not solve the CLO import problem while the plugin still depends on CSV import APIs.

### Method 6: Direct JSON/property-based plugin route

- Transport: JSON body sent directly to the plugin
- Experimental routes:
  - `POST /avatar/set-properties`
  - `GET /avatar/property-debug`
- Current state: `implemented in code and compile-validated locally`
- Result: `not yet runtime-verified in CLO`

Why this method is worth exploring:

- The installed Windows SDK exposes:
  - `SetAvatarProperties(...)`
  - `GetAvatarProperties(...)`
- This gives us a non-CSV experiment path on the plugin side.

Current risk:

- The live readback from `/avatars/state` only shows generic avatar properties such as:
  - `DivideMesh`
  - `KineticFriction`
  - `SkinOffsetMM`
  - `SoftBodySimulation`
  - `StaticFriction`
- It does not currently expose body measurements like `Total Height`, `Chest`, or `Waist`.
- So a JSON/property path may still fail to control body size, even if the endpoint itself works technically.

What is already proven about this method:

- The Windows plugin code was updated to add the JSON/property route.
- The updated plugin builds successfully in a local workspace build:
  - `clo_workspace/windows/build-local/Release/RestPlugin.dll`

What is still unproven:

- The currently running CLO plugin has not been replaced with this rebuilt DLL yet.
- So the new JSON/property route has not yet been exercised against the live CLO instance.

Example request shape for the next test:

```json
{
  "avatar_index": 0,
  "unit": "cm",
  "properties": {
    "Total Height": "187.96"
  }
}
```

Important note:

- This payload shape is now supported by the experimental plugin code.
- It does not prove that `Total Height` is a valid `SetAvatarProperties` key.
- We still need a live CLO test after installing the rebuilt plugin.

### Method 7: Direct `.avt` patch route with live CLO import/export verification

- Transport:
  - JSON input on our side -> patch the base `.avt` feature values directly -> `POST /import-avatar-avt` -> `POST /export-avatar-avt`
- Current state: `working for the AVT-backed Step-1 body fields`
- Result: `working`

What was proven live on 2026-04-07:

- A one-field patched avatar with only `Total Height` changed imported successfully into CLO.
- Exporting that avatar back out of CLO preserved the requested `Total Height` value.
- The re-exported avatar also showed many dependent feature-value changes, which is strong evidence that CLO accepted the resized avatar rather than merely echoing the file back unchanged.

Verified AVT-backed Step-1 field indexes currently in use:

- `Total Height` -> feature index `0`
- `Chest` -> feature index `2`
- `Waist` -> feature index `6`
- `Low Hip` -> feature index `8`
- `Inseam` -> feature index `26`
- `Across Shoulder (Curvilinear)` -> feature index `36`

Current limitation:

- `Weight` is still not verified on the AVT patch route.
- A provisional weight-like feature index was tested, but CLO re-export normalized it back to the base value instead of preserving the requested target.

Live verification evidence:

- Full Step-1 run:
  - [u_001-012](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-012)
  - [apply_result.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-012/apply_result.json)
  - [measurement_verification.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-012/measurement_verification.json)
  - [save_outputs.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/u_001-012/save_outputs.json)
- One-field batch:
  - [summary.json](c:/D-drive-data/mirra-mvp/clo_avatar_generation/output/field_probes_20260407/summary.json)

What this tells us:

- We now have a Step-1 route that is verified by the saved avatar itself, not by weak plugin readback.
- The current working implementation path is:
  - start from `base-1.avt`
  - patch the verified AVT feature values in `cm`
  - import the patched avatar into a fresh CLO project
  - export/save the result
- This route is stronger than both current alternatives:
  - the CSV import path still fails
  - the avatar-property path still accepts requests without changing body measurements

## Findings From The Live Windows Plugin

Source file:

- [RestPlugin_windows.cpp](c:/D-drive-data/mirra-mvp/clo_workspace/windows/RestPlugin_windows.cpp)

Currently available measurement-related behavior:

- `POST /import-avatar-avt`
  - imports the base `.avt`
- `POST /import-avatar-measurements`
  - queues measurement apply
- inside the queue processor, the plugin uses:
  - `ImportAvatarMeasurement(csvPath, avtPath, options)` when `template_path` is provided
  - `ImportMeasurement(csvPath)` when `template_path` is empty
- `GET /avatars/state`
  - reads current avatar properties through `GetAvatarProperties(...)`

What the live plugin state proved on 2026-04-07:

- base avatar import succeeds
- arrangement slots exist after avatar import
- measurement CSV import fails even with the repo template used unchanged
- readable avatar properties are currently generic simulation/render properties, not body measurements

## Findings From The Local Windows SDK

SDK root configured locally:

- `C:/Users/Saumy/Downloads/CLO_SDK_v2025.2.368_Win`

Important SDK findings:

- `ImportAPIInterface.h` contains:
  - `ImportAvatarMeasurement(std::string csvPath, std::string avtPath, ImportExportOption opt)`
  - `ImportMeasurement(std::string csvPath)`
- `UtilityAPIInterface.h` contains:
  - `SetAvatarProperties(unsigned int avatarIndex, const std::map<std::string, std::string>& avatarPropertyMap)`
  - `GetAvatarProperties(unsigned int avatarIndex)`
- `ExportAPIInterface.h` contains:
  - `ExportAVT(const std::string& filePath)`

What this means:

- A JSON/property-based experimental plugin route is technically possible.
- A direct `.avt` save route is also technically possible in the Windows SDK.
- Neither one is proven yet in our plugin until we expose and test them.

## Current Conclusion

- The existing CSV bridge should now be treated as `unverified and likely unsuitable in its current form`.
- The failure is not limited to:
  - sending too many fields
  - the specific `u_001` values
  - runtime overrides only
- The repo CSV template itself is not accepted by the live import path.

## Next Steps

1. Keep the existing CSV methods in the repo for reference and comparison.
2. Add an experimental Windows plugin endpoint for direct JSON/property updates.
3. Install the rebuilt Windows plugin DLL into CLO and restart CLO.
4. Use the JSON/property endpoint first with safe observable properties to prove the route works technically.
5. Then test body-related keys one field at a time, using `cm` values.
6. Only remove failed or redundant methods after one method is fully verified.

## Removal Rule

Do not remove any existing approach until one method is:

- fully working
- repeatable
- clearly better than the alternatives

Until then, this file should keep a running list of:

- method name
- transport path
- plugin call used
- result
- evidence
- conclusion
