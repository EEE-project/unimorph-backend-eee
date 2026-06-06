"""Declarative tag profile interpreter for UniMorph tag generation.

Public API:
  load_profiles()       — read and cache tag_profiles.toml
  _build_tags()         — build UniMorph tag(s) from (language, pos, features)
  register_tag_hook()   — register a per-(language, pos) Python callable
  detect_profile()      — classify a TSV file into a profile name
  _clear_profile_cache() — test utility: reset TOML cache
  _clear_all_hooks()    — test utility: clear hook registry
"""
from __future__ import annotations

import importlib.resources
import tomllib
from typing import Callable

from unimorph_backend_eee._exceptions import (
    FeatureNotSupportedError,
    PosNotSupportedError,
    UnsupportedLanguageError,
)
from unimorph_backend_eee.tags import CASE_MAP, DEGREE_MAP, GENDER_MAP, LANGUAGE_CODE_MAP, NUMBER_MAP

_KNOWN_SLOTS = frozenset({
    "pos",
    "case",
    "number",
    "?gender",
    "?gender_if_singular",
    "?degree",
})

_KNOWN_FLAGS = frozenset({
    "animacy_acc",
    "masc_fem_combined_fallback",
    "noun_strip_gender",
    "adjective_drop_gender_fallback",
    "adjective_masc_fem_combined_fallback",
})

# Module-level cache; reset by _clear_profile_cache() in tests.
_profile_cache: dict | None = None

# Module-level hook registry; populated by register_tag_hook().
# Not thread-safe: all registrations must complete before concurrent _build_tags() calls.
_HOOK_REGISTRY: dict[tuple[str, str], Callable[[dict], list[str]]] = {}

# Resolved at module level so tests can monkeypatch it.
_TOML_PATH = importlib.resources.files("unimorph_backend_eee.data").joinpath(
    "tag_profiles.toml"
)


def load_profiles() -> dict:
    """Read and parse tag_profiles.toml. Cached after first call.

    Returns a dict with keys:
      "profiles": dict of profile_name → profile config dict
      "languages": dict of language_code → language config dict

    Raises ValueError on:
      - Malformed TOML (parse error)
      - Unknown slot keyword in any profile's slots list
      - Unknown flag name in any profile's or language's flags table
      - A language assignment references a profile name not defined in [profiles]
    """
    global _profile_cache
    if _profile_cache is not None:
        return _profile_cache
    with _TOML_PATH.open("rb") as f:
        data = tomllib.load(f)
    _validate_schema(data)
    _profile_cache = data
    return _profile_cache


def _validate_schema(data: dict) -> None:
    """Validate parsed TOML against known slot/flag vocabularies.

    Raises ValueError with a descriptive message on any violation.
    """
    profiles = data.get("profiles", {})
    languages = data.get("languages", {})

    for name, profile in profiles.items():
        for slot in profile.get("slots", []):
            if slot not in _KNOWN_SLOTS:
                known = ", ".join(sorted(_KNOWN_SLOTS))
                raise ValueError(
                    f"Unknown slot keyword '{slot}' in profile '{name}'. "
                    f"Known slots: {known}"
                )
        for flag in profile.get("flags", {}):
            if flag not in _KNOWN_FLAGS:
                known = ", ".join(sorted(_KNOWN_FLAGS))
                raise ValueError(
                    f"Unknown flag '{flag}' in profile '{name}'. "
                    f"Known flags: {known}"
                )

    for lang, lang_cfg in languages.items():
        for flag in lang_cfg.get("flags", {}):
            if flag not in _KNOWN_FLAGS:
                known = ", ".join(sorted(_KNOWN_FLAGS))
                raise ValueError(
                    f"Unknown flag '{flag}' for language '{lang}'. "
                    f"Known flags: {known}"
                )
        for pos_key, profile_name in lang_cfg.get("pos", {}).items():
            if profile_name not in profiles:
                raise ValueError(
                    f"Profile '{profile_name}' referenced by language '{lang}' "
                    f"(pos '{pos_key}') is not defined in [profiles]."
                )


def _clear_profile_cache() -> None:
    """Test utility. Reset cached TOML data so next call re-reads the file."""
    global _profile_cache
    _profile_cache = None


_POS_TOKEN: dict[str, str] = {"verb": "V", "noun": "N", "adjective": "ADJ"}


def _animacy_acc_tags(pos_token: str, features: dict) -> list[str]:
    """Build tag(s) for Russian-style accusative animacy (animacy_acc flag, ACC case).

    Four sub-cases:
    - ACC + PL (any gender): [POS, ACC, ANIM|INAN, PL] — gender dropped
    - ACC + SG + Masc:       [POS, ANIM|INAN, ACC, MASC, SG] — animacy before case
    - ACC + SG + Fem/Neut:   [POS, ACC, GENDER, SG] — no animacy prefix
    Unknown animacy → two tags (ANIM and INAN variants).
    """
    number_ud = features.get("Number")
    number = NUMBER_MAP.get(number_ud)  # type: ignore[arg-type]
    if number is None:
        raise FeatureNotSupportedError("Number", str(number_ud))
    gender_ud = features.get("Gender")
    gender = GENDER_MAP.get(gender_ud) if gender_ud else None  # type: ignore[arg-type]
    if gender_ud is not None and gender is None:
        raise FeatureNotSupportedError("Gender", str(gender_ud))
    animacy_ud = features.get("Animacy")

    if number == "PL":
        if animacy_ud == "Anim":
            return [f"{pos_token};ACC;ANIM;PL"]
        elif animacy_ud == "Inan":
            return [f"{pos_token};ACC;INAN;PL"]
        else:
            return [f"{pos_token};ACC;ANIM;PL", f"{pos_token};ACC;INAN;PL"]
    else:  # SG
        if gender == "MASC":
            if animacy_ud == "Anim":
                return [f"{pos_token};ANIM;ACC;MASC;SG"]
            elif animacy_ud == "Inan":
                return [f"{pos_token};INAN;ACC;MASC;SG"]
            else:
                return [f"{pos_token};ANIM;ACC;MASC;SG", f"{pos_token};INAN;ACC;MASC;SG"]
        elif gender in ("FEM", "NEUT"):
            return [f"{pos_token};ACC;{gender};SG"]
        elif gender is None and pos_token == "N":  # noun — no gender in TSV tag
            if animacy_ud == "Anim":
                return [f"{pos_token};ACC;ANIM;SG"]
            elif animacy_ud == "Inan":
                return [f"{pos_token};ACC;INAN;SG"]
            else:
                return [f"{pos_token};ACC;ANIM;SG", f"{pos_token};ACC;INAN;SG"]
        else:
            raise FeatureNotSupportedError("Gender", str(gender_ud))


def _drop_gender_secondary_tag(primary_tag: str) -> str | None:
    """Return primary_tag with the gender token (MASC/FEM/NEUT) removed.

    Returns None if no gender token is present.
    Used for grc adjective_drop_gender_fallback secondary lookup (called from section-07
    _fallback_lookups, not from _build_tags directly — _lookup requires lemma).
    """
    parts = primary_tag.split(";")
    new_parts = [p for p in parts if p not in ("MASC", "FEM", "NEUT")]
    if len(new_parts) == len(parts):
        return None
    return ";".join(new_parts)


def _masc_fem_combined_secondary_tag(primary_tag: str) -> str | None:
    """Return primary_tag with MASC or FEM replaced by the combined MASC+FEM token.

    Returns None if gender token is NEUT or absent (no substitution needed).
    Used for lat/spa adjective_masc_fem_combined_fallback secondary lookup.
    """
    parts = primary_tag.split(";")
    for i, part in enumerate(parts):
        if part in ("MASC", "FEM"):
            new_parts = list(parts)
            new_parts[i] = "MASC+FEM"
            return ";".join(new_parts)
    return None


def _build_tags(unimorph_code: str, pos: str, features: dict) -> list[str]:
    """Build UniMorph tag string(s) for a (language, POS, features) triple.

    Priority order:
    1. If a hook is registered for (unimorph_code, pos), call and return it.
    2. If pos == "verb" and no TOML profile exists, fall back to ud_to_unimorph_tag().
    3. Apply pre-processing language flags (noun_strip_gender).
    4. If animacy_acc flag and Case==Acc: delegate to animacy_acc logic.
    5. Resolve each slot in order; return ["POS;SLOT1;SLOT2;..."].
    """
    hook = _HOOK_REGISTRY.get((unimorph_code, pos))
    if hook is not None:
        return hook(features)

    config = load_profiles()
    lang_config = config["languages"].get(unimorph_code, {})
    lang_flags = lang_config.get("flags", {})
    profile_name = lang_config.get("pos", {}).get(pos)
    if profile_name is None:
        if pos == "verb":
            # Lazy import breaks the backend→profiles→backend cycle (backend is already loaded).
            from unimorph_backend_eee.backend import ud_to_unimorph_tag  # noqa: PLC0415
            return ud_to_unimorph_tag(features, pos)
        raise PosNotSupportedError(pos)
    profile = config["profiles"][profile_name]
    profile_flags = profile.get("flags", {})
    case_overrides = profile.get("case_overrides", {})

    # Pre-processing: strip Gender for grc nouns before slot resolution.
    if lang_flags.get("noun_strip_gender") and pos == "noun":
        features = {k: v for k, v in features.items() if k != "Gender"}

    # animacy_acc: Russian-style ACC handling.
    # Adjectives: always dispatch (animacy prefix for Masc SG, no prefix for Fem/Neut SG).
    # Nouns: dispatch only when caller provides explicit Animacy (rare animate nouns in TSV).
    if profile_flags.get("animacy_acc") and features.get("Case") == "Acc":
        if pos == "adjective" or (pos == "noun" and features.get("Animacy") is not None):
            return _animacy_acc_tags(_POS_TOKEN[pos], features)

    parts: list[str] = []
    for slot in profile["slots"]:
        if slot == "pos":
            parts.append(_POS_TOKEN[pos])
        elif slot == "case":
            case_ud = features.get("Case")
            if case_ud in case_overrides:
                parts.append(case_overrides[case_ud])
            elif case_ud in CASE_MAP:
                parts.append(CASE_MAP[case_ud])
            else:
                raise FeatureNotSupportedError("Case", str(case_ud))
        elif slot == "number":
            number_ud = features.get("Number")
            number = NUMBER_MAP.get(number_ud)  # type: ignore[arg-type]
            if number is None:
                raise FeatureNotSupportedError("Number", str(number_ud))
            parts.append(number)
        elif slot == "?gender":
            gender_ud = features.get("Gender")
            if gender_ud is not None:
                gender = GENDER_MAP.get(gender_ud)
                if gender is None:
                    raise FeatureNotSupportedError("Gender", str(gender_ud))
                parts.append(gender)
        elif slot == "?gender_if_singular":
            if features.get("Number") == "Sing":
                gender_ud = features.get("Gender")
                if gender_ud is not None:
                    gender = GENDER_MAP.get(gender_ud)
                    if gender is None:
                        raise FeatureNotSupportedError("Gender", str(gender_ud))
                    parts.append(gender)
        elif slot == "?degree":
            degree_ud = features.get("Degree")
            if degree_ud is not None:
                if degree_ud not in DEGREE_MAP:
                    raise FeatureNotSupportedError("Degree", str(degree_ud))
                degree_token = DEGREE_MAP[degree_ud]
                if degree_token is not None:  # None = Pos = omit slot
                    parts.append(degree_token)

    return [";".join(parts)]


def _fallback_lookups(
    unimorph_code: str,
    pos: str,
    lemma: str,
    primary_tags: list[str],
    features: dict,
    lookup_fn: Callable,
) -> set[str]:
    """Apply secondary lookups for two-termination adjectives and combined-gender tokens.

    Reads adjective_drop_gender_fallback, adjective_masc_fem_combined_fallback, and
    masc_fem_combined_fallback from the TOML profile. Returns forms to union into the
    primary result set. All three flags only trigger when Gender is Masc or Fem.
    """
    config = load_profiles()
    lang_cfg = config["languages"].get(unimorph_code, {})
    lang_flags = lang_cfg.get("flags", {})
    profile_name = lang_cfg.get("pos", {}).get(pos)
    profile_flags = config["profiles"].get(profile_name, {}).get("flags", {}) if profile_name else {}

    results: set[str] = set()
    gender = features.get("Gender")

    if (lang_flags.get("adjective_drop_gender_fallback")
            and pos == "adjective"
            and gender in ("Masc", "Fem")):
        for tag in primary_tags:
            secondary = _drop_gender_secondary_tag(tag)
            if secondary:
                results |= lookup_fn(lemma, secondary, unimorph_code)

    combined = (
        (lang_flags.get("adjective_masc_fem_combined_fallback") and pos == "adjective")
        or profile_flags.get("masc_fem_combined_fallback")
    )
    if combined and gender in ("Masc", "Fem"):
        for tag in primary_tags:
            secondary = _masc_fem_combined_secondary_tag(tag)
            if secondary:
                results |= lookup_fn(lemma, secondary, unimorph_code)

    return results


def register_tag_hook(language: str, pos: str, fn: Callable[[dict], list[str]]) -> None:
    """Register a Python callable as tag builder for a (language, pos) pair.

    Takes priority over TOML profile dispatch for that pair. Language is
    resolved via LANGUAGE_CODE_MAP; raises UnsupportedLanguageError if unknown.
    pos must be a key in _POS_TOKEN; raises PosNotSupportedError if unknown.
    """
    unimorph_code = LANGUAGE_CODE_MAP.get(language)
    if unimorph_code is None:
        raise UnsupportedLanguageError(language)
    if pos not in _POS_TOKEN:
        raise PosNotSupportedError(pos)
    # Guard: reject (language, pos) pairs that inflect() would reject before _build_tags is called,
    # since hooks are dispatched inside _build_tags and would never fire for those pairs.
    from unimorph_backend_eee.backend import _SUPPORTED_POS  # noqa: PLC0415
    supported = _SUPPORTED_POS.get(unimorph_code, [])
    if supported and pos not in supported:
        raise PosNotSupportedError(pos)
    _HOOK_REGISTRY[(unimorph_code, pos)] = fn


def _clear_all_hooks() -> None:
    """Test utility. Clear all registered hooks."""
    _HOOK_REGISTRY.clear()


_CASE_TOKENS = frozenset({"NOM", "ACC", "GEN", "DAT", "VOC", "ABL", "INS", "LOC", "ESS"})
_GENDER_TOKENS = frozenset({"MASC", "FEM", "NEUT", "MASC+FEM"})
_NUMBER_TOKENS = frozenset({"SG", "PL"})


def detect_profile(language_code: str, tsv_path: str) -> str:
    """Sample up to 200 lines from tsv_path and classify into a profile name.

    Heuristic order (must not be reordered):
    1. No case tokens anywhere → "caseless_nominal"
    2. Any ANIM or INAN token → "slavic_nominal"
    3. Gender token position < number token position in any tag → "latin_nominal"
    4. Default → "standard_nominal"

    language_code is accepted for API consistency but not used in heuristic.
    """
    adj_tags: list[list[str]] = []
    with open(tsv_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 200:
                break
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            tag = parts[2]
            if tag.startswith("ADJ;"):
                adj_tags.append(tag.split(";"))

    if not adj_tags:
        return "standard_nominal"

    all_tokens: set[str] = {tok for tokens in adj_tags for tok in tokens}

    if not (_CASE_TOKENS & all_tokens):
        return "caseless_nominal"

    if "ANIM" in all_tokens or "INAN" in all_tokens:
        return "slavic_nominal"

    for tokens in adj_tags:
        gender_idx = next((i for i, t in enumerate(tokens) if t in _GENDER_TOKENS), None)
        number_idx = next((i for i, t in enumerate(tokens) if t in _NUMBER_TOKENS), None)
        if gender_idx is not None and number_idx is not None and gender_idx < number_idx:
            return "latin_nominal"

    return "standard_nominal"
