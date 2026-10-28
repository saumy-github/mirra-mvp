"""Front + side observations + known height -> tailoring measurements (cm).

Method: each photo is scaled independently so the silhouette's height equals the
user's stated height. Front view gives transverse widths, side view gives sagittal
depths at the *same anatomical level* (levels are defined relative to the shoulder
and hip landmarks, so they line up across views even if the camera distance
differs). Each girth is the perimeter of the width x depth ellipse. Systematic
error (torso slices aren't true ellipses, clothing, hair) is removed afterwards by
the per-measurement linear calibration in calibrate.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .capture import Observation
from .geometry import (
    ellipse_circumference,
    polyline_length,
    row_extent,
    run_containing,
    runs_in_row,
    vertical_extent,
    width_perpendicular,
)

# Ratio of the unseen axis to the seen axis for limbs we only see in one view.
# Placeholders until calibrate.py has real tape-measured data.
BICEP_DEPTH_RATIO = 0.95
WRIST_DEPTH_RATIO = 1.35  # palms-in A-pose shows the narrow side of the wrist from the front
# A hand in front of the thigh in the side photo sticks out at least this far.
HAND_BUMP_MIN_CM = 2.0


@dataclass
class Measurement:
    value_cm: float
    method: str          # "two_view" | "one_view" | "length" | "input"
    note: str = ""


@dataclass
class MeasurementResult:
    height_cm: float
    values: dict[str, Measurement] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "unit": "cm",
            "height_cm": self.height_cm,
            "measurements": {k: round(m.value_cm, 1) for k, m in self.values.items()},
            "methods": {k: m.method for k, m in self.values.items()},
            "notes": {k: m.note for k, m in self.values.items() if m.note},
            "warnings": self.warnings,
        }


class _View:
    """Helpers for one observation: scale, anatomical levels, centre lines."""

    def __init__(self, obs: Observation, height_cm: float, shoe_sole_cm: float = 0.0):
        self.obs = obs
        self.mask = obs.mask
        self.top, self.bottom = vertical_extent(obs.mask)
        # The silhouette includes shoe soles but the stated height is barefoot.
        self.cm_per_px = (height_cm + shoe_sole_cm) / (self.bottom - self.top)
        self.sh = obs.mid("left_shoulder", "right_shoulder")
        self.hp = obs.mid("left_hip", "right_hip")
        self.ear = obs.mid("left_ear", "right_ear")

    def y_at(self, t: float) -> float:
        """t=0 at shoulder line, t=1 at hip line, extrapolates outside."""
        return self.sh[1] + t * (self.hp[1] - self.sh[1])

    def t_at(self, y: float) -> float:
        return (y - self.sh[1]) / (self.hp[1] - self.sh[1])

    def torso_x(self, y: float) -> float:
        t = self.t_at(y)
        return float(self.sh[0] + t * (self.hp[0] - self.sh[0]))

    def torso_run(self, y: float) -> tuple[int, int] | None:
        return run_containing(self.mask, int(round(y)), self.torso_x(y))

    def torso_width_px(self, y: float) -> float:
        r = self.torso_run(y)
        return float(r[1] - r[0]) if r else 0.0

    def neck_x(self, y: float) -> float:
        u = (y - self.ear[1]) / (self.sh[1] - self.ear[1])
        return float(self.ear[0] + u * (self.sh[0] - self.ear[0]))

    def neck_y(self, u: float) -> float:
        return self.ear[1] + u * (self.sh[1] - self.ear[1])

    def crotch_y(self) -> float:
        """First row below the hips where the gap between the legs opens at the centre
        line and stays open for a few rows (ignores single-row mask noise)."""
        x = int(round(self.hp[0]))
        col = self.mask[int(self.hp[1]):self.bottom, x]
        for i in range(len(col) - 3):
            if not col[i:i + 4].any():
                return float(int(self.hp[1]) + i)
        return float(self.bottom)

    def shoulder_point(self, side: str) -> np.ndarray:
        """Top of the shoulder silhouette straight above the shoulder joint (~acromion)."""
        x, y = self.obs.pt(f"{side}_shoulder")
        col = np.flatnonzero(self.mask[: int(y) + 1, int(round(x))])
        return np.array([x, float(col[0]) if col.size else y])

    def leg_point(self, side: str, r: float) -> np.ndarray:
        """r=0 at hip joint, 1 at knee, 2 at ankle (piecewise linear)."""
        hip, knee, ankle = (self.obs.pt(f"{side}_{j}") for j in ("hip", "knee", "ankle"))
        return hip + r * (knee - hip) if r <= 1 else knee + (r - 1) * (ankle - knee)

    def leg_mid_point(self, r: float) -> np.ndarray:
        return (self.leg_point("left", r) + self.leg_point("right", r)) / 2


def _arm_overlaps(view: _View, y: float, run: tuple[int, int]) -> bool:
    """True if either arm's polyline crosses row y inside the torso run (arms touching body)."""
    for side in ("left", "right"):
        pts = [view.obs.pt(f"{side}_{j}") for j in ("elbow", "wrist")]
        (x0, y0), (x1, y1) = pts
        if min(y0, y1) <= y <= max(y0, y1) and y1 != y0:
            x = x0 + (y - y0) / (y1 - y0) * (x1 - x0)
            if run[0] < x < run[1]:
                return True
    return False


def _without_side_hand(side: Observation, height_cm: float) -> Observation:
    """Arms hang at the sides in the profile photo, so the hand sits in front of the
    thigh and gets counted as hip/thigh depth. Within the hand's height band, clip the
    silhouette's front edge to the straight line joining the edge just above and just
    below the hand. Only removes pixels, never adds them."""
    vis = {s: side.landmarks[f"{s}_wrist"][2] for s in ("left", "right")}
    wrist = side.pt(f"{max(vis, key=vis.get)}_wrist")
    top, bottom = vertical_extent(side.mask)
    body = bottom - top
    y0, y1 = int(wrist[1] - 0.02 * body), int(wrist[1] + 0.12 * body)
    if y0 < top or y1 >= bottom:
        return side
    facing_left = side.pt("nose")[0] < side.mid("left_ear", "right_ear")[0]
    centre_x = side.mid("left_hip", "right_hip")[0]

    def front_edge(y):
        r = run_containing(side.mask, y, centre_x)
        return None if r is None else (r[0] if facing_left else r[1] - 1)

    e0, e1 = front_edge(y0), front_edge(y1)
    if e0 is None or e1 is None:
        return side
    px_per_cm = body / height_cm
    edges = {y: front_edge(y) for y in range(y0, y1 + 1)}
    sign = -1 if facing_left else 1  # +ve protrusion = further in front of the body
    protrusion = {y: sign * (e - (e0 + (e1 - e0) * (y - y0) / (y1 - y0)))
                  for y, e in edges.items() if e is not None}
    if max(protrusion.values(), default=0) < HAND_BUMP_MIN_CM * px_per_cm:
        return side  # front contour is smooth: no hand in front of the body
    # Rows the hand covers; bridge them with the body edge just above and below.
    hand_rows = [y for y, p in protrusion.items() if p > 0.75 * px_per_cm]
    ya, yb = max(y0, hand_rows[0] - 1), min(y1, hand_rows[-1] + 1)
    ea, eb = edges[ya] if edges[ya] is not None else e0, edges[yb] if edges[yb] is not None else e1
    mask = side.mask.copy()
    for y in range(ya, yb + 1):
        edge = int(round(ea + (eb - ea) * (y - ya) / max(1, yb - ya)))
        if facing_left:
            mask[y, :edge] = False
        else:
            mask[y, edge + 1:] = False
    return replace(side, mask=mask)


def _argbest(fn, ts, best=min):
    vals = [(fn(t), t) for t in ts]
    vals = [v for v in vals if v[0] > 0]
    return best(vals)[1] if vals else ts[len(ts) // 2]


def check_pose(front: Observation, side: Observation) -> list[str]:
    """Reject captures that break the protocol, since they would silently give wrong sizes."""
    out = []
    torso_f = front.mid("left_hip", "right_hip")[1] - front.mid("left_shoulder", "right_shoulder")[1]
    sh_w = abs(front.pt("left_shoulder")[0] - front.pt("right_shoulder")[0])
    if torso_f <= 0 or sh_w < 0.45 * torso_f:
        out.append("front: person is not facing the camera squarely")
    for s in ("left", "right"):
        dx, dy = front.pt(f"{s}_wrist") - front.pt(f"{s}_shoulder")
        angle = np.degrees(np.arctan2(abs(dx), dy))  # 0 = hanging straight down
        if not 8 <= angle <= 50:
            out.append(f"front: {s} arm is {angle:.0f} deg from vertical; needs an A-pose (~20-40 deg)")
    torso_s = side.mid("left_hip", "right_hip")[1] - side.mid("left_shoulder", "right_shoulder")[1]
    if torso_s <= 0 or abs(side.pt("left_shoulder")[0] - side.pt("right_shoulder")[0]) > 0.25 * torso_s:
        out.append("side: person is not in profile (shoulders don't overlap)")
    return out


def extract(front: Observation, side: Observation, height_cm: float,
            shoe_sole_cm: float = 0.0) -> MeasurementResult:
    F = _View(front, height_cm, shoe_sole_cm)
    S = _View(_without_side_hand(side, height_cm), height_cm, shoe_sole_cm)
    res = MeasurementResult(height_cm=height_cm)
    res.warnings += [f"front: {w}" for w in front.warnings] + [f"side: {w}" for w in side.warnings]
    res.warnings += check_pose(front, side)
    put = res.values.__setitem__

    def torso_wd(t: float) -> tuple[float, float]:
        return F.torso_width_px(F.y_at(t)) * F.cm_per_px, S.torso_width_px(S.y_at(t)) * S.cm_per_px

    def torso_girth(name: str, t: float, check_arms: bool = True, note: str = "") -> None:
        w, d = torso_wd(t)
        put(name, Measurement(ellipse_circumference(w, d), "two_view",
                              f"width {w:.1f} cm x depth {d:.1f} cm" + (f"; {note}" if note else "")))
        yf = F.y_at(t)
        run = F.torso_run(yf)
        if check_arms and run and _arm_overlaps(F, yf, run):
            res.warnings.append(f"{name}: arm appears to touch the torso in the front photo; "
                                "ask the user to hold arms ~30 degrees away from the body")

    put("height", Measurement(height_cm, "input"))

    # Neck: smallest girth between ears and shoulders, judged on both views so the
    # jaw (side view) and trapezius (front view) are both avoided.
    def neck_wd(u):
        return _neck_width(F, u) * F.cm_per_px, _neck_width(S, u) * S.cm_per_px

    u_neck = _argbest(lambda u: ellipse_circumference(*neck_wd(u)), np.linspace(0.45, 0.85, 17), min)
    w, d = neck_wd(u_neck)
    put("neck", Measurement(ellipse_circumference(w, d), "two_view", f"width {w:.1f} x depth {d:.1f}"))

    # Shoulder point to shoulder point: silhouette width halfway between the top of the
    # shoulders and the shoulder joints (where the shoulder slope turns into the arm).
    sp_y = np.mean([(F.shoulder_point(s)[1] + front.pt(f"{s}_shoulder")[1]) / 2 for s in ("left", "right")])
    put("shoulder_width", Measurement(F.torso_width_px(sp_y) * F.cm_per_px, "length",
                                      "silhouette, shoulder point to shoulder point"))

    # Overarm: around shoulders *including* the arms.
    t = 0.12
    ef, es = row_extent(F.mask, int(F.y_at(t))), row_extent(S.mask, int(S.y_at(t)))
    if ef and es:
        put("overarm", Measurement(
            ellipse_circumference((ef[1] - ef[0]) * F.cm_per_px, (es[1] - es[0]) * S.cm_per_px), "two_view"))

    # Armpit: first level where both arms separate from the torso in the front view.
    # Above it the torso run includes the arms, so no torso girth is taken there.
    t_armpit = next((t for t in np.linspace(0.0, 0.7, 71)
                     if len(runs_in_row(F.mask, int(round(F.y_at(t))))) >= 3), None)
    if t_armpit is None:
        t_armpit = 0.4
        res.warnings.append("arms never separate from the torso in the front photo; chest/bust "
                            "are unreliable. Hold arms further from the body")
    t_top = t_armpit + 0.03
    torso_girth("chest", max(0.30, t_top))
    # Bust: fullest girth in the upper torso (the side view's depth carries the bust
    # prominence). Under-bust: smallest girth just below it.
    girth = lambda t: ellipse_circumference(*torso_wd(t))  # noqa: E731
    t_bust = _argbest(girth, np.linspace(max(0.18, t_top), 0.45, 13), max)
    torso_girth("bust", t_bust, note="fullest upper-torso girth")
    t_under = _argbest(girth, np.linspace(t_bust + 0.04, t_bust + 0.2, 9), min)
    torso_girth("under_bust", t_under, note="narrowest girth below bust; low confidence over clothing")
    t_waist = _argbest(lambda t: F.torso_width_px(F.y_at(t)), np.linspace(0.45, 0.85, 21), min)
    torso_girth("waist", t_waist)
    torso_girth("abdomen", min(t_waist + 0.12, 0.95))

    crotch_f = F.crotch_y()
    t_crotch = F.t_at(crotch_f)
    hip_ts = [t for t in np.linspace(0.85, 1.4, 23) if t < t_crotch - 0.03]
    t_hip = _argbest(lambda t: F.torso_width_px(F.y_at(t)), hip_ts or [1.0], max)
    torso_girth("hip", t_hip)

    # Arms (front view, A-pose keeps them roughly in the image plane).
    for side_name in ("left", "right"):
        sh, el, wr = (front.pt(f"{side_name}_{j}") for j in ("shoulder", "elbow", "wrist"))
        put(f"{side_name}_arm_length", Measurement(
            polyline_length([F.shoulder_point(side_name), el, wr]) * F.cm_per_px, "length",
            "shoulder point -> elbow -> wrist"))
        bw = width_perpendicular(F.mask, sh, el, 0.5, free_side_only=True) * F.cm_per_px
        put(f"{side_name}_bicep", Measurement(ellipse_circumference(bw, bw * BICEP_DEPTH_RATIO), "one_view",
                                              "depth assumed from width; calibrate"))
        ww = width_perpendicular(F.mask, el, wr, 0.92, free_side_only=True) * F.cm_per_px
        put(f"{side_name}_wrist", Measurement(ellipse_circumference(ww, ww * WRIST_DEPTH_RATIO), "one_view",
                                              "depth assumed from width; calibrate"))

    # Legs.
    floor_f = F.bottom
    put("inseam", Measurement((floor_f - crotch_f) * F.cm_per_px, "length"))
    for side_name in ("left", "right"):
        put(f"{side_name}_outside_leg", Measurement((floor_f - F.y_at(t_waist)) * F.cm_per_px, "length",
                                                    "natural waist to floor"))

    hip_y, knee_y = F.hp[1], (front.pt("left_knee")[1] + front.pt("right_knee")[1]) / 2
    r_thigh = float(np.clip((crotch_f + 0.03 * (F.bottom - F.top) - hip_y) / (knee_y - hip_y), 0.05, 0.6))
    for side_name in ("left", "right"):
        put(f"{side_name}_thigh", _leg_girth(F, S, side_name, r_thigh))
        r_calf = _argbest(lambda r: _leg_width(F, side_name, r), np.linspace(1.15, 1.5, 15), max)
        put(f"{side_name}_calf", _leg_girth(F, S, side_name, r_calf))

    return res


def _neck_width(v: _View, u: float) -> float:
    y = v.neck_y(u)
    r = run_containing(v.mask, int(round(y)), v.neck_x(y))
    return float(r[1] - r[0]) if r else 0.0


def _leg_width(v: _View, side: str, r: float) -> float:
    p = v.leg_point(side, r)
    run = run_containing(v.mask, int(round(p[1])), p[0])
    if not run:
        return 0.0
    # Touching thighs merge into one run: split it at the body's centre line.
    mid = float(v.leg_mid_point(r)[0])
    if run[0] < mid < run[1]:
        run = (run[0], mid) if p[0] < mid else (mid, run[1])
    return float(run[1] - run[0])


def _leg_girth(F: _View, S: _View, side: str, r: float) -> Measurement:
    w = _leg_width(F, side, r) * F.cm_per_px
    p = S.leg_mid_point(r)
    run = run_containing(S.mask, int(round(p[1])), p[0])
    d = (run[1] - run[0]) * S.cm_per_px if run else w
    return Measurement(ellipse_circumference(w, d), "two_view", f"width {w:.1f} x depth {d:.1f}")
