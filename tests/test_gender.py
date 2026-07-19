"""Tests for noun-gender inference (gender.py)."""
from unimorph_backend_eee.gender import (
    _strip_all_accents,
    _strip_diacritics,
    gender_from_ending,
    infer_noun_gender,
)


def test_strip_diacritics_removes_breathing_and_quantity_keeps_accent():
    # βᾰρῠ́της: breve-alpha, breve-upsilon + separate combining acute should
    # recompose to the plainly-typed "βαρύτης", keeping the accent on υ.
    assert _strip_diacritics("βᾰρῠ́της") == "βαρύτης"


def test_strip_diacritics_noop_on_plain_form():
    assert _strip_diacritics("ναύτης") == "ναύτης"


def test_strip_all_accents_also_drops_accent():
    assert _strip_all_accents("θεός") == "θεος"
    assert _strip_all_accents("βᾰρῠ́της") == "βαρυτης"


def test_gender_from_ending_grc_potes_and_xotes_carveouts():
    # Agent nouns in -ότης (συμπότης "drinker", τοξότης "archer") are
    # masculine, distinct from the abstract-noun -ότης class below.
    for word in ("συμπότης", "δεσπότης", "ἱππότης", "τοξότης", "ἱπποτοξότης"):
        assert gender_from_ending(word, "grc") == "Masc"


def test_gender_from_ending_grc_autes_carveout():
    # ναύτης (ναῦς + -της): the accented υ is half of the -αυ- diphthong,
    # not the paroxytone -ύτης abstract-noun suffix.
    assert gender_from_ending("ναύτης", "grc") == "Masc"


def test_gender_from_ending_grc_otes_utes_abstract_nouns():
    for word in ("ποιότης", "ἀρχαιότης", "βαρύτης", "ὀξύτης", "δασύτης"):
        assert gender_from_ending(word, "grc") == "Fem"


def test_gender_from_ending_grc_oxytone_as_is_distinct_from_plain_as():
    # Oxytone -άς (Τρωάς, τετράς) is a 3rd-decl fem class, distinct from
    # unaccented/paroxytone -ας (1st-decl masc: νεανίας).
    assert gender_from_ending("τετράς", "grc") == "Fem"
    assert gender_from_ending("Τρωάς", "grc") == "Fem"
    assert gender_from_ending("νεανίας", "grc") == "Masc"


def test_gender_from_ending_grc_oxytone_words_still_match_bare_ending():
    # An oxytone nominative is completely ordinary and must still match its
    # bare declension-class ending, not silently fall through to None.
    assert gender_from_ending("θεός", "grc") == "Masc"
    assert gender_from_ending("τιμή", "grc") == "Fem"
    assert gender_from_ending("ψυχή", "grc") == "Fem"
    assert gender_from_ending("ἀρετή", "grc") == "Fem"


def test_gender_from_ending_grc_common_endings():
    assert gender_from_ending("δῶρον", "grc") == "Neut"
    assert gender_from_ending("σῶμα", "grc") == "Neut"
    assert gender_from_ending("πολίτης", "grc") == "Masc"
    assert gender_from_ending("χώρα", "grc") == "Fem"
    assert gender_from_ending("ἄνοδος", "grc") == "Fem"


def test_gender_from_ending_grc_unmatched_suffix_returns_none():
    assert gender_from_ending("φύλαξ", "grc") is None


def test_gender_from_ending_grc_irreducible_ambiguity_not_claimed_as_a_win():
    # τρωγλοδύτης ("cave-dweller", masc) has its accent on the same
    # paroxytone position as the abstract -ύτης class (βαρύτης, fem) — a
    # genuine lexical ambiguity no suffix rule can resolve. Documenting the
    # known-wrong guess here so a future accuracy regression is visible.
    assert gender_from_ending("τρωγλοδύτης", "grc") == "Fem"


def test_gender_from_ending_ell_common_endings():
    assert gender_from_ending("αιχμαλωτισμός", "ell") == "Masc"
    assert gender_from_ending("πρόγραμμα", "ell") == "Neut"
    assert gender_from_ending("καλαμάκι", "ell") == "Neut"
    assert gender_from_ending("δασκάλα", "ell") == "Fem"
    assert gender_from_ending("καρδιά", "ell") == "Fem"


def test_gender_from_ending_unknown_language_returns_none():
    assert gender_from_ending("θεός", "xx") is None


def test_infer_noun_gender_grc_article_overrides_ending_default():
    # ἡ κύπρος: ending-only guess would say "Masc" (bare -ος default);
    # the TSV's own article says otherwise and must win.
    assert gender_from_ending("κύπρος", "grc") == "Masc"
    assert infer_noun_gender("κύπρος", "grc") == "Fem"


def test_infer_noun_gender_grc_known_words():
    assert infer_noun_gender("ναύτης", "grc") == "Masc"
    assert infer_noun_gender("πολίτης", "grc") == "Masc"
    assert infer_noun_gender("βαρύτης", "grc") == "Fem"


def test_infer_noun_gender_grc_falls_back_to_ending_when_no_tsv_entry():
    assert infer_noun_gender("ζζζμα", "grc") == "Neut"


def test_infer_noun_gender_ell_has_no_articles_uses_ending():
    # ell's bundled data carries no articles at all, so infer_noun_gender
    # must fall through to the ending heuristic even for a lemma that IS
    # present in the TSV.
    assert infer_noun_gender("αιχμαλωτισμός", "ell") == "Masc"


def test_infer_noun_gender_unknown_lemma_and_ending_returns_none():
    assert infer_noun_gender("ζζζξ", "grc") is None
