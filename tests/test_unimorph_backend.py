"""UniMorphBackend unit tests — _lookup is patched, no external deps required."""
from unittest.mock import patch
import logging

import pytest

from unimorph_backend_eee.backend import UniMorphBackend
from unimorph_backend_eee._exceptions import (
    FeatureNotSupportedError,
    PosNotSupportedError,
    UnsupportedLanguageError,
)

VERB_FEATURES = {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}
NOUN_FEATURES = {"Case": "Gen", "Number": "Sing"}


@pytest.fixture()
def backend():
    return UniMorphBackend()


def test_grc_verb_raises_pos_not_supported(backend):
    with pytest.raises(PosNotSupportedError):
        backend.inflect("λύω", VERB_FEATURES, "verb", language="grc")


def test_grc_verb_emits_warning(backend, caplog):
    with caplog.at_level(logging.WARNING):
        with pytest.raises(PosNotSupportedError):
            backend.inflect("λύω", VERB_FEATURES, "verb", language="grc")
    assert any("grc" in r.message and "verb" in r.message for r in caplog.records)


def test_ell_unsupported_pos_raises(backend):
    with pytest.raises(PosNotSupportedError):
        backend.inflect("ο", {}, "article", language="ell")


def test_unknown_language_raises(backend):
    with pytest.raises(UnsupportedLanguageError):
        backend.inflect("foo", {}, "noun", language="xx")


def test_ell_noun_returns_set(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value={"λόγου"}):
        result = backend.inflect("λόγος", NOUN_FEATURES, "noun", language="ell")
    assert result == {"λόγου"}


def test_empty_result_returns_empty_set(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value=set()):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_unk_sentinel_filtered(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value={"UNK"}):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_empty_string_filtered(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value={""}):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_supported_languages_contains_ell(backend):
    assert "ell" in backend.supported_languages()


def test_supported_languages_excludes_el(backend):
    assert "el" not in backend.supported_languages()


def test_emdash_sentinel_filtered(backend):
    with patch("unimorph_backend_eee.backend._lookup", return_value={"—"}):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_inflect_future_no_aspect_calls_lookup_twice(backend):
    """Future without Aspect → _lookup called twice (IPFV;FUT and PFV;FUT), results unioned."""
    per_tag = {"V;1;SG;IPFV;FUT": {"ακούω"}, "V;1;SG;PFV;FUT": {"ακούσω"}}

    def _side(lemma, tag, language):
        return per_tag.get(tag, set())

    with patch("unimorph_backend_eee.backend._lookup", side_effect=_side) as mock_lookup:
        result = backend.inflect(
            "ακούω",
            {"Tense": "Fut", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
            "verb",
            language="ell",
        )
    assert mock_lookup.call_count == 2
    assert result == {"ακούω", "ακούσω"}


def test_inflect_future_explicit_aspect_calls_lookup_once(backend):
    """Future with explicit Aspect=Imp → _lookup called exactly once."""
    with patch("unimorph_backend_eee.backend._lookup", return_value={"ακούω"}) as mock_lookup:
        result = backend.inflect(
            "ακούω",
            {"Tense": "Fut", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
            "verb",
            language="ell",
        )
    assert mock_lookup.call_count == 1
    assert result == {"ακούω"}
