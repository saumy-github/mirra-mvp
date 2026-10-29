"""Warp a frontal photo onto the head albedo's UV layout and composite it over the stock texture."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .constants import BASE_TEMPLATE, FACE_BBOX_UV, INFORMATIVE_UV, anchors_for_size
from .landmarks import _MP_FACE_OVAL as _OVAL_INDICES, FaceLandmarks

REFERENCE_DIR = Path(__file__).resolve().parents[1] / 'reference' / BASE_TEMPLATE

# Feather width as a fraction of texture size. Weights are feathered, not pixels:
# blurring the pixels ghosts the edge, blurring the weights blends it.
FEATHER_FRACTION = 0.05
# How far the face oval is grown before feathering, so the blend lands on cheek/forehead
# skin rather than cutting exactly at the silhouette. Used by the similarity fallback,
# whose oval comes from the photo and therefore stops short of the real face edge.
OVAL_DILATE_FRACTION = 0.06
# How far the dense-path oval is pulled inward. The mesh silhouette hugs the face edge,
# where the outer triangles pick up background, so this trims that contaminated band.
OVAL_INSET_FRACTION = 0.035


@dataclass
class FitReport:
    landmark_source: str
    warp_mode: str
    interocular_px: float
    scale: float
    rotation_deg: float
    anchor_error_px: dict[str, float]
    similarity_residual_px: dict[str, float]
    coverage_fraction: float
    tone_shift_lab: tuple[float, float, float]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            'landmark_source': self.landmark_source,
            'warp_mode': self.warp_mode,
            'interocular_px': round(self.interocular_px, 2),
            'scale': round(self.scale, 4),
            'rotation_deg': round(self.rotation_deg, 2),
            'anchor_error_px': {k: round(v, 2) for k, v in self.anchor_error_px.items()},
            'similarity_residual_px': {k: round(v, 2) for k, v in self.similarity_residual_px.items()},
            'coverage_fraction': round(self.coverage_fraction, 4),
            'tone_shift_lab': [round(v, 2) for v in self.tone_shift_lab],
            'warnings': self.warnings,
        }


def load_reference_dense(size: int) -> np.ndarray | None:
    """Stock-albedo mesh measured by calibrate_reference.py, scaled to the working texture size."""
    dense_path = REFERENCE_DIR / 'dense_landmarks.npy'
    anchors_path = REFERENCE_DIR / 'anchors.json'
    if not dense_path.exists() or not anchors_path.exists():
        return None
    meta = json.loads(anchors_path.read_text(encoding='utf-8'))
    dense = np.load(dense_path).astype(np.float32)
    return dense * (size / float(meta.get('texture_size', size)))


def shift_albedo_tone(image_bgr: np.ndarray, delta_lab: tuple[float, float, float],
                      protect: np.ndarray | None = None) -> np.ndarray:
    """Apply a Lab mean shift to a texture, optionally leaving a protected region untouched."""
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    strength = np.ones(lab.shape[:2], np.float32) if protect is None else (1.0 - protect)
    for channel in range(3):
        lab[..., channel] += delta_lab[channel] * strength
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def face_tone_delta(composite_bgr: np.ndarray, stock_bgr: np.ndarray,
                    weight: np.ndarray) -> tuple[float, float, float]:
    """How far the fitted face sits from the stock skin it has to blend into, in Lab."""
    face_region = weight > 0.6
    skin_region = (weight < 0.05) & _head_skin_band(stock_bgr.shape[0])
    if not face_region.any() or not skin_region.any():
        return (0.0, 0.0, 0.0)
    face_lab = cv2.cvtColor(composite_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    stock_lab = cv2.cvtColor(stock_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    return tuple(float(face_lab[..., c][face_region].mean() - stock_lab[..., c][skin_region].mean())
                 for c in range(3))


def _head_skin_band(size: int) -> np.ndarray:
    """Forehead/temple/cheek band of the head map - skin, and never garment or shoulder."""
    u0, v0, u1, v1 = INFORMATIVE_UV
    band = np.zeros((size, size), bool)
    band[int(v0 * size):int(v1 * size), int(u0 * size):int(u1 * size)] = True
    return band


def _target_anchors(size: int) -> np.ndarray:
    """Prefer detector-measured targets; the constants are pupil centres in a different convention."""
    anchors_path = REFERENCE_DIR / 'anchors.json'
    if anchors_path.exists():
        meta = json.loads(anchors_path.read_text(encoding='utf-8'))
        scale = size / float(meta.get('texture_size', size))
        px = meta['anchors_px']
        return np.array([px['eye_l'], px['eye_r'], px['mouth']], dtype=np.float32) * scale
    anchors = anchors_for_size(size)
    return np.array([anchors['eye_l'], anchors['eye_r'], anchors['mouth']], dtype=np.float32)


def _warp_piecewise_affine(photo: np.ndarray, source_pts: np.ndarray, target_pts: np.ndarray,
                           size: int) -> tuple[np.ndarray, np.ndarray]:
    """Delaunay-triangulate the target mesh and affine-warp each matching photo triangle into it."""
    # scipy triangulates by index; cv2.Subdiv2D returns perturbed float coordinates that
    # cannot be matched back to the input points reliably.
    from scipy.spatial import Delaunay

    clipped = np.clip(target_pts, 0, size - 1)
    triangulation = Delaunay(clipped)

    out = np.zeros((size, size, 3), np.uint8)
    covered = np.zeros((size, size), np.uint8)
    for idx in triangulation.simplices:
        dst_tri = clipped[idx].astype(np.float32)
        src_tri = source_pts[idx].astype(np.float32)

        rect = cv2.boundingRect(dst_tri)
        x, y, w, h = rect
        if w <= 0 or h <= 0:
            continue
        matrix = cv2.getAffineTransform(src_tri, dst_tri - np.array([x, y], np.float32))
        patch = cv2.warpAffine(photo, matrix, (w, h), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REFLECT_101)
        mask = np.zeros((h, w), np.uint8)
        cv2.fillConvexPoly(mask, (dst_tri - np.array([x, y], np.float32)).astype(np.int32), 255)
        region = out[y:y + h, x:x + w]
        np.copyto(region, patch, where=mask[..., None].astype(bool))
        covered[y:y + h, x:x + w] |= mask
    return out, covered


def _default_oval_mask(size: int) -> np.ndarray:
    """Elliptical stand-in for the face silhouette, used when no dense mesh is available."""
    u0, v0, u1, v1 = FACE_BBOX_UV
    cx, cy = (u0 + u1) / 2.0 * size, (v0 + v1) / 2.0 * size
    ax, ay = (u1 - u0) / 2.0 * size, (v1 - v0) / 2.0 * size
    mask = np.zeros((size, size), np.uint8)
    cv2.ellipse(mask, (int(cx), int(cy)), (int(ax * 1.02), int(ay * 1.18)), 0, 0, 360, 255, -1)
    return mask


def _oval_mask_from_dense(oval_uv: np.ndarray, size: int,
                          grow_fraction: float = OVAL_DILATE_FRACTION) -> np.ndarray:
    """Fill the face silhouette, growing it (positive) or pulling it inward (negative)."""
    mask = np.zeros((size, size), np.uint8)
    cv2.fillPoly(mask, [oval_uv.astype(np.int32)], 255)
    radius = max(1, int(size * abs(grow_fraction)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius, radius))
    return cv2.dilate(mask, kernel) if grow_fraction >= 0 else cv2.erode(mask, kernel)


def _match_tone(warped_lab: np.ndarray, stock_lab: np.ndarray,
                weight: np.ndarray, strength: float) -> tuple[np.ndarray, tuple[float, float, float]]:
    """Shift the warped face's Lab mean toward the stock face's, leaving variance (identity detail) intact."""
    valid = weight > 0.35
    if not valid.any():
        return warped_lab, (0.0, 0.0, 0.0)

    shift = tuple(float(stock_lab[..., c][valid].mean() - warped_lab[..., c][valid].mean())
                  for c in range(3))
    adjusted = warped_lab.copy()
    for c in range(3):
        adjusted[..., c] += shift[c] * strength
    return adjusted, shift


def fit_face_to_albedo(photo_bgr: np.ndarray, landmarks: FaceLandmarks, stock_albedo: np.ndarray,
                       *, tone_strength: float = 1.0) -> tuple[np.ndarray, np.ndarray, FitReport]:
    """Return (composited albedo, weight map, report) for one frontal photo."""
    size = stock_albedo.shape[0]
    warnings: list[str] = []

    source = landmarks.anchor_matrix()
    target = _target_anchors(size)
    matrix, _ = cv2.estimateAffinePartial2D(source, target, method=cv2.LMEDS)
    if matrix is None:
        raise ValueError('Could not estimate a transform from the photo anchors to the UV anchors')

    scale = float(np.hypot(matrix[0, 0], matrix[0, 1]))
    rotation_deg = float(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0])))

    reference_dense = load_reference_dense(size)
    use_dense = landmarks.dense is not None and reference_dense is not None
    warp_mode = 'piecewise_affine' if use_dense else 'similarity'

    if use_dense:
        # A similarity transform can only move, rotate and scale a face; it cannot reshape one.
        # Matching the photo mesh onto the stock mesh is what makes a real face fit this head.
        warped, covered = _warp_piecewise_affine(photo_bgr, landmarks.dense, reference_dense, size)
        # The outermost triangles straddle the silhouette and sample whatever is behind the
        # head, so pull the blend inside the face rather than growing it past the edge.
        mask = cv2.bitwise_and(
            _oval_mask_from_dense(reference_dense[_OVAL_INDICES], size, -OVAL_INSET_FRACTION),
            covered)
    else:
        warped = cv2.warpAffine(photo_bgr, matrix, (size, size), flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)
        if landmarks.oval is not None:
            oval_uv = cv2.transform(landmarks.oval.reshape(-1, 1, 2), matrix).reshape(-1, 2)
            mask = _oval_mask_from_dense(oval_uv, size)
        else:
            mask = _default_oval_mask(size)
            warnings.append('No dense mesh available; used an elliptical face mask (prototype quality).')
        # Anything the photo did not actually cover must not be blended in.
        photo_area = cv2.warpAffine(np.full(photo_bgr.shape[:2], 255, np.uint8), matrix, (size, size),
                                    flags=cv2.INTER_NEAREST, borderValue=0)
        mask = cv2.bitwise_and(mask, photo_area)

    feather = max(3, int(size * FEATHER_FRACTION) | 1)
    # Pull the mask in by the feather radius before blurring. If the ramp runs past the edge
    # of the warped region it blends uncovered black pixels in and rings the face with a halo.
    erode_radius = max(1, feather // 2)
    inner = cv2.erode(mask, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (erode_radius * 2 + 1, erode_radius * 2 + 1)))
    weight = cv2.GaussianBlur(inner.astype(np.float32) / 255.0, (feather, feather), 0)
    weight = np.clip(weight, 0.0, 1.0)

    warped_lab = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB).astype(np.float32)
    stock_lab = cv2.cvtColor(stock_albedo, cv2.COLOR_BGR2LAB).astype(np.float32)
    toned_lab, tone_shift = _match_tone(warped_lab, stock_lab, weight, tone_strength)
    toned = cv2.cvtColor(np.clip(toned_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)

    alpha = weight[..., None]
    composite = (toned.astype(np.float32) * alpha +
                 stock_albedo.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)

    placed = cv2.transform(source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    # How far a rigid fit misses by - i.e. how much this face's proportions differ from the
    # template's. The piecewise warp absorbs exactly this difference.
    similarity_residual = {name: float(np.hypot(*(placed[i] - target[i])))
                           for i, name in enumerate(('eye_l', 'eye_r', 'mouth'))}
    # The dense warp pins every landmark to its reference position by construction.
    anchor_error = ({name: 0.0 for name in similarity_residual} if use_dense
                    else dict(similarity_residual))

    if scale > 1.0:
        warnings.append(f'Photo upscaled {scale:.2f}x into the UV map; source resolution is the quality ceiling.')
    if abs(rotation_deg) > 15.0:
        warnings.append(f'Large head roll corrected ({rotation_deg:.1f} deg); check the result.')

    report = FitReport(
        landmark_source=landmarks.source,
        warp_mode=warp_mode,
        interocular_px=landmarks.interocular,
        scale=scale,
        rotation_deg=rotation_deg,
        anchor_error_px=anchor_error,
        similarity_residual_px=similarity_residual,
        coverage_fraction=float((weight > 0.5).sum()) / float(size * size),
        tone_shift_lab=tone_shift,
        warnings=warnings,
    )
    return composite, weight, report
