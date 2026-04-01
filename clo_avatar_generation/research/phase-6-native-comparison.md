# Phase 6 Native Comparison

## Goal

Create an isolated comparison harness for the CLO-native avatar lane so we can:

1. import a native `.avt`
2. import a measurement CSV
3. inspect arrangement availability
4. optionally load panel DXF files
5. write a report without touching the default VTO lane

## What was added

### Runner

- `run_clo_vto.py`

This is now the isolated comparison entrypoint for the CLO-native lane.

### Reporting helper

- `reporting.py`

### Client and importer upgrades

- `adapters/clo_native_client.py`
- `adapters/clo_native_importer.py`

These now support:

- new project
- queue waiting
- native avatar import
- native measurement import
- optional pattern import
- arrangement-list querying
- pattern-arrangement querying
- native debug querying

### Plugin-side debug enrichment

The native debug endpoint now also reports:

- pattern count
- arrangement slot count
- pattern arrangement count
- slot names when available

## What this phase still depends on externally

This harness still requires real runtime assets to be useful:

1. a valid `.avt`
2. a valid measurement CSV
3. optionally a valid panel DXF directory
4. a built and loaded plugin with the new additive endpoints
5. CLO running locally

## What this phase does not do

1. It does not alter the existing `vto/run_vto.py`.
2. It does not change the default OBJ avatar lane.
3. It does not decide the winner between STAR and CLO-native paths.

