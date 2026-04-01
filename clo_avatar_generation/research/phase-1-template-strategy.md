# Phase 1 Template Strategy

## Goal

Lock the first testing strategy for the CLO-native avatar path without changing the existing STAR path or current VTO runtime.

## Locked decisions

### 1. CLO version family

For Phase 1 we keep the target version family recorded as:

- `2025.x`

This is intentionally broad in the code scaffold because the exact local installed build may vary slightly across machines. In Phase 2, once a real test template is selected, this should be tightened to the exact installed CLO version.

### 2. Avatar families to support first

The first two avatar families to support are:

- `male`
- `female`

These are treated as the minimum viable comparison set for the CLO-native lane.

### 3. Candidate source modes

The locked candidate modes are:

1. `default_clo_avatar`
2. `converted_size_editable_avatar`
3. `converted_custom_shape_avatar`

### 4. Preferred first test mode

The preferred first test mode is:

- `default_clo_avatar`

Reason:

1. it is the most native CLO path
2. it minimizes ambiguity during the first import experiments
3. it gives the cleanest baseline before testing conversion tradeoffs

### 5. Required reference templates in Phase 1

Phase 1 requires:

- one reference template for male
- one reference template for female

The actual `.avt` files do not need to be committed yet in Phase 1, but the registry and folder structure must be ready for them.

## What Phase 1 does not decide yet

Phase 1 does not yet lock:

1. the exact `.avt` files
2. the final measurement CSV format
3. the Mirra-to-CLO measurement mapping
4. whether the final winning CLO path will be default, size-editable, or custom-shape converted

Those belong to later phases after actual template inspection and import testing.

## Why this structure is removable

This experiment is intentionally isolated.

If this path is rejected later, cleanup should mostly mean:

1. delete `clo_avatar_generation/`
2. remove additive plugin extensions related only to the native path

This is why Phase 1 stores only isolated metadata and docs here, and does not modify existing runtime logic.

