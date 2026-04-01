# Phase 3 Mirra-to-CLO Mapping

## Goal

Translate the current Mirra measurement schema into the best currently known CLO-native measurement targets without changing any existing Mirra data logic.

This phase is a mapping-definition phase only.

It does not:

1. rewrite `mirra_measurements/`
2. create measurement CSV files
3. import anything into CLO

## Current Mirra input fields

From the current repo, Mirra currently uses these important body fields:

- `height_cm`
- `weight_kg`
- `shoulder_width_cm`
- `waist_circumference_cm`
- `hip_circumference_cm`
- `leg_length_cm`
- `chest_circumference_cm` for male flows
- `bust_circumference_cm` for female flows
- `under_bust_circumference_cm` for female flows
- optional:
  - `body_shape_type`
  - `skin_tone_hex`

## Current mapping position

### Strong direct candidates

These are the safest current mapping candidates from public CLO documentation:

- `height_cm` -> `Total Height`
- `weight_kg` -> `Weight`
- `waist_circumference_cm` -> `Waist`
- `bust_circumference_cm` -> `Bust`
- `under_bust_circumference_cm` -> `Under Bust`

### Likely derived candidates

- `hip_circumference_cm` -> `Low Hip`
- `leg_length_cm` -> `Inseam`

These are plausible but still depend on exact measurement-definition alignment.

### Currently blocked candidates

- `shoulder_width_cm` -> likely `Across Shoulder (Curvilinear)` or similar
- `chest_circumference_cm` for male flows -> exact male template field still needs confirmation

These are important fields, but the exact target names and import headers are still not confirmed from a real template.

### Not measurement-import targets

- `skin_tone_hex`
- some parts of `body_shape_type`

These do not belong in the measurement-import lane and should remain separate.

## Key design rule for this phase

We are not forcing Mirra to rename its schema to match CLO.

Instead, this experiment introduces a translation layer:

- Mirra remains the source schema
- CLO receives a mapped profile

That keeps cleanup easy later if the CLO-native path is removed.

## Major unresolved questions

1. What exact male chest field exists in the chosen CLO template?
2. What exact shoulder-related field should Mirra shoulder width map to?
3. What exact import names appear in the measurement CSV?
4. Which documented guide-visible fields are actually editable in the chosen template?

## Deliverables stored in code

Phase 3 stores the mapping definitions in:

- `clo_avatar_generation/measurement_mapping.py`

That file now separates:

1. direct candidates
2. derived candidates
3. approximation candidates
4. blocked mappings

## What the next phase will do

The next coding phase can build on this by:

1. defining run contracts and bundle structure for a CLO-native input package
2. preparing for CSV generation once the schema is confirmed
3. keeping all of that inside `clo_avatar_generation/`

