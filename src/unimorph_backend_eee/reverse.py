"""Reverse maps: UniMorph token → UD feature value.

Public API:
  CASE_MAP_INV, NUMBER_MAP_INV, GENDER_MAP_INV, DEGREE_MAP_INV, PERSON_MAP_INV
  tag_to_ud(tag)  — parse a UniMorph tag string into a UD feature dict
"""

from unimorph_backend_eee.tags import (
    CASE_MAP, DEGREE_MAP, GENDER_MAP, NUMBER_MAP, PERSON_MAP,
)

CASE_MAP_INV   = {v: k for k, v in CASE_MAP.items()}
CASE_MAP_INV["ESS"] = "Loc"    # Slavic Locative surfaces as ESS in UniMorph

NUMBER_MAP_INV = {v: k for k, v in NUMBER_MAP.items()}

GENDER_MAP_INV = {v: k for k, v in GENDER_MAP.items()}
DEGREE_MAP_INV = {v: k for k, v in DEGREE_MAP.items() if v is not None}
PERSON_MAP_INV = {v: k for k, v in PERSON_MAP.items()}

_ASPECT_TOKENS   = {"IPFV": "Imp", "PFV": "Perf"}
_TENSE_TOKENS    = {"PRS": "Pres", "PST": "Past", "FUT": "Fut"}
_MOOD_TOKENS     = {"IND": "Ind", "SBJV": "Sub", "IMP": "Imp", "OPT": "Opt", "COND": "Cnd"}
_VERBFORM_TOKENS = {"PTCP": "Part", "INF": "Inf", "CONV": "Conv", "VNOUN": "Vnoun"}
_VOICE_TOKENS    = {"ACT": "Act", "MID": "Mid", "PASS": "Pass"}


def _parse_nominal(tokens: list[str]) -> dict[str, str]:
    feats: dict[str, str] = {}
    for tok in tokens:
        if tok in CASE_MAP_INV:
            feats["Case"] = CASE_MAP_INV[tok]
        elif tok in NUMBER_MAP_INV:
            feats["Number"] = NUMBER_MAP_INV[tok]
        elif tok in GENDER_MAP_INV:
            feats["Gender"] = GENDER_MAP_INV[tok]
        elif tok in DEGREE_MAP_INV:
            feats["Degree"] = DEGREE_MAP_INV[tok]
    return feats


def _parse_verb(tokens: list[str]) -> dict[str, str]:
    feats: dict[str, str] = {}
    prf = False
    aspect_ud: str | None = None
    tense_ud: str | None = None

    for tok in tokens:
        if tok in PERSON_MAP_INV:
            feats["Person"] = PERSON_MAP_INV[tok]
        elif tok in NUMBER_MAP_INV:
            feats["Number"] = NUMBER_MAP_INV[tok]
        elif tok == "PRF":
            prf = True
        elif tok in _ASPECT_TOKENS:
            aspect_ud = _ASPECT_TOKENS[tok]
        elif tok in _TENSE_TOKENS:
            tense_ud = _TENSE_TOKENS[tok]
        elif tok in _MOOD_TOKENS:
            feats["Mood"] = _MOOD_TOKENS[tok]
        elif tok in _VERBFORM_TOKENS:
            feats["VerbForm"] = _VERBFORM_TOKENS[tok]
        elif tok in _VOICE_TOKENS:
            feats["Voice"] = _VOICE_TOKENS[tok]

    if prf:
        feats["Tense"] = "Pqp" if tense_ud == "Past" else "Perf"
    else:
        if aspect_ud:
            feats["Aspect"] = aspect_ud
        if tense_ud:
            feats["Tense"] = tense_ud
    if tense_ud and "Mood" not in feats and "VerbForm" not in feats:
        feats["Mood"] = "Ind"
    if "VerbForm" not in feats and ("Person" in feats or "Mood" in feats):
        feats["VerbForm"] = "Fin"

    return feats


def tag_to_ud(tag: str) -> dict[str, str]:
    """Parse a UniMorph tag string into a UD feature dict.

    Unknown tokens are silently ignored (language-specific extensions,
    compound gender tokens like MASC+FEM, absolute superlative AB, etc.).
    Returns an empty dict for unrecognised POS tokens.
    """
    parts = tag.split(";")
    pos, tokens = parts[0], parts[1:]
    if pos in ("N", "ADJ"):
        return _parse_nominal(tokens)
    if pos == "V":
        return _parse_verb(tokens)
    return {}
