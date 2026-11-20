"""Classical image enhancement, restoration, smoothing and edge detection for garment photos.

Written for the CV project (plan P03, syllabus Units I and II). Every function is a
plain function on numpy images and takes an optional garment mask, so the colour step (P04) and
the design step (P05) can call them directly.

Conventions
-----------
* Colour images are RGB uint8, shape (H, W, 3). Grey images are uint8 (H, W) unless noted.
* ``mask`` is a boolean (H, W) array, True on the garment. Statistics (histograms, channel means,
  percentiles) are computed inside the mask only. Filters that would leak the background into the
  garment first replace the background by the nearest garment pixel (``fill_outside``).
* Functions return a new array and never modify their inputs. No global state, no randomness.

Contents
--------
Enhancement  : hist_equalize, clahe, gamma_correct, grey_world, white_patch, retinex
Restoration  : denoise (median, gaussian, bilateral, nlm)
Shading      : remove_shading_divide (optionally per colour region), remove_shading_homomorphic
Smoothing    : smooth_gray (none, mean, median, gaussian, bilateral)
Edges        : detect_edges (sobel, prewitt, scharr, laplacian, log, dog, canny, canny_pyr_and,
               canny_pyr_or), auto_canny
Chains       : apply_chain, ENHANCERS, SMOOTHERS, EDGE_DETECTORS
Recommended  : design_edges, prepare_for_colour (best choices of the P03 study; see REPORT.md)

Edge thresholds. The project pipeline (step_04_0_design_extraction.py ``_auto_canny``) sets
Canny thresholds from the median grey level: low = 0.67 median, high = 1.33 median on an
unnormalised Sobel magnitude, which means "a step of at least 0.17 / 0.33 of the median grey level".
All gradient and zero-crossing detectors here use the same rule after normalising their response so
that an ideal step of height A gives a response A, so detectors can be compared at the same
sensitivity (``step_hi = 0.33 * median``, ``step_lo = 0.5 * step_hi``).
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage as ndi

# ============================================================================================
# helpers
# ============================================================================================


def _as_mask(mask, shape):
    if mask is None:
        return np.ones(shape[:2], bool)
    return np.asarray(mask).astype(bool)


def fill_outside(img: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
    """Replace every pixel outside ``mask`` by its nearest pixel inside the mask.

    Stops the garment outline from becoming a strong step edge and stops background colour from
    bleeding into the garment when the image is blurred or Fourier transformed.
    """
    if mask is None or mask.all() or not mask.any():
        return img.copy()
    idx = ndi.distance_transform_edt(~mask, return_distances=False, return_indices=True)
    return img[idx[0], idx[1]]


def masked_gaussian(img: np.ndarray, mask: np.ndarray | None, sigma: float) -> np.ndarray:
    """Gaussian blur that only averages garment pixels (normalised convolution)."""
    f = img.astype(np.float32)
    if mask is None:
        return cv2.GaussianBlur(f, (0, 0), sigma)
    m = mask.astype(np.float32)
    num = cv2.GaussianBlur(f * (m[..., None] if f.ndim == 3 else m), (0, 0), sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigma)
    den = np.maximum(den, 1e-4)
    return num / (den[..., None] if f.ndim == 3 else den)


def to_gray(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 -> grey uint8 (same weights as OpenCV)."""
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def _lab(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)


def _unlab(lab):
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def _apply_L(rgb, fn, mask=None):
    """Apply fn(L_uint8) -> L_uint8 on the L channel of LAB and rebuild the RGB image."""
    lab = _lab(fill_outside(rgb, mask))
    lab[..., 0] = fn(lab[..., 0])
    out = _unlab(lab)
    if mask is not None:
        out = np.where(mask[..., None], out, rgb)
    return out


# ============================================================================================
# enhancement (syllabus Unit I: histogram processing)
# ============================================================================================


def hist_equalize(rgb, mask=None, space: str = "L"):
    """Histogram equalisation. ``space='L'``: equalise the L channel of LAB (colour kept);
    ``space='rgb'``: equalise each RGB channel separately (changes hue). The CDF is built from
    garment pixels only."""
    m = _as_mask(mask, rgb.shape)

    def eq(ch):
        hist = np.bincount(ch[m].ravel(), minlength=256).astype(np.float64)
        cdf = hist.cumsum()
        cdf = (cdf - cdf[cdf > 0].min()) / max(cdf[-1] - cdf[cdf > 0].min(), 1)
        lut = np.clip(np.round(cdf * 255), 0, 255).astype(np.uint8)
        return lut[ch]

    if space == "rgb":
        out = np.stack([eq(rgb[..., c]) for c in range(3)], -1)
        return np.where(m[..., None], out, rgb)
    return _apply_L(rgb, eq, mask)


def clahe(rgb, mask=None, clip: float = 2.0, tile: int = 8):
    """Contrast-limited adaptive histogram equalisation on the L channel of LAB."""
    c = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile))
    return _apply_L(rgb, c.apply, mask)


def gamma_correct(rgb, gamma="auto", mask=None):
    """Power-law correction out = 255 (in/255)^gamma. gamma < 1 brightens, > 1 darkens.
    ``gamma='auto'`` picks gamma so the mean grey level inside the mask becomes 0.5."""
    m = _as_mask(mask, rgb.shape)
    if gamma == "auto":
        mean = float(to_gray(rgb)[m].mean()) / 255.0
        mean = min(max(mean, 0.02), 0.98)
        gamma = float(np.clip(np.log(0.5) / np.log(mean), 0.4, 2.5))
    lut = (255.0 * (np.arange(256) / 255.0) ** gamma).clip(0, 255).astype(np.uint8)
    return lut[rgb]


def grey_world(rgb, mask=None):
    """Grey-world white balance: scale channels so the mean R, G, B inside the mask are equal.
    (Assumes the average scene colour is grey; wrong for a single strongly coloured garment.)"""
    m = _as_mask(mask, rgb.shape)
    mean = rgb[m].reshape(-1, 3).mean(0)
    gain = mean.mean() / np.maximum(mean, 1e-3)
    return np.clip(rgb.astype(np.float32) * gain, 0, 255).astype(np.uint8)


def white_patch(rgb, mask=None, percentile: float = 99.0):
    """White-patch (max-RGB) white balance: the ``percentile`` of each channel is mapped to 255."""
    m = _as_mask(mask, rgb.shape)
    top = np.percentile(rgb[m].reshape(-1, 3), percentile, axis=0)
    gain = 255.0 / np.maximum(top, 1.0)
    return np.clip(rgb.astype(np.float32) * gain, 0, 255).astype(np.uint8)


def retinex(rgb, mask=None, sigmas=(0.02, 0.08, 0.25), clip_pct: float = 1.0):
    """Multi-scale Retinex: log(I) - log(Gaussian(I)) averaged over scales, then stretched to
    0..255 with a 1%/99% colour balance. ``sigmas`` are fractions of the longest image side.
    One scale gives single-scale Retinex."""
    m = _as_mask(mask, rgb.shape)
    work = fill_outside(rgb, mask).astype(np.float32) + 1.0
    side = max(rgb.shape[:2])
    acc = np.zeros_like(work)
    for s in sigmas:
        acc += np.log(work) - np.log(masked_gaussian(work, mask, max(1.0, s * side)) + 1e-3)
    acc /= len(sigmas)
    out = np.empty_like(acc)
    for c in range(3):
        lo, hi = np.percentile(acc[..., c][m], (clip_pct, 100 - clip_pct))
        out[..., c] = (acc[..., c] - lo) / max(hi - lo, 1e-6)
    return np.where(m[..., None], np.clip(out * 255, 0, 255).astype(np.uint8), rgb)


# ============================================================================================
# restoration (denoising)
# ============================================================================================


def denoise(rgb, method="median", k: int = 5, mask=None, strength: float = 6.0):
    """Denoise a colour image.

    median    : median over k x k (impulse and JPEG block noise; edges kept better than mean)
    gaussian  : Gaussian k x k (linear, blurs edges)
    bilateral : edge-preserving; space sigma = k, colour sigma = 25 grey levels, diameter k
    nlm       : non-local means (OpenCV fastNlMeansDenoisingColored, filter strength ``strength``)
    """
    src = fill_outside(rgb, mask)
    if method == "median":
        out = cv2.medianBlur(src, k)
    elif method == "gaussian":
        out = cv2.GaussianBlur(src, (k, k), 0)
    elif method == "bilateral":
        out = cv2.bilateralFilter(src, k, 25, k)
    elif method == "nlm":
        out = cv2.fastNlMeansDenoisingColored(src, None, strength, strength, 7, 21)
    else:
        raise ValueError(method)
    if mask is not None:
        out = np.where(mask[..., None], out, rgb)
    return out


# ============================================================================================
# shading removal (folds, uneven light)
# ============================================================================================


def _luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)


def _apply_gain(rgb, ratio, mask):
    out = np.clip(rgb.astype(np.float32) * ratio[..., None], 0, 255).astype(np.uint8)
    return out if mask is None else np.where(mask[..., None], out, rgb)


def colour_regions(rgb, mask, k: int = 3, seed: int = 0):
    """Split the garment into k colour regions (k-means in Lab on a 1/4-size median-blurred copy,
    fixed seed). Returns an int label image (-1 outside the mask)."""
    m = _as_mask(mask, rgb.shape)
    small = cv2.resize(cv2.medianBlur(fill_outside(rgb, mask), 5), None, fx=0.25, fy=0.25,
                       interpolation=cv2.INTER_AREA)
    lab_s = _lab(small).reshape(-1, 3).astype(np.float32)
    msk_s = cv2.resize(m.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    pts = lab_s[msk_s.ravel()]
    if len(pts) < k * 10:
        return np.where(m, 0, -1)
    cv2.setRNGSeed(seed)
    _, _, cen = cv2.kmeans(pts, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5),
                           3, cv2.KMEANS_PP_CENTERS)
    lab_full = _lab(cv2.medianBlur(fill_outside(rgb, mask), 5)).astype(np.float32)
    d = ((lab_full[:, :, None, :] - cen[None, None, :, :]) ** 2).sum(-1)
    return np.where(m, d.argmin(-1), -1)


def remove_shading_divide(rgb, mask=None, sigma_frac: float = 0.12, ratio_clip=(0.4, 2.5),
                          regions: int = 1):
    """Flat-field by division. The illumination is a very blurred copy of the luminance
    (masked Gaussian, sigma = sigma_frac x longest side). Each pixel is multiplied by
    mean_luma / blurred_luma, so chromaticity is kept and slow brightness changes (folds, lighting
    gradients) go away. A large print also lowers the blurred estimate, so very large sigma is safer
    for printed garments.

    regions > 1: the garment is first split into ``regions`` colour regions and the illumination
    is estimated inside each region only (normalised convolution per region, target = region mean),
    so a colour-block garment (white upper / dark lower) keeps its blocks. With regions=1 the whole
    garment is treated as one fabric and the blocks are flattened into one grey level (a failure)."""
    m = _as_mask(mask, rgb.shape)
    y = _luma(rgb)
    sigma = max(2.0, sigma_frac * max(rgb.shape[:2]))
    if regions <= 1:
        illum = masked_gaussian(y, mask, sigma)
        target = float(y[m].mean())
        ratio = np.clip(target / np.maximum(illum, 1.0), *ratio_clip)
        return _apply_gain(rgb, ratio, mask)
    lab_img = colour_regions(rgb, mask, regions)
    ratio = np.ones(y.shape, np.float32)
    for r in range(regions):
        mr = lab_img == r
        if mr.sum() < 0.005 * m.sum():
            continue
        illum = masked_gaussian(y, mr, sigma)
        ratio[mr] = np.clip(float(y[mr].mean()) / np.maximum(illum[mr], 1.0), *ratio_clip)
    return _apply_gain(rgb, ratio, mask)


def remove_shading_homomorphic(rgb, mask=None, d0_frac: float = 0.03, gamma_low: float = 0.5,
                               gamma_high: float = 1.5, c: float = 1.0):
    """Homomorphic filtering in the Fourier domain. Luminance = illumination x reflectance, so in
    the log domain they add; illumination is low frequency, reflectance (texture, print) high
    frequency. A Gaussian high-emphasis filter
        H(u,v) = (gamma_high - gamma_low) (1 - exp(-c D^2 / D0^2)) + gamma_low
    attenuates low frequencies (gamma_low < 1) and boosts high ones (gamma_high > 1).
    D0 = d0_frac x longest side, in cycles per image. The image is reflect-padded before the FFT."""
    m = _as_mask(mask, rgb.shape)
    work = fill_outside(rgb, mask)
    y = _luma(work)
    h, w = y.shape
    ph, pw = h // 2, w // 2
    yp = np.pad(np.log1p(y), ((ph, ph), (pw, pw)), mode="reflect")
    H, W = yp.shape
    F = np.fft.fftshift(np.fft.fft2(yp))
    u = (np.arange(H) - H // 2)[:, None]
    v = (np.arange(W) - W // 2)[None, :]
    D2 = u.astype(np.float64) ** 2 + v.astype(np.float64) ** 2
    d0 = max(1.0, d0_frac * max(h, w) * (max(H, W) / max(h, w)))
    Hf = (gamma_high - gamma_low) * (1 - np.exp(-c * D2 / d0 ** 2)) + gamma_low
    yo = np.real(np.fft.ifft2(np.fft.ifftshift(F * Hf)))[ph:ph + h, pw:pw + w]
    yo = np.expm1(yo).astype(np.float32)
    # keep the mean luminance of the garment
    yo = yo * (float(y[m].mean()) / max(float(yo[m].mean()), 1e-3))
    ratio = np.clip(yo / np.maximum(y, 1.0), 0.3, 3.0)
    return _apply_gain(rgb, ratio, mask)


# ============================================================================================
# smoothing before edge detection (syllabus Unit I: convolution, filtering)
# ============================================================================================


def smooth_gray(gray: np.ndarray, kind: str = "gaussian", k: int = 5) -> np.ndarray:
    """Smooth a uint8 grey image. kind: none, mean (box), median, gaussian (sigma from k, as
    cv2.GaussianBlur with sigma=0), bilateral (diameter k, sigma_colour 25, sigma_space k)."""
    if kind == "none":
        return gray.copy()
    if kind == "mean":
        return cv2.blur(gray, (k, k))
    if kind == "median":
        return cv2.medianBlur(gray, k)
    if kind == "gaussian":
        return cv2.GaussianBlur(gray, (k, k), 0)
    if kind == "bilateral":
        return cv2.bilateralFilter(gray, k, 25, k)
    raise ValueError(kind)


# ============================================================================================
# edge detectors (syllabus Unit II)
# ============================================================================================

# Gradient kernels; the divisor makes the response of an ideal step of height A equal A.
_KERNELS = {
    "sobel": (np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32), 4.0),
    "prewitt": (np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], np.float32), 3.0),
    "scharr": (np.array([[-3, 0, 3], [-10, 0, 10], [-3, 0, 3]], np.float32), 16.0),
}


def auto_canny(gray: np.ndarray, sigma: float = 0.33, ref_level: float | None = None) -> np.ndarray:
    """Canny with thresholds from the median grey level; identical rule to the pipeline's
    ``_auto_canny`` (median over grey > 0 unless ``ref_level`` is given). Returns 0/255 uint8."""
    if ref_level is None:
        ref_level = float(np.median(gray[gray > 0])) if np.any(gray > 0) else 128.0
    low = int(max(0, (1.0 - sigma) * ref_level))
    high = int(min(255, (1.0 + sigma) * ref_level))
    return cv2.Canny(gray, low, high)


def _nms(mag, gx, gy):
    """Non-maximum suppression along the gradient direction (4 quantised directions)."""
    ang = np.rad2deg(np.arctan2(gy, gx)) % 180.0
    q = (((ang + 22.5) // 45) % 4).astype(np.int8)
    p = np.pad(mag, 1)
    c = p[1:-1, 1:-1]
    pairs = {
        0: (p[1:-1, 2:], p[1:-1, :-2]),
        1: (p[2:, 2:], p[:-2, :-2]),
        2: (p[2:, 1:-1], p[:-2, 1:-1]),
        3: (p[2:, :-2], p[:-2, 2:]),
    }
    keep = np.zeros(mag.shape, bool)
    for k, (a, b) in pairs.items():
        keep |= (q == k) & (c >= a) & (c >= b)
    return np.where(keep, mag, 0.0)


def _hysteresis(resp, lo, hi):
    """Hysteresis with 8-connectivity: keep weak (>=lo) components that contain a strong (>=hi) pixel."""
    weak = (resp >= lo).astype(np.uint8)
    n, lab = cv2.connectedComponents(weak, connectivity=8)
    if n <= 1:
        return np.zeros(resp.shape, np.uint8)
    strong_labels = np.unique(lab[resp >= hi])
    strong_labels = strong_labels[strong_labels > 0]
    return (np.isin(lab, strong_labels).astype(np.uint8)) * 255


def _gradient_edges(gray, kind, lo, hi, thin=True):
    g = gray.astype(np.float32)
    ker, norm = _KERNELS[kind]
    gx = cv2.filter2D(g, -1, ker, borderType=cv2.BORDER_REFLECT)
    gy = cv2.filter2D(g, -1, ker.T, borderType=cv2.BORDER_REFLECT)
    mag = np.hypot(gx, gy) / norm
    if thin:
        mag = _nms(mag, gx, gy)
    return _hysteresis(mag, lo, hi)


_ZC_GAIN: dict = {}


def _zero_cross_response(R: np.ndarray) -> np.ndarray:
    """Per-pixel strength of a zero crossing: size of the jump of R across the sign change,
    assigned to the pixel with the smaller |R|. Looks right and down."""
    out = np.zeros(R.shape, np.float32)
    for dy, dx in ((0, 1), (1, 0)):
        a = R[: R.shape[0] - dy, : R.shape[1] - dx]
        b = R[dy:, dx:]
        cross = (a * b) < 0
        jump = np.abs(a - b) * cross
        pick_a = np.abs(a) <= np.abs(b)
        sa = out[: R.shape[0] - dy, : R.shape[1] - dx]
        sb = out[dy:, dx:]
        np.maximum(sa, np.where(pick_a, jump, 0), out=sa)
        np.maximum(sb, np.where(~pick_a, jump, 0), out=sb)
    return out


def _second_derivative(gray, kind, sigma, sigma2):
    g = gray.astype(np.float32)
    if kind == "laplacian":
        return cv2.Laplacian(g, cv2.CV_32F, ksize=1, borderType=cv2.BORDER_REFLECT)
    if kind == "log":
        return cv2.Laplacian(cv2.GaussianBlur(g, (0, 0), sigma), cv2.CV_32F, ksize=1,
                             borderType=cv2.BORDER_REFLECT)
    if kind == "dog":
        return cv2.GaussianBlur(g, (0, 0), sigma) - cv2.GaussianBlur(g, (0, 0), sigma2)
    raise ValueError(kind)


def _zc_gain(kind, sigma, sigma2):
    """Jump of the zero-crossing response for an ideal step of height 1 (calibration)."""
    key = (kind, sigma, sigma2)
    if key not in _ZC_GAIN:
        step = np.zeros((48, 48), np.float32)
        step[:, 24:] = 100.0
        zc = _zero_cross_response(_second_derivative(step, kind, sigma, sigma2))
        _ZC_GAIN[key] = float(zc[24, 8:40].max()) / 100.0
    return _ZC_GAIN[key]


def _zero_cross_edges(gray, kind, lo, hi, sigma=1.5, sigma2=2.4):
    R = _second_derivative(gray, kind, sigma, sigma2)
    z = _zero_cross_response(R) / _zc_gain(kind, sigma, sigma2)
    return _hysteresis(z, lo, hi)


def _canny_pyramid(gray, ref_level, mode, levels=3):
    """Canny on a Gaussian pyramid (scale space). Level 0 is the full image, level i is blurred and
    halved i times; each level uses the auto-Canny rule with the same ``ref_level``.
    mode 'or' : union of all levels (coarse edges upsampled, location error up to 2^i pixels)
    mode 'and': level-0 edges kept only if a level-1 edge lies within 3 px (scale-consistent edges)."""
    h, w = gray.shape
    cur = gray
    maps = []
    for i in range(levels):
        e = auto_canny(cur, ref_level=ref_level)
        if i:
            e = cv2.resize(e, (w, h), interpolation=cv2.INTER_NEAREST)
        maps.append(e)
        cur = cv2.pyrDown(cur)
    if mode == "or":
        out = maps[0].copy()
        for e in maps[1:]:
            out = np.maximum(out, e)
        return out
    support = cv2.dilate(maps[1], np.ones((7, 7), np.uint8))
    return np.where(support > 0, maps[0], 0).astype(np.uint8)


def detect_edges(gray: np.ndarray, method: str = "canny", mask: np.ndarray | None = None,
                 sigma: float = 0.33, log_sigma: float = 1.5, dog_sigmas=(1.0, 1.6)) -> np.ndarray:
    """Binary edge map (0/255 uint8) of a uint8 grey image (already smoothed by the caller).

    method: sobel, prewitt, scharr (gradient magnitude, NMS thinning, hysteresis);
            laplacian, log, dog (zero crossings of the second derivative, hysteresis);
            canny (pipeline's auto-Canny); canny_pyr_and, canny_pyr_or (Canny on a pyramid).
    Thresholds follow the shared step rule in the module docstring, with the reference grey level
    = median grey inside ``mask`` (or over grey > 0 when no mask is given). ``sigma`` is the Canny
    band width (0.33 as in the pipeline). The outline of ``mask`` is not suppressed here; erode
    the mask and AND it with the result if the garment border must be ignored.
    """
    m = _as_mask(mask, gray.shape)
    ref = float(np.median(gray[m])) if m.any() else 128.0
    ref = max(ref, 1.0)
    hi = sigma * ref
    lo = 0.5 * hi
    if method in _KERNELS:
        return _gradient_edges(gray, method, lo, hi)
    if method == "laplacian":
        return _zero_cross_edges(gray, "laplacian", lo, hi)
    if method == "log":
        return _zero_cross_edges(gray, "log", lo, hi, sigma=log_sigma)
    if method == "dog":
        return _zero_cross_edges(gray, "dog", lo, hi, sigma=dog_sigmas[0], sigma2=dog_sigmas[1])
    if method == "canny":
        return auto_canny(gray, sigma=sigma, ref_level=ref)
    if method == "canny_pyr_and":
        return _canny_pyramid(gray, ref, "and")
    if method == "canny_pyr_or":
        return _canny_pyramid(gray, ref, "or")
    raise ValueError(method)


EDGE_DETECTORS = ["sobel", "prewitt", "scharr", "laplacian", "log", "dog", "canny",
                  "canny_pyr_and", "canny_pyr_or"]
SMOOTHERS = [("none", 0)] + [(kind, k) for kind in ("mean", "median", "gaussian", "bilateral")
                             for k in (3, 5, 9)]

# ============================================================================================
# chains
# ============================================================================================

ENHANCERS = {
    "none": lambda im, m=None: im.copy(),
    "hist_eq_L": lambda im, m=None: hist_equalize(im, m, "L"),
    "hist_eq_rgb": lambda im, m=None: hist_equalize(im, m, "rgb"),
    "clahe_L_2": lambda im, m=None: clahe(im, m, 2.0, 8),
    "clahe_L_4": lambda im, m=None: clahe(im, m, 4.0, 8),
    "gamma_0.7": lambda im, m=None: gamma_correct(im, 0.7, m),
    "gamma_1.5": lambda im, m=None: gamma_correct(im, 1.5, m),
    "gamma_auto": lambda im, m=None: gamma_correct(im, "auto", m),
    "grey_world": grey_world,
    "white_patch": white_patch,
    "retinex_ssr": lambda im, m=None: retinex(im, m, sigmas=(0.08,)),
    "retinex_msr": lambda im, m=None: retinex(im, m),
    "denoise_median5": lambda im, m=None: denoise(im, "median", 5, m),
    "denoise_gauss5": lambda im, m=None: denoise(im, "gaussian", 5, m),
    "denoise_bilateral9": lambda im, m=None: denoise(im, "bilateral", 9, m),
    "denoise_nlm": lambda im, m=None: denoise(im, "nlm", 5, m, strength=6.0),
    "shading_divide": remove_shading_divide,
    "shading_divide_regions": lambda im, m=None: remove_shading_divide(im, m, regions=3),
    "shading_homomorphic": remove_shading_homomorphic,
}


def apply_chain(rgb: np.ndarray, steps, mask=None) -> np.ndarray:
    """Run named enhancers from ``ENHANCERS`` in order, e.g.
    ``apply_chain(img, ["denoise_bilateral9", "shading_divide", "grey_world"], mask)``."""
    out = rgb
    for s in steps:
        out = ENHANCERS[s](out, mask)
    return out


# ============================================================================================
# recommended entry point (updated after the P03 study; see REPORT.md)
# ============================================================================================

# Best fold-safe combination of the P03 study (bilateral 9 + Laplacian zero crossings): design-edge F1 0.734,
# fold false-edge rate 0.646 % (0.059 % on the plain c_002), against 0.630 / 1.024 % / 0.090 % for the
# pipeline's Gaussian 5 + auto-Canny. For contiguous contours use ("bilateral", 9) + "canny" or "canny_pyr_and".
RECOMMENDED = {"smooth": ("bilateral", 9), "detector": "laplacian"}
# Colour reading: only edge-preserving denoising and per-region shading removal kept colour fidelity
# (clean DeltaE2000 0.47, flatness ratio 0.89, print contrast kept 1.00).
RECOMMENDED_COLOUR_CHAIN = ["denoise_bilateral9", "shading_divide_regions"]


def prepare_for_colour(rgb: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Image to read fabric colours from: bilateral 9 denoise, then shading removal per colour region.
    Does NOT white-balance or equalise (those raised DeltaE2000 from 0.2 to 4-26 in the P03 study)."""
    return apply_chain(rgb, RECOMMENDED_COLOUR_CHAIN, mask)


def design_edges(rgb: np.ndarray, mask: np.ndarray, border_px: int | None = None,
                 smooth: tuple | None = None, detector: str | None = None,
                 shading: str | None = None) -> np.ndarray:
    """Edge map of print/design edges inside the garment, 0/255 uint8.

    Steps: optional shading removal -> grey -> smoothing -> detector -> mask eroded by
    ``border_px`` (default 1.2 % of the longest side, at least 3 px) so the garment's own outline is
    not reported. ``smooth`` = (kind, k), ``detector`` = name in ``EDGE_DETECTORS``.
    """
    smooth = smooth or RECOMMENDED["smooth"]
    detector = detector or RECOMMENDED["detector"]
    mask = mask.astype(bool)
    if border_px is None:
        border_px = max(3, int(round(0.012 * max(mask.shape))))
    img = apply_chain(rgb, [shading], mask) if shading else rgb
    g = smooth_gray(to_gray(fill_outside(img, mask)), *smooth)
    e = detect_edges(g, detector, mask)
    inner = cv2.erode(mask.astype(np.uint8), cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * border_px + 1, 2 * border_px + 1))) > 0
    return np.where(inner, e, 0).astype(np.uint8)
