"""Two-view silhouette network (BMnet-style, Ruiz et al. 2022) with a scalar branch.

front silhouette -> ResNet ┐
side  silhouette -> ResNet ├─ concat -> MLP -> 14 measurements (cm)
height, weight, BMI, sex -> MLP ┘

The head predicts each measurement as mean + std * z, where mean/std come from the
training set, so the network only has to learn deviations from the average body.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torchvision

from .data import N_SCALARS, TARGETS


def _backbone(name: str, pretrained: bool) -> tuple[nn.Module, int]:
    weights = "DEFAULT" if pretrained else None
    net = getattr(torchvision.models, name)(weights=weights)
    # 1-channel input: sum the RGB filters of the first conv (keeps pretrained edges)
    w = net.conv1.weight.detach().sum(dim=1, keepdim=True)
    net.conv1 = nn.Conv2d(1, 64, 7, 2, 3, bias=False)
    net.conv1.weight = nn.Parameter(w)
    dim = net.fc.in_features
    net.fc = nn.Identity()
    return net, dim


class BodyMeasureNet(nn.Module):
    def __init__(self, backbone: str = "resnet18", pretrained: bool = True,
                 target_mean=None, target_std=None):
        super().__init__()
        self.front, dim = _backbone(backbone, pretrained)
        self.side, _ = _backbone(backbone, pretrained)
        self.scalars = nn.Sequential(nn.Linear(N_SCALARS, 64), nn.GELU(), nn.Linear(64, 64), nn.GELU())
        self.head = nn.Sequential(
            nn.Linear(2 * dim + 64, 512), nn.GELU(), nn.Dropout(0.2),
            nn.Linear(512, 256), nn.GELU(),
            nn.Linear(256, len(TARGETS)),
        )
        n = len(TARGETS)
        self.register_buffer("mean", torch.as_tensor(target_mean if target_mean is not None else [0.0] * n,
                                                     dtype=torch.float32))
        self.register_buffer("std", torch.as_tensor(target_std if target_std is not None else [1.0] * n,
                                                    dtype=torch.float32))

    def forward(self, views: torch.Tensor, scalars: torch.Tensor) -> torch.Tensor:
        f = self.front(views[:, 0:1])
        s = self.side(views[:, 1:2])
        z = self.head(torch.cat([f, s, self.scalars(scalars)], dim=1))
        return self.mean + self.std * z
