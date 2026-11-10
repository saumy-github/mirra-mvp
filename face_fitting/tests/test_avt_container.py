"""The container is the floor everything else stands on: if a patched .avt stops being a
valid .avt, CLO rejects the whole avatar and no amount of correct texture work shows up."""

from __future__ import annotations

import zlib

import pytest

from face_fitting.face_runtime.constants import (AVT_ENTRY_COUNT, AVT_PREFIX_BYTES,
                                                 EYE_ALBEDO_ENTRY, HAIR_MAIN_ALPHA_ENTRY,
                                                 HEAD_ALBEDO_ENTRY)
from face_fitting.io.avt_container import read_avt, write_avt


def test_entry_count_matches_the_measured_template(container):
    assert len(container.entries) == AVT_ENTRY_COUNT


def test_prefix_size_matches_the_measured_template(container):
    assert container.prefix_size == AVT_PREFIX_BYTES


def test_the_entries_the_face_job_patches_all_exist(container):
    for name in (HEAD_ALBEDO_ENTRY, HAIR_MAIN_ALPHA_ENTRY, EYE_ALBEDO_ENTRY):
        assert name in container.names()


def test_untouched_round_trip_is_byte_identical(base_avt_path, tmp_path):
    out = tmp_path / 'round_trip.avt'
    write_avt(read_avt(base_avt_path), out)
    assert out.read_bytes() == base_avt_path.read_bytes()


def test_replaced_entry_reads_back_exactly(container, tmp_path):
    payload = b'not a jpeg, but the container must not care' * 100
    container.replace_entry(HEAD_ALBEDO_ENTRY, payload)
    out = tmp_path / 'patched.avt'
    write_avt(container, out)

    reread = read_avt(out)
    assert reread.read_entry(HEAD_ALBEDO_ENTRY) == payload
    assert len(reread.entries) == AVT_ENTRY_COUNT


def test_replace_updates_the_crc_to_match_the_payload(container):
    payload = b'x' * 5000
    container.replace_entry(HEAD_ALBEDO_ENTRY, payload)
    entry = container.entry(HEAD_ALBEDO_ENTRY)
    assert entry.crc == zlib.crc32(payload) & 0xFFFFFFFF
    assert entry.uncompressed_size == len(payload)
    assert entry.method == 8


def test_a_replace_leaves_every_other_entry_untouched(container, base_avt_path, tmp_path):
    original = read_avt(base_avt_path)
    container.replace_entry(HEAD_ALBEDO_ENTRY, b'replaced')
    out = tmp_path / 'one_entry.avt'
    write_avt(container, out)

    reread = read_avt(out)
    assert reread.names() == original.names()
    for name in original.names():
        if name == HEAD_ALBEDO_ENTRY:
            continue
        assert reread.read_entry(name) == original.read_entry(name), name


def test_replaced_names_reports_only_what_changed(container):
    assert container.replaced_names() == []
    container.replace_entry(EYE_ALBEDO_ENTRY, b'eye')
    container.replace_entry(HEAD_ALBEDO_ENTRY, b'head')
    assert set(container.replaced_names()) == {EYE_ALBEDO_ENTRY, HEAD_ALBEDO_ENTRY}


def test_first_dan_survives_patching_untouched(container, base_avt_path, tmp_path):
    """The geometry brain is 33 MB of opaque data we must never perturb."""
    original_dan = read_avt(base_avt_path).read_entry('first.dan')
    container.replace_entry(HEAD_ALBEDO_ENTRY, b'whatever')
    out = tmp_path / 'dan.avt'
    write_avt(container, out)
    assert read_avt(out).read_entry('first.dan') == original_dan


def test_a_non_avt_file_is_rejected(tmp_path):
    bogus = tmp_path / 'bogus.avt'
    bogus.write_bytes(b'PK\x03\x04 but no AVT magic')
    with pytest.raises(ValueError, match='bad magic'):
        read_avt(bogus)


def test_unknown_entry_raises(container):
    with pytest.raises(KeyError):
        container.read_entry('no_such_texture.jpg')
