# unimorph-backend-eee

[UniMorph](https://unimorph.github.io/) TSV-lookup backend for the
[EEE](https://codeberg.org/EEE-project/eee) morphology framework.

Provides `UniMorphBackend`, satisfying the `MorphologyBackend` protocol
defined in the [`eee`](https://codeberg.org/EEE-project/eee) package.

Six languages are **bundled** (work offline): Modern Greek, Ancient Greek,
Latin, Russian, Spanish, Turkish. All other
[187 UniMorph languages](https://github.com/unimorph) are fetched from
GitHub on first use and cached locally (`~/.cache/unimorph/`).

Bundled TSVs are derived from Wiktionary. License: **CC BY-SA 3.0**.


## Installation

```bash
pip install "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git"
```


## Usage

```python
from unimorph_backend_eee import UniMorphBackend

# Bundled languages — no network required
el  = UniMorphBackend("el")
grc = UniMorphBackend("grc")
lat = UniMorphBackend("la")
rus = UniMorphBackend("ru")

forms = el.inflect("γυναίκα", {"Case": "Gen", "Number": "Plur"}, "noun")  # {"γυναικών"}
forms = lat.inflect("puella", {"Case": "Gen", "Number": "Plur"}, "noun")  # {"puellarum"}
```

Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).

Auto-registered as `el`, `grc`, `la`, `ru`, `es`, `tr` entry points — installing
this package makes all six languages available to `eee` without explicit registration.

### Fetching additional languages

```python
from unimorph_backend_eee import fetch_language_list, fetch_tsv, register_language

# List all 187 UniMorph languages (cached 7 days)
langs = fetch_language_list()   # [{"code": "bel", "name": "Belarusian"}, ...]

# Download and register any language on demand
index, pos_names = register_language("jpn")   # fetches jpn TSV from GitHub
backend = UniMorphBackend("jpn")
forms = backend.inflect("歌う", {"Tag": "PRS;IPFV"}, "verb", language="jpn")
```

`register_language()` is idempotent — subsequent calls return the cached index.
Downloaded TSVs are stored in `~/.cache/unimorph/`.


## Bundled coverage

| Language | Code | TSV | POS | Lemmas |
|----------|------|-----|-----|-------:|
| Modern Greek | `el` | `ell.tsv` | Noun | 8,351 |
| Modern Greek | `el` | `ell.tsv` | Adjective | 2,492 |
| Modern Greek | `el` | `ell.tsv` | Verb | 1,094 |
| Ancient Greek | `grc` | `grc.tsv` | Noun | 2,224 |
| Ancient Greek | `grc` | `grc.tsv` | Adjective | 207 |
| Latin | `la` | `lat.tsv` | Noun | 3,584 |
| Latin | `la` | `lat.tsv` | Adjective | 1,349 |
| Russian | `ru` | `rus.tsv` | Noun | 4,490 |
| Russian | `ru` | `rus.tsv` | Adjective | 3,234 |
| Spanish | `es` | `spa.tsv` | Noun | 2,631 |
| Spanish | `es` | `spa.tsv` | Adjective | 2,186 |
| Turkish | `tr` | `tur.tsv` | Noun | 1,002 |

**Limitations**

- Ancient Greek verb data is absent from `grc.tsv` — use
  [ancient-greek-backend-eee](https://codeberg.org/EEE-project/ancient-greek-backend-eee)
  for verbs.
- Noun gender is omitted from tags in `ell.tsv` and `grc.tsv`.
- Modern Greek verb tags use UniMorph aspect codes (`IPFV`/`PFV`) and do not
  map to all UD features (conditional, pluperfect are empty).
- The `ell.tsv` vocabulary is corpus-derived — common words such as λόγος,
  άνθρωπος may be absent.
- Non-bundled languages use raw UniMorph feature strings rather than UD feature
  dicts; use `register_language()` + direct index lookup for them.


## Slot templates

TOML-based slot templates let you define structured inflection tables for any language
and terms language. Templates are stored in `~/.cache/unimorph/slots_{lang}_{terms_lang}.toml`.

```python
from eee import SlotTemplate
from unimorph_backend_eee.fetch import save_slot_template, load_slot_template

# Save a template (e.g. after using the slot editor)
slots = [
    SlotTemplate(tag_type="unimorph", label="Hab. Pres. 3sg Direct",   tag="V;HAB;PRS;3;SG;DIR"),
    SlotTemplate(tag_type="unimorph", label="Hab. Pres. 3sg Indirect",  tag="V;HAB;PRS;3;SG;IND"),
]
save_slot_template("ail", "verb", "en", slots)   # → ~/.cache/unimorph/slots_ail_en.toml

# Load it back
slots = load_slot_template("ail", "verb", "en")  # → list[SlotTemplate] or None

# Via the backend (used by unimorph_notebook.py)
backend = UniMorphBackend("ail")
slots = backend.get_slot_templates("ail", "verb", terms_lang="en")
```

`unimorph_notebook.py` uses a four-step fallback chain when displaying inflection tables:
bundled UD slots → TOML template (requested language) → TOML template (English fallback) → raw tag dump.

### Slot editor

`tools/unimorph_slot_editor.py` is a Marimo notebook for linguists to build templates interactively:

```bash
uv run marimo edit tools/unimorph_slot_editor.py
```

Browse corpus tags with sample forms, assign labels (with auto-fill in 7 built-in languages
or any cached language), and save TOML templates for any of the 187 UniMorph languages.
Use the download section to fetch community-contributed templates by URL.


## Tools

| Tool | Description |
|------|-------------|
| `tools/unimorph_slot_editor.py` | Marimo notebook: browse tags, assign labels, save TOML slot templates |
| `scripts/browse.py` | CLI: browse any UniMorph language (pick lemma, see all forms) |
| `scripts/verify_identity.py` | CLI: verify `_build_tags()` round-trips for all bundled TSVs |

The interactive inflection browser ([`eee/tools/unimorph_notebook.py`](https://codeberg.org/EEE-project/eee)) consumes templates saved by the slot editor.


## Development

```bash
uv sync --dev
uv run pytest
```


## Status

v0.4.0
