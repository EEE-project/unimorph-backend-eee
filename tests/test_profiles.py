"""Tests for profiles.py — loading, caching, schema validation, slot resolution."""
import pytest
from unimorph_backend_eee import profiles
from unimorph_backend_eee.profiles import load_profiles, _clear_profile_cache, _clear_all_hooks, _build_tags
from unimorph_backend_eee._exceptions import FeatureNotSupportedError


@pytest.fixture(autouse=True)
def reset_cache():
    _clear_profile_cache()
    _clear_all_hooks()
    yield
    _clear_profile_cache()
    _clear_all_hooks()


def test_load_profiles_returns_dict_with_expected_keys():
    cfg = load_profiles()
    assert "profiles" in cfg
    assert "languages" in cfg


def test_load_profiles_is_cached():
    cfg1 = load_profiles()
    cfg2 = load_profiles()
    assert cfg1 is cfg2


def test_clear_profile_cache_causes_reload():
    cfg1 = load_profiles()
    _clear_profile_cache()
    cfg2 = load_profiles()
    assert cfg1 is not cfg2


def _write_bad_toml(tmp_path, content: str):
    p = tmp_path / "bad.toml"
    p.write_bytes(content.encode("utf-8"))
    return p


def test_load_profiles_raises_on_unknown_slot(tmp_path, monkeypatch):
    p = _write_bad_toml(
        tmp_path,
        '[profiles.x]\nslots = ["pos", "unknown_slot"]\n[languages.ell.pos]\nnoun = "x"\n',
    )
    monkeypatch.setattr(profiles, "_TOML_PATH", p)
    with pytest.raises(ValueError, match="unknown_slot"):
        load_profiles()


def test_load_profiles_raises_on_undefined_profile_reference(tmp_path, monkeypatch):
    p = _write_bad_toml(
        tmp_path,
        '[profiles.real_profile]\nslots = ["pos", "case", "number"]\n'
        '[languages.ell.pos]\nnoun = "ghost_profile"\n',
    )
    monkeypatch.setattr(profiles, "_TOML_PATH", p)
    with pytest.raises(ValueError, match="ghost_profile"):
        load_profiles()


def test_load_profiles_raises_on_unknown_profile_flag(tmp_path, monkeypatch):
    p = _write_bad_toml(
        tmp_path,
        '[profiles.x]\nslots = ["pos", "case", "number"]\n'
        "[profiles.x.flags]\nbad_flag = true\n"
        '[languages.ell.pos]\nnoun = "x"\n',
    )
    monkeypatch.setattr(profiles, "_TOML_PATH", p)
    with pytest.raises(ValueError, match="bad_flag"):
        load_profiles()


def test_load_profiles_raises_on_unknown_language_flag(tmp_path, monkeypatch):
    p = _write_bad_toml(
        tmp_path,
        '[profiles.x]\nslots = ["pos", "case", "number"]\n'
        '[languages.ell.pos]\nnoun = "x"\n'
        "[languages.ell.flags]\nbad_lang_flag = true\n",
    )
    monkeypatch.setattr(profiles, "_TOML_PATH", p)
    with pytest.raises(ValueError, match="bad_lang_flag"):
        load_profiles()


def test_load_profiles_raises_on_malformed_toml(tmp_path, monkeypatch):
    p = tmp_path / "bad.toml"
    p.write_bytes(b"this is [not valid toml !!!!")
    monkeypatch.setattr(profiles, "_TOML_PATH", p)
    with pytest.raises(ValueError):
        load_profiles()


# ── section-03: slot resolution ───────────────────────────────────────────────

# standard_nominal

def test_standard_nominal_no_gender():
    assert _build_tags("ell", "noun", {"Case": "Nom", "Number": "Sing"}) == ["N;NOM;SG"]


def test_standard_nominal_with_gender():
    assert _build_tags("ell", "noun", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}) == ["N;NOM;SG;MASC"]


def test_standard_nominal_plural_gender():
    assert _build_tags("ell", "noun", {"Case": "Acc", "Number": "Plur", "Gender": "Neut"}) == ["N;ACC;PL;NEUT"]


def test_standard_nominal_degree_cmp():
    assert _build_tags("ell", "adjective", {"Case": "Nom", "Number": "Sing", "Degree": "Cmp"}) == ["ADJ;NOM;SG;CMPR"]


def test_standard_nominal_degree_pos_omitted():
    assert _build_tags("ell", "adjective", {"Case": "Nom", "Number": "Sing", "Degree": "Pos"}) == ["ADJ;NOM;SG"]


def test_standard_nominal_missing_number_raises():
    with pytest.raises(FeatureNotSupportedError) as exc_info:
        _build_tags("ell", "noun", {"Case": "Nom"})
    assert exc_info.value.key == "Number"
    assert exc_info.value.value == "None"


def test_standard_nominal_missing_case_raises():
    with pytest.raises(FeatureNotSupportedError) as exc_info:
        _build_tags("ell", "noun", {"Number": "Sing"})
    assert exc_info.value.key == "Case"
    assert exc_info.value.value == "None"


def test_standard_nominal_unknown_case_raises():
    with pytest.raises(FeatureNotSupportedError) as exc_info:
        _build_tags("ell", "noun", {"Case": "XYZ", "Number": "Sing"})
    assert exc_info.value.key == "Case"
    assert exc_info.value.value == "XYZ"


# latin_nominal

def test_latin_nominal_gender_before_number():
    assert _build_tags("lat", "adjective", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}) == ["ADJ;NOM;MASC;SG"]


def test_latin_nominal_fem_plural():
    assert _build_tags("lat", "adjective", {"Case": "Acc", "Number": "Plur", "Gender": "Fem"}) == ["ADJ;ACC;FEM;PL"]


def test_latin_nominal_no_gender():
    assert _build_tags("lat", "adjective", {"Case": "Gen", "Number": "Sing"}) == ["ADJ;GEN;SG"]


def test_latin_nominal_slot_order():
    tag = _build_tags("lat", "adjective", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"})[0]
    parts = tag.split(";")
    assert parts.index("MASC") < parts.index("SG")


# slavic_nominal — ?gender_if_singular

def test_slavic_gender_present_for_singular():
    assert _build_tags("rus", "noun", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}) == ["N;NOM;MASC;SG"]


def test_slavic_gender_absent_for_plural():
    result = _build_tags("rus", "noun", {"Case": "Nom", "Number": "Plur", "Gender": "Masc"})
    assert result == ["N;NOM;PL"]
    assert "MASC" not in result[0]


def test_slavic_no_gender_feature():
    assert _build_tags("rus", "noun", {"Case": "Nom", "Number": "Sing"}) == ["N;NOM;SG"]


# slavic_nominal — case_overrides

def test_slavic_case_override_loc_to_ess():
    assert _build_tags("rus", "noun", {"Case": "Loc", "Number": "Sing"}) == ["N;ESS;SG"]


def test_slavic_case_override_does_not_affect_nom():
    assert _build_tags("rus", "noun", {"Case": "Nom", "Number": "Sing"}) == ["N;NOM;SG"]


# caseless_nominal

def test_caseless_with_gender():
    assert _build_tags("spa", "noun", {"Number": "Sing", "Gender": "Fem"}) == ["N;FEM;SG"]


def test_caseless_no_gender():
    assert _build_tags("spa", "noun", {"Number": "Plur"}) == ["N;PL"]


def test_caseless_no_case_token_in_output():
    case_tokens = {"NOM", "ACC", "GEN", "DAT", "ABL", "INS", "LOC", "VOC", "ESS"}
    tag = _build_tags("spa", "noun", {"Number": "Sing", "Gender": "Masc"})[0]
    for token in case_tokens:
        assert token not in tag.split(";")


# noun_strip_gender (grc)

def test_grc_noun_strip_gender():
    tag = _build_tags("grc", "noun", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"})[0]
    assert "MASC" not in tag.split(";")


def test_grc_noun_strip_gender_before_slot_resolution():
    with_gender = _build_tags("grc", "noun", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"})
    without_gender = _build_tags("grc", "noun", {"Case": "Nom", "Number": "Sing"})
    assert with_gender == without_gender


# animacy_acc boundary: nouns pass through normally, adjective ACC deferred to section-04

def test_slavic_noun_acc_singular_no_animacy():
    # rus noun ACC is plain N;ACC;SG — animacy_acc flag does not apply to nouns
    assert _build_tags("rus", "noun", {"Case": "Acc", "Number": "Sing"}) == ["N;ACC;SG"]


def test_slavic_noun_acc_plural_no_animacy():
    assert _build_tags("rus", "noun", {"Case": "Acc", "Number": "Plur"}) == ["N;ACC;PL"]


def test_slavic_adj_acc_raises_not_implemented():
    # This test is superseded by section-04; kept here as documentation only.
    # After section-04, animacy_acc logic is implemented and this test is removed.
    pass


# ── section-04: animacy_acc ────────────────────────────────────────────────────

from unimorph_backend_eee.profiles import (
    _drop_gender_secondary_tag,
    _masc_fem_combined_secondary_tag,
)

# animacy_acc: ACC + PL

def test_animacy_acc_pl_anim():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Plur", "Animacy": "Anim"})
    assert result == ["ADJ;ACC;ANIM;PL"]


def test_animacy_acc_pl_inan():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Plur", "Animacy": "Inan"})
    assert result == ["ADJ;ACC;INAN;PL"]


def test_animacy_acc_pl_unknown():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Plur"})
    assert set(result) == {"ADJ;ACC;ANIM;PL", "ADJ;ACC;INAN;PL"}


# animacy_acc: ACC + SG + Masc

def test_animacy_acc_sg_masc_anim():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Anim"})
    assert result == ["ADJ;ANIM;ACC;MASC;SG"]


def test_animacy_acc_sg_masc_inan():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Inan"})
    assert result == ["ADJ;INAN;ACC;MASC;SG"]


def test_animacy_acc_sg_masc_unknown():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Sing", "Gender": "Masc"})
    assert set(result) == {"ADJ;ANIM;ACC;MASC;SG", "ADJ;INAN;ACC;MASC;SG"}


# animacy_acc: ACC + SG + Fem/Neut (no animacy prefix)

def test_animacy_acc_sg_fem():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Sing", "Gender": "Fem"})
    assert result == ["ADJ;ACC;FEM;SG"]


def test_animacy_acc_sg_neut():
    result = _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Sing", "Gender": "Neut"})
    assert result == ["ADJ;ACC;NEUT;SG"]


# animacy_acc: non-ACC cases unaffected

def test_animacy_acc_non_acc_nom_sg_masc():
    assert _build_tags("rus", "adjective", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}) == ["ADJ;NOM;MASC;SG"]


def test_animacy_acc_non_acc_noun_gen_pl():
    assert _build_tags("rus", "noun", {"Case": "Gen", "Number": "Plur"}) == ["N;GEN;PL"]


def test_animacy_acc_noun_sg_anim():
    # Russian animate noun ACC SG: N;ACC;ANIM;SG (no gender in tag)
    assert _build_tags("rus", "noun", {"Case": "Acc", "Number": "Sing", "Animacy": "Anim"}) == ["N;ACC;ANIM;SG"]


def test_animacy_acc_noun_sg_inan():
    assert _build_tags("rus", "noun", {"Case": "Acc", "Number": "Sing", "Animacy": "Inan"}) == ["N;ACC;INAN;SG"]


def test_animacy_acc_noun_pl_anim():
    assert _build_tags("rus", "noun", {"Case": "Acc", "Number": "Plur", "Animacy": "Anim"}) == ["N;ACC;ANIM;PL"]


def test_animacy_acc_noun_sg_no_animacy_returns_bare():
    # No Animacy feature → bare N;ACC;SG (common path for inanimate-only nouns)
    assert _build_tags("rus", "noun", {"Case": "Acc", "Number": "Sing"}) == ["N;ACC;SG"]


def test_animacy_acc_sg_no_gender_raises():
    # Adjective ACC SG with no Gender: _animacy_acc_tags raises (gender required for adj forms)
    with pytest.raises(FeatureNotSupportedError) as exc_info:
        _build_tags("rus", "adjective", {"Case": "Acc", "Number": "Sing"})
    assert exc_info.value.key == "Gender"


# _drop_gender_secondary_tag

def test_drop_gender_removes_masc():
    assert _drop_gender_secondary_tag("ADJ;NOM;SG;MASC") == "ADJ;NOM;SG"


def test_drop_gender_removes_fem():
    assert _drop_gender_secondary_tag("ADJ;NOM;SG;FEM") == "ADJ;NOM;SG"


def test_drop_gender_no_gender_token():
    assert _drop_gender_secondary_tag("ADJ;NOM;SG") is None


def test_drop_gender_any_input_gender():
    # Secondary tag has no gender token regardless of input gender
    assert _drop_gender_secondary_tag("ADJ;NOM;SG;MASC") == _drop_gender_secondary_tag("ADJ;NOM;SG;FEM")


# _masc_fem_combined_secondary_tag

def test_masc_fem_combined_replaces_masc():
    assert _masc_fem_combined_secondary_tag("ADJ;NOM;MASC;SG") == "ADJ;NOM;MASC+FEM;SG"


def test_masc_fem_combined_replaces_fem():
    assert _masc_fem_combined_secondary_tag("ADJ;NOM;FEM;SG") == "ADJ;NOM;MASC+FEM;SG"


def test_masc_fem_combined_neut_returns_none():
    assert _masc_fem_combined_secondary_tag("ADJ;NOM;NEUT;SG") is None


def test_masc_fem_combined_no_gender_returns_none():
    assert _masc_fem_combined_secondary_tag("ADJ;NOM;SG") is None


def test_masc_fem_combined_spa_caseless():
    # spa caseless_nominal: N;FEM;SG → N;MASC+FEM;SG
    assert _masc_fem_combined_secondary_tag("N;FEM;SG") == "N;MASC+FEM;SG"


# ── section-06: detect_profile ────────────────────────────────────────────────

from unimorph_backend_eee.profiles import detect_profile


def _write_tsv(tmp_path, rows: list[str]) -> str:
    p = tmp_path / "test.tsv"
    p.write_text("\n".join(rows), encoding="utf-8")
    return str(p)


class TestDetectProfile:
    def test_caseless(self, tmp_path):
        path = _write_tsv(tmp_path, [
            "palabra\tpalabra\tADJ;FEM;SG",
            "palabra\tpalabras\tADJ;FEM;PL",
            "largo\tlargo\tADJ;MASC;SG",
        ])
        assert detect_profile("spa", path) == "caseless_nominal"

    def test_slavic_anim_wins_over_latin_slot_order(self, tmp_path):
        # Has ANIM token and gender before number — slavic must win over latin
        path = _write_tsv(tmp_path, [
            "красивый\tкрасивого\tADJ;ANIM;ACC;MASC;SG",
            "красивый\tкрасивый\tADJ;NOM;MASC;SG",
        ])
        assert detect_profile("rus", path) == "slavic_nominal"

    def test_latin_gender_before_number(self, tmp_path):
        path = _write_tsv(tmp_path, [
            "bonus\tbona\tADJ;ACC;FEM;PL",
            "bonus\tbonum\tADJ;NOM;NEUT;SG",
        ])
        assert detect_profile("lat", path) == "latin_nominal"

    def test_standard_gender_after_number(self, tmp_path):
        path = _write_tsv(tmp_path, [
            "καλός\tκαλός\tADJ;NOM;SG;MASC",
            "καλός\tκαλή\tADJ;NOM;SG;FEM",
        ])
        assert detect_profile("ell", path) == "standard_nominal"

    def test_no_adj_entries(self, tmp_path):
        path = _write_tsv(tmp_path, [
            "λόγος\tλόγου\tN;GEN;SG",
            "λόγος\tλόγοι\tN;NOM;PL",
        ])
        assert detect_profile("ell", path) == "standard_nominal"

    def test_empty_tsv(self, tmp_path):
        path = _write_tsv(tmp_path, [])
        assert detect_profile("ell", path) == "standard_nominal"

    def test_reads_at_most_200_lines(self, tmp_path):
        # Lines 1-200: caseless (no case tokens)
        # Lines 201-300: standard (case tokens present) → must not be seen
        caseless = [f"w\tw\tADJ;FEM;SG" for _ in range(200)]
        standard = [f"w\tw\tADJ;NOM;SG;MASC" for _ in range(100)]
        path = _write_tsv(tmp_path, caseless + standard)
        assert detect_profile("spa", path) == "caseless_nominal"

    def test_masc_fem_combined_latin(self, tmp_path):
        # MASC+FEM token at lower index than number → latin_nominal
        path = _write_tsv(tmp_path, [
            "bonus\tbono\tADJ;ABL;MASC+FEM;SG",
        ])
        assert detect_profile("lat", path) == "latin_nominal"

    def test_inan_beyond_200_lines_not_seen(self, tmp_path):
        # Lines 1-200: standard (NOM present, no ANIM/INAN)
        # Line 201: has INAN → must not be seen (cap at 200)
        standard = [f"w\tw\tADJ;NOM;SG;MASC" for _ in range(200)]
        slavic = ["w\tw\tADJ;INAN;ACC;MASC;SG"]
        path = _write_tsv(tmp_path, standard + slavic)
        assert detect_profile("ell", path) == "standard_nominal"


# ── section-07: _fallback_lookups ─────────────────────────────────────────────

from unimorph_backend_eee.profiles import _fallback_lookups


def _make_lookup(table: dict):
    def _lookup(lemma, tag, lang):
        return table.get(tag, set())
    return _lookup


def test_fallback_grc_adj_masc_drops_gender():
    # adjective_drop_gender_fallback: ADJ;NOM;SG;MASC → secondary tag ADJ;NOM;SG
    lookup = _make_lookup({"ADJ;NOM;SG": {"σαφής"}})
    result = _fallback_lookups("grc", "adjective", "σαφής", ["ADJ;NOM;SG;MASC"],
                               {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, lookup)
    assert "σαφής" in result


def test_fallback_grc_adj_neut_no_secondary():
    # Neut gender: adjective_drop_gender_fallback must NOT trigger (Neut has its own entries)
    called = []
    def lookup(lemma, tag, lang):
        called.append(tag)
        return set()
    _fallback_lookups("grc", "adjective", "σαφές", ["ADJ;NOM;SG;NEUT"],
                      {"Case": "Nom", "Number": "Sing", "Gender": "Neut"}, lookup)
    assert called == []  # no secondary lookup triggered


def test_fallback_lat_adj_masc_fem_combined():
    lookup = _make_lookup({"ADJ;NOM;MASC+FEM;SG": {"algēnsis"}})
    result = _fallback_lookups("lat", "adjective", "algēnsis", ["ADJ;NOM;MASC;SG"],
                               {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, lookup)
    assert "algēnsis" in result


def test_fallback_spa_noun_masc_fem_combined():
    lookup = _make_lookup({"N;MASC+FEM;SG": {"artista"}})
    result = _fallback_lookups("spa", "noun", "artista", ["N;MASC;SG"],
                               {"Number": "Sing", "Gender": "Masc"}, lookup)
    assert "artista" in result


def test_fallback_ell_no_fallbacks():
    # ell has no fallback flags; no secondary lookups
    called = []
    def lookup(lemma, tag, lang):
        called.append(tag)
        return set()
    _fallback_lookups("ell", "noun", "λόγος", ["N;NOM;SG"],
                      {"Case": "Nom", "Number": "Sing"}, lookup)
    assert called == []
