"""Shape configuration for DynamicPatternGenerator.

All parameters are dimensionless fractions (relative to a measurement) or
explicit centimetre values so the config scales automatically with any body
size.  Nothing is a magic constant — every number here can be overridden for
a different garment type by constructing a different CurveConfig.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ArmholeConfig:
    """Per-panel armhole S-curve parameters.

    Both fractions are relative to the armhole geometry, not to any absolute
    size, so the shape scales with the body measurement automatically.
    """
    # Fraction of armhole height at which the deepest concave hollow sits.
    # 0.0 = at the underarm, 1.0 = at the shoulder.
    hollow_position_frac: float = 0.40

    # How deep the hollow reaches inward, as a fraction of the horizontal
    # distance from the underarm edge to the shoulder point.
    hollow_depth_frac: float = 0.18

    # How much the upper section opens/flares outward near the shoulder,
    # as a fraction of the same horizontal distance.  0 = no flare.
    shoulder_flare_frac: float = 0.05


@dataclass
class CurveConfig:
    """All tunable shape parameters for DynamicPatternGenerator.

    Default values produce a well-fitted standard T-shirt.  Pass a custom
    instance to DynamicPatternGenerator for slim-fit, relaxed, or other
    garment types.
    """

    # ------------------------------------------------------------------ #
    # Sleeve cap binary search                                             #
    # ------------------------------------------------------------------ #
    # Initial cap height as fraction of armhole_depth (starting guess).
    cap_height_start_frac: float = 0.35

    # Binary search bracket — cap_height is clamped within these fractions.
    cap_height_min_frac: float = 0.20
    cap_height_max_frac: float = 0.95   # generous ceiling; search narrows it

    # Target extra arc length of sleeve cap over the matched armhole.
    # Industry standard for a set-in sleeve: 3–5 cm of ease.
    cap_ease_cm: float = 3.5

    # Convergence tolerance for the binary search (cm).  Tight enough to
    # be meaningful, loose enough to always converge within max_iter.
    cap_ease_tolerance_cm: float = 0.20

    # Maximum binary-search iterations before giving up.
    cap_search_max_iter: int = 40

    # Ease distribution: fraction of total ease placed at the cap crown
    # (top) vs each side underarm.  Must satisfy:
    #   cap_ease_crown_frac + 2 * cap_ease_side_frac == 1.0
    cap_ease_crown_frac: float = 0.60   # 60% at crown
    cap_ease_side_frac: float = 0.20    # 20% per side (front + back = 40%)

    # ------------------------------------------------------------------ #
    # Armhole S-curves (separate configs for front and back)               #
    # ------------------------------------------------------------------ #
    front_armhole: ArmholeConfig = field(
        default_factory=lambda: ArmholeConfig(
            hollow_position_frac=0.40,
            hollow_depth_frac=0.16,
            shoulder_flare_frac=0.03,
        )
    )
    back_armhole: ArmholeConfig = field(
        default_factory=lambda: ArmholeConfig(
            hollow_position_frac=0.35,   # back hollow sits lower
            hollow_depth_frac=0.20,      # back hollow is deeper
            shoulder_flare_frac=0.08,    # back opens more at shoulder
        )
    )

    # ------------------------------------------------------------------ #
    # Shoulder seam crown                                                  #
    # ------------------------------------------------------------------ #
    # Convex rise at the midpoint of each shoulder seam (cm).
    # Causes the seam to fall to the back of the shoulder in simulation.
    shoulder_crown_cm: float = 0.5

    # ------------------------------------------------------------------ #
    # Side seam waist suppression                                          #
    # ------------------------------------------------------------------ #
    # Inward bow at waist level on each side seam (cm).
    # Set to 0.0 for a boxy/relaxed garment with straight sides.
    side_waist_suppression_cm: float = 0.5

    # ------------------------------------------------------------------ #
    # Neckline                                                             #
    # ------------------------------------------------------------------ #
    # Number of fit points sampled for the neckline spline (higher = smoother).
    neckline_fit_points: int = 20

    # ------------------------------------------------------------------ #
    # Curve tessellation (for SPLINE fit-point export and SVG)             #
    # ------------------------------------------------------------------ #
    # Number of fit points sampled along each curved edge for DXF export.
    # Has no effect on the mathematical shape — only on CLO's approximation.
    curve_fit_points: int = 24
