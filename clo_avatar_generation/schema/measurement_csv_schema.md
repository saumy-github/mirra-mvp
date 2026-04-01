# Measurement CSV Schema

## Purpose

This document tracks the exact CSV schema required by CLO for avatar measurement import.

## Current status

Status: `unconfirmed`

What is known:

1. Public CLO developer docs list:
   - `ImportAvatarMeasurement(csvPath, avtPath, opt)`
   - `ImportMeasurement(csvPath)`
2. Public docs confirm that a measurement CSV import path exists.
3. Public docs do not clearly publish the exact CSV header schema in one place.

## What must be confirmed in Phase 2

Before coding the CSV builder, we must capture from a real template or SDK sample:

1. file encoding
2. delimiter
3. whether there is a unit row
4. whether one row contains one avatar profile or multiple size rows are allowed
5. exact column names
6. whether family-specific fields use different headers
7. whether optional fields can be omitted or must be blank-filled
8. whether the avatar must already be loaded before `ImportMeasurement(csvPath)` is called
9. whether `ImportAvatarMeasurement(csvPath, avtPath, opt)` expects a different structure from `ImportMeasurement(csvPath)`

## Placeholder schema shape

The final schema is expected to look something like:

```csv
field_a,field_b,field_c
value_a,value_b,value_c
```

But this is only a placeholder. The real schema must be captured from an actual CLO-compatible example before Phase 4 coding begins.

## Required evidence to store in repo later

When the exact schema is discovered, this document should be updated with:

1. an exact sample header
2. example values
3. notes on required versus optional fields
4. the source of truth used to derive it

