# 010 Plan: Plugin Build System, Versioning, and Cross-Platform Sync

## Purpose

Create a proper plugin build and release-management system for the CLO plugin so
that:

1. team members do not need to remember machine-specific SDK/build paths
2. plugin rebuild requirements are visible and easy to verify
3. Windows and Mac plugin behavior can be kept in sync
4. unstable plugin versions can be blocked from normal team use
5. plugin metadata can be checked from both the repo and the running CLO plugin

This plan is about plugin infrastructure and release discipline, not about
adding new CLO endpoints.

## Current Problems This Plan Solves

### 1. Build inputs are too manual

Right now, rebuilding the plugin requires knowing machine-specific details such
as:

1. CLO SDK root path
2. CLO plugin install path
3. CMake location
4. Visual Studio generator/version
5. platform-specific build expectations

These are currently partly hardcoded, partly tribal knowledge.

This plan must explicitly remove that pattern from the active
`clo_workspace/plugins/` build flow.

### 2. Plugin versioning is not real yet

The plugin currently reports a static version like `1.0`, plus a build
timestamp. That is not enough to tell:

1. whether the installed DLL matches the latest repo changes
2. whether a rebuild is required
3. whether Windows and Mac are aligned
4. whether the current version is safe to install

### 3. Windows and Mac can drift silently

As plugin functionality grows, there is a risk that:

1. Windows exposes endpoints that Mac does not
2. response payloads differ by platform
3. one platform has bug fixes the other does not
4. team members assume parity that does not actually exist

### 4. There is no release-state control

If the latest plugin change is broken, there is no clear repo-level signal such
as:

1. `stable`
2. `unstable`
3. `blocked`

So teammates may rebuild and install a bad plugin version accidentally.

## High-Level Direction

The plugin system should move to this model:

1. one shared build configuration source
2. one shared plugin version/manifest source
3. one shared release-state source
4. health metadata returned by the plugin at runtime
5. one cross-platform parity contract for endpoints and behavior

This should make the plugin feel like a proper product artifact, not a local
one-off DLL build.

## Core Decisions Locked For This Plan

### 1. Add `.env` and `.env.example`

The build should no longer depend on hardcoded machine-specific paths.

We will introduce:

1. repo-level `.env.example`
2. local `.env`

These will define the values needed to build and install the plugin on each
machine.

This is not optional layering on top of the current hardcoded setup.

The existing hardcoded machine-specific values inside `clo_workspace/`,
especially under `clo_workspace/plugins/`, must be removed or replaced with:

1. env-driven values
2. shared manifest/config-driven values
3. validated fallbacks only where truly necessary

Hardcoded developer-specific paths must not remain as the primary build path.

### 2. Track plugin version in one repo file

We will add one source-of-truth version file that contains:

1. plugin version
2. release date
3. build metadata fields
4. current release status
5. changes for that version
6. platform sync status

### 3. Keep Windows and Mac behavior in sync

We will define a shared plugin contract so that both Windows and Mac builds are
expected to expose the same runtime behavior unless explicitly marked otherwise.

### 4. No previous-version download system

We are not building a full old-version artifact archive system.

The intended usage remains:

1. keep your currently installed plugin
2. or install the latest allowed plugin

This plan is about version tracking and release-state control, not binary
artifact storage.

## Main Deliverables

### Deliverable A: Build Configuration Files

Add:

1. `.env.example`
2. `.env`

Expected configuration categories:

1. CLO SDK root
2. CLO plugin install directory
3. CMake executable or directory
4. generator/toolchain
5. build config
6. platform identifier
7. plugin port if configurable

These values should support both Windows and Mac usage patterns.

This deliverable also requires cleanup of the current hardcoded values in:

1. `clo_workspace/plugins/build_rest_plugin.bat`
2. `clo_workspace/plugins/BUILD_GUIDE.md`
3. `clo_workspace/plugins/BUILD_INSTRUCTIONS.md`
4. any other plugin build/install helper under `clo_workspace/plugins/`

Those files should no longer rely on developer-specific paths as the normal
documented flow.

### Deliverable B: Shared Plugin Version / Manifest File

Add one version/manifest file, for example under:

1. `clo_workspace/plugins/plugin_version.json`
2. or `clo_workspace/plugins/plugin_manifest.json`

This file should include:

1. `plugin_version`
2. `api_version`
3. `release_date`
4. `status`
5. `platforms`
6. `changes`
7. `notes`

Suggested `status` values:

1. `stable`
2. `unstable`
3. `blocked`

Suggested platform states:

1. `in_sync`
2. `pending`
3. `diverged`
4. `untested`

### Deliverable C: Shared Build Entry Point

Replace the “remember everything manually” approach with one shared build entry
point.

Preferred direction:

1. a shared Python build script that reads `.env`
2. optional platform wrappers that call that script

This script should:

1. detect platform
2. load and validate environment values
3. resolve the correct SDK paths
4. resolve the correct toolchain/generator
5. run the build
6. tell the user exactly where the resulting plugin binary is
7. optionally print the install step

This deliverable must also demote the old hardcoded scripts to one of these
states:

1. thin wrappers around the shared build entry point
2. compatibility wrappers that read env/config values
3. deprecated scripts clearly marked as legacy

They must not continue to be the main source of hardcoded SDK/build/install
logic.

### Deliverable D: Runtime Health Metadata

The plugin `/health` response should expose enough metadata to verify that the
installed plugin matches the repo’s expected state.

At minimum it should report:

1. plugin name
2. plugin version
3. api version
4. release status
5. build timestamp
6. platform
7. maybe compatibility or manifest revision

This should be sourced from the shared version/manifest information, not from a
separate hardcoded version string.

### Deliverable E: Cross-Platform Parity Contract

Define one shared parity contract for Windows and Mac plugin behavior.

This should include:

1. endpoint list
2. request schema expectations
3. response schema expectations
4. capability flags
5. known platform exceptions if any

This contract should be stored in a repo file and used as the reference point
for both builds.

## Recommended File Structure

Suggested additions:

1. `clo_workspace/plugins/.env.example`
2. `clo_workspace/plugins/plugin_version.json`
3. `clo_workspace/plugins/plugin_contract.json`
4. `clo_workspace/plugins/build_plugin.py`
5. optional:
   - `build_plugin.bat`
   - `build_plugin.sh`
   as thin wrappers only

The wrappers should not carry build logic themselves if the shared Python build
entry point exists.

## What The Version File Should Track

The version file should answer these questions clearly:

1. what version is current?
2. when was that version released?
3. is it safe for the team to install?
4. what changed in this version?
5. is Windows in sync with Mac?
6. does this version require a rebuild after source changes?

Suggested change sections:

1. `added`
2. `changed`
3. `fixed`
4. `resolved`
5. `known_issues`

This should be written for team clarity, not only machine consumption.

## What The Build Config Should Track

The build config should contain only machine-specific or environment-specific
values, such as:

1. `CLO_SDK_PATH`
2. `CLO_PLUGINS_DIR`
3. `CMAKE_EXE`
4. `VS_GENERATOR`
5. `BUILD_CONFIG`
6. `PLUGIN_PORT`
7. `PLUGIN_PLATFORM`

It should not contain:

1. repo version information
2. endpoint contracts
3. change logs

Those belong in tracked repo files, not local environment config.

Developer-specific absolute paths must be treated as local environment data,
not as repo-owned build logic.

## Health / Verification Flow

After implementation, the ideal verification flow should be:

1. check repo version file
2. build plugin using env-driven build script
3. install plugin
4. start CLO
5. call `/health`
6. compare:
   - plugin version
   - status
   - platform
   - api version
7. confirm the running plugin matches the repo expectation

This should make it obvious when someone forgot to rebuild after a plugin code
change.

## Release-State Rules

The repo should clearly communicate whether the newest plugin should be used.

Suggested rules:

### `stable`

Meaning:

1. latest recommended version
2. safe for normal team install/rebuild

### `unstable`

Meaning:

1. active development version
2. may be used by testers
3. should not be treated as team-safe default

### `blocked`

Meaning:

1. known issue exists
2. teammates should not rebuild/install this latest version for normal use

The build output or docs should surface this status clearly.

## Windows / Mac Sync Rules

To keep parity manageable, we should explicitly define what “in sync” means.

Suggested definition:

Windows and Mac are in sync when they share:

1. the same `plugin_version`
2. the same `api_version`
3. the same endpoint list
4. the same request/response schema contract
5. the same capability flags

If one platform is missing or lagging:

1. it must be marked in the version/manifest file
2. that mismatch must be visible to the team

## Build Script Responsibilities

The shared build script should:

1. load `.env`
2. validate required config values
3. resolve current platform
4. load plugin version/manifest info
5. confirm release status
6. print what is being built
7. copy source files into the SDK sample/plugin build location
8. run configure/build steps
9. print resulting binary path
10. print install guidance

Optional later:

1. auto-copy after explicit confirmation
2. verify installed plugin matches built plugin

## Documentation Updates Required

The docs should be updated so a new teammate can answer these without asking
someone else:

1. where is the CLO SDK?
2. how do I configure my machine?
3. how do I build the plugin?
4. how do I install the plugin?
5. how do I know whether I need to rebuild?
6. how do I know whether the current version is blocked?
7. how do I know whether Windows and Mac are in sync?

The documentation update is not complete unless the old hardcoded examples in
`clo_workspace/` are cleaned up or clearly marked as legacy.

## Phase Plan

### Phase 1: Define Plugin Metadata

Build:

1. plugin version file
2. release status fields
3. change sections
4. platform sync fields

### Phase 2: Define Plugin Contract

Build:

1. plugin contract file
2. endpoint list
3. request/response expectations
4. capability flags

### Phase 3: Add Environment-Based Build Config

Build:

1. `.env.example`
2. env loading strategy
3. machine-specific build configuration separation
4. removal of hardcoded machine-specific defaults from the active
   `clo_workspace/plugins/` build flow

### Phase 4: Create Shared Build Entry Point

Build:

1. one shared build script
2. Windows/Mac branching inside the script
3. config validation
4. clean output messages
5. migration of old hardcoded scripts into wrappers or legacy status

### Phase 5: Connect Runtime Metadata

Build:

1. `/health` metadata from shared version info
2. maybe `/capabilities` metadata alignment
3. clearer rebuild verification path

### Phase 6: Update Team Docs

Build:

1. updated build guide
2. updated plugin status guidance
3. how to know whether rebuild is required
4. how to know whether a version is blocked

## Success Criteria

This plan is complete when:

1. a teammate can configure their machine using `.env.example`
2. plugin build inputs are no longer hardcoded in build scripts
3. the plugin reports real version/status metadata at runtime
4. the repo clearly marks whether the latest plugin is stable or blocked
5. the repo clearly marks Windows/Mac sync state
6. the team no longer has to remember SDK/generator/install details manually
7. active build scripts in `clo_workspace/` no longer depend on hardcoded
   developer-specific paths as the default behavior

## Notes

This plan does not require:

1. keeping downloadable old plugin binaries
2. supporting rollback artifacts inside the repo
3. implementing every future Mac build detail immediately

The first goal is to establish:

1. one shared build configuration pattern
2. one shared versioning pattern
3. one shared contract pattern

Then platform parity can be maintained with much less confusion.
