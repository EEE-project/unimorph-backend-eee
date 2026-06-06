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


# ---------------------------------------------------------------------------
# Latin tests
# ---------------------------------------------------------------------------

def test_lat_noun_ablative_returns_forms(backend):
    """puella ablative singular → puellā (real lat.tsv data)."""
    result = backend.inflect("puella", {"Case": "Abl", "Number": "Sing"}, "noun", language="la")
    assert "puellā" in result


def test_lat_noun_ablative_plural(backend):
    result = backend.inflect("puella", {"Case": "Abl", "Number": "Plur"}, "noun", language="la")
    assert "puellīs" in result


def test_lat_adj_three_termination_masc(backend):
    """lūminōsus nom sg masc → lūminōsus (three-termination, MASC entry)."""
    result = backend.inflect("lūminōsus", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "adjective", language="la")
    assert "lūminōsus" in result


def test_lat_adj_three_termination_fem(backend):
    """lūminōsus nom sg fem → lūminōsa (three-termination, FEM entry)."""
    result = backend.inflect("lūminōsus", {"Case": "Nom", "Number": "Sing", "Gender": "Fem"}, "adjective", language="la")
    assert "lūminōsa" in result


def test_lat_adj_two_termination_masc_uses_masc_fem_fallback(backend):
    """algēnsis nom sg masc → algēnsis (two-termination, resolved via MASC+FEM fallback)."""
    result = backend.inflect("algēnsis", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "adjective", language="la")
    assert "algēnsis" in result


def test_lat_adj_two_termination_fem_uses_masc_fem_fallback(backend):
    """algēnsis nom sg fem → algēnsis (two-termination, resolved via MASC+FEM fallback)."""
    result = backend.inflect("algēnsis", {"Case": "Nom", "Number": "Sing", "Gender": "Fem"}, "adjective", language="la")
    assert "algēnsis" in result


def test_lat_verb_raises_pos_not_supported(backend):
    """Latin verbs not supported (different tag structure)."""
    with pytest.raises(PosNotSupportedError):
        backend.inflect("amare", {"Case": "Nom", "Number": "Sing"}, "verb", language="la")


def test_lat_language_code_lat_also_works(backend):
    """'lat' code resolves same as 'la'."""
    result = backend.inflect("puella", {"Case": "Nom", "Number": "Sing"}, "noun", language="lat")
    assert "puella" in result


def test_supported_languages_contains_lat(backend):
    assert "lat" in backend.supported_languages()


# ---------------------------------------------------------------------------
# Russian tests
# ---------------------------------------------------------------------------

def test_rus_noun_ins_sg(backend):
    """работа instrumental singular → работой."""
    result = backend.inflect("работа", {"Case": "Ins", "Number": "Sing"}, "noun", language="ru")
    assert "работой" in result


def test_rus_noun_loc_sg(backend):
    """работа locative/prepositional singular → работе (UD Loc → UniMorph ESS)."""
    result = backend.inflect("работа", {"Case": "Loc", "Number": "Sing"}, "noun", language="ru")
    assert "работе" in result


def test_rus_adj_nom_sg_masc(backend):
    """красивый nominative singular masculine → красивый."""
    result = backend.inflect("красивый", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "adjective", language="ru")
    assert "красивый" in result


def test_rus_adj_nom_sg_fem(backend):
    """красивый nominative singular feminine → красивая."""
    result = backend.inflect("красивый", {"Case": "Nom", "Number": "Sing", "Gender": "Fem"}, "adjective", language="ru")
    assert "красивая" in result


def test_rus_adj_acc_sg_masc_anim(backend):
    """красивый accusative singular masculine animate → красивого."""
    result = backend.inflect("красивый", {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Anim"}, "adjective", language="ru")
    assert "красивого" in result


def test_rus_adj_acc_sg_masc_inan(backend):
    """красивый accusative singular masculine inanimate → красивый."""
    result = backend.inflect("красивый", {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Inan"}, "adjective", language="ru")
    assert "красивый" in result


def test_rus_adj_ins_sg_fem(backend):
    """красивый instrumental singular feminine → красивой."""
    result = backend.inflect("красивый", {"Case": "Ins", "Number": "Sing", "Gender": "Fem"}, "adjective", language="ru")
    assert "красивой" in result


def test_rus_language_code_rus_also_works(backend):
    result = backend.inflect("работа", {"Case": "Nom", "Number": "Sing"}, "noun", language="rus")
    assert "работа" in result


def test_supported_languages_contains_rus(backend):
    assert "rus" in backend.supported_languages()


# ---------------------------------------------------------------------------
# Spanish tests
# ---------------------------------------------------------------------------

def test_spa_noun_fem_sg(backend):
    """casa feminine singular → casa."""
    result = backend.inflect("casa", {"Gender": "Fem", "Number": "Sing"}, "noun", language="es")
    assert "casa" in result


def test_spa_noun_fem_pl(backend):
    """casa feminine plural → casas."""
    result = backend.inflect("casa", {"Gender": "Fem", "Number": "Plur"}, "noun", language="es")
    assert "casas" in result


def test_spa_adj_invariant_masc_fem_fallback(backend):
    """grande plural → grandes (ADJ;PL invariant form via no-gender fallback)."""
    result = backend.inflect("grande", {"Number": "Plur"}, "adjective", language="es")
    assert "grandes" in result


def test_spa_language_code_spa_also_works(backend):
    result = backend.inflect("casa", {"Gender": "Fem", "Number": "Sing"}, "noun", language="spa")
    assert "casa" in result


def test_supported_languages_contains_spa(backend):
    assert "spa" in backend.supported_languages()


# ---------------------------------------------------------------------------
# Turkish tests
# ---------------------------------------------------------------------------

def test_tur_noun_nom_sg(backend):
    """köpek nominative singular → köpek."""
    result = backend.inflect("köpek", {"Case": "Nom", "Number": "Sing"}, "noun", language="tr")
    assert "köpek" in result


def test_tur_noun_loc_sg(backend):
    """köpek locative singular → köpekte."""
    result = backend.inflect("köpek", {"Case": "Loc", "Number": "Sing"}, "noun", language="tr")
    assert "köpekte" in result


def test_tur_noun_dat_pl(backend):
    """köpek dative plural → köpeklere."""
    result = backend.inflect("köpek", {"Case": "Dat", "Number": "Plur"}, "noun", language="tr")
    assert "köpeklere" in result


def test_tur_noun_abl_pl(backend):
    """köpek ablative plural → köpeklerden."""
    result = backend.inflect("köpek", {"Case": "Abl", "Number": "Plur"}, "noun", language="tr")
    assert "köpeklerden" in result


def test_tur_adj_raises_pos_not_supported(backend):
    with pytest.raises(PosNotSupportedError):
        backend.inflect("büyük", {"Case": "Nom", "Number": "Sing"}, "adjective", language="tr")


def test_tur_language_code_tur_also_works(backend):
    result = backend.inflect("köpek", {"Case": "Nom", "Number": "Sing"}, "noun", language="tur")
    assert "köpek" in result


def test_supported_languages_contains_tur(backend):
    assert "tur" in backend.supported_languages()
