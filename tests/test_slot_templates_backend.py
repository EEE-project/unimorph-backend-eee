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


def test_get_slot_templates_noun_returns_list():
    result = UniMorphBackend("el").get_slot_templates("el", "noun", "en")
    assert result is not None
    assert len(result) > 0


def test_get_slot_templates_noun_has_nom_sg():
    result = UniMorphBackend("el").get_slot_templates("el", "noun", "en")
    tags = {s.tag for s in result}
    assert "N;NOM;SG" in tags
    assert "N;ACC;PL" in tags


def test_get_slot_templates_verb_returns_none():
    result = UniMorphBackend("el").get_slot_templates("el", "verb", "en")
    assert result is None


def test_get_slot_templates_terms_lang_ignored():
    r_en = UniMorphBackend("el").get_slot_templates("el", "noun", "en")
    r_ru = UniMorphBackend("el").get_slot_templates("el", "noun", "ru")
    assert [s.tag for s in r_en] == [s.tag for s in r_ru]


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
