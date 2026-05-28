# unimorph-backend-eee

[UniMorph](https://unimorph.github.io/) TSV-lookup backend for the
Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools.

Provides `UniMorphBackend`, satisfying the `MorphologyBackend` protocol
defined in the [`eee`](https://codeberg.org/EEE-project/eee) package.

Covers Modern Greek (`el`, `ell.tsv`) and Ancient Greek (`grc`, `grc.tsv`)
via static lookup tables derived from Wiktionary. License: **CC BY-SA 3.0**.


## Installation

```bash
pip install "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git"
```


## Usage

```python
from unimorph_backend_eee import UniMorphBackend

# Instantiate per language (required for list_lemmas())
el = UniMorphBackend("el")
grc = UniMorphBackend("grc")

# Modern Greek noun
forms = el.inflect("γυναίκα", {"Case": "Gen", "Number": "Plur"}, "noun")
# {"γυναικών"}

# Ancient Greek noun
forms = grc.inflect("βοηθός", {"Case": "Gen", "Number": "Sing"}, "noun")
# {"βοηθοῦ"}

# List available lemmas
nouns = el.list_lemmas("noun")   # ~8,351 entries
```

Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).

Auto-registered as `el` and `grc` entry points — installing this package
makes both languages available to `eee` without explicit registration.


## Coverage

| Language | TSV | POS | Lemmas |
|----------|-----|-----|-------:|
| Modern Greek (`el`) | `ell.tsv` | Noun | 8,351 |
| Modern Greek (`el`) | `ell.tsv` | Adjective | 2,492 |
| Modern Greek (`el`) | `ell.tsv` | Verb | 1,094 |
| Ancient Greek (`grc`) | `grc.tsv` | Noun | 2,224 |
| Ancient Greek (`grc`) | `grc.tsv` | Adjective | 207 |
| Ancient Greek (`grc`) | `grc.tsv` | Verb | 0 |

**Limitations**

- Ancient Greek verb data is absent from `grc.tsv` — use
  [ancient-greek-backend-eee](https://codeberg.org/EEE-project/ancient-greek-backend-eee)
  for verbs.
- Noun gender is omitted from tags in both TSVs — passing `Gender` returns an
  empty set; `inflect()` always returns bare forms.
- Modern Greek verb tags use UniMorph aspect codes (`IPFV`/`PFV`) and do not
  map to all eee UD features (e.g. conditional, pluperfect cells are empty).
- The `ell.tsv` vocabulary is corpus-derived — common words such as λόγος,
  άνθρωπος may be absent.


## Development

```bash
uv sync --dev
uv run pytest
```


## Status

v0.1.0
