#!/usr/bin/env python3
"""Verify that _build_tags() produces the correct tag for every unique tag in every bundled TSV.

Exit 0 = zero divergences. Exit 1 = divergences found (implementation bug).

Usage:
    uv run python scripts/verify_identity.py              # all bundled languages
    uv run python scripts/verify_identity.py rus lat      # specific languages only

To add a new language, you must:
  1. Add an entry to PROFILE_MAP (maps (unimorph_code, pos_token) → profile name).
  2. If the profile uses a tag ordering not yet in parse_features(), add a branch.
  3. Add the language code to BUNDLED_LANGUAGES (or pass it on the command line).
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from unimorph_backend_eee.reverse import CASE_MAP_INV, NUMBER_MAP_INV, GENDER_MAP_INV, DEGREE_MAP_INV
from unimorph_backend_eee.profiles import _build_tags

NUMBER_TOKENS = set(NUMBER_MAP_INV)
GENDER_TOKENS = set(GENDER_MAP_INV)
DEGREE_TOKENS = set(DEGREE_MAP_INV)
ANIMACY_TOKENS = {"ANIM", "INAN"}

DATA_DIR = SRC_ROOT / "unimorph_backend_eee" / "data"

PROFILE_MAP: dict[tuple[str, str], str] = {
    ("ell", "N"):   "standard_nominal",
    ("ell", "ADJ"): "standard_nominal",
    ("grc", "N"):   "standard_nominal",
    ("grc", "ADJ"): "standard_nominal",
    ("lat", "N"):   "standard_nominal",
    ("lat", "ADJ"): "latin_nominal",
    ("rus", "N"):   "slavic_nominal",
    ("rus", "ADJ"): "slavic_nominal",
    ("spa", "N"):   "caseless_nominal",
    ("spa", "ADJ"): "caseless_nominal",
    ("tur", "N"):   "standard_nominal",
}

POS_TOKEN_TO_POS = {"N": "noun", "ADJ": "adjective"}


def _parse_caseless(parts: list[str]) -> dict | None:
    features: dict = {}
    for tok in parts[1:]:
        if tok in GENDER_TOKENS:
            features["Gender"] = GENDER_MAP_INV[tok]
        elif tok in NUMBER_TOKENS:
            features["Number"] = NUMBER_MAP_INV[tok]
        else:
            return None
    return features if "Number" in features else None


def _parse_slavic_adj(parts: list[str]) -> dict | None:
    remaining = parts[1:]
    features: dict = {}

    # ADJ;ANIM/INAN;ACC;MASC;SG — animacy-before-case pattern
    if len(remaining) == 4 and remaining[0] in ANIMACY_TOKENS:
        anim, case_tok, gender_tok, num_tok = remaining
        if case_tok not in CASE_MAP_INV or gender_tok not in GENDER_TOKENS or num_tok not in NUMBER_TOKENS:
            return None
        features["Animacy"] = "Anim" if anim == "ANIM" else "Inan"
        features["Case"] = CASE_MAP_INV[case_tok]
        features["Gender"] = GENDER_MAP_INV[gender_tok]
        features["Number"] = NUMBER_MAP_INV[num_tok]
        return features

    # ADJ;ACC;ANIM/INAN;PL — animacy-between-case-and-number pattern
    if len(remaining) == 3 and remaining[1] in ANIMACY_TOKENS:
        case_tok, anim, num_tok = remaining
        if case_tok not in CASE_MAP_INV or num_tok not in NUMBER_TOKENS:
            return None
        features["Case"] = CASE_MAP_INV[case_tok]
        features["Animacy"] = "Anim" if anim == "ANIM" else "Inan"
        features["Number"] = NUMBER_MAP_INV[num_tok]
        return features

    # Normal: ADJ;CASE;[GENDER;]NUM[;CMPR|SPRL]
    if not remaining or remaining[0] not in CASE_MAP_INV:
        return None
    features["Case"] = CASE_MAP_INV[remaining[0]]
    for tok in remaining[1:]:
        if tok in GENDER_TOKENS:
            features["Gender"] = GENDER_MAP_INV[tok]
        elif tok in NUMBER_TOKENS:
            features["Number"] = NUMBER_MAP_INV[tok]
        elif tok in DEGREE_TOKENS:
            features["Degree"] = DEGREE_MAP_INV[tok]
        else:
            return None
    return features if "Number" in features else None


def parse_features(unimorph_code: str, pos_token: str, tag: str) -> dict | None:
    """Inverse-map a UniMorph tag string to a UD feature dict.

    Returns None for tags that should be skipped (MASC+FEM combined tokens,
    unrecognised structure).
    """
    parts = tag.split(";")
    if not parts or parts[0] not in POS_TOKEN_TO_POS:
        return None

    # Skip combined gender tokens — these are secondary fallback tags, not primary
    if any("MASC+FEM" in tok for tok in parts):
        return None

    profile = PROFILE_MAP.get((unimorph_code, pos_token))
    if profile is None:
        return None

    if profile == "caseless_nominal":
        return _parse_caseless(parts)

    if profile == "slavic_nominal" and pos_token == "ADJ":
        return _parse_slavic_adj(parts)

    # standard_nominal, latin_nominal, slavic_nominal noun — all have CASE at position 1
    if len(parts) < 3 or parts[1] not in CASE_MAP_INV:
        return None

    features: dict = {"Case": CASE_MAP_INV[parts[1]]}
    for tok in parts[2:]:
        if tok in NUMBER_TOKENS:
            features["Number"] = NUMBER_MAP_INV[tok]
        elif tok in GENDER_TOKENS:
            features["Gender"] = GENDER_MAP_INV[tok]
        elif tok in DEGREE_TOKENS:
            features["Degree"] = DEGREE_MAP_INV[tok]
        elif tok in ANIMACY_TOKENS:
            features["Animacy"] = "Anim" if tok == "ANIM" else "Inan"
        else:
            return None  # Unknown token (DU dual, AB absolute superlative) — skip

    return features if "Number" in features else None


def collect_tags(tsv_path: Path) -> dict[str, set[str]]:
    """Read TSV; return {pos_token: {tag, ...}} for N and ADJ."""
    result: dict[str, set[str]] = {}
    try:
        text = tsv_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return result
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        tag = parts[2]
        pos_token = tag.split(";")[0]
        if pos_token in POS_TOKEN_TO_POS:
            result.setdefault(pos_token, set()).add(tag)
    return result


def verify_language(unimorph_code: str) -> tuple[int, int, int]:
    """Check all N/ADJ tags for one language. Returns (divergences, total_checked, total_skipped)."""
    tsv_path = DATA_DIR / f"{unimorph_code}.tsv"
    tags_by_pos = collect_tags(tsv_path)
    divergences = 0
    total = 0
    skipped = 0

    for pos_token, tags in tags_by_pos.items():
        pos = POS_TOKEN_TO_POS.get(pos_token)
        if pos is None:
            continue
        for tag in sorted(tags):
            features = parse_features(unimorph_code, pos_token, tag)
            if features is None:
                skipped += 1
                continue  # combined token or unsupported feature (DU dual, AB absolute superlative)
            total += 1
            try:
                result_tags = _build_tags(unimorph_code, pos, features)
            except Exception as exc:
                print(f"  DIVERGENCE: lang={unimorph_code} pos={pos} tag={tag} features={features} error={exc}")
                divergences += 1
                continue
            if tag not in result_tags:
                print(f"  DIVERGENCE: lang={unimorph_code} pos={pos} tag={tag} features={features} got={result_tags}")
                divergences += 1

    return divergences, total, skipped


BUNDLED_LANGUAGES = ("ell", "grc", "lat", "rus", "spa", "tur")


def main() -> None:
    langs = sys.argv[1:] if len(sys.argv) > 1 else BUNDLED_LANGUAGES
    unknown = [l for l in langs if (DATA_DIR / f"{l}.tsv").exists() is False]
    if unknown:
        print(f"Error: no bundled TSV for: {', '.join(unknown)}", file=sys.stderr)
        print(f"Available: {', '.join(BUNDLED_LANGUAGES)}", file=sys.stderr)
        sys.exit(1)

    total_div = 0
    total_checked = 0
    total_skipped = 0
    for lang in langs:
        div, checked, skipped = verify_language(lang)
        print(f"{lang}: {div} divergences (checked {checked}, skipped {skipped})")
        total_div += div
        total_checked += checked
        total_skipped += skipped
    print("---")
    print(f"Total: {total_div} divergences across {total_checked} tags ({total_skipped} skipped)")
    sys.exit(0 if total_div == 0 else 1)


if __name__ == "__main__":
    main()
