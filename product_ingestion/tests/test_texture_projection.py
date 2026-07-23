"""Texture projection unit tests.

Verifies:
- Projected texture has correct canvas dimensions for each panel.
- Output is RGBA (4 channels) with non-zero alpha.
- Panel alpha mask is non-empty (polygon was rasterised).
- Graphic composite does not crash on small/mismatched sizes.
"""
import sys
import unittest
import tempfile
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from garment_measurements import GarmentMeasurements
from panels import DynamicPatternGenerator
from texture_projection import TextureProjector, project_textures


def _make_measurements() -> GarmentMeasurements:
    return GarmentMeasurements(
        half_chest_width=50.0,
        garment_length=70.0,
        shoulder_width=42.0,
        neck_width=18.0,
        neck_depth_front=7.0,
        neck_depth_back=2.0,
        sleeve_length=60.0,
        bicep_width=18.0,
        armhole_depth=20.0,
        seam_allowance=1.0,
        fit_type="regular",
        ease_cm=4.0,
        body_height=175.0,
        body_chest=96.0,
        body_shoulder=44.0,
    )


def _make_garment_rgba(w=300, h=400) -> np.ndarray:
    """Create a synthetic RGBA with a centred 50% square as the garment."""
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    # Garment region: centre 50% of image
    y0, y1 = h // 4, 3 * h // 4
    x0, x1 = w // 4, 3 * w // 4
    rgba[y0:y1, x0:x1, :3] = 128   # grey
    rgba[y0:y1, x0:x1, 3] = 255    # opaque
    return rgba


def _make_layouts():
    m = _make_measurements()
    gen = DynamicPatternGenerator(m)
    gen.generate_front_panel()
    gen.generate_back_panel()
    arm = (gen.front_armhole_length + gen.back_armhole_length) / 2
    gen.generate_sleeve("sleeve_left",  target_armhole_length=arm)
    gen.generate_sleeve("sleeve_right", target_armhole_length=arm)
    return gen.layouts


class TestTextureProjection(unittest.TestCase):

    def setUp(self):
        self.garment_rgba = _make_garment_rgba()
        self.layouts = _make_layouts()
        self.projector = TextureProjector()

    def test_all_pieces_produce_textures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = project_textures(
                garment_rgba=self.garment_rgba,
                layouts=self.layouts,
                textures_dir=Path(tmpdir),
            )
        self.assertTrue(result.success, result.message)
        self.assertEqual(set(result.textures.keys()), set(self.layouts.keys()))

    def test_texture_is_rgba(self):
        for piece_name, layout in self.layouts.items():
            texture = self.projector.project_panel_texture(
                self.garment_rgba, layout
            )
            self.assertEqual(texture.ndim, 3, f"{piece_name}: expected 3D array")
            self.assertEqual(texture.shape[2], 4, f"{piece_name}: expected 4 channels (RGBA)")

    def test_texture_canvas_size_matches_panel(self):
        px = TextureProjector.PX_PER_CM
        for piece_name, layout in self.layouts.items():
            poly = layout.polygon()
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            expected_w = max(1, round((max(xs) - min(xs)) * px))
            expected_h = max(1, round((max(ys) - min(ys)) * px))
            texture = self.projector.project_panel_texture(self.garment_rgba, layout)
            self.assertEqual(
                (texture.shape[1], texture.shape[0]),
                (expected_w, expected_h),
                f"{piece_name}: canvas size mismatch",
            )

    def test_alpha_mask_non_empty(self):
        for piece_name, layout in self.layouts.items():
            texture = self.projector.project_panel_texture(self.garment_rgba, layout)
            alpha = texture[:, :, 3]
            self.assertGreater(
                np.sum(alpha > 0), 0,
                f"{piece_name}: alpha mask is entirely zero (polygon not rasterised?)",
            )

    def test_graphic_composite_does_not_crash(self):
        graphic = np.zeros((50, 50, 4), dtype=np.uint8)
        graphic[:, :, :3] = 200
        graphic[:, :, 3] = 200
        layout = self.layouts["front_panel"]
        base_texture = self.projector.project_panel_texture(self.garment_rgba, layout)
        result = self.projector._composite_graphic(base_texture, layout, graphic)
        self.assertEqual(result.shape, base_texture.shape)

    def test_empty_garment_returns_zero_texture(self):
        empty_rgba = np.zeros((400, 300, 4), dtype=np.uint8)
        layout = self.layouts["front_panel"]
        texture = self.projector.project_panel_texture(empty_rgba, layout)
        self.assertEqual(texture[:, :, 3].sum(), 0)

    def test_metadata_json_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = project_textures(
                garment_rgba=self.garment_rgba,
                layouts=self.layouts,
                textures_dir=Path(tmpdir),
            )
            meta_path = Path(tmpdir) / "texture_projection_metadata.json"
            self.assertTrue(meta_path.exists(), "texture_projection_metadata.json not written")


if __name__ == "__main__":
    unittest.main()
