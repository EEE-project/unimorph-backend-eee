"""Infer noun gender from nominative-singular form.

UniMorph tags never carry gender for nouns (it's a fixed lexical property,
not inflectional — unlike adjectives, where GENDER_MAP applies directly).
Two strategies, tried in order:

1. Read the article off the raw nominative-singular TSV form, when present
   (grc only — ell's bundled data has no articles at all). More reliable
   than guessing from the ending: correctly handles exceptions like
   masculine ναύτης/πολίτης (1st-declension -ης, would otherwise look
   feminine) because the TSV's own "ὁ ναύτης" already encodes the answer.
2. Fall back to an ending-pattern heuristic. Best-effort — genuinely
   ambiguous endings (e.g. grc/ell -ος, masculine by far the common case
   but with a real, non-enumerable feminine/neuter exception class) return
   ``None`` rather than a guess that would be silently wrong.
"""

import importlib.resources
import unicodedata

_NOMSG_CACHE: dict[str, dict[str, str]] = {}

_GRC_ARTICLES = {"ὁ": "Masc", "ἡ": "Fem", "τό": "Neut", "τὸ": "Neut"}
_ELL_ARTICLES = {"ο": "Masc", "η": "Fem", "το": "Neut"}
_ARTICLES_BY_LANGUAGE = {"grc": _GRC_ARTICLES, "ell": _ELL_ARTICLES}

# Two priority tiers, most-specific-suffix-first within each; first match
# wins. Endings absent from both tiers (mostly 3rd-declension consonant
# stems with no reliable shared pattern) fall through to None.
#
# _SPECIFIC_ENDING_RULES: derivational/compound suffixes where accent
# position is itself part of the signal (matched with accents intact, via
# _strip_diacritics — breathing/quantity marks stripped, accents kept).
#
# _GENERIC_ENDING_RULES: plain declension-class endings, used as a
# majority-default fallback. Matched fully accent-blind (_strip_all_accents)
# because accent position doesn't reliably split these classes, and an
# oxytone nominative (θεός, τιμή, ὁδός) is completely ordinary — it must
# still match its bare ending, not silently fall through to None.
_SPECIFIC_ENDING_RULES: dict[str, list[tuple[str, str]]] = {
    "grc": [
        # Agent-noun carve-outs, checked before the broader -ότης/-ύτης abstract-noun
        # rules below (which would otherwise wrongly swallow them as their own suffix):
        ("πότης", "Masc"),  # συμπότης, δεσπότης, ἱππότης
        ("ξότης", "Masc"),  # τοξότης, ἱπποτοξότης ("archer")
        ("αύτης", "Masc"),  # ναύτης (ναῦς + -της) — accented υ is half of the -αυ- diphthong
        ("ότης", "Fem"),  # abstract nouns from adjectives: ποιότης, ἀρχαιότης
        ("ύτης", "Fem"),  # abstract nouns from adjectives: βαρύτης, ὀξύτης
        ("οδος", "Fem"),  # ὁδός compounds (ἄνοδος, κάθοδος); bare ὁδός itself is oxytone and
                          # falls through to the generic -ος/Masc default below (known gap)
        ("μα", "Neut"),   # ὄνομα, σῶμα, πρᾶγμα — 3rd-decl -μα/-ματος class
        # Accent position is the only signal splitting these two, so both stay out of
        # the accent-blind generic pass (unlike every other -ας-shaped ending there):
        ("άς", "Fem"),    # oxytone: 3rd-decl fem (Τρωάς, τετράς, λοπάς)
        ("ας", "Masc"),   # paroxytone/unaccented: 1st-decl masc (νεανίας)
    ],
    "ell": [
        ("ιμο", "Neut"),
        ("μα", "Neut"),
        # Always oxytone in practice (αλεπού) — stripping its accent would let it wrongly
        # swallow unrelated genitive-case forms ending in plain -ου.
        ("ού", "Fem"),
    ],
}

_GENERIC_ENDING_RULES: dict[str, list[tuple[str, str]]] = {
    "grc": [
        ("ον", "Neut"),   # 2nd declension neuter, essentially exceptionless
        ("ης", "Masc"),   # 1st-decl masculine (ναύτης, πολίτης, θεραπευτής)
        ("η", "Fem"),      # 1st declension feminine (χώρα-type -η, incl. oxytone τιμή/ψυχή)
        ("α", "Fem"),      # 1st declension feminine, incl. oxytone (χαρά)
        ("ος", "Masc"),   # 2nd declension — majority default; real fem exceptions exist (ὁδός, νῆσος)
    ],
    "ell": [
        ("ος", "Masc"),   # majority default; real neut exceptions exist (δάσος, έθνος)
        ("ης", "Masc"),
        ("ας", "Masc"),
        ("η", "Fem"),
        ("α", "Fem"),
        ("ι", "Neut"),
        ("ο", "Neut"),
    ],
}


_BREATHING_AND_QUANTITY_MARKS = {
    chr(0x0313),  # combining comma above — smooth breathing (psili)
    chr(0x0314),  # combining reversed comma above — rough breathing (dasia)
    chr(0x0304),  # combining macron — long vowel
    chr(0x0306),  # combining breve — short vowel
}

_ACCENT_MARKS = {
    chr(0x0301),  # combining acute accent (oxia)
    chr(0x0300),  # combining grave accent (varia)
    chr(0x0342),  # combining Greek perispomeni (circumflex)
}


def _strip_marks(text: str, marks: set[str]) -> str:
    """NFD-decompose, drop the given combining marks, then NFC-recompose so
    any marks left in place land back on the same precomposed letter the
    (plainly typed) rule suffixes above use.

    The bundled data marks vowel quantity using combining marks with no
    precomposed target codepoint (e.g. breve-upsilon U+1FE0 plus a separate
    COMBINING ACUTE ACCENT U+0301) — NFC normalization alone can't recompose
    that, so plain ``.endswith()`` silently misses a large share of forms.
    """
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if ch not in marks)
    return unicodedata.normalize("NFC", stripped)


def _strip_diacritics(text: str) -> str:
    """Drop breathing and vowel-quantity marks, but keep accent marks."""
    return _strip_marks(text, _BREATHING_AND_QUANTITY_MARKS)


def _strip_all_accents(text: str) -> str:
    """Like _strip_diacritics, but also drops accent marks — for the generic
    rules, where accent position carries no signal we have a rule for."""
    return _strip_marks(text, _BREATHING_AND_QUANTITY_MARKS | _ACCENT_MARKS)


_STRIPPED_SPECIFIC_RULES: dict[str, list[tuple[str, str]]] = {
    language: [(_strip_diacritics(suffix), gender) for suffix, gender in rules]
    for language, rules in _SPECIFIC_ENDING_RULES.items()
}

_STRIPPED_GENERIC_RULES: dict[str, list[tuple[str, str]]] = {
    language: [(_strip_all_accents(suffix), gender) for suffix, gender in rules]
    for language, rules in _GENERIC_ENDING_RULES.items()
}


def _load_nomsg_index(language: str) -> dict[str, str]:
    """lemma -> raw N;NOM;SG form (article intact, unlike backend._load_index)."""
    if language in _NOMSG_CACHE:
        return _NOMSG_CACHE[language]
    index: dict[str, str] = {}
    try:
        text = (
            importlib.resources.files("unimorph_backend_eee.data")
            .joinpath(f"{language}.tsv")
            .read_text(encoding="utf-8")
        )
    except Exception:
        _NOMSG_CACHE[language] = index
        return index
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        lemma, form, tag = parts
        if tag == "N;NOM;SG" and lemma not in index:
            index[lemma] = form.split(",")[0].strip()
    _NOMSG_CACHE[language] = index
    return index


def _split_article(raw_form: str, language: str) -> tuple[str | None, str]:
    """(gender if the leading token is a known article else None, rest of raw_form)."""
    articles = _ARTICLES_BY_LANGUAGE.get(language)
    if not articles or " " not in raw_form:
        return None, raw_form
    article, _, rest = raw_form.partition(" ")
    return articles.get(article), (rest if article in articles else raw_form)


def gender_from_ending(form: str, language: str) -> str | None:
    """Best-effort ending-pattern guess. Public so callers can use it directly
    on a form that has no TSV entry at all (e.g. a word from a course vocab
    list, not the bundled UniMorph data)."""
    bare = _strip_diacritics(form)
    for suffix, gender in _STRIPPED_SPECIFIC_RULES.get(language, []):
        if bare.endswith(suffix):
            return gender
    fully_bare = _strip_all_accents(form)
    for suffix, gender in _STRIPPED_GENERIC_RULES.get(language, []):
        if fully_bare.endswith(suffix):
            return gender
    return None


def infer_noun_gender(lemma: str, language: str) -> str | None:
    """Infer a noun's gender ('Masc'/'Fem'/'Neut'), or None if unknown.

    *language* is the UniMorph TSV code ("grc"/"ell"), matching
    ``backend._load_index``'s own convention — map from an EEE-level code
    via ``tags.LANGUAGE_CODE_MAP`` first if needed.
    """
    raw_form = _load_nomsg_index(language).get(lemma)
    if raw_form is None:
        return gender_from_ending(lemma, language)
    from_article, rest = _split_article(raw_form, language)
    return from_article if from_article is not None else gender_from_ending(rest, language)
