#!/usr/bin/env python3
"""Browse any UniMorph language: pick a lemma, see all inflected forms.

Without arguments shows all languages in the UniMorph GitHub org.
Bundled languages work offline; others are fetched and cached on first use.

Usage:
    uv run python scripts/browse.py           # full UniMorph language list
    uv run python scripts/browse.py dak       # jump straight to Dakota
    uv run python scripts/browse.py file.tsv  # local TSV file
"""
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from unimorph_backend_eee.backend import _SUPPORTED_POS, _load_index
from unimorph_backend_eee.fetch import (
    CACHE_DIR,
    ISO639_FALLBACK,
    fetch_language_list,
    fetch_tsv,
    register_language,
    _parse_tsv,
    _POS_TOKEN,
)

_BUNDLED = set(_SUPPORTED_POS.keys())
_BUNDLED_NAMES = {
    "ell": "Modern Greek", "grc": "Ancient Greek", "lat": "Latin",
    "rus": "Russian", "spa": "Spanish", "tur": "Turkish",
}


# ── language picker ───────────────────────────────────────────────────────────

def choose_language(languages: list[dict]) -> str:
    """Show full language list; return chosen language code."""
    cached_codes = {p.stem for p in CACHE_DIR.glob("*.tsv")} if CACHE_DIR.exists() else set()

    rows = []
    for lang in languages:
        code = lang["code"].lower()
        name = lang["name"]
        status = ""
        if code in _BUNDLED:
            status = " [bundled]"
        elif code in cached_codes:
            status = " [cached]"
        rows.append((code, name, status))

    print(f"\n{len(rows)} UniMorph languages  "
          "([bundled]=offline, [cached]=downloaded, others fetched on demand)")
    print("─" * 60)
    for i, (code, name, status) in enumerate(rows, 1):
        label = f"{code:<6} {name}"
        print(f"  {i:>3}. {label:<42}{status}")
    print("─" * 60)
    print("  0. random")
    print()

    all_codes = [r[0] for r in rows]
    while True:
        raw = input("Enter number, language code, or name fragment: ").strip().lower()
        if not raw:
            continue
        if raw == "0":
            return random.choice(all_codes)
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(rows):
                return rows[idx][0]
        if raw in all_codes:
            return raw
        matches = [r for r in rows if raw in r[0] or raw in r[1].lower()]
        if len(matches) == 1:
            return matches[0][0]
        if matches:
            print(f"  matches: {', '.join(r[0] for r in matches[:12])}")
        else:
            print("  not found")


# ── lemma + forms ─────────────────────────────────────────────────────────────

def choose_from(prompt: str, options: list[str]) -> str:
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    if len(options) > 1:
        print("  0. random")
    while True:
        raw = input("> ").strip()
        if raw == "0" and len(options) > 1:
            return random.choice(options)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        if raw in options:
            return raw
        print("  invalid")


def choose_lemma(lemmas: list[str]) -> str:
    sample = sorted(random.sample(lemmas, min(10, len(lemmas))))
    print(f"\nLemma  ({len(lemmas)} available — type, pick from sample, or 0 for random):")
    for i, lm in enumerate(sample, 1):
        print(f"  {i}. {lm}")
    print("  0. random")
    while True:
        raw = input("> ").strip()
        if raw == "0":
            return random.choice(lemmas)
        if raw.isdigit() and 1 <= int(raw) <= len(sample):
            return sample[int(raw) - 1]
        if raw in lemmas:
            return raw
        matches = [lm for lm in lemmas if raw.lower() in lm.lower()]
        if len(matches) == 1:
            return matches[0]
        if matches:
            print(f"  ambiguous ({len(matches)}): {', '.join(matches[:8])}")
        else:
            print("  not found — try again")


def show_forms(label: str, pos: str, lemma: str, index: dict) -> None:
    pos_token = {"noun": "N", "adjective": "ADJ", "verb": "V"}[pos]
    prefix = pos_token + ";"
    entries = sorted(
        ((tag, forms) for (lm, tag), forms in index.items()
         if lm == lemma and (tag.startswith(prefix) or tag == pos_token)),
        key=lambda x: x[0],
    )
    print(f"\n{'─' * 54}")
    print(f"  {label}  ·  {pos}  ·  {lemma}")
    print(f"{'─' * 54}")
    for tag, forms in entries:
        tag_part = tag[len(pos_token) + 1:] if ";" in tag else tag
        print(f"  {tag_part:<32} {', '.join(sorted(forms))}")
    if not entries:
        print("  (no entries)")
    print(f"{'─' * 54}")


def _browse(label: str, pos_options: list[str], index: dict) -> None:
    if not pos_options:
        print("No supported POS found for this language.")
        return
    pos = pos_options[0] if len(pos_options) == 1 else choose_from("POS:", pos_options)
    pos_token = {"noun": "N", "adjective": "ADJ", "verb": "V"}[pos]
    lemmas = sorted({lm for (lm, tag) in index
                     if tag.startswith(pos_token + ";") or tag == pos_token})
    if not lemmas:
        print("No lemmas found for this POS.")
        return
    lemma = choose_lemma(lemmas)
    show_forms(label, pos, lemma, index)


# ── flows ─────────────────────────────────────────────────────────────────────

def run_code(code: str) -> None:
    try:
        index, pos_options = register_language(code, verbose=True)
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except (ValueError, UnicodeDecodeError) as e:
        print(f"\nError: {e}")
        sys.exit(1)
    label = _BUNDLED_NAMES.get(code, code.upper())
    _browse(label, pos_options, index)


def run_file(tsv_path: Path) -> None:
    code = tsv_path.stem.lower()
    if code in _BUNDLED:
        print(f"Warning: '{tsv_path.name}' has the same stem as a bundled language. "
              f"Using local file.")
    try:
        index = _parse_tsv(tsv_path)
        if not index:
            print("\nError: TSV appears empty or malformed.")
            sys.exit(1)
        pos_tokens = sorted({tag.split(";")[0] for (_, tag) in index} & _POS_TOKEN.keys())
        if not pos_tokens:
            print("\nError: No recognised POS tokens (N / ADJ / V) found.")
            sys.exit(1)
        pos_options = [_POS_TOKEN[pt] for pt in pos_tokens]
    except (ValueError, UnicodeDecodeError) as e:
        print(f"\nError: {e}")
        sys.exit(1)
    _browse(code.upper(), pos_options, index)


def run_menu() -> None:
    languages = fetch_language_list(verbose=True)
    if not languages:
        languages = [{"code": c, "name": _BUNDLED_NAMES.get(c, "")} for c in sorted(_BUNDLED)]
    code = choose_language(languages)
    run_code(code)


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        p = Path(arg)
        if p.is_file():
            run_file(p)
        else:
            run_code(arg.lower())
    else:
        run_menu()


if __name__ == "__main__":
    main()
