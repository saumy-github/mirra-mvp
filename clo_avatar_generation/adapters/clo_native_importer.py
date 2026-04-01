"""Placeholder import-sequence adapter for the CLO-native path.

This file will later orchestrate:

1. native avatar template import
2. measurement CSV import
3. optional arrangement-point import
4. optional bounding-volume import
"""

from __future__ import annotations

from pathlib import Path

from .clo_native_client import CLONativeClient


class CLONativeImporter:
    """Import orchestrator for the isolated CLO-native path."""

    def __init__(self, client: CLONativeClient | None = None) -> None:
        self.client = client or CLONativeClient()
        self.ready = True

    def import_template_and_measurements(
        self,
        avt_path: str | Path,
        csv_path: str | Path,
        reset_project: bool = True,
    ) -> dict:
        """Queue native avatar import followed by measurement import."""

        if reset_project:
            self.client.new_project()
            self.client.wait_for_queue()

        avatar_result = self.client.import_avatar_avt(avt_path)
        measurement_result = self.client.import_avatar_measurements(
            csv_path=csv_path,
            template_path=avt_path,
        )
        self.client.wait_for_queue()
        return {
            "avatar_result": avatar_result,
            "measurement_result": measurement_result,
        }
