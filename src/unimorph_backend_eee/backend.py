import importlib.resources
import logging

from unimorph_backend_eee._exceptions import (
    FeatureNotSupportedError,
    PosNotSupportedError,
    UnsupportedLanguageError,
)
from unimorph_backend_eee.tags import (
    CASE_MAP,
    DEGREE_MAP,
    GENDER_MAP,
    LANGUAGE_CODE_MAP,
    NUMBER_MAP,
    PERSON_MAP,
    TENSE_ASPECT_MAP,
)

logger = logging.getLogger(__name__)

_POS_TOKEN = {"verb": "V", "noun": "N", "adjective": "ADJ"}

_INDEX_CACHE: dict[str, dict[tuple[str, str], set[str]]] = {}

# Supported POS per unimorph dataset code.
_SUPPORTED_POS: dict[str, list[str]] = {
    "ell": ["verb", "noun", "adjective"],
    "grc": ["noun", "adjective"],  # no verb data in grc.tsv
}


def _load_index(language: str) -> dict[tuple[str, str], set[str]]:
    if language in _INDEX_CACHE:
        return _INDEX_CACHE[language]
    tsv = (
        importlib.resources.files("unimorph_backend_eee.data")
        .joinpath(f"{language}.tsv")
    )
    index: dict[tuple[str, str], set[str]] = {}
    try:
        text = tsv.read_text(encoding="utf-8")
    except Exception:
        logger.warning("UniMorph TSV not found for language '%s'", language)
        _INDEX_CACHE[language] = index
        return index
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        lemma_tsv, form, tag_tsv = parts
        if lemma_tsv.startswith("'"):  # elided/corrupt entry; real spelling also in TSV
            continue
        # Split comma-separated variants, strip particle prefixes, filter sentinels.
        # "θα δροσίζουμε, δροσίζομε" → {"δροσίζουμε", "δροσίζομε"}; "—" → nothing.
        for raw_variant in form.split(","):
            token = raw_variant.strip()
            if " " in token:
                token = token.rsplit(" ", 1)[1]
            if token and token != "—":
                index.setdefault((lemma_tsv, tag_tsv), set()).add(token)
    _INDEX_CACHE[language] = index
    return index


def _lookup(lemma: str, tag: str, language: str) -> set[str]:
    return _load_index(language).get((lemma, tag), set())


def ud_to_unimorph_tag(features: dict, pos: str) -> list[str]:
    """Translate a UD feature dict + POS to UniMorph tag(s)."""
    pos_token = _POS_TOKEN.get(pos)
    if pos_token is None:
        raise PosNotSupportedError(pos)

    remaining = dict(features)

    if pos == "verb":
        verbform = remaining.pop("VerbForm", None)
        if verbform in ("Part", "Inf"):
            raise FeatureNotSupportedError("VerbForm", verbform)

        remaining.pop("Voice", None)  # voice not present in UniMorph ell.tsv verb tags

        mood_ud = remaining.pop("Mood", None)

        person_ud = remaining.pop("Person", None)
        if person_ud not in PERSON_MAP:
            raise FeatureNotSupportedError("Person", str(person_ud))
        person = PERSON_MAP[person_ud]

        number_ud = remaining.pop("Number", None)
        if number_ud not in NUMBER_MAP:
            raise FeatureNotSupportedError("Number", str(number_ud))
        number = NUMBER_MAP[number_ud]

        if mood_ud == "Imp":
            remaining.pop("Tense", None)   # unimorph imperative tag carries no tense
            remaining.pop("Aspect", None)  # or aspect info
            if remaining:
                key, val = next(iter(remaining.items()))
                raise FeatureNotSupportedError(key, str(val))
            return [f"V;{person};{number};IMP"]

        tense_ud = remaining.pop("Tense", None)
        aspect_ud = remaining.pop("Aspect", None)

        if remaining:
            key, val = next(iter(remaining.items()))
            raise FeatureNotSupportedError(key, str(val))

        if mood_ud == "Sub":
            if aspect_ud is None:
                return [f"V;{person};{number};IPFV;SBJV", f"V;{person};{number};PFV;SBJV"]
            elif aspect_ud == "Imp":
                return [f"V;{person};{number};IPFV;SBJV"]
            elif aspect_ud == "Perf":
                return [f"V;{person};{number};PFV;SBJV"]
            else:
                raise FeatureNotSupportedError("Aspect", str(aspect_ud))

        ta_key = (tense_ud, aspect_ud)
        if ta_key not in TENSE_ASPECT_MAP:
            raise FeatureNotSupportedError("Tense+Aspect", f"{tense_ud}+{aspect_ud}")
        ta_result = TENSE_ASPECT_MAP[ta_key]

        if isinstance(ta_result, list):
            return [f"V;{person};{number};{asp};{tns}" for asp, tns in ta_result]
        asp, tns = ta_result
        return [f"V;{person};{number};{asp};{tns}"]

    else:  # noun / adjective
        degree_ud = remaining.pop("Degree", None)
        if degree_ud is not None and degree_ud not in DEGREE_MAP:
            raise FeatureNotSupportedError("Degree", str(degree_ud))
        degree = DEGREE_MAP.get(degree_ud) if degree_ud is not None else None

        case_ud = remaining.pop("Case", None)
        if case_ud not in CASE_MAP:
            raise FeatureNotSupportedError("Case", str(case_ud))
        case = CASE_MAP[case_ud]

        number_ud = remaining.pop("Number", None)
        if number_ud not in NUMBER_MAP:
            raise FeatureNotSupportedError("Number", str(number_ud))
        number = NUMBER_MAP[number_ud]

        gender_ud = remaining.pop("Gender", None)
        gender = GENDER_MAP.get(gender_ud)
        if gender_ud is not None and gender is None:
            raise FeatureNotSupportedError("Gender", str(gender_ud))

        if remaining:
            key, val = next(iter(remaining.items()))
            raise FeatureNotSupportedError(key, str(val))

        parts = [pos_token, case, number]
        if gender:
            parts.append(gender)
        if degree:
            parts.append(degree)
        return [";".join(parts)]


class UniMorphBackend:
    def __init__(self, language: str = "") -> None:
        self._language = language

    def inflect(self, lemma: str, features: dict, pos: str, **_kw) -> set[str]:
        language = self._language or _kw.get("language", "")
        if not language or language not in LANGUAGE_CODE_MAP:
            raise UnsupportedLanguageError(language or "<no language>")

        unimorph_code = LANGUAGE_CODE_MAP[language]

        # grc/verb is not supported by UniMorph
        if unimorph_code == "grc" and pos == "verb":
            logger.warning(
                "UniMorphBackend called for grc/verb — unimorph_inflect does not "
                "support Ancient Greek verbs; use AncientGreekBackend instead"
            )
            raise PosNotSupportedError(f"{language}/{pos}")

        allowed_pos = _SUPPORTED_POS.get(unimorph_code, [])
        if allowed_pos and pos not in allowed_pos:
            raise PosNotSupportedError(f"{language}/{pos}")

        # grc.tsv gender conventions:
        # - nouns: N;CASE;NUM (gender never present)
        # - adjectives: ADJ;CASE;NUM;GENDER for three-termination;
        #               both ADJ;CASE;NUM;GENDER and ADJ;CASE;NUM for two-termination
        if unimorph_code == "grc" and pos == "noun":
            features = {k: v for k, v in features.items() if k != "Gender"}

        tags = ud_to_unimorph_tag(features, pos)
        results: set[str] = set()
        for tag in tags:
            results |= _lookup(lemma, tag, unimorph_code)

        # grc two-termination adjectives index Masc/Fem without a gender tag;
        # Neut has its own NEUT-tagged entries and must not use the bare fallback.
        if unimorph_code == "grc" and pos == "adjective" and features.get("Gender") in ("Masc", "Fem"):
            features_ng = {k: v for k, v in features.items() if k != "Gender"}
            for tag in ud_to_unimorph_tag(features_ng, pos):
                results |= _lookup(lemma, tag, unimorph_code)

        return {f for f in results if f and f not in {"UNK", "—"}}

    def list_lemmas(self, pos: str) -> list[str]:
        language = self._language
        if not language or language not in LANGUAGE_CODE_MAP:
            return []
        pos_token = _POS_TOKEN.get(pos)
        if pos_token is None:
            return []
        unimorph_code = LANGUAGE_CODE_MAP[language]
        index = _load_index(unimorph_code)
        prefix = pos_token + ";"
        lemmas = {lemma for (lemma, tag) in index if tag.startswith(prefix)}
        # ell.tsv contains conjugated forms as spurious lemmas (Wiktionary scraping artifact).
        # Modern Greek verbal lemmas always end in ω/ώ (active) or μαι (deponent/passive).
        if unimorph_code == "ell" and pos == "verb":
            lemmas = {l for l in lemmas if l.endswith(("ω", "ώ", "μαι"))}
        return sorted(lemmas)

    def supported_languages(self) -> list[str]:
        return list(_SUPPORTED_POS.keys())
