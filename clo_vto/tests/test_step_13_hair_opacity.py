"""Step 13 must never cost a shopper their try-on.

It is a cosmetic step that runs after simulation, so the contract is absolute: every path
returns True, and `final_glb_path` is set only when there is genuinely a better file to
ship. Most of these tests are therefore about the ways it is allowed to give up.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clo_vto.native_vto import step_13_hair_opacity as step13  # noqa: E402


def _ctx(tmp_path, **overrides):
    output_dir = tmp_path / 'run'
    output_dir.mkdir(exist_ok=True)
    defaults = dict(output_dir=output_dir, avatar_path=tmp_path / 'avatar.avt',
                    glb_path=None, textured_glb_path=None, final_glb_path=None,
                    skip_glb_postprocess=False)
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _touch(path: Path, payload: bytes = b'x') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


# --- the source GLB it operates on ----------------------------------------------------

def test_the_textured_glb_is_preferred_over_the_raw_export(tmp_path):
    raw = _touch(tmp_path / 'raw.glb')
    textured = _touch(tmp_path / 'textured.glb')
    ctx = _ctx(tmp_path, glb_path=raw, textured_glb_path=textured)
    assert step13._source_glb(ctx) == textured


def test_the_raw_export_is_used_when_step_12_produced_nothing(tmp_path):
    raw = _touch(tmp_path / 'raw.glb')
    assert step13._source_glb(_ctx(tmp_path, glb_path=raw)) == raw


def test_a_path_that_points_at_nothing_is_not_a_source(tmp_path):
    ctx = _ctx(tmp_path, textured_glb_path=tmp_path / 'missing.glb')
    assert step13._source_glb(ctx) is None


# --- every way of giving up, all of which must still return True ----------------------

def test_it_returns_true_when_post_processing_is_disabled(tmp_path):
    ctx = _ctx(tmp_path, skip_glb_postprocess=True)
    assert step13.run(ctx) is True
    assert ctx.final_glb_path is None


def test_it_returns_true_when_there_is_no_glb(tmp_path):
    ctx = _ctx(tmp_path)
    assert step13.run(ctx) is True
    assert ctx.final_glb_path is None


def test_it_returns_true_when_the_avatar_is_not_an_avt(tmp_path):
    """The faced.glb rung of the resolution ladder has no container to read alphas from."""
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'),
               avatar_path=_touch(tmp_path / 'faced.glb'))
    assert step13.run(ctx) is True
    assert ctx.final_glb_path is None


def test_it_returns_true_when_the_avatar_file_is_gone(tmp_path):
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'),
               avatar_path=tmp_path / 'vanished.avt')
    assert step13.run(ctx) is True
    assert ctx.final_glb_path is None


def test_it_returns_true_when_the_patch_raises(tmp_path, monkeypatch):
    """A corrupt GLB must be a cosmetic loss, not a failed render."""
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'),
               avatar_path=_touch(tmp_path / 'avatar.avt'))

    def boom(*args, **kwargs):
        raise RuntimeError('corrupt GLB')

    monkeypatch.setattr('face_fitting.export_glb.patch_hair_alpha', boom)
    assert step13.run(ctx) is True
    assert ctx.final_glb_path is None


def test_it_returns_true_and_ships_nothing_when_no_hair_matched(tmp_path, monkeypatch):
    """A garment-only scene with no avatar hair must leave the previous GLB alone."""
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'),
               avatar_path=_touch(tmp_path / 'avatar.avt'))
    out = ctx.output_dir / step13.OUTPUT_NAME

    def no_hair(source, avatar, out_path, log, hair_texture_size=None):
        _touch(out_path)
        return SimpleNamespace(glb=str(out_path), images_patched=[], warnings=[])

    monkeypatch.setattr('face_fitting.export_glb.patch_hair_alpha', no_hair)
    assert step13.run(ctx) is True
    assert ctx.final_glb_path is None, 'nothing was patched, so nothing should be shipped'
    assert out.exists(), 'the file may exist; it just must not become the shipped one'


def test_it_returns_true_when_the_patch_writes_no_file(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'),
               avatar_path=_touch(tmp_path / 'avatar.avt'))

    def nothing(source, avatar, out_path, log, hair_texture_size=None):
        return SimpleNamespace(glb=None, images_patched=[], warnings=['could not save'])

    monkeypatch.setattr('face_fitting.export_glb.patch_hair_alpha', nothing)
    assert step13.run(ctx) is True
    assert ctx.final_glb_path is None


# --- the one path where it does ship something ----------------------------------------

def test_a_successful_patch_becomes_the_shipped_glb(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'),
               avatar_path=_touch(tmp_path / 'avatar.avt'))

    def patched(source, avatar, out_path, log, hair_texture_size=None):
        _touch(out_path, b'patched glb')
        return SimpleNamespace(glb=str(out_path), warnings=[],
                               images_patched=[{'albedo_entry': 'hair_main.jpg'},
                                               {'albedo_entry': 'hair_cap.jpg'}])

    monkeypatch.setattr('face_fitting.export_glb.patch_hair_alpha', patched)
    assert step13.run(ctx) is True
    assert ctx.final_glb_path == ctx.output_dir / step13.OUTPUT_NAME
    assert ctx.final_glb_path.read_bytes() == b'patched glb'


def test_it_downscales_hair_to_keep_the_file_near_its_original_size(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'),
               avatar_path=_touch(tmp_path / 'avatar.avt'))
    seen = {}

    def record(source, avatar, out_path, log, hair_texture_size=None):
        seen['size'] = hair_texture_size
        _touch(out_path)
        return SimpleNamespace(glb=str(out_path), warnings=[],
                               images_patched=[{'albedo_entry': 'hair_main.jpg'}])

    monkeypatch.setattr('face_fitting.export_glb.patch_hair_alpha', record)
    step13.run(ctx)
    assert seen['size'] == step13.HAIR_TEXTURE_SIZE == 1024


def test_the_step_is_registered_last_in_the_pipeline():
    """It must run after simulation and after texturing, or it patches a stale file."""
    from clo_vto.native_vto import pipeline
    source = Path(pipeline.__file__).read_text(encoding='utf-8')
    assert '(14, step_13_hair_opacity)' in source
    assert source.index('step_12_texture_glb),') < source.index('step_13_hair_opacity),')


# --- step 14: the texture budget ------------------------------------------------------

from clo_vto.native_vto import step_14_glb_budget as step14  # noqa: E402


def _report(before, after, output):
    return SimpleNamespace(before_bytes=before, after_bytes=after, output=output,
                           warnings=[], saved_fraction=1.0 - after / before)


def test_the_budget_runs_on_step_13s_output_when_there_is_one(tmp_path):
    hair = _touch(tmp_path / 'hair.glb')
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'), final_glb_path=hair)
    assert step14._source_glb(ctx) == hair


def test_the_budget_falls_back_down_the_same_chain(tmp_path):
    textured = _touch(tmp_path / 'textured.glb')
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'), textured_glb_path=textured)
    assert step14._source_glb(ctx) == textured


def test_the_budget_returns_true_with_no_glb(tmp_path):
    assert step14.run(_ctx(tmp_path)) is True


def test_the_budget_returns_true_when_disabled(tmp_path):
    assert step14.run(_ctx(tmp_path, skip_glb_postprocess=True)) is True


def test_the_budget_returns_true_when_optimizing_raises(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'))

    def boom(*args, **kwargs):
        raise RuntimeError('unreadable buffer')

    monkeypatch.setattr('face_fitting.optimize_glb.optimize', boom)
    assert step14.run(ctx) is True
    assert ctx.final_glb_path is None


def test_a_worthwhile_saving_becomes_the_shipped_file(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'))

    def shrink(source, out_path, budget, log=None):
        _touch(out_path, b'smaller')
        return _report(36_700_000, 16_200_000, str(out_path))

    monkeypatch.setattr('face_fitting.optimize_glb.optimize', shrink)
    assert step14.run(ctx) is True
    assert ctx.final_glb_path == ctx.output_dir / step14.OUTPUT_NAME


def test_a_negligible_saving_is_not_worth_re_encoding(tmp_path, monkeypatch):
    """Re-encoding costs a generation of quality; 2% is not worth paying it for."""
    ctx = _ctx(tmp_path, glb_path=_touch(tmp_path / 'raw.glb'))

    def barely(source, out_path, budget, log=None):
        _touch(out_path)
        return _report(1_000_000, 980_000, str(out_path))

    monkeypatch.setattr('face_fitting.optimize_glb.optimize', barely)
    assert step14.run(ctx) is True
    assert ctx.final_glb_path is None


def test_the_budget_keeps_the_face_at_full_resolution():
    """The face albedo is the identity; everything upstream exists to get it right."""
    assert step14.BUDGET['face_colour'] == 2048
    assert step14.BUDGET['base_colour'] < step14.BUDGET['face_colour']
    assert step14.BUDGET['data_map'] < step14.BUDGET['base_colour']


def test_the_budget_runs_after_hair_opacity():
    from clo_vto.native_vto import pipeline
    source = Path(pipeline.__file__).read_text(encoding='utf-8')
    assert source.index('step_13_hair_opacity),') < source.index('step_14_glb_budget),')
