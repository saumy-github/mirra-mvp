# Phase 2 Measurement Inventory Notes

## Goal

Build a repo-local record of:

1. which CLO measurement controls are already confirmed by public documentation
2. which fields are only visible in guides or screenshots
3. which fields still need template confirmation from a real `.avt`
4. what still blocks implementation of CSV import

This phase does not yet generate CSV files or import them into CLO.

## Confirmed from public documentation

### Size-basis controls

- `Bust`
- `Under Bust`
- `Weight`
- `Total Height`
- `HPS Height`
- `Inseam`

### Detailed groups

- `Circumference`
- `Height`
- `Length`

### Documented movable regions

- `Under Bust`
- `Waist`
- `High Hip`
- `Low Hip`
- `Thigh`

### Documented additional controls

- `Cup Size`
- `Hands & Head`
- `Crotch Gap`
- `Crotch Volume` for male avatars
- `Breast Shape`
- `Breast Space`
- `Breast Height`
- `Hip Dips`
- `Hip Volume`

## Visible in official guides but still needing exact template confirmation

- `Neck Base`
- `Bicep`
- `Across Shoulder (Curvilinear)`
- `Arm`

These are strong candidates for later Mirra-to-CLO mapping, but the exact editability and import naming still need to be verified from a real template.

## What this means for Mirra

### Strong direct candidates

- height
- waist
- hip / low hip
- bust and under bust for female flows
- weight if needed by the chosen template strategy

### Likely derived or approximate candidates

- shoulder-related fields
- neck-related fields
- arm length and arm circumference fields
- thigh and other regional fields not currently supplied by the user

## Current unresolved blockers

1. We do not yet have the exact CSV schema for `ImportAvatarMeasurement`.
2. We do not yet have the exact editable field list for the chosen male template.
3. We do not yet have the exact editable field list for the chosen female template.
4. We do not yet know the exact import header names for shoulder and arm-related fields.

## Phase 2 deliverables now stored in this folder

- code-level inventory scaffold in `measurement_inventory.py`
- schema placeholder in `schema/measurement_csv_schema.md`
- this summary note

## What remains manual for the next step

The next real confirmation step must be done against an actual CLO installation and template:

1. open the chosen avatar template
2. enable all detailed measures
3. record the exact editable fields
4. obtain or export a real measurement CSV example

