"""A synthetic person with exactly known cross-sections, rendered as front/side masks.

Lets us test the measurement maths end to end without photos or MediaPipe.
"""
from __future__ import annotations

import numpy as np

from photo_measurement.capture import Observation
from photo_measurement.geometry import ellipse_circumference

PX_PER_CM = 4.0
TOP_PAD_CM = 10.0
HEIGHT_CM = 175.0

# (y_cm from head top, full width cm, full depth cm) of the torso, linearly interpolated.
TORSO = [(24, 13, 12), (26, 40, 22), (45, 34, 25), (60, 28, 20), (72, 31, 22), (82, 36, 24), (92, 34, 22)]
# per-leg (y_cm, width, depth)
LEG = [(92, 17, 18), (100, 16, 17), (128, 10, 11), (140, 13, 12), (167, 7, 7), (175, 9, 24)]
NECK = (12.0, 11.0)
LEG_OFFSET_CM = 9.0
SH_Y, HIP_Y, EAR_Y, CROTCH_Y = 26.0, 88.0, 12.0, 92.0
ARM = [(17, SH_Y), (26, 55), (33, 80)]  # shoulder, elbow, wrist (x offset, y) in cm
ARM_THICK = (9.0, 6.0)


def _interp(table, y):
    ys = [r[0] for r in table]
    return [float(np.interp(y, ys, [r[i] for r in table])) for i in (1, 2)]


def true_girth(y_cm: float) -> float:
    w, d = _interp(TORSO, y_cm)
    return ellipse_circumference(w, d)


def _px(v_cm: float) -> int:
    return int(round(v_cm * PX_PER_CM))


def _make(view: str, hand: bool = False) -> Observation:
    H = _px(HEIGHT_CM + 2 * TOP_PAD_CM)
    W = _px(120)
    cx = W / 2
    mask = np.zeros((H, W), bool)

    def fill(y_cm, x0_cm, x1_cm):
        y = _px(y_cm + TOP_PAD_CM)
        mask[y, max(0, int(round(cx + x0_cm * PX_PER_CM))):int(round(cx + x1_cm * PX_PER_CM))] = True

    for y in range(_px(HEIGHT_CM)):
        ycm = y / PX_PER_CM
        if ycm < 22:  # head ellipse
            r = 1 - ((ycm - 11) / 11) ** 2
            hw = (8 if view == "front" else 10) * np.sqrt(max(r, 0))
            if hw > 0:
                fill(ycm, -hw, hw)
        if 16 <= ycm < 24:
            hw = (NECK[0] if view == "front" else NECK[1]) / 2
            fill(ycm, -hw, hw)
        if 24 <= ycm <= CROTCH_Y:
            w, d = _interp(TORSO, ycm)
            hw = (w if view == "front" else d) / 2
            fill(ycm, -hw, hw)
        if ycm > CROTCH_Y:
            w, d = _interp(LEG, ycm)
            if view == "front":
                for s in (-1, 1):
                    fill(ycm, s * LEG_OFFSET_CM - w / 2, s * LEG_OFFSET_CM + w / 2)
            else:
                fill(ycm, -d / 2, d / 2)

    if hand:  # a hand hanging in front of the thigh in the profile photo (faces right)
        for y in range(_px(80), _px(97)):
            ycm = y / PX_PER_CM
            front_x = _interp(TORSO if ycm <= CROTCH_Y else LEG, ycm)[1] / 2
            fill(ycm, front_x - 1, front_x + 4)

    if view == "front":  # A-pose arms as thick polylines
        import cv2
        m = mask.astype(np.uint8)
        for s in (-1, 1):
            pts = [(int(cx + s * x * PX_PER_CM), _px(y + TOP_PAD_CM)) for x, y in ARM]
            cv2.line(m, pts[0], pts[1], 1, _px(ARM_THICK[0]))
            cv2.line(m, pts[1], pts[2], 1, _px(ARM_THICK[1]))
        mask = m.astype(bool)

    def lm(x_cm, y_cm):
        return (cx + x_cm * PX_PER_CM, (y_cm + TOP_PAD_CM) * PX_PER_CM, 1.0)

    # MediaPipe convention: person's left appears on image right in a front photo.
    sgn = {"left": 1, "right": -1} if view == "front" else {"left": 0, "right": 0}
    landmarks = {"nose": lm(0, 11)}
    for side, s in sgn.items():
        landmarks.update({
            f"{side}_ear": lm(s * 7, EAR_Y),
            f"{side}_shoulder": lm(s * ARM[0][0], SH_Y),
            f"{side}_elbow": lm(s * ARM[1][0], ARM[1][1]),
            f"{side}_wrist": lm(s * ARM[2][0], ARM[2][1]),
            f"{side}_hip": lm(s * LEG_OFFSET_CM, HIP_Y),
            f"{side}_knee": lm(s * LEG_OFFSET_CM, 128),
            f"{side}_ankle": lm(s * LEG_OFFSET_CM, 167),
        })
    return Observation(mask=mask, landmarks=landmarks, image_path=f"synthetic_{view}")


def front() -> Observation:
    return _make("front")


def side(hand: bool = False) -> Observation:
    return _make("side", hand)
