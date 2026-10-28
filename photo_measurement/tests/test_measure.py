import math

import numpy as np
import pytest

from photo_measurement import calibrate
from photo_measurement.geometry import ellipse_circumference, run_containing, width_perpendicular
from photo_measurement.measure import extract

from . import synthetic as syn


def test_ellipse_circle_and_degenerate():
    assert ellipse_circumference(10, 10) == pytest.approx(math.pi * 10)
    assert ellipse_circumference(10, 0) == pytest.approx(20, rel=1e-3)


def test_run_containing_picks_torso_not_arm():
    m = np.zeros((1, 30), bool)
    m[0, 2:5] = m[0, 10:20] = m[0, 25:28] = True
    assert run_containing(m, 0, 15) == (10, 20)


def test_width_perpendicular_on_diagonal_bar():
    import cv2
    m = np.zeros((200, 200), np.uint8)
    cv2.line(m, (20, 20), (180, 180), 1, 20)
    assert width_perpendicular(m.astype(bool), (20, 20), (180, 180), 0.5) == pytest.approx(20, abs=2)


@pytest.fixture(scope="module")
def result():
    return extract(syn.front(), syn.side(), syn.HEIGHT_CM)


def _m(result, key):
    return result.values[key].value_cm


def test_chest_matches_truth(result):
    y = syn.SH_Y + 0.30 * (syn.HIP_Y - syn.SH_Y)
    assert _m(result, "chest") == pytest.approx(syn.true_girth(y), abs=1.0)


def test_waist_is_narrowest_and_matches_truth(result):
    assert _m(result, "waist") == pytest.approx(syn.true_girth(60), abs=1.5)


def test_hip_is_widest_and_matches_truth(result):
    assert _m(result, "hip") == pytest.approx(syn.true_girth(82), abs=1.5)


def test_neck(result):
    assert _m(result, "neck") == pytest.approx(ellipse_circumference(*syn.NECK), abs=1.0)


def test_lengths(result):
    (x0, y0), (x1, y1), (x2, y2) = syn.ARM
    shoulder_top = y0 - syn.ARM_THICK[0] / 2  # arm drawn with round caps
    arm = math.dist((x0, shoulder_top), (x1, y1)) + math.dist((x1, y1), (x2, y2))
    assert _m(result, "left_arm_length") == pytest.approx(arm, abs=0.5)
    assert _m(result, "right_arm_length") == pytest.approx(arm, abs=0.5)
    assert _m(result, "inseam") == pytest.approx(syn.HEIGHT_CM - syn.CROTCH_Y, abs=0.5)
    assert _m(result, "left_outside_leg") == pytest.approx(syn.HEIGHT_CM - 60, abs=2.0)


def test_thigh_and_calf(result):
    w, d = syn._interp(syn.LEG, 140)
    assert _m(result, "left_calf") == pytest.approx(ellipse_circumference(w, d), abs=1.5)
    assert 40 < _m(result, "left_thigh") < 60


def test_calibration_removes_bias():
    rng = np.random.default_rng(0)
    actual = rng.uniform(80, 110, 30)
    rows = [{"measurement": "chest", "predicted_cm": a * 0.95 - 2 + rng.normal(0, 0.3), "actual_cm": a}
            for a in actual]
    c = calibrate.fit(rows)["chest"]
    assert c["mae_after_cm"] < 0.5 < c["mae_before_cm"]
    assert calibrate.apply({"chest": 0.95 * 100 - 2}, {"chest": c})["chest"] == pytest.approx(100, abs=0.5)


def test_clean_capture_has_no_pose_warnings(result):
    assert result.warnings == []


def test_pose_check_rejects_t_pose_and_frontal_side_photo():
    from photo_measurement.measure import check_pose

    f = syn.front()
    for s in ("left", "right"):  # raise wrists to shoulder height -> T-pose
        x, _, v = f.landmarks[f"{s}_wrist"]
        f.landmarks[f"{s}_wrist"] = (x, f.landmarks[f"{s}_shoulder"][1], v)
    warnings = check_pose(f, syn.front())
    assert any("left arm" in w for w in warnings) and any("right arm" in w for w in warnings)
    assert any("not in profile" in w for w in warnings)


def test_bust_and_under_bust(result):
    import numpy as np
    # synthetic torso is fullest at y=45 cm (t ~ 0.31)
    assert _m(result, "bust") == pytest.approx(syn.true_girth(45), abs=1.5)
    assert _m(result, "under_bust") < _m(result, "bust")


def test_profile_fields_and_skin_tone(result):
    from photo_measurement.report import body_shape_type, format_text, to_profile

    f = syn.front()
    f.image = np.zeros(f.mask.shape + (3,), np.uint8)
    f.image[f.mask] = (0xC6, 0x86, 0x42)
    profile = to_profile(result.as_dict(), f, weight_kg=72)
    assert profile["skin_tone_hex"] == "#C68642"
    assert profile["leg_length_cm"] == round(_m(result, "inseam"), 1)
    assert profile["weight_kg"] == 72
    assert set(profile) == {"height_cm", "weight_kg", "shoulder_width_cm", "waist_circumference_cm",
                            "hip_circumference_cm", "leg_length_cm", "chest_circumference_cm",
                            "bust_circumference_cm", "under_bust_circumference_cm", "body_shape_type",
                            "skin_tone_hex"}
    assert "waist" in format_text(result.as_dict(), profile)
    assert body_shape_type(92, 66, 94) == "hourglass"
    assert body_shape_type(88, 72, 102) == "pear"
    assert body_shape_type(105, 85, 95) == "inverted_triangle"
    assert body_shape_type(95, 93, 96) == "apple"
    assert body_shape_type(90, 78, 92) == "rectangle"


def test_hand_in_side_photo_does_not_inflate_hip_or_thigh(result):
    with_hand = extract(syn.front(), syn.side(hand=True), syn.HEIGHT_CM)
    # Uncorrected, the hand adds ~6 cm to the hip. The straight bridge across the hand
    # flattens the hip's own curve slightly, so allow ~1 cm.
    for k in ("hip", "left_thigh", "waist"):
        assert with_hand.values[k].value_cm == pytest.approx(_m(result, k), abs=1.5), k


def test_shoe_sole_rescales_lengths(result):
    shod = extract(syn.front(), syn.side(), syn.HEIGHT_CM - 3, shoe_sole_cm=3)
    assert shod.values["inseam"].value_cm == pytest.approx(_m(result, "inseam"), abs=0.1)


def test_bicep_ignores_torso_when_arm_touches_body():
    import cv2
    m = np.zeros((300, 300), np.uint8)
    m[:, 100:200] = 1                       # torso
    cv2.line(m, (210, 0), (210, 299), 1, 20)  # arm touching torso (merged in the mask)
    w = width_perpendicular(m.astype(bool), (210, 0), (210, 299), 0.5, free_side_only=True)
    assert w == pytest.approx(20, abs=2)


def test_touching_thighs_are_split_at_the_centre_line(result):
    f = syn.front()
    # close the gap between the legs a little below the crotch (thighs touching)
    y0, y1 = (int((syn.CROTCH_Y + d + syn.TOP_PAD_CM) * syn.PX_PER_CM) for d in (3, 20))
    cx = f.mask.shape[1] // 2
    f.mask[y0:y1, cx - 12:cx + 12] = True
    touching = extract(f, syn.side(), syn.HEIGHT_CM)
    for k in ("left_thigh", "right_thigh"):
        assert touching.values[k].value_cm == pytest.approx(_m(result, k), abs=1.5), k
