# GPU Acceleration Implementation Plan

## Overview

Add PyTorch GPU acceleration to the STAR digital twin generation pipeline to significantly speed up beta fitting optimization. The implementation will automatically detect GPU availability and fall back to CPU when needed.

---

## Design Decisions (Based on User Requirements)

### QA1: Keep Old STAR Runner

✅ **Keep** `star_runner.py` (Chumpy version) as CPU fallback option

### QA2: Automatic GPU/CPU Detection

✅ **Single command** runs the pipeline with automatic GPU detection:

```bash
python3 pipeline_star/run_digital twin_pipeline.py
# Automatically uses GPU if available, otherwise CPU
```

### QA3: GPU Monitoring

⏸️ **Later stage** - Add after manual verification of GPU pipeline working

---

## Key Discovery

STAR library has **built-in PyTorch support**:

- Current: `star.ch.star.STAR` (Chumpy - CPU-only)
- Available: `star.pytorch.star.STAR` (PyTorch - GPU-ready)

---

## Implementation Steps

### Phase 1: Setup & Configuration

#### 1.1 Install PyTorch with CUDA

```bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### 1.2 Create GPU Configuration Module

**File**: [NEW] `pipeline_star/gpu_config.py`

```python
import torch

def get_device():
    """Auto-detect and return CUDA device if available, else CPU"""
    if torch.cuda.is_available():
        return torch.device('cuda')
    return torch.device('cpu')

def log_device_info():
    """Print GPU/CPU status"""
    device = get_device()
    if device.type == 'cuda':
        print(f"🚀 GPU Mode: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("💻 CPU Mode: No GPU detected")
    return device
```

---

### Phase 2: Core Implementation

#### 2.1 Create PyTorch STAR Runner

**File**: [NEW] `pipeline_star/star_runner_torch.py`

- Import `star.pytorch.star.STAR` instead of `star.ch.star.STAR`
- Accept `device` parameter
- Return PyTorch tensors (move to device)
- Keep same API as `star_runner.py`
- Model caching (same as current)

Key changes:

```python
from star.pytorch.star import STAR
import torch

def generate_mesh_torch(gender, betas, pose, scale, num_betas, device):
    # Convert to PyTorch tensors
    betas_t = torch.tensor(betas).float().to(device)
    pose_t = torch.tensor(pose).float().to(device)
    trans_t = torch.zeros(1, 3).to(device)

    # Forward pass (GPU accelerated)
    output = model.forward(pose_t.unsqueeze(0),
                          betas_t.unsqueeze(0),
                          trans_t)

    # Return vertices and faces
    return output
```

#### 2.2 Update Beta Fitting

**File**: [MODIFY] `pipeline_star/fit_betas.py`

Major changes:

1. Replace manual gradient descent with PyTorch optimizer (`torch.optim.Adam`)
2. Use automatic differentiation (no finite differences!)
3. Convert arrays to tensors, move to device
4. Return NumPy arrays for compatibility

**Current approach** (manual gradient):

```python
for i in range(num_betas):
    betas_plus = betas.copy()
    betas_plus[i] += epsilon
    loss_plus = compute_loss(betas_plus)
    gradient[i] = (loss_plus - loss) / epsilon
betas = betas - learning_rate * gradient
```

**New approach** (automatic differentiation):

```python
betas = torch.tensor(betas, requires_grad=True, device=device)
optimizer = torch.optim.Adam([betas], lr=0.1)

for iteration in range(max_iterations):
    optimizer.zero_grad()
    loss = compute_loss_torch(betas)
    loss.backward()  # Automatic gradient computation!
    optimizer.step()
```

#### 2.3 Update Measurement Extraction

**File**: [MODIFY] `pipeline_star/mesh_measure.py`

Add tensor support:

```python
def extract_measurements_from_mesh(vertices, debug=False):
    # Convert tensor to numpy if needed
    if torch.is_tensor(vertices):
        vertices = vertices.cpu().numpy()

    # Rest of code unchanged (stays on CPU)
    ...
```

---

### Phase 3: Integration

#### 3.1 Update Main Pipeline

**File**: [MODIFY] `pipeline_star/first.py`

Add device detection at start:

```python
from pipeline_star.gpu_config import log_device_info, get_device

def main():
    device = log_device_info()  # Auto-detect and print status

    # Pass device to fitting
    fitting_result = fit_betas_to_measurements_torch(
        target_measurements, gender, num_betas, device
    )
```

#### 3.2 Keep CPU Fallback

**File**: [KEEP] `pipeline_star/star_runner.py`

No changes - keep as-is for:

- CPU-only machines
- Debugging
- Backward compatibility

---

### Phase 4: Testing & Verification

#### Test 1: GPU Detection

```bash
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

#### Test 2: PyTorch STAR Load

```bash
python3 -c "from star.pytorch.star import STAR; STAR(gender='male'); print('✓')"
```

#### Test 3: Performance Comparison

```bash
# Measure time before GPU
time python3 pipeline_star/run_digital twin_pipeline.py
# (user_m_002, run 004)

# Measure time after GPU
time python3 pipeline_star/run_digital twin_pipeline.py
# (user_m_002, run 005)
```

#### Test 4: Output Consistency

- Compare GLB files (CPU vs GPU)
- Open in Blender
- Verify visually identical

#### Test 5: CPU Fallback

- Run on machine without GPU
- Verify no errors, generates valid output

---

### Phase 5: GPU Monitoring (Later Stage)

**After manual verification**, add monitoring:

```python
def log_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        print(f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")
```

Add calls after key operations:

- After model load
- After optimization iterations
- After mesh generation

---

## File Changes Summary

| File                   | Type   | Description                     |
| ---------------------- | ------ | ------------------------------- |
| `gpu_config.py`        | NEW    | Auto GPU/CPU detection          |
| `star_runner_torch.py` | NEW    | PyTorch STAR runner             |
| `fit_betas.py`         | MODIFY | Add PyTorch optimization option |
| `mesh_measure.py`      | MODIFY | Support PyTorch tensors         |
| `first.py`             | MODIFY | Add device detection            |
| `star_runner.py`       | KEEP   | CPU fallback (no changes)       |

---

## Expected Performance

- **10 betas**: 5-10x faster
- **50 betas**: 20-50x faster
- **100 betas**: 30-100x faster

Speedup scales with number of betas due to parallel computation on GPU.

---

## Backward Compatibility

✅ **Same command for all users**:

```bash
python3 pipeline_star/run_digital twin_pipeline.py
```

- Laptop with GPU → Uses GPU automatically ⚡
- Laptop without GPU → Uses CPU automatically 💻
- Zero configuration needed
- Same codebase for everyone
