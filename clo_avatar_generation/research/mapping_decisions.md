# Mapping Decisions

## Purpose

This file records the current decision status of Mirra-to-CLO field mapping in plain language.

## Current decision summary

### High-confidence direct mappings

- `height_cm` -> `Total Height`
- `weight_kg` -> `Weight`
- `waist_circumference_cm` -> `Waist`
- `bust_circumference_cm` -> `Bust`
- `under_bust_circumference_cm` -> `Under Bust`

### Medium-confidence derived mappings

- `hip_circumference_cm` -> `Low Hip`
- `leg_length_cm` -> `Inseam`

### Mappings blocked by missing template evidence

- `shoulder_width_cm` -> likely a shoulder control such as `Across Shoulder (Curvilinear)`
- `chest_circumference_cm` -> exact male chest target still unknown

### Fields outside the measurement-import lane

- `skin_tone_hex`
- appearance-related traits

## Why this is still only a draft

These decisions are based on:

1. public CLO support docs
2. guide-visible measurement names
3. current Mirra schema

They are not yet based on:

1. a real `.avt` template inspection
2. a real import CSV sample

So this file should be treated as the current best mapping position, not final truth.

