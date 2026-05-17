# Plan 004: GPU-Enabled STAR Forward Pass Migration (Chumpy → PyTorch)

## Overview

Migrate the current avatar generation STAR execution path from Chumpy-based computation to PyTorch STAR so the forward pass can run on GPU when available, with automatic fallback to CPU.

The migration is scoped to STAR execution only and must preserve compatibility with the existing downstream pipeline.

## Scope and Constraints

- Enable STAR forward pass execution on:
  - CUDA (NVIDIA)
  - MPS (Apple Silicon)
  - CPU fallback
- Support batched forward passes for current and future scaling.
- Keep existing downstream modules unchanged:
  - mapping_layer
  - mesh_measure
  - avatar_exporter
  - MongoDB-related logic
- Keep mesh measurement and GLB export on CPU.
- Use PyTorch with float32 consistently.
- Do not hardcode device-specific tensor types.
- Explicitly wrap STAR forward inference in torch.no_grad() to prevent gradient graph creation.
- Patch only the minimum required lines inside the local STAR library to remove hardcoded CUDA tensor construction.
- Reuse centralized utils/device.py in STAR integration where feasible, while keeping STAR library edits minimal and localized.

## Phases

### Phase 1: Baseline Audit and Migration Contract

**Goal**: Lock migration boundaries, identify STAR execution touchpoints, and define success criteria before implementation.

**Steps**:

1. Identify the exact STAR execution flow in the current pipeline CLI path and supporting modules.
2. Document all call sites where STAR model creation, tensor creation, and forward pass occur.
3. Confirm integration boundaries with unchanged modules (mapping_layer, mesh_measure, avatar_exporter, DB logic).
4. Define acceptance criteria for device fallback behavior, batch behavior, and output compatibility.

### Phase 2: Centralized Device Management

**Goal**: Introduce a single source of truth for device selection and eliminate hardcoded device logic.

**Steps**:

1. Create centralized device utility module at utils/device.py.
2. Implement ordered device resolution policy: CUDA first, then MPS, then CPU.
3. Expose a shared DEVICE constant for imports across STAR execution modules.
4. Replace any local or hardcoded device selection with imports from the centralized utility.
5. Log the selected device at runtime so hardware usage is visible when the pipeline starts.

### Phase 3: PyTorch STAR Runner Refactor

**Goal**: Move STAR execution to PyTorch with device-agnostic, float32, batched inference.

**Steps**:

1. Refactor star_runner to load and use the PyTorch STAR implementation.
2. Ensure STAR model initialization occurs once and is reused across forward invocations.
3. Place model on DEVICE and enforce input tensors on the same DEVICE.
4. Standardize all continuous model STAR input tensors (betas, pose, trans) to float32 and preserve batch dimensions for single and multi-sample flows. Ensure structural configuration tensors (faces, kintree_table, parent) remain as native torch.long ints.
5. Enforce betas input-shape normalization at the STAR boundary so single-avatar input is converted from (10,) to (1,10) and batched input remains (B,10).
6. Remove any CUDA-specific tensor constructors and replace with device-agnostic tensor handling.

### Phase 3B: Minimal STAR Library Compatibility Patch

**Goal**: Make the vendored STAR PyTorch library device-agnostic (CUDA/MPS/CPU) with the smallest possible code changes.

**Steps**:

1. Patch only the specific hardcoded CUDA tensor creation points in the local STAR library files (no broad refactor).
2. Replace CUDA-specific constructors with device-agnostic tensor creation that follows the selected runtime device.
3. Keep tensor dtype explicitly float32 and preserve existing STAR math/path logic.
4. Prefer using shared device policy from utils/device.py where practical; otherwise use input/model device-derived placement to avoid invasive changes.
5. Avoid changing public STAR interfaces so pipeline integration remains stable.

### Phase 4: Batched Forward-Pass Interface

**Goal**: Make STAR execution batch-capable while remaining backward-compatible with current single-avatar usage.

**Steps**:

1. Define batch-oriented STAR generation interface in star_runner.
2. Ensure single-avatar callers are internally mapped to batch size 1 without breaking existing behavior.
3. Validate output tensor shape contract for batched results.
4. Validate and enforce shape contracts for all STAR inputs (betas, pose, trans) before forward pass.
5. Keep API responses compatible with downstream consumers that expect current output semantics.

### Phase 5: Inference and Transfer Boundary Hardening

**Goal**: Optimize inference behavior and establish a clean GPU-to-CPU boundary for downstream CPU tooling.

**Steps**:

1. Enforce inference-only STAR execution mode by wrapping STAR forward pass with torch.no_grad().
2. Keep all STAR math on DEVICE through forward pass completion.
3. Establish a hard GPU-to-CPU boundary constraint before returning mesh data. Ensure all exported objects returning from `star_runner.py` (like vertices and faces) are fully explicitly detached using `.detach().cpu().numpy()` so PyTorch does not hold open GPU memory graphs.
4. Eliminate repeated device transfer patterns inside per-user processing paths.

### Phase 6: Cross-Environment Validation

> [!WARNING]
> Regarding Apple Silicon (MPS): The model training currently exclusively targets laptops with RTX GPUs or A100 workstations. MPS testing is strictly intended for generating single avatars. Be advised that PyTorch MPS support is historically incomplete. If a crash relating to unsupported matrix or indexing operations surfaces during future testing on Apple Silicon, we will investigate injecting `PYTORCH_ENABLE_MPS_FALLBACK` or rewriting the operation.

**Goal**: Verify robust behavior across CPU-only, CUDA, and MPS environments with unchanged downstream processing.

**Steps**:

1. Validate pipeline behavior on CPU-only execution path.
2. Validate pipeline behavior on CUDA-enabled execution path.
3. Validate pipeline behavior on MPS-enabled execution path.
4. Confirm fallback behavior does not crash when a preferred accelerator is unavailable.
5. Confirm patched STAR library paths do not call CUDA-only constructors at runtime on MPS/CPU.
6. Confirm mesh measurement and GLB export remain CPU operations and produce compatible artifacts.

### Phase 7: Numerical Validation

**Goal**: Ensure PyTorch STAR produces the same mesh as the original Chumpy implementation.

**Steps**:

1. Run both implementations with identical inputs (betas, pose, trans).
2. Compare vertex outputs between Chumpy and PyTorch STAR.
3. Compute maximum vertex deviation.
4. Confirm deviation remains within acceptable tolerance.

### Phase 8: Performance and Regression Verification

**Goal**: Confirm functional parity and readiness for larger-scale batched generation.

**Steps**:

1. Compare generated outputs against baseline expectations for representative users.
2. Verify no regressions in downstream measurements and export outputs.
3. Run smoke tests for batch size 1 and multi-sample batches (the vendored library naturally supports batch outputs).
4. Document observed runtime improvements and any remaining limitations for future optimization.

### Phase 9: Remove Legacy Chumpy Dependencies

**Goal**: Cleanly excise all traces of the legacy Chumpy library after the new PyTorch path is fully manually verified.

**Steps**:

1. Validate the PyTorch STAR migration is 100% complete and functionally approved.
2. Search the entire `pipeline_star` and `libs/star/star` directories for any remaining `import chumpy` statements.
3. Remove Chumpy from the project's dependency lists (e.g. `requirements.txt`).
4. Delete any legacy `.pkl` serialization fallback paths or fit modules strictly dependent on Chumpy if they are designated as obsolete.

## Dependencies

- PyTorch runtime with CUDA and/or MPS support depending on host environment.
- Existing STAR model assets configured and readable by the PyTorch STAR implementation.
- Existing pipeline CLI and module structure in pipeline_star.
- Test environments for:
  - CPU-only
  - CUDA-enabled GPU
  - Apple Silicon MPS

## Expected Outcomes

- STAR forward pass automatically runs on best available device (CUDA, MPS, or CPU).
- CPU fallback works without crashes when accelerators are unavailable.
- star_runner supports batched betas and batched STAR forward pass.
- Tensor dtype and device usage are standardized and device-agnostic.
- Downstream modules remain unchanged and continue functioning as before.
- Mesh measurement and GLB export remain CPU-only with compatible outputs.

## Manual Verification Checklist

1. Run the pipeline on a CPU-only machine and confirm successful end-to-end execution.
2. Run the pipeline on an NVIDIA CUDA machine and confirm STAR forward pass uses CUDA.
3. Run the pipeline on Apple Silicon and confirm STAR forward pass uses MPS (Keep an eye out for unsupported Operation Errors per the warning in Phase 6).
4. Confirm no runtime device mismatch errors occur during STAR forward pass.
5. Confirm batch size 1 and batch size >1 both execute successfully.
6. Confirm exported GLB files are generated and match expected structure.
7. Confirm measurement extraction and export behavior remain unchanged from user perspective.
8. Confirm no autograd graph is tracked during inference (torch.no_grad() path is active).
9. Confirm startup logs clearly print the selected runtime device.
10. Confirm Chumpy vs PyTorch max vertex deviation remains within agreed tolerance.
11. Confirm single-avatar beta input (10,) is automatically normalized to (1,10) and produces valid output.
12. Confirm patched local STAR library changes are minimal, localized, and limited to device-compatibility points.
