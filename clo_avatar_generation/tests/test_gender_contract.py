"""Steps 03-06 for both genders, offline (no CLO): fetch from a JSON measurement
file, resolve the per-gender base avatar, normalise, build the avt_patch
payload, and patch a real .avt. What only a CLO run can confirm is that the
female base avatar's slots mean what the contract says (see female_note)."""

import json
import logging
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clo_avatar_generation.avatar_runtime import (  # noqa: E402
    avt_patch,
    field_contract,
    step_03_fetch_measurements as step03,
    step_04_resolve_base_avatar as step04,
    step_05_normalize_targets as step05,
    step_06_build_payloads as step06,
)
from clo_avatar_generation.avatar_runtime.context import Step1Context  # noqa: E402

MALE_BASE = REPO_ROOT / "clo_avatar_generation" / "input" / "base-1.avt"
needs_base = pytest.mark.skipif(not MALE_BASE.exists(), reason="base-1.avt not present (gitignored binary)")

COMMON = {"height_cm": 168.0, "weight_kg": 60.0, "shoulder_width_cm": 37.5, "waist_circumference_cm": 70.0,
          "hip_circumference_cm": 96.0, "leg_length_cm": 76.0}


def _ctx(tmp_path: Path, doc: dict) -> Step1Context:
    path = tmp_path / "m.json"
    path.write_text(json.dumps(doc))
    return Step1Context(
        user_id="u_test", requested_run_number=1, base_avatar_path_input=None,
        measurement_file_input=str(path), measurement_apply_mode_input="avt_patch",
        enable_legacy_route=False, active_field_filters=[], interactive=False,
        logger=logging.getLogger("test"),
    )


@pytest.fixture
def female_base(tmp_path, monkeypatch):
    """A stand-in female base avatar (the real one is CLO's FV2 file)."""
    target = tmp_path / "base-female.avt"
    shutil.copy(MALE_BASE, target)
    contract = dict(field_contract.load_field_contract())
    contract["base_avatars"] = {**contract["base_avatars"], "female": str(target)}
    monkeypatch.setattr(field_contract, "load_field_contract", lambda: contract)
    return target


def test_both_genders_are_supported_and_bust_is_female_only():
    assert field_contract.get_supported_genders() == {"male", "female"}
    female = {f["mongo_field"]: f for f in field_contract.get_v1_fields_for_gender("female")}
    male = {f["mongo_field"] for f in field_contract.get_v1_fields_for_gender("male")}
    assert "chest_circumference_cm" in male and "chest_circumference_cm" not in female
    assert female["bust_circumference_cm"]["avt_feature_index"] == 2
    assert not field_contract.is_required(female["under_bust_circumference_cm"])
    slots = [f["avt_feature_index"] for f in female.values() if f.get("avt_feature_index") is not None]
    assert len(slots) == len(set(slots))  # no two female fields write the same slot


@needs_base
def test_female_profile_runs_steps_03_to_06_and_patches_bust_into_slot_2(tmp_path, female_base):
    ctx = _ctx(tmp_path, {"user_id": "u_test", "gender": "female", **COMMON, "bust_circumference_cm": 91.0,
                          "under_bust_circumference_cm": 76.0})
    for step in (step03, step04, step05):
        assert step.run(ctx)
    assert ctx.base_avatar_path == female_base
    assert ctx.resolved_measurement_apply_mode == "avt_patch"

    payload, fields, skipped = step06._build_avt_patch_payload(ctx)
    assert payload["field_indexes"]["Bust"] == 2
    assert "Under Bust" in skipped  # no .avt slot: property/CSV routes only

    out = tmp_path / "patched.avt"
    result = avt_patch.build_patched_avatar(
        female_base, out,
        {k: float(v) for k, v in payload["field_values"].items()}, payload["field_indexes"],
    )
    assert result["patched_values"]["Bust"] == pytest.approx(91.0)
    assert result["patched_values"]["Total Height"] == pytest.approx(168.0)


@needs_base
def test_manual_female_entry_uses_chest_as_bust(tmp_path, female_base):
    ctx = _ctx(tmp_path, {"user_id": "u_test", "gender": "female", **COMMON, "chest_circumference_cm": 89.0})
    for step in (step03, step04, step05):
        assert step.run(ctx)
    assert ctx.normalized_targets["flat_requested_fields"]["Bust"] == 89.0
    assert any("bust" in w for w in ctx.warnings)


def test_missing_female_base_avatar_says_how_to_install_it(tmp_path, monkeypatch):
    contract = dict(field_contract.load_field_contract())
    contract["base_avatars"] = {**contract["base_avatars"], "female": str(tmp_path / "absent.avt")}
    monkeypatch.setattr(field_contract, "load_field_contract", lambda: contract)
    ctx = _ctx(tmp_path, {"user_id": "u_test", "gender": "female", **COMMON, "bust_circumference_cm": 91.0})
    step03.run(ctx)
    with pytest.raises(FileNotFoundError, match="FV2"):
        step04.run(ctx)


@needs_base
def test_male_profile_is_unchanged(tmp_path):
    ctx = _ctx(tmp_path, {"user_id": "u_test", "gender": "male", **COMMON, "chest_circumference_cm": 100.0})
    for step in (step03, step04, step05):
        assert step.run(ctx)
    assert ctx.base_avatar_path == MALE_BASE.resolve()
    payload, _, _ = step06._build_avt_patch_payload(ctx)
    assert payload["field_indexes"] == {"Total Height": 0, "Across Shoulder (Curvilinear)": 36, "Chest": 2,
                                        "Waist": 6, "Low Hip": 8, "Inseam": 26}
