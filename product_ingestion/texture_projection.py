"""UV Texture Projection — garment photo → flat panel texture atlases.

Since panels are 2D flat shapes, the panel polygon IS the UV space.  The
segmented product photo is already a near-frontal 2D projection of the
garment.  This module warps the photo into each panel's coordinate system
so CLO can apply a photo-accurate texture before physics simulation.

Pipeline per panel
------------------
1. Get panel polygon → compute axis-aligned bounding box.
2. Get garment bounding box from segmented RGBA.
3. Compute a homography: garment-bbox corners → panel-bbox corners.
4. Warp the feathered RGBA using the homography.
5. Alpha-clip the output to the panel polygon shape.
6. Composite graphic_diffuse.png over the front panel chest region.
7. Save as panels/textures/{piece_name}_texture.png.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

try:
    from .curve_segment import PieceLayout
except ImportError:
    from curve_segment import PieceLayout  # type: ignore


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class TextureProjectionResult:
    """Paths and metadata produced by texture projection."""
    textures_dir: Path
    textures: dict[str, Path] = field(default_factory=dict)   # piece → PNG path
    projection_metadata: dict = field(default_factory=dict)
    success: bool = False
    message: str = ""


# ---------------------------------------------------------------------------
# Main projector
# ---------------------------------------------------------------------------

class TextureProjector:
    """Projects a segmented garment photo onto flat panel UV spaces."""

    # Pixels per centimetre for the output texture atlas.
    PX_PER_CM: float = 10.0

    # Fraction of garment width used as the sleeve source region.
    # 0.35 = left 35% for left sleeve, right 35% for right sleeve.
    # Tune this if sleeves are being cut off or torso fabric bleeds in.
    ARM_FRAC: float = 0.35

    # Vertical position of the graphic overlay on the front panel (0.0 = top,
    # 1.0 = bottom).  0.35 centres the graphic in the chest region for a
    # typical t-shirt.  Tunable without code changes.
    GRAPHIC_V_FRAC: float = 0.35

    def project_all(
        self,
        garment_rgba: np.ndarray,             # H×W×4 RGBA (feathered preferred)
        layouts: dict[str, PieceLayout],
        textures_dir: Path,
        graphic_rgba: Optional[np.ndarray] = None,  # H×W×4 RGBA design overlay
        design_type: str = "",
    ) -> TextureProjectionResult:
        """Project garment photo onto all panel layouts and save PNGs.

        Parameters
        ----------
        garment_rgba  : Segmented RGBA from segmentation step (feathered or hard).
        layouts       : dict of piece_name → PieceLayout (from DynamicPatternGenerator).
        textures_dir  : Output directory (created if absent).
        graphic_rgba  : Optional isolated design (logo / print) to composite on front.
        design_type   : Classification of the design ('logo', 'text', 'pattern', '').
        """
        textures_dir.mkdir(parents=True, exist_ok=True)

        # Garment bounding box in photo space (non-transparent pixels)
        garment_bbox = self._garment_bbox(garment_rgba)
        if garment_bbox is None:
            return TextureProjectionResult(
                textures_dir=textures_dir,
                success=False,
                message="Garment RGBA has no visible pixels; skipping texture projection.",
            )

        result = TextureProjectionResult(textures_dir=textures_dir, success=True)
        metadata_entries = {}

        # If design is logo or text (chest-centric), we do not warp the torso photo
        # onto the front panel or sleeves. We instead fill with solid base color
        # and lay the logo cleanly over the chest.
        is_chest_centric = design_type in ("logo", "text")

        for piece_name, layout in layouts.items():
            name_lower = piece_name.lower()

            if "back" in name_lower:
                # No back-view photo available: fill with the garment's median color.
                texture_np = self._solid_color_panel(layout, garment_rgba)
            elif "sleeve" in name_lower:
                if is_chest_centric:
                    # Clean solid color sleeves to prevent chest graphic bleed.
                    texture_np = self._solid_color_panel(layout, garment_rgba)
                else:
                    # Use only the arm region of the front photo.
                    side = "left" if "left" in name_lower else "right"
                    arm_bbox = self._arm_region_bbox(garment_bbox, side)
                    texture_np = self.project_panel_texture(garment_rgba, layout, arm_bbox)
            else:
                # Front panel
                if is_chest_centric:
                    # Fill front with solid base color; graphic is composited below.
                    texture_np = self._solid_color_panel(layout, garment_rgba)
                else:
                    # All-over pattern or no design: warp full segmented garment.
                    texture_np = self.project_panel_texture(garment_rgba, layout, garment_bbox)

            # Composite graphic overlay on front panel (chest area)
            if "front" in name_lower and graphic_rgba is not None:
                texture_np = self._composite_graphic(texture_np, layout, graphic_rgba)

            out_path = textures_dir / f"{piece_name}_texture.png"
            Image.fromarray(texture_np, mode="RGBA").save(str(out_path))
            result.textures[piece_name] = out_path

            polygon = layout.polygon(n_per_segment=64)
            metadata_entries[piece_name] = {
                "texture_path": str(out_path),
                "texture_size_px": [texture_np.shape[1], texture_np.shape[0]],
                "panel_bbox_cm": self._polygon_bbox(polygon),
            }
            print(f"  Texture projected: {out_path.name} ({texture_np.shape[1]}×{texture_np.shape[0]}px)")

        result.projection_metadata = {
            "px_per_cm": self.PX_PER_CM,
            "garment_bbox_px": garment_bbox,
            "pieces": metadata_entries,
        }
        meta_path = textures_dir / "texture_projection_metadata.json"
        meta_path.write_text(json.dumps(result.projection_metadata, indent=2), encoding="utf-8")
        return result

    def _get_median_color(self, garment_rgba: np.ndarray) -> tuple[int, int, int]:
        """Extract the median fabric body color from the segmented RGBA.

        Excludes stitching, shadows, and high-saturation design components.
        """
        alpha = garment_rgba[:, :, 3]
        visible = alpha > 10
        r_val, g_val, b_val = 200, 200, 200
        if visible.any():
            rgb = garment_rgba[:, :, :3]
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
            sat = hsv[:, :, 1]   # 0–255
            val = hsv[:, :, 2]   # 0–255
            # Fabric body: mid-value, mid-saturation filter.
            fabric = visible & (val > 40) & (val < 230) & (sat < 180)
            if fabric.any():
                r_val = int(np.median(rgb[:, :, 0][fabric]))
                g_val = int(np.median(rgb[:, :, 1][fabric]))
                b_val = int(np.median(rgb[:, :, 2][fabric]))
            else:
                r_val = int(np.median(rgb[:, :, 0][visible]))
                g_val = int(np.median(rgb[:, :, 1][visible]))
                b_val = int(np.median(rgb[:, :, 2][visible]))
        return (r_val, g_val, b_val)

    def _pad_transparent_edges(self, garment_rgba: np.ndarray, pad_color: tuple[int, int, int]) -> np.ndarray:
        """Fill transparent background pixels with a solid padding color.

        This prevents outer background / checkerboards from bleeding into
        the warped garment boundaries during homography interpolation.
        """
        alpha = garment_rgba[:, :, 3]
        mask = alpha < 50
        padded = garment_rgba.copy()
        padded[mask, :3] = pad_color
        return padded

    def project_panel_texture(
        self,
        garment_rgba: np.ndarray,
        layout: PieceLayout,
        garment_bbox: Optional[list] = None,
    ) -> np.ndarray:
        """Warp garment RGBA into a single panel's UV space.

        Returns an RGBA uint8 array sized to cover the panel bounding box at
        PX_PER_CM resolution, with pixels outside the panel polygon made transparent.
        """
        polygon = layout.polygon(n_per_segment=64)
        panel_bbox = self._polygon_bbox(polygon)  # [x_min, y_min, x_max, y_max] in cm
        pw = panel_bbox[2] - panel_bbox[0]  # panel width cm
        ph = panel_bbox[3] - panel_bbox[1]  # panel height cm

        # Output canvas size in pixels
        out_w = max(1, round(pw * self.PX_PER_CM))
        out_h = max(1, round(ph * self.PX_PER_CM))

        # Source bbox in photo pixels
        if garment_bbox is None:
            garment_bbox = self._garment_bbox(garment_rgba)
        if garment_bbox is None:
            return np.zeros((out_h, out_w, 4), dtype=np.uint8)

        gx0, gy0, gx1, gy1 = garment_bbox

        # 4-point homography: garment bbox corners → panel output corners
        src_pts = np.float32([
            [gx0, gy0], [gx1, gy0],
            [gx1, gy1], [gx0, gy1],
        ])
        dst_pts = np.float32([
            [0, 0],       [out_w - 1, 0],
            [out_w - 1, out_h - 1], [0, out_h - 1],
        ])
        H, _ = cv2.findHomography(src_pts, dst_pts)
        if H is None:
            return np.zeros((out_h, out_w, 4), dtype=np.uint8)

        # Extract base color and pad transparent background of input image
        pad_color = self._get_median_color(garment_rgba)
        padded_rgba = self._pad_transparent_edges(garment_rgba, pad_color)

        # Warp perspective with base color as border background
        warped = cv2.warpPerspective(padded_rgba, H, (out_w, out_h),
                                     flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT,
                                     borderValue=(int(pad_color[0]), int(pad_color[1]), int(pad_color[2]), 0))

        # Clip to panel polygon shape
        panel_mask = self._panel_alpha_mask(polygon, panel_bbox, out_w, out_h)
        result = warped.copy()
        result[:, :, 3] = panel_mask
        return result

    # -----------------------------------------------------------------------
    # Per-panel strategy helpers
    # -----------------------------------------------------------------------

    def _solid_color_panel(self, layout: "PieceLayout", garment_rgba: np.ndarray) -> np.ndarray:
        """Return an RGBA panel filled with the garment's median fabric color.

        Used for the back panel and optionally sleeves/front panel when no view is
        available or when the design is logo- or text-centric.
        """
        polygon = layout.polygon(n_per_segment=64)
        panel_bbox = self._polygon_bbox(polygon)
        out_w = max(1, round((panel_bbox[2] - panel_bbox[0]) * self.PX_PER_CM))
        out_h = max(1, round((panel_bbox[3] - panel_bbox[1]) * self.PX_PER_CM))

        r_val, g_val, b_val = self._get_median_color(garment_rgba)

        canvas = np.zeros((out_h, out_w, 4), dtype=np.uint8)
        canvas[:, :, 0] = r_val
        canvas[:, :, 1] = g_val
        canvas[:, :, 2] = b_val
        canvas[:, :, 3] = self._panel_alpha_mask(polygon, panel_bbox, out_w, out_h)
        return canvas

    def _arm_region_bbox(self, garment_bbox: list, side: str) -> list:
        """Return a bbox covering the arm/sleeve region of the garment photo.

        In a front-facing t-shirt photo the left sleeve occupies roughly the
        left ARM_FRAC of the garment width and the right sleeve the right ARM_FRAC.
        We use the full garment image (not a crop) so warpPerspective reads from
        the correct absolute pixel coordinates.

        Tune ARM_FRAC on the class if the split cuts off sleeve fabric or bleeds
        torso fabric into the sleeve texture.
        """
        gx0, gy0, gx1, gy1 = garment_bbox
        arm_px = int((gx1 - gx0) * self.ARM_FRAC)
        if side == "left":
            return [gx0, gy0, gx0 + arm_px, gy1]
        return [gx1 - arm_px, gy0, gx1, gy1]

    # -----------------------------------------------------------------------
    # Graphic overlay
    # -----------------------------------------------------------------------

    def _composite_graphic(
        self,
        panel_rgba: np.ndarray,
        layout: PieceLayout,
        graphic_rgba: np.ndarray,
    ) -> np.ndarray:
        """Composite a graphic (logo/print) onto the chest area of the panel.

        The graphic is scaled to fit ~30 % of the panel width and placed at
        35 % from top of the panel (chest position).
        """
        ph, pw = panel_rgba.shape[:2]
        if graphic_rgba is None or graphic_rgba.size == 0:
            return panel_rgba

        # Target size: 30% panel width, proportional height
        target_w = max(1, int(pw * 0.30))
        gh, gw = graphic_rgba.shape[:2]
        if gw == 0:
            return panel_rgba
        scale = target_w / gw
        target_h = max(1, int(gh * scale))

        graphic_resized = cv2.resize(graphic_rgba, (target_w, target_h),
                                     interpolation=cv2.INTER_AREA)

        # Center horizontally; place at GRAPHIC_V_FRAC from top (chest position).
        x_off = (pw - target_w) // 2
        y_off = int(ph * self.GRAPHIC_V_FRAC)

        # Clamp to panel bounds
        x1 = min(x_off + target_w, pw)
        y1 = min(y_off + target_h, ph)
        gw_clip = x1 - x_off
        gh_clip = y1 - y_off
        if gw_clip <= 0 or gh_clip <= 0:
            return panel_rgba

        graphic_crop = graphic_resized[:gh_clip, :gw_clip]
        panel_out = panel_rgba.copy()
        region = panel_out[y_off:y1, x_off:x1]

        # Alpha-composite graphic over panel
        g_alpha = graphic_crop[:, :, 3:4].astype(np.float32) / 255.0
        panel_out[y_off:y1, x_off:x1, :3] = (
            graphic_crop[:, :, :3] * g_alpha
            + region[:, :, :3] * (1.0 - g_alpha)
        ).astype(np.uint8)
        panel_out[y_off:y1, x_off:x1, 3] = np.maximum(
            region[:, :, 3], graphic_crop[:, :, 3]
        )
        return panel_out

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _garment_bbox(rgba: np.ndarray) -> Optional[list]:
        """Return [x_min, y_min, x_max, y_max] of non-transparent pixels."""
        alpha = rgba[:, :, 3] if (rgba.ndim == 3 and rgba.shape[2] == 4) else np.ones(rgba.shape[:2], np.uint8) * 255
        ys, xs = np.where(alpha > 10)
        if len(xs) == 0:
            return None
        return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]

    @staticmethod
    def _polygon_bbox(polygon: list) -> list:
        """Return [x_min, y_min, x_max, y_max] for a list of (x, y) points."""
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return [min(xs), min(ys), max(xs), max(ys)]

    @staticmethod
    def _panel_alpha_mask(
        polygon: list,
        bbox: list,
        out_w: int,
        out_h: int,
    ) -> np.ndarray:
        """Return uint8 [0/255] mask of pixels inside the panel polygon.

        The polygon is in panel coordinate space (cm); bbox offsets it so the
        origin is (0, 0).  Then it is scaled to pixel space at PX_PER_CM.
        """
        px_per_cm = TextureProjector.PX_PER_CM
        x_min, y_max = bbox[0], bbox[3]

        pts_px = np.array([
            [(p[0] - x_min) * px_per_cm, (y_max - p[1]) * px_per_cm]
            for p in polygon
        ], dtype=np.float32)
        pts_px = pts_px.reshape((-1, 1, 2)).astype(np.int32)

        mask = np.zeros((out_h, out_w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts_px], 255)
        return mask


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def project_textures(
    garment_rgba: np.ndarray,
    layouts: dict[str, "PieceLayout"],
    textures_dir: Path,
    graphic_rgba: Optional[np.ndarray] = None,
    design_type: str = "",
) -> TextureProjectionResult:
    """Convenience wrapper around TextureProjector.project_all."""
    projector = TextureProjector()
    return projector.project_all(
        garment_rgba=garment_rgba,
        layouts=layouts,
        textures_dir=textures_dir,
        graphic_rgba=graphic_rgba,
        design_type=design_type,
    )
