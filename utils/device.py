#!/usr/bin/env python3
import torch

# Resolve best available device: CUDA > MPS > CPU
def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device('cuda')
    if torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


# Shared constant - import this across all STAR execution modules
DEVICE: torch.device = get_device()


# Log the selected runtime device at pipeline startup
def log_device() -> None:
    print(f'[device] Runtime device selected: {DEVICE}')


# Move an existing tensor to the runtime device
def to_device(tensor: torch.Tensor) -> torch.Tensor:
    return tensor.to(DEVICE)


# Create tensor and place it directly on the runtime device
def as_device_tensor(data, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.tensor(data, dtype=dtype, device=DEVICE)
