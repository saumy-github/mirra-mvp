"""Modular CLO automation pipeline steps."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["CLORestClient", "run_pipeline"]

def __getattr__(name: str) -> Any:
    if name == "CLORestClient":
        return import_module(".client", __name__).CLORestClient
    if name == "run_pipeline":
        return import_module(".pipeline", __name__).run_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
