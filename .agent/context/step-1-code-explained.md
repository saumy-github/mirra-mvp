# Step 1 Code Explained: pipeline_star Folder

## Purpose of this folder

The pipeline_star folder is the implementation backbone of MVP Step 1: generating a reusable 3D digital twin avatar from user measurement data.

At a high level, this folder does five things:

1. Pulls a user measurement profile from MongoDB.
2. Converts that profile into fitting targets and run configuration artifacts.
3. Fits STAR body shape parameters so the generated body approximates those targets.
4. Produces a final mesh and exports it as files that downstream systems can use.
5. Writes structured artifacts so each run is auditable and reproducible.

This folder is therefore both a compute pipeline and an operational record system.

## How Pipeline Runs

Your team runs one command:

python pipeline_star/run_avatar_pipeline.py

From that moment, the runtime flow is:

1. Interactive launcher starts.
The command enters the interactive wrapper, which is the operational front door for the Step 1 pipeline.

2. User ID is collected from terminal input.
The script waits for an operator to type a user ID and does not proceed with empty input.

3. MongoDB existence check happens immediately.
It verifies that a measurement document exists for that user. If no document exists, the run exits early with a clear error message.

4. Next run number is auto-discovered.
The script scans prior generated artifacts and calculates the next available run index for that user so run naming remains sequential and consistent.

5. Operator confirms run number.
The default suggestion is shown in terminal, but the operator can override with a custom run number.

6. Operator selects pose mode.
The script asks for pose selection and supports current allowed values. If nothing is entered, the default pose is applied.

7. Launcher spawns the orchestrator process.
After gathering all runtime inputs, the wrapper starts the main pipeline controller with normalized arguments.

8. Runtime device is logged.
At orchestrator startup, the system resolves and prints hardware device selection order so operators can see whether the run is using accelerator hardware or CPU fallback.

9. Measurement document is fetched again in orchestrator context.
The orchestrator reads the user measurement record as the source of truth for fitting and artifact generation.

10. Required-field validation runs.
The pipeline checks whether mandatory profile fields are present, including gender-specific requirements.

11. Plausibility-range validation runs.
All configured numeric measurements are checked against expected human-range limits. If values are out of range, the run fails fast with explicit reasons.

12. Mapping layer builds run identity.
The run identity is created from user ID plus run number and becomes the canonical naming key for all output files.

13. Mapping layer creates fitting targets.
The source profile is converted into the optimizer target set used for shape fitting. This includes current MVP mapping decisions such as chest-target handling.

14. Mapping layer builds run config payload.
Tolerance threshold, gated fields, validate-only fields, and fitter options are bundled into config metadata.

15. Inputs artifact is written.
The pipeline writes an inputs JSON file containing:
source snapshot, derived targets, and run configuration used for this run.

16. Beta fitting begins.
The fitting module starts from initial shape parameters and iteratively updates them to minimize weighted relative measurement error.

17. Scale estimation is applied when enabled.
Before iterative optimization, global scale is aligned to target height so fitting starts closer to feasible shape dimensions.

18. Repeated predict-and-evaluate cycle runs.
Each iteration generates a mesh from current parameters, extracts predicted measurements, computes loss terms, and updates parameters.

19. Convergence or max-iteration stop condition is reached.
The optimizer stops when improvement falls below threshold for enough iterations, or when configured iteration ceiling is reached.

20. Predicted measurement report is finalized.
After optimization, the pipeline computes final predicted values and per-field error percentages against targets.

21. Fitness gate is evaluated.
The maximum measurement error is compared against tolerance. Run status is marked passed or failed.

22. Pose vector is resolved.
The requested pose mode is converted into final theta values used for mesh generation and persisted to artifacts.

23. Values artifact is written.
A values JSON file is generated containing:
status, fitted parameters, pose metadata, fit report, error percentages, and pointer to inputs artifact.

24. Final mesh is generated for export.
The STAR runner generates the final posed mesh using fitted shape parameters, selected pose, and scale.

25. Post-processing and integrity checks run.
Mesh arrays are validated for shape and numeric validity before export to reduce downstream import issues.

26. GLB export is produced.
The final avatar mesh is exported as GLB with configured mannequin material properties for standard 3D usage.

27. CLO export bundle is produced.
The same mesh is also exported for CLO workflows, including OBJ geometry and sidecar metadata files.

28. Terminal summary is printed.
The orchestrator prints a run summary showing pass or fail status, key errors when failed, and list of generated files.

29. Important behavior on failed fit.
Even when the fit gate fails, export artifacts are still generated. This enables visual inspection and debugging without rerunning the entire pipeline just to inspect geometry.

30. Artifacts become the run record.
At completion, generated files represent the canonical evidence of what data was used, what fitting result occurred, and what avatar outputs were produced for that run.

In short, this single command triggers a complete pipeline lifecycle: operator input, data validation, target derivation, optimization, quality gating, multi-format export, and traceable artifact logging.

## End-to-end flow in plain language

The flow starts at an interactive CLI, asks for user identity and run settings, and then calls the main orchestrator.

Inside the orchestrator, execution proceeds in five stages:

1. Input mapping stage:
The user profile is fetched and validated, then written to an inputs artifact containing the source snapshot, derived fitting targets, and run configuration.

2. Shape fitting stage:
The fitting module optimizes STAR betas to reduce measurement error against the target values.

3. Fitness gate stage:
Predicted measurements are compared to targets, error percentages are calculated, and pass or fail status is determined using the configured tolerance.

4. Values artifact stage:
A second artifact is written containing model parameters, pose, fit report, and status.

5. Export stage:
The final mesh is generated and exported to GLB for general use and OBJ plus metadata files for CLO workflows.

Important behavior detail:
Export still happens even when the fit gate fails. This is intentional so failed runs can be inspected and debugged.

## Primary entrypoints and orchestration files

### run_avatar_pipeline.py

This is the interactive command-line wrapper used by humans.

Responsibilities:

1. Prompt for user ID.
2. Verify that user exists in MongoDB.
3. Auto-detect next run number by scanning existing generated artifacts.
4. Let operator confirm run number or enter a custom one.
5. Let operator select pose mode.
6. Invoke the main orchestrator process with normalized arguments.

Operational value:
It removes manual run-number bookkeeping and reduces user error for routine pipeline execution.

### first.py

This is the core orchestrator and operational controller for all modes.

Supported modes:

1. validate_only:
Only validation and summary display.

2. star_preflight:
Loads STAR and generates a test mesh to verify model readiness.

3. fit_betas:
Runs optimization and prints before-after measurement comparison.

4. generate_avatar:
Runs the full production path with artifact writing and mesh export.

Key orchestration responsibilities:

1. Calls the mapping layer.
2. Calls beta fitting.
3. Evaluates tolerance gate.
4. Creates values schema payload.
5. Generates posed mesh and post-processes it.
6. Exports GLB and CLO outputs.
7. Prints detailed success or failure terminal summary.

This file is the single source of truth for run sequencing and operator-facing status output.

### run_manifest.py

Defines canonical run identity and deterministic file paths.

Responsibilities:

1. Encodes run ID format using user ID plus zero-padded run number.
2. Provides canonical paths for inputs artifact, values artifact, and avatar GLB.
3. Centralizes generated directory resolution.

Why this matters:
Consistent naming prevents drift across modules and keeps run artifacts easy to trace.

## STAR model execution and compute core

### star_runner.py

This module is the STAR runtime adapter.

Current implementation profile:

1. Uses PyTorch STAR backend from local STAR library.
2. Selects runtime device from shared device utility.
3. Caches model instances by gender and beta-count to avoid reloading cost.
4. Supports both single-sample and batched generation.
5. Normalizes input shapes for betas, pose, and translation.
6. Runs inference in no-gradient mode.
7. Returns vertices on CPU as standard arrays with cached faces.

Additional design detail:
The internal cache is intentionally non-thread-safe and currently tuned for single-process CLI usage.

### utils/device.py dependency used by this folder

The runtime device policy is defined outside this folder in utils and consumed by pipeline_star.

Policy order:

1. CUDA
2. MPS
3. CPU

Effect on pipeline behavior:
The same command can run across different hardware without changing user workflow.

## Measurement extraction and fitting logic

### mesh_measure.py

This module converts mesh geometry into measurement estimates.

Measurement strategy used:

1. Height from vertical range.
2. Shoulder width by landmark method when joint regressor is available.
3. Chest, waist, and hip circumference by horizontal band sampling and ellipse approximation.

Important nuance:

1. A fallback shoulder method still exists that estimates width from horizontal x-range in a band.
2. The preferred path is anatomical shoulder landmarks with the STAR joint regressor.

This module is foundational because fitting quality depends on how target and predicted measurements are computed.

### fit_betas.py

This module performs optimization from target measurements to STAR shape parameters.

Current optimizer profile:

1. Initializes betas at zero.
2. Optionally estimates global scale from target height.
3. Computes weighted relative-error loss plus beta regularization.
4. Uses finite-difference gradient descent with fixed hyperparameters.
5. Tracks convergence by loss-change threshold and patience.
6. Returns fitted betas, scale, loss history, predicted measurements, and iteration count.

Loss design implications:

1. Uses relative error so metrics are normalized across measurement magnitudes.
2. Includes regularization to limit extreme beta drift.

Operational caveat:
This module still contains hardcoded model-path assumptions for loading joint regressor, which can cause portability issues if environment paths differ.

## Data mapping, schemas, and artifact lifecycle

### mapping_layer.py

This module bridges MongoDB measurement documents into pipeline-ready artifacts and fitting targets.

Core responsibilities:

1. Fetches user measurement document.
2. Validates required fields with gender-aware logic.
3. Applies plausible-range validation checks.
4. Creates derived fitting targets used by optimizer.
5. Builds run configuration payload.
6. Sanitizes source snapshot for JSON compatibility.
7. Writes the inputs artifact.

Notable design choices:

1. Female path maps bust to chest fitting target in current MVP logic.
2. Some fields are intentionally validate-only and excluded from optimization.

### artifact_schema.py

Defines canonical data contracts for pipeline artifacts.

It establishes:

1. Which fields are gated for fit tolerance.
2. Which fields are validate-only.
3. Global tolerance percent used for pass/fail.
4. Shape of inputs artifact and values artifact payloads.

This file is the contract layer that keeps producer and consumer expectations aligned.

### artifact_io.py

Handles deterministic JSON writing and serialization normalization.

Responsibilities:

1. Converts arrays and numeric scalar types into JSON-safe forms.
2. Writes sorted, indented UTF-8 JSON with stable formatting.
3. Validates allowed run status values before values artifact write.
4. Generates UTC timestamp strings.

Result:
Artifacts are predictable for humans, scripts, and diff-based review.

## Export and styling modules

### avatar_exporter.py

Provides GLB export with optional material configuration.

Responsibilities:

1. Validates mesh array shapes.
2. Applies optional PBR material properties.
3. Exports GLB via trimesh.

### avatar_exporter_clo.py

Adds CLO-oriented export path and rich sidecar outputs.

Responsibilities:

1. Exports OBJ with centimeter scaling for CLO compatibility.
2. Supports normals and optional UV generation.
3. Writes measurement JSON sidecar.
4. Writes human-readable info sidecar.
5. Keeps backward-compatible GLB export helper.

Design relevance:
This module is the bridge from Step 1 avatar generation into clothing design and simulation workflows.

### avatar_style.py

Defines mannequin visual style metadata and material properties.

Current style intent:

1. Textureless mannequin appearance.
2. Fixed skin-tone base color.
3. PBR properties tuned for non-metallic matte look.

This aligns with MVP direction where fit visualization is prioritized over photoreal skin detail.

## Pose and postprocess support

### pose_catalog.py

Central catalog for pose vectors and pose metadata.

Current capabilities:

1. T-pose support.
2. A-pose support via shoulder angle modifications.
3. Pose selector utility for runtime mode.
4. Metadata payload for traceability in values artifact.
5. Backward compatibility wrappers for older function naming.

### mesh_postprocess.py

Provides conservative post-processing with strong validation and minimal mutation.

Current behavior:

1. Optional array validity checks.
2. Optional recentering.
3. Placeholder for future smoothing behavior.

Why conservative mode matters:
It lowers the chance of introducing geometric side effects before export.

## Utility and maintenance tools in this folder

### clear_generated.py

Interactive cleanup tool for generated artifacts.

Behavior:

1. Lists removable generated files except repository keep-file.
2. Requires explicit confirmation.
3. Deletes files to reset run state.

### diagnose_shoulder.py

Diagnostic script focused on shoulder-width discrepancy analysis.

Purpose:
Explains how band-based width can include arm contribution and inflate shoulder estimate.

### inspect_star_joints.py

Inspection script for STAR model internals and likely joint mapping references.

Purpose:
Helps verify shoulder landmark assumptions and debugging context for measurement logic.

### test_shoulder_landmarks.py

Comparison script between old shoulder method and landmark-based method.

Purpose:
Demonstrates expected error reduction when anatomical landmarks are used.

### A_POSE_CONVERSION_PLAN.md

Planning document describing minimal-change strategy for adding pose options while preserving default behavior.

Role in folder:
Acts as implementation intent and rationale for pose evolution.

## Generated artifacts: what they contain and why they matter

This folder stores run outputs under generated.

Primary artifacts per run:

1. inputs file:
Contains source snapshot, derived targets, and run config used to fit.

2. values file:
Contains fitted parameters, pose, fit report, and pass or fail status.

3. GLB file:
Avatar mesh for visualization and downstream integration.

4. CLO outputs:
OBJ plus metadata sidecars for CLO workflows.

Why this artifact set is strong:

1. Inputs and values provide reproducibility.
2. Export files provide practical interoperability.
3. Failed runs still preserve debugging evidence.

## Current strengths of this Step 1 implementation

1. Clear stage orchestration from mapping to export.
2. Deterministic artifact naming and schema contracts.
3. Interactive run management for operators.
4. Hardware-aware STAR runtime path.
5. Rich diagnostic utilities for known weak points.
6. Dual export strategy for GLB and CLO ecosystems.

## Current constraints and risk points observed

1. Shoulder fit remains a sensitive area despite landmark improvements; this requires continued validation across users.
2. fit_betas includes environment-specific model path logic for regressor loading that can break on different machines.
3. Optimization method is finite-difference based and can be comparatively slow for larger scaling scenarios.
4. Some modules include absolute path assumptions in diagnostics, reducing portability.
5. Thread safety is not designed for concurrent service usage yet due to mutable model cache.

## How this folder maps to MVP Step 1 objectives

MVP Step 1 requires a persistent, measurement-driven digital twin that is reusable across sessions.

This folder directly satisfies that requirement by:

1. Using measured user data as fitting targets.
2. Producing a stable run identity and file outputs.
3. Persisting artifacts that can be linked back to user and run.
4. Exporting geometry in formats usable by later try-on and garment systems.

## Practical mental model for future contributors

If someone new opens pipeline_star, they should think of it as four layers:

1. Interface layer:
run_avatar_pipeline and first.

2. Compute layer:
star_runner, fit_betas, mesh_measure, pose_catalog.

3. Contract and persistence layer:
mapping_layer, artifact_schema, artifact_io, run_manifest.

4. Export and diagnostics layer:
avatar_exporter modules, style, postprocess, and helper scripts.

This layered view makes maintenance easier and clarifies where to modify behavior when requirements evolve.

## Summary

pipeline_star is a mature Step 1 pipeline that combines data validation, model fitting, artifact governance, and export interoperability into one coherent flow. Its strongest trait is traceable run outputs and clear module boundaries. Its main improvement opportunities are portability hardening and further fitting robustness for difficult measurements.

For MVP progression, this folder already provides the critical digital twin generation foundation that Step 2 and Step 3 can build on.
