"""Tests for the UniMorph→UD reverse map (unimorph_backend_eee.reverse) and extract_tags.py."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from unimorph_backend_eee.reverse import tag_to_ud
from extract_tags import extract, _NOMINAL_COLS, _VERB_COLS


# ── nominal reverse map ───────────────────────────────────────────────────────

def test_noun_nom_sg():
    assert tag_to_ud("N;NOM;SG") == {"Case": "Nom", "Number": "Sing"}

def test_noun_gen_pl():
    assert tag_to_ud("N;GEN;PL") == {"Case": "Gen", "Number": "Plur"}

def test_noun_dat_sg():
    assert tag_to_ud("N;DAT;SG") == {"Case": "Dat", "Number": "Sing"}

def test_noun_acc_pl():
    assert tag_to_ud("N;ACC;PL") == {"Case": "Acc", "Number": "Plur"}

def test_noun_voc_sg():
    assert tag_to_ud("N;VOC;SG") == {"Case": "Voc", "Number": "Sing"}

def test_noun_abl_sg():
    assert tag_to_ud("N;ABL;SG") == {"Case": "Abl", "Number": "Sing"}

def test_noun_ins_pl():
    assert tag_to_ud("N;INS;PL") == {"Case": "Ins", "Number": "Plur"}

def test_noun_loc_sg():
    assert tag_to_ud("N;LOC;SG") == {"Case": "Loc", "Number": "Sing"}

def test_noun_ess_maps_to_loc():
    assert tag_to_ud("N;ESS;SG") == {"Case": "Loc", "Number": "Sing"}

def test_noun_dual():
    assert tag_to_ud("N;NOM;DU") == {"Case": "Nom", "Number": "Dual"}

def test_adj_nom_sg_masc():
    assert tag_to_ud("ADJ;NOM;SG;MASC") == {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}

def test_adj_acc_pl_fem():
    assert tag_to_ud("ADJ;ACC;PL;FEM") == {"Case": "Acc", "Number": "Plur", "Gender": "Fem"}

def test_adj_gen_sg_neut():
    assert tag_to_ud("ADJ;GEN;SG;NEUT") == {"Case": "Gen", "Number": "Sing", "Gender": "Neut"}

def test_adj_comparative():
    assert tag_to_ud("ADJ;NOM;SG;MASC;CMPR") == {
        "Case": "Nom", "Number": "Sing", "Gender": "Masc", "Degree": "Cmp"
    }

def test_adj_superlative():
    assert tag_to_ud("ADJ;NOM;SG;MASC;SPRL") == {
        "Case": "Nom", "Number": "Sing", "Gender": "Masc", "Degree": "Sup"
    }

def test_adj_no_gender():
    assert tag_to_ud("ADJ;NOM;SG") == {"Case": "Nom", "Number": "Sing"}

def test_compound_gender_ignored():
    # MASC+FEM has no UD equivalent — Gender should be absent
    feats = tag_to_ud("ADJ;NOM;MASC+FEM;SG")
    assert "Gender" not in feats
    assert feats.get("Case") == "Nom"
    assert feats.get("Number") == "Sing"

def test_unknown_tokens_ignored():
    # AB (absolute superlative marker) is not a UD feature
    feats = tag_to_ud("ADJ;NOM;SG;MASC;SPRL;AB")
    assert feats.get("Degree") == "Sup"
    assert "AB" not in feats.values()


# ── verb reverse map ──────────────────────────────────────────────────────────

def test_verb_pres_ipfv_ind_1sg():
    assert tag_to_ud("V;1;SG;IPFV;PRS") == {
        "VerbForm": "Fin", "Person": "1", "Number": "Sing",
        "Aspect": "Imp", "Tense": "Pres", "Mood": "Ind",
    }

def test_verb_past_ipfv_ind_3pl():
    assert tag_to_ud("V;3;PL;IPFV;PST") == {
        "VerbForm": "Fin", "Person": "3", "Number": "Plur",
        "Aspect": "Imp", "Tense": "Past", "Mood": "Ind",
    }

def test_verb_past_pfv_ind_1sg():
    assert tag_to_ud("V;1;SG;PFV;PST") == {
        "VerbForm": "Fin", "Person": "1", "Number": "Sing",
        "Aspect": "Perf", "Tense": "Past", "Mood": "Ind",
    }

def test_verb_fut_ipfv_ind_2sg():
    assert tag_to_ud("V;2;SG;IPFV;FUT") == {
        "VerbForm": "Fin", "Person": "2", "Number": "Sing",
        "Aspect": "Imp", "Tense": "Fut", "Mood": "Ind",
    }

def test_verb_subjunctive_no_tense():
    assert tag_to_ud("V;1;SG;IPFV;SBJV") == {
        "VerbForm": "Fin", "Person": "1", "Number": "Sing",
        "Aspect": "Imp", "Mood": "Sub",
    }

def test_verb_imperative():
    feats = tag_to_ud("V;2;SG;IMP")
    assert feats == {"VerbForm": "Fin", "Person": "2", "Number": "Sing", "Mood": "Imp"}

def test_verb_imperative_no_tense():
    feats = tag_to_ud("V;2;SG;IMP")
    assert "Tense" not in feats

def test_verb_prf_prs_maps_to_perf():
    feats = tag_to_ud("V;1;SG;PRF;PRS")
    assert feats.get("Tense") == "Perf"
    assert "Aspect" not in feats

def test_verb_prf_pst_maps_to_pqp():
    feats = tag_to_ud("V;1;SG;PRF;PST")
    assert feats.get("Tense") == "Pqp"
    assert "Aspect" not in feats

def test_verb_infinitive():
    feats = tag_to_ud("V;INF")
    assert feats.get("VerbForm") == "Inf"
    assert "Person" not in feats

def test_verb_participle_active():
    feats = tag_to_ud("V;PTCP;PRS;ACT")
    assert feats.get("VerbForm") == "Part"
    assert feats.get("Voice") == "Act"
    assert feats.get("Tense") == "Pres"

def test_verb_tense_implies_indicative():
    feats = tag_to_ud("V;1;SG;IPFV;PRS")
    assert feats.get("Mood") == "Ind"

def test_verb_no_tense_no_indicative_default():
    feats = tag_to_ud("V;1;SG;IPFV;SBJV")
    assert feats.get("Mood") == "Sub"


# ── extract() — sort order ────────────────────────────────────────────────────

def test_el_noun_sort_order():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("ell")
    pairs = extract(index, "noun")
    tags = [t for t, _ in pairs]
    assert tags.index("N;NOM;SG") < tags.index("N;GEN;SG")
    assert tags.index("N;NOM;SG") < tags.index("N;NOM;PL")

def test_el_adj_base_before_comparative():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("ell")
    pairs = extract(index, "adjective")
    tags = [t for t, _ in pairs]
    assert tags.index("ADJ;NOM;SG;MASC") < tags.index("ADJ;NOM;SG;MASC;CMPR")
    assert tags.index("ADJ;NOM;SG;MASC;CMPR") < tags.index("ADJ;NOM;SG;MASC;SPRL;AB")

def test_el_verb_pres_before_past():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("ell")
    pairs = extract(index, "verb")
    tags = [t for t, _ in pairs]
    assert tags.index("V;1;SG;IPFV;PRS") < tags.index("V;1;SG;IPFV;PST")

def test_el_verb_ind_before_subj():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("ell")
    pairs = extract(index, "verb")
    tags = [t for t, _ in pairs]
    assert tags.index("V;1;SG;IPFV;PRS") < tags.index("V;1;SG;IPFV;SBJV")

def test_grc_noun_has_dual():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("grc")
    pairs = extract(index, "noun")
    tags = [t for t, _ in pairs]
    assert "N;NOM;DU" in tags

def test_grc_adj_gender_neutral_before_gendered():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("grc")
    pairs = extract(index, "adjective")
    tags = [t for t, _ in pairs]
    assert tags.index("ADJ;NOM;SG") < tags.index("ADJ;NOM;SG;MASC")

def test_es_noun_no_case_column():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("spa")
    pairs = extract(index, "noun")
    active = [c for c in _NOMINAL_COLS if any(c in f for _, f in pairs)]
    assert "Case" not in active

def test_ru_noun_has_ins():
    from unimorph_backend_eee.backend import _load_index
    index = _load_index("rus")
    pairs = extract(index, "noun")
    tags = [t for t, _ in pairs]
    assert any("INS" in t for t in tags)
