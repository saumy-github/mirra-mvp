"""Shape constants reverse-engineered from the CLO 3D default t-shirt block.

Source: CLO Standalone 2026.0.300 default t-shirt, exported as AAMA/ASTM DXF
(AC1009 / R12), size M.  Every number in `CloDraftConfig` was fitted directly
to the layer-1 boundary polylines of front_panel.dxf / back_panel.dxf /
sleeve_left.dxf, not chosen by eye.

Two ideas carry most of the realism:

1. Every curved edge in the CLO block is a single cubic Bezier (the back
   armhole is two).  Fitting each one gave a max residual below 0.5 mm across
   the whole block, so the control points below reproduce CLO's curves rather
   than approximating them.

   Handles are stored as (dx, dy) offsets from their anchor point, normalised
   by the width and height of that edge's bounding box.  This is what a
   pattern grader does by hand: the curve shears with the box as the block is
   graded, so the same constants work at any size.

2. Cap ease is NEGATIVE and lives entirely above the notches.  In the CLO
   block the sleeve cap is 12.68 mm SHORTER than the armhole it is sewn to
   (-2.25%), and below the notches the two seams match to within 0.05 mm.
   That is the standard jersey-knit set-in sleeve rule and it is the opposite
   of the +3.5 cm woven-tailoring ease the previous generator searched for.

Units are millimetres throughout, matching CLO's own DXF export.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

Vec2 = Tuple[float, float]


# --------------------------------------------------------------------------- #
# Input measurements                                                            #
# --------------------------------------------------------------------------- #

@dataclass
class CloBlockMeasurements:
    """Independent pattern dimensions, in millimetres.

    These are the only true degrees of freedom.  Everything else — shoulder
    drop, back neck width, back shoulder width, sleeve cap height, sleeve cap
    peak offset — is derived, either from a fitted ratio in `CloDraftConfig`
    or, for the cap, by solving the seam-length constraint.

    Conventions
    -----------
    All width fields are HALF or FLAT measurements taken on the pattern piece,
    not body girths:

      half_chest_width     one body panel's half-width at the chest line.
                           Front + back = the full tube, so the finished
                           garment chest girth is 4 x this value.

      shoulder_half_width  centre-front to the FRONT shoulder point.  The back
                           shoulder point is derived by adding
                           `back_shoulder_widen_mm`.

      neck_half_width      centre-front to the FRONT neck point.  The back
                           neck point is derived by adding
                           `back_neck_widen_mm`.

      bicep_full_width     the UNFOLDED sleeve width at the bicep line, i.e.
                           the full tube circumference laid flat.  Note this
                           is twice the convention used by the older
                           GarmentMeasurements.bicep_width.

      wrist_full_width     unfolded sleeve width at the wrist, measured as the
                           straight chord between the two wrist corners.

    Vertical fields:

      garment_length       hem to the neck point (the shoulder reference
                           line), measured at centre.
      armhole_depth        shoulder point down to the chest line.
      underarm_to_wrist    sleeve underarm point down to the wrist line.

    Cap height is deliberately absent: it is solved, not specified.
    """

    half_chest_width: float
    hem_half_width: float
    garment_length: float
    shoulder_half_width: float
    neck_half_width: float
    neck_depth_front: float
    neck_depth_back: float
    armhole_depth: float
    bicep_full_width: float
    wrist_full_width: float
    underarm_to_wrist: float

    label: str = "M"

    # ---------------------------------------------------------------- #
    def validate(self) -> None:
        """Raise ValueError on measurement sets that cannot produce a block."""
        if self.shoulder_half_width <= self.neck_half_width:
            raise ValueError(
                "shoulder_half_width must exceed neck_half_width "
                f"({self.shoulder_half_width} <= {self.neck_half_width})"
            )
        if self.half_chest_width <= self.shoulder_half_width:
            raise ValueError(
                "half_chest_width must exceed shoulder_half_width "
                f"({self.half_chest_width} <= {self.shoulder_half_width})"
            )
        if self.wrist_full_width >= self.bicep_full_width:
            raise ValueError(
                "wrist_full_width must be less than bicep_full_width "
                f"({self.wrist_full_width} >= {self.bicep_full_width})"
            )
        for name in ("garment_length", "armhole_depth", "underarm_to_wrist",
                     "neck_depth_front", "neck_depth_back", "hem_half_width"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.neck_depth_back >= self.neck_depth_front:
            raise ValueError(
                "neck_depth_back must be shallower than neck_depth_front"
            )

    # ---------------------------------------------------------------- #
    @classmethod
    def clo_default_M(cls) -> "CloBlockMeasurements":
        """The exact size-M block measured out of the CLO reference DXFs.

        Generating from this and diffing against the source DXF is the
        regression test in validate_against_reference.py.
        """
        return cls(
            half_chest_width=290.0975,
            hem_half_width=269.9999,
            garment_length=718.5886,
            shoulder_half_width=233.2811,
            neck_half_width=97.8661,
            neck_depth_front=101.0923,
            neck_depth_back=36.5000,
            armhole_depth=252.1610,
            bicep_full_width=490.2734,
            wrist_full_width=384.3506,
            underarm_to_wrist=125.6077,
            label="M",
        )

    # ---------------------------------------------------------------- #
    @classmethod
    def from_body(
        cls,
        chest_girth: float,
        shoulder_span: float,
        back_length: float,
        *,
        chest_ease: float = 160.0,
        fit: str = "regular",
    ) -> "CloBlockMeasurements":
        """Rough body-to-block mapping for when only body measurements exist.

        This is a convenience seed, NOT a fitted grading rule — the CLO
        reference gave us exactly one size, so the proportions here are simply
        the size-M block's own ratios applied to a new chest.  Treat the
        output as a starting point to be corrected once real graded sizes are
        available.

        Parameters are body measurements in millimetres:
          chest_girth   full chest circumference
          shoulder_span full shoulder point to shoulder point across the back
          back_length   nape to desired hem
        """
        ref = cls.clo_default_M()
        half_chest = (chest_girth + chest_ease) / 4.0
        k = half_chest / ref.half_chest_width
        if fit == "slim":
            k *= 0.96
        elif fit == "relaxed":
            k *= 1.05

        return cls(
            half_chest_width=half_chest,
            hem_half_width=half_chest * (ref.hem_half_width / ref.half_chest_width),
            garment_length=back_length,
            shoulder_half_width=shoulder_span / 2.0,
            neck_half_width=(shoulder_span / 2.0)
            * (ref.neck_half_width / ref.shoulder_half_width),
            neck_depth_front=ref.neck_depth_front * k,
            neck_depth_back=ref.neck_depth_back * k,
            armhole_depth=ref.armhole_depth * k,
            bicep_full_width=ref.bicep_full_width * k,
            wrist_full_width=ref.wrist_full_width * k,
            underarm_to_wrist=ref.underarm_to_wrist * k,
            label=fit,
        )


# --------------------------------------------------------------------------- #
# Fitted shape constants                                                        #
# --------------------------------------------------------------------------- #

@dataclass
class CloDraftConfig:
    """Every shape constant fitted from the CLO reference block.

    Defaults reproduce the CLO size-M draft to sub-millimetre accuracy.
    Override individual fields for a different garment character (a boxier
    tee, a deeper armhole, a flatter cap) without touching the generator.
    """

    # ------------------------------------------------------------------ #
    # Shoulder                                                            #
    # ------------------------------------------------------------------ #
    # Drop divided by run.  The CLO block measures 0.399791, i.e. a clean
    # 2:5 slope (21.79 deg).  Front and back use the same value: the two
    # shoulder seams in the reference differ by 0.005 mm in length.
    shoulder_slope: float = 0.399791

    # The back shoulder line is not longer than the front, it is shifted
    # outboard.  Applying the same offset to the back neck point and the back
    # shoulder point keeps the two shoulder seams exactly equal in length,
    # which is marginally cleaner than CLO's own 0.005 mm discrepancy.
    back_neck_widen_mm: float = 4.9416
    back_shoulder_widen_mm: float = 4.9025
    # CLO's own offsets differ slightly (4.9806 at the neck, 4.9025 at the
    # shoulder point), which leaves a 0.005 mm front/back shoulder seam
    # mismatch. Holding them equal removes it; the default value above is the
    # mean of CLO's two, so each landmark is within 0.04 mm of the reference.
    equal_shoulder_seams: bool = True

    # ------------------------------------------------------------------ #
    # Necklines — box is (neck_half_width, neck_depth)                     #
    # ------------------------------------------------------------------ #
    # Anchors: p0 = centre neck low point, p3 = neck/shoulder point.
    # c1 is offset from p0, c2 from p3, each normalised by (W, H).
    front_neck_c1: Vec2 = (0.345835, 0.003749)
    front_neck_c2: Vec2 = (-0.107898, -0.851297)
    back_neck_c1: Vec2 = (0.385308, 0.011738)
    back_neck_c2: Vec2 = (-0.270741, -1.090053)

    # ------------------------------------------------------------------ #
    # Armholes — box is (chest_half - shoulder_half, armhole_depth)        #
    # ------------------------------------------------------------------ #
    # Front is a single cubic, walked shoulder point -> underarm.  The very
    # long, nearly horizontal c2 handle is what produces the deep scoop that
    # meets the chest line tangentially.
    front_armhole_c1: Vec2 = (-0.282054, -0.105917)
    front_armhole_c2: Vec2 = (-1.840874, 0.014668)

    # Back is two cubics.  The split sits 73.4% of the way down from the
    # shoulder and only 0.98 mm outboard of it: the upper section runs almost
    # straight down, then the lower section scoops out to the underarm.
    back_armhole_split: Vec2 = (0.018905, -0.734346)
    back_armhole_upper_c1: Vec2 = (-0.260342, -0.191932)
    back_armhole_upper_c2: Vec2 = (-0.153904, 0.113161)
    back_armhole_lower_c1: Vec2 = (0.160653, -0.137009)
    back_armhole_lower_c2: Vec2 = (-0.580635, 0.046989)

    # ------------------------------------------------------------------ #
    # Sleeve cap — box is (cap half width, cap height)                     #
    # ------------------------------------------------------------------ #
    # Front half walked underarm -> peak; back half walked peak -> underarm.
    # Both are single cubics with an inflection, giving the classic S.
    cap_front_c1: Vec2 = (0.522683, 0.309352)
    cap_front_c2: Vec2 = (-0.338712, -0.046924)
    cap_back_c1: Vec2 = (0.392062, -0.041149)
    cap_back_c2: Vec2 = (-0.387426, 0.232161)

    # ------------------------------------------------------------------ #
    # Sleeve underarm and wrist                                            #
    # ------------------------------------------------------------------ #
    # The wrist is not centred under the bicep line.  Total taper splits
    # 53.84% to the front, 46.16% to the back.
    sleeve_front_taper_frac: float = 0.538377
    # The wrist line bows upward at its midpoint by this fraction of the
    # wrist chord (6.49 mm on the reference block).
    wrist_rise_frac: float = 0.016898
    # Underarm seams in the reference bow outward by ~0.57 mm over 138 mm.
    # Below 0.5% of the seam length, so they are drafted straight.
    underarm_straight: bool = True

    # ------------------------------------------------------------------ #
    # Cap ease and notches                                                 #
    # ------------------------------------------------------------------ #
    # Negative: the cap is shorter than the armhole and gets stretched in.
    # Expressed as a fraction of the matching armhole arc.
    cap_ease_front_frac: float = -0.018438
    cap_ease_back_frac: float = -0.027143

    # Notch distance from the underarm point, measured along the seam.
    # The CLO block puts all four notches at 170 mm, which is 0.674177 of the
    # armhole depth.  Tying it to armhole depth reproduces 170.0 exactly at
    # size M and keeps the notch below the cap inflection when graded.
    # GRADING CAVEAT: with a single reference size we cannot tell whether
    # CLO holds 170 mm absolute or scales it.  Set notch_absolute_mm to
    # override with a fixed distance.
    notch_frac_of_armhole_depth: float = 0.674177
    notch_absolute_mm: float | None = None
    # The back carries a double notch; this is the gap between the pair.
    back_notch_gap_mm: float = 10.0

    # ------------------------------------------------------------------ #
    # Cap solver                                                           #
    # ------------------------------------------------------------------ #
    # Cap height divided by bicep width outside this band means the solve
    # found a mathematically valid but unwearable sleeve — usually because the
    # bicep is too narrow for the armhole it has to fill. Warned, not raised:
    # a designer may legitimately want an unusual cap.
    cap_height_ratio_band: Tuple[float, float] = (0.16, 0.38)
    cap_solve_tol_mm: float = 0.01
    cap_solve_max_iter: int = 60
    # Starting guesses, as fractions of the reference block.
    cap_height_start_frac_of_bicep: float = 0.243781
    peak_offset_start_frac_of_half_bicep: float = 0.040714

    # ------------------------------------------------------------------ #
    # Construction / internal lines (DXF layer 8)                          #
    # ------------------------------------------------------------------ #
    hem_fold_offsets_mm: Tuple[float, ...] = (15.0, 20.0)
    sleeve_hem_fold_offsets_mm: Tuple[float, ...] = (21.75, 26.75)
    grainline_length_mm: float = 180.0
    emit_internal_lines: bool = True

    # ------------------------------------------------------------------ #
    # Output                                                              #
    # ------------------------------------------------------------------ #
    # Points sampled per Bezier segment when tessellating for DXF/SVG.
    # CLO's own export uses roughly 30 per armhole; 24 keeps residuals well
    # under 0.1 mm.
    n_fit: int = 24
    # CLO exports the sewing line only, with no seam allowance in the file.
    seam_allowance_mm: float = 0.0

    def __post_init__(self) -> None:
        if not 0.05 <= self.shoulder_slope <= 0.90:
            raise ValueError(f"shoulder_slope {self.shoulder_slope} out of range")
        if not -0.10 <= self.cap_ease_front_frac <= 0.10:
            raise ValueError("cap_ease_front_frac must be within +/-10%")
        if not -0.10 <= self.cap_ease_back_frac <= 0.10:
            raise ValueError("cap_ease_back_frac must be within +/-10%")
        if self.n_fit < 8:
            raise ValueError("n_fit below 8 will visibly facet the curves")

    # ---------------------------------------------------------------- #
    def notch_distance(self, armhole_depth: float) -> float:
        """Arc distance from the underarm point to the first notch."""
        if self.notch_absolute_mm is not None:
            return float(self.notch_absolute_mm)
        return armhole_depth * self.notch_frac_of_armhole_depth


# Convenience presets -------------------------------------------------------- #

def relaxed_tee() -> CloDraftConfig:
    """Boxier: straighter back armhole, slightly flatter cap."""
    cfg = CloDraftConfig()
    cfg.cap_ease_front_frac = -0.012
    cfg.cap_ease_back_frac = -0.020
    cfg.cap_height_start_frac_of_bicep = 0.225
    return cfg


def woven_tee() -> CloDraftConfig:
    """For non-stretch fabric: positive cap ease so the cap can be eased in."""
    cfg = CloDraftConfig()
    cfg.cap_ease_front_frac = 0.012
    cfg.cap_ease_back_frac = 0.016
    return cfg
