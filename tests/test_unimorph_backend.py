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
# Imperative aspect disambiguation (real ell.tsv data — δροσίζω was resolved
# by cross-referencing its own IPFV/PFV rows; see backend.py's Imp branch).
# ---------------------------------------------------------------------------

def test_ell_imperative_aspect_imp_disambiguates(backend):
    """δροσίζω 2sg imperative + Aspect=Imp → only the continuous form."""
    result = backend.inflect(
        "δροσίζω", {"Mood": "Imp", "Aspect": "Imp", "Person": "2", "Number": "Sing"}, "verb", language="ell"
    )
    assert result == {"δρόσιζε"}


def test_ell_imperative_aspect_perf_disambiguates(backend):
    """δροσίζω 2sg imperative + Aspect=Perf → only the aorist form."""
    result = backend.inflect(
        "δροσίζω", {"Mood": "Imp", "Aspect": "Perf", "Person": "2", "Number": "Sing"}, "verb", language="ell"
    )
    assert result == {"δρόσισε"}


def test_ell_imperative_no_aspect_still_returns_union(backend):
    """δροσίζω 2sg imperative with no Aspect → unchanged legacy behavior (both forms)."""
    result = backend.inflect(
        "δροσίζω", {"Mood": "Imp", "Person": "2", "Number": "Sing"}, "verb", language="ell"
    )
    assert result == {"δρόσιζε", "δρόσισε"}


def test_ell_imperative_aspect_unresolved_lemma_returns_empty(backend):
    """συζητάω's 2sg imperative rows bundle both aspects in each comma-separated form
    ('συζήτα, συζήταγε' / 'συζήτησε, συζήτα') and were left unresolved on purpose (see
    patch_imp_aspect.py) — querying with Aspect must return empty rather than guessing,
    since no V;2;SG;{aspect};IMP tag exists. The no-aspect query is untouched (still the
    pre-existing 3-way union)."""
    result = backend.inflect(
        "συζητάω", {"Mood": "Imp", "Aspect": "Perf", "Person": "2", "Number": "Sing"}, "verb", language="ell"
    )
    assert result == set()

    result = backend.inflect(
        "συζητάω", {"Mood": "Imp", "Person": "2", "Number": "Sing"}, "verb", language="ell"
    )
    assert result == {"συζήτα", "συζήταγε", "συζήτησε"}


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


# ---------------------------------------------------------------------------
# get_tags
# ---------------------------------------------------------------------------

def test_get_tags_noun_row_count(backend):
    assert len(backend.get_tags("noun")) == 10


def test_get_tags_adj_row_count(backend):
    assert len(backend.get_tags("adjective")) == 40


def test_get_tags_verb_returns_empty(backend):
    assert backend.get_tags("verb") == []


def test_get_tags_unknown_pos_returns_empty(backend):
    assert backend.get_tags("particle") == []


def test_get_tags_noun_no_gender_field(backend):
    for t in backend.get_tags("noun"):
        assert "Gender" not in t


def test_get_tags_noun_first_row(backend):
    tags = backend.get_tags("noun")
    assert tags[0] == {"tag": "N;NOM;SG", "Case": "Nom", "Number": "Sing"}


def test_get_tags_noun_last_row(backend):
    tags = backend.get_tags("noun")
    assert tags[-1] == {"tag": "N;VOC;PL", "Case": "Voc", "Number": "Plur"}


def test_get_tags_adj_first_10_no_gender(backend):
    tags = backend.get_tags("adjective")
    for t in tags[:10]:
        assert "Gender" not in t


def test_get_tags_adj_rows_10_to_19_masc(backend):
    tags = backend.get_tags("adjective")
    for t in tags[10:20]:
        assert t.get("Gender") == "Masc"


def test_get_tags_adj_rows_20_to_29_fem(backend):
    tags = backend.get_tags("adjective")
    for t in tags[20:30]:
        assert t.get("Gender") == "Fem"


def test_get_tags_adj_rows_30_to_39_neut(backend):
    tags = backend.get_tags("adjective")
    for t in tags[30:40]:
        assert t.get("Gender") == "Neut"


def test_get_tags_noun_roundtrip_grc_boethos(backend):
    """βοηθός nom sg using features from get_tags() returns forms."""
    nom_sg = next(t for t in backend.get_tags("noun") if t["Case"] == "Nom" and t["Number"] == "Sing")
    feats = {k: v for k, v in nom_sg.items() if k != "tag"}
    result = backend.inflect("βοηθός", feats, "noun", language="grc")
    assert result


def test_get_tags_adj_2term_no_gender_slot_populated_grc(backend):
    """ἄγναπτος (2-term): the no-gender nom sg slot is populated."""
    no_gender = next(
        t for t in backend.get_tags("adjective")
        if t["Case"] == "Nom" and t["Number"] == "Sing" and "Gender" not in t
    )
    feats = {k: v for k, v in no_gender.items() if k != "tag"}
    result = backend.inflect("ἄγναπτος", feats, "adjective", language="grc")
    assert result


def test_get_tags_adj_2term_masc_same_as_no_gender_grc(backend):
    """ἄγναπτος (2-term): MASC nom sg falls back to the shared M/F form (same as no-gender slot)."""
    tags = backend.get_tags("adjective")
    no_gender = next(t for t in tags if t["Case"] == "Nom" and t["Number"] == "Sing" and "Gender" not in t)
    masc = next(t for t in tags if t["Case"] == "Nom" and t["Number"] == "Sing" and t.get("Gender") == "Masc")
    feats_ng = {k: v for k, v in no_gender.items() if k != "tag"}
    feats_m = {k: v for k, v in masc.items() if k != "tag"}
    assert backend.inflect("ἄγναπτος", feats_ng, "adjective", language="grc") == \
           backend.inflect("ἄγναπτος", feats_m, "adjective", language="grc")


def test_get_tags_adj_3term_masc_slot_populated_grc(backend):
    """λισσός (3-term): the MASC nom sg slot is populated."""
    masc = next(
        t for t in backend.get_tags("adjective")
        if t["Case"] == "Nom" and t["Number"] == "Sing" and t.get("Gender") == "Masc"
    )
    feats = {k: v for k, v in masc.items() if k != "tag"}
    result = backend.inflect("λισσός", feats, "adjective", language="grc")
    assert result


def test_get_tags_adj_3term_fem_slot_populated_grc(backend):
    """λισσός (3-term): the FEM nom sg slot is populated."""
    fem = next(
        t for t in backend.get_tags("adjective")
        if t["Case"] == "Nom" and t["Number"] == "Sing" and t.get("Gender") == "Fem"
    )
    feats = {k: v for k, v in fem.items() if k != "tag"}
    result = backend.inflect("λισσός", feats, "adjective", language="grc")
    assert result


# --- analyze() ---
# Needs a language bound at construction (self._language), like list_lemmas() --
# there is no per-call language= kwarg, so the bare `backend` fixture (which
# every inflect() test above passes language= to directly) doesn't apply here.

def test_analyze_verb_ell_real_roundtrip():
    """άγω PRS.1SG.IND generates 'άγω'; analyzing it back finds the verb reading."""
    b = UniMorphBackend("ell")
    assert {"lemma": "άγω", "pos": "verb", "tag": "V;1;SG;IPFV;PRS",
            "features": {"Tense": "Pres", "Aspect": "Imp", "Mood": "Ind",
                          "Person": "1", "Number": "Sing", "VerbForm": "Fin"}} \
        in b.analyze("άγω")


def test_analyze_noun_grc_real_roundtrip():
    """βοηθός nom sg is its own bare lemma form in grc.tsv (article-stripped)."""
    b = UniMorphBackend("grc")
    assert {"lemma": "βοηθός", "pos": "noun", "tag": "N;NOM;SG",
            "features": {"Case": "Nom", "Number": "Sing"}} in b.analyze("βοηθός")


def test_analyze_cross_pos_ambiguity_ell():
    """άβαθα is both a noun's own form (several cells share the -α ending)
    and the neuter of the adjective άβαθος -- real ambiguity in the data,
    not a bug; both readings must come back."""
    b = UniMorphBackend("ell")
    results = b.analyze("άβαθα")
    assert any(r["lemma"] == "άβαθα" and r["pos"] == "noun" for r in results)
    assert any(r["lemma"] == "άβαθος" and r["pos"] == "adjective" for r in results)


def test_analyze_unknown_form_returns_empty_list():
    assert UniMorphBackend("ell").analyze("xyzabc") == []


def test_analyze_no_language_bound_returns_empty_list():
    """Matches list_lemmas()'s same requirement: entry-point-instantiated
    backends (bare UniMorphBackend(), no language) can't resolve a dataset."""
    assert UniMorphBackend().analyze("άγω") == []


def test_analyze_result_features_match_tag_to_ud():
    from unimorph_backend_eee.reverse import tag_to_ud
    b = UniMorphBackend("ell")
    for r in b.analyze("άγω"):
        assert r["features"] == tag_to_ud(r["tag"])
