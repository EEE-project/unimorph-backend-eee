#!/usr/bin/env python3
"""Extract unique UniMorph tags for a language/POS and write a starter TSV.

Output has the same schema as the bundled noun-tags.tsv / adj-tags.tsv:
a "tag" column plus UD feature columns reverse-mapped from each UniMorph token.
Only columns that appear in at least one tag are emitted.

Stdout is the TSV; redirect it to a file for bundling:
    uv run python scripts/extract_tags.py el verb > verb-tags-ell.tsv
    uv run python scripts/extract_tags.py grc adj > adj-tags-grc.tsv
    uv run python scripts/extract_tags.py jpn noun   # fetches from GitHub

Usage:
    extract_tags.py <lang|file.tsv> <noun|adjective|verb>
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unimorph_backend_eee.reverse import tag_to_ud
from unimorph_backend_eee.tags import CASE_MAP, NUMBER_MAP, GENDER_MAP, DEGREE_MAP, LANGUAGE_CODE_MAP
from unimorph_backend_eee.fetch import register_language, _parse_tsv


# ── sort orders (paradigm sequence) ──────────────────────────────────────────

_CASE_ORDER     = list(CASE_MAP.keys())
_NUMBER_ORDER   = list(NUMBER_MAP.keys())
_GENDER_ORDER   = list(GENDER_MAP.keys())
_DEGREE_ORDER   = ["Pos"] + [k for k, v in DEGREE_MAP.items() if v is not None]
_VERBFORM_ORDER = ["Fin", "Part", "Inf", "Conv"]
_MOOD_ORDER     = ["Ind", "Sub", "Opt", "Imp", "Cnd"]
_TENSE_ORDER    = ["Pres", "Past", "Fut"]
_ASPECT_ORDER   = ["Imp", "Perf"]
_PERSON_ORDER   = ["1", "2", "3"]
_VOICE_ORDER    = ["Act", "Mid", "Pass"]


def _rank(value: str, order: list[str]) -> int:
    try:
        return order.index(value)
    except ValueError:
        return 99


def _nominal_key(feats: dict) -> tuple:
    gender = feats.get("Gender", "")
    return (
        _rank(feats.get("Case", ""), _CASE_ORDER),
        _rank(feats.get("Number", ""), _NUMBER_ORDER),
        _rank(gender, _GENDER_ORDER) if gender else -1,  # gender-neutral forms first
        _rank(feats.get("Degree", "Pos"), _DEGREE_ORDER),
    )


def _verb_key(feats: dict) -> tuple:
    return (
        _rank(feats.get("VerbForm", "Fin"), _VERBFORM_ORDER),
        _rank(feats.get("Mood", "Ind"), _MOOD_ORDER),
        _rank(feats.get("Tense", ""), _TENSE_ORDER),
        _rank(feats.get("Aspect", ""), _ASPECT_ORDER),
        _rank(feats.get("Person", ""), _PERSON_ORDER),
        _rank(feats.get("Number", ""), _NUMBER_ORDER),
        _rank(feats.get("Voice", ""), _VOICE_ORDER),
    )


# ── extraction and output ─────────────────────────────────────────────────────

_NOMINAL_COLS = ["Case", "Number", "Gender", "Degree"]
_VERB_COLS    = ["VerbForm", "Tense", "Aspect", "Mood", "Voice", "Person", "Number"]


def extract(index: dict, pos: str) -> list[tuple[str, dict]]:
    pos_token = {"noun": "N", "adjective": "ADJ", "verb": "V"}[pos]
    prefix = pos_token + ";"
    seen: set[str] = set()
    pairs: list[tuple[str, dict]] = []
    for (_, tag) in index:
        if tag not in seen and tag.startswith(prefix):
            seen.add(tag)
            pairs.append((tag, tag_to_ud(tag)))
    sort_key = _verb_key if pos == "verb" else _nominal_key
    pairs.sort(key=lambda x: sort_key(x[1]))
    return pairs


def write_tsv(pairs: list[tuple[str, dict]], pos: str) -> None:
    col_order = _VERB_COLS if pos == "verb" else _NOMINAL_COLS
    all_keys = set().union(*(f for _, f in pairs))
    active = [c for c in col_order if c in all_keys]
    writer = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    writer.writerow(["tag"] + active)
    for tag, feats in pairs:
        writer.writerow([tag] + [feats.get(c, "") for c in active])


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    lang_arg, pos_arg = sys.argv[1], sys.argv[2].lower()
    pos_arg = {"n": "noun", "adj": "adjective", "v": "verb"}.get(pos_arg, pos_arg)
    if pos_arg not in ("noun", "adjective", "verb"):
        print(f"Error: pos must be noun, adjective, or verb (got {pos_arg!r})", file=sys.stderr)
        sys.exit(1)

    p = Path(lang_arg)
    if p.is_file():
        index = _parse_tsv(p)
        label = p.stem
        available_pos = None
    else:
        code = LANGUAGE_CODE_MAP.get(lang_arg, lang_arg)
        try:
            index, available_pos = register_language(code, verbose=True)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            print(f"Tip: run scripts/browse.py to see all available UniMorph languages.", file=sys.stderr)
            sys.exit(1)
        label = code

    pairs = extract(index, pos_arg)
    if not pairs:
        msg = f"No {pos_arg} data in '{label}'"
        if available_pos:
            msg += f". Available POS: {', '.join(available_pos)}"
        print(msg, file=sys.stderr)
        if available_pos and pos_arg not in available_pos:
            print(f"Tip: try `extract_tags.py {lang_arg} {available_pos[0]}`", file=sys.stderr)
        sys.exit(1)

    print(f"# {len(pairs)} unique {pos_arg} tags from '{label}'", file=sys.stderr)
    write_tsv(pairs, pos_arg)


if __name__ == "__main__":
    main()
