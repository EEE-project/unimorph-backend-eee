"""Tests for UniMorphBackend str-features path and get_slot_templates()."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from unimorph_backend_eee.backend import UniMorphBackend


@pytest.fixture()
def backend():
    return UniMorphBackend()


def test_inflect_str_features_returns_set(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value={"γυναίκα"}) as mock_lookup:
        result = backend.inflect("γυναίκα", "N;NOM;SG", "noun", language="ell")
    assert result == {"γυναίκα"}
    mock_lookup.assert_called_once_with("γυναίκα", "N;NOM;SG", "ell")


def test_inflect_str_features_nonexistent_tag_returns_empty(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value=set()):
        result = backend.inflect("γυναίκα", "N;NOTEXIST", "noun", language="ell")
    assert result == set()


def test_inflect_str_features_skips_build_tags(backend):
    with patch("unimorph_backend_eee.backend._build_tags") as mock_build, \
         patch("unimorph_backend_eee.backend._lookup", return_value=set()):
        backend.inflect("γυναίκα", "N;NOM;SG", "noun", language="ell")
    mock_build.assert_not_called()


def test_inflect_str_features_ietf_lang_maps_to_iso(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value={"γυναίκα"}) as mock_lookup:
        backend.inflect("γυναίκα", "N;NOM;SG", "noun", language="el")
    _, _, lang_arg = mock_lookup.call_args[0]
    assert lang_arg == "ell"


def test_inflect_str_features_filters_sentinels(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value={"γυναίκα", "UNK", "—", ""}):
        result = backend.inflect("γυναίκα", "N;NOM;SG", "noun", language="ell")
    assert result == {"γυναίκα"}


def test_get_slot_templates_returns_none_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path)
    result = UniMorphBackend("el").get_slot_templates("el", "verb", "en")
    assert result is None


def test_get_slot_templates_delegates_with_iso_code():
    with patch("unimorph_backend_eee.fetch.load_slot_template", return_value=None) as mock_load:
        UniMorphBackend("el").get_slot_templates("el", "verb", "en")
    mock_load.assert_called_once()
    # load_slot_template(pos, terms_lang, lang) — lang is 3rd positional
    call_args = mock_load.call_args[0]
    assert call_args[2] == "ell"


def test_get_slot_templates_returns_list_when_file_exists():
    from eee_project import SlotTemplate
    fake_slots = [SlotTemplate(label="Nom Sg", tag="N;NOM;SG", tag_type="unimorph")]
    with patch("unimorph_backend_eee.fetch.load_slot_template", return_value=fake_slots):
        result = UniMorphBackend("el").get_slot_templates("el", "noun", "en")
    assert result == fake_slots


def test_get_slot_templates_passthrough_for_unknown_lang():
    with patch("unimorph_backend_eee.fetch.load_slot_template", return_value=None) as mock_load:
        UniMorphBackend("ail").get_slot_templates("ail", "verb", "en")
    call_args = mock_load.call_args[0]
    assert call_args[2] == "ail"


def test_inflect_slot_full_stack_unimorph():
    import eee_project as eee
    from unimorph_backend_eee.backend import UniMorphBackend
    from unimorph_backend_eee.fetch import register_language
    from eee_project import SlotTemplate

    register_language("ell")
    eee.register_backend("el", UniMorphBackend())
    slot = SlotTemplate(label="Nom Sg", tag="N;NOM;SG", tag_type="unimorph")
    result = eee.inflect_slot("γυναίκα", slot, "noun", language="el")
    assert isinstance(result, set)
    assert len(result) > 0
