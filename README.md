# unimorph-backend-eee

[UniMorph](https://unimorph.github.io/) TSV-lookup backend for the
[EEE](https://codeberg.org/EEE-project/eee-project) morphology framework.

Provides `UniMorphBackend`, satisfying the `MorphologyBackend` protocol
defined in the [`eee`](https://codeberg.org/EEE-project/eee-project) package.

Six languages are **bundled** (work offline): Modern Greek, Ancient Greek,
Latin, Russian, Spanish, Turkish. All other
[187 UniMorph languages](https://github.com/unimorph) are fetched from
GitHub on first use and cached locally (`~/.cache/eee/unimorph-backend-eee/`).

Bundled TSVs are from the [UniMorph](https://unimorph.github.io/) project (data derived from Wiktionary).
License: **CC BY-SA 3.0**.


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

Auto-registered as the `unimorph` named backend and as the default backend for `la`, `ru`, `es`,
and `tr` — installing this package makes those four languages available to `eee-project` without
explicit registration. For `el` and `grc`, use `backend="unimorph"` alongside the dedicated
backends ([modern-greek-backend-eee](https://codeberg.org/EEE-project/modern-greek-backend-eee),
[ancient-greek-backend-eee](https://codeberg.org/EEE-project/ancient-greek-backend-eee)).

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
Downloaded TSVs are stored in `~/.cache/eee/unimorph-backend-eee/`.


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


## UD feature mapping — known gaps

`inflect()` accepts UD FEATS dicts and translates them to UniMorph tags. The
translation covers the dimensions that appear in the six bundled TSVs. The
following UniMorph schema dimensions are **not yet mapped** from UD features
and will raise `FeatureNotSupportedError` (or silently produce wrong results):

| Gap | Schema dimension | Detail |
|-----|-----------------|--------|
| **VerbForm** | Finiteness / Part/Inf | `VerbForm=Part` and `VerbForm=Inf` raise `FeatureNotSupportedError`. UniMorph TSVs contain `V;PTCP` and `V;INF` entries but there is no UD→tag path for them. |
| **Voice** | Voice | Silently discarded (`remaining.pop("Voice", None)`) because `ell.tsv` verb tags omit voice. Blocks Active/Passive distinction for any fetched language that encodes it. |
| **Paucal / Trial number** | Number | `NUMBER_MAP` covers `Sing→SG`, `Plur→PL`, `Dual→DU`. Languages with `PAUC` or `TRI` require raw tag strings. |
| **Definiteness** | Definiteness | Not implemented. `tur.tsv` uses `INDF`/`DEF`; ignored by the Turkish profile. |
| **Mood beyond IMP/SBJV** | Mood | `OPT`, `COND`, etc. appear in some TSVs but are unreachable via UD dict. Use raw tag strings. |
| **Non-`ell` verbs** | Tense/Aspect/Person | The profile system has no verb entry for any language except `ell`. Verbs in on-demand fetched languages require raw tag strings. |
| **Animacy beyond Russian ACC** | Animacy | `HUM`/`NHUM` and non-accusative ANIM/INAN are not implemented. Only Russian masculine accusative animacy is handled. |

**Workaround for all gaps:** pass a raw UniMorph tag string as `features` instead
of a dict — this skips all UD mapping and queries the TSV index directly.

```python
backend = UniMorphBackend("jpn")
forms = backend.inflect("歌う", "V;PRS;3;SG", "verb")  # raw tag — no UD mapping
```

See `tags.py` (`CASE_MAP`, `TENSE_ASPECT_MAP`, etc.) and `profiles.py` (`_build_tags`)
for the current mapping implementation. The UniMorph feature schema is documented in
Sylak-Glassman (2016) — see [References](#references).


## Slot templates

`get_slot_templates` returns `SlotTemplate` objects derived from the bundled TSV tag tables
(`noun-tags.tsv`, `adj-tags.tsv`). This works offline with no TOML files or cache required.

```python
backend = UniMorphBackend("grc")
slots = backend.get_slot_templates("grc", "noun")  # → list[SlotTemplate]
# slot.tag e.g. "N;NOM;SG", slot.tag_type == "ud"
```

Returns `None` for POS without a bundled tag table (currently verb).

For non-bundled languages or custom slot definitions, use `save_slot_template` /
`load_slot_template` from `unimorph_backend_eee.fetch` to store TOML templates
in `~/.cache/eee/unimorph-backend-eee/`.

```python
from eee_project import SlotTemplate
from unimorph_backend_eee.fetch import save_slot_template, load_slot_template

slots = [
    SlotTemplate(tag_type="unimorph", label="Hab. Pres. 3sg Direct",   tag="V;HAB;PRS;3;SG;DIR"),
    SlotTemplate(tag_type="unimorph", label="Hab. Pres. 3sg Indirect",  tag="V;HAB;PRS;3;SG;IND"),
]
save_slot_template("ail", "verb", "en", slots)
slots = load_slot_template("ail", "verb", "en")  # → list[SlotTemplate] or None
```


## Tools

| Tool | Description |
|------|-------------|
| `scripts/browse.py` | CLI: browse any UniMorph language (pick lemma, see all forms) |
| `scripts/verify_identity.py` | CLI: verify `_build_tags()` round-trips for bundled TSVs |
| `scripts/extract_tags.py` | CLI: extract unique tags from any language TSV and write a starter `*-tags.tsv` |

### extract_tags.py

Reverse-maps UniMorph tokens to UD features, producing a TSV ready to bundle as a new
language's tag table. Output goes to stdout; redirect to a file:

```bash
uv run python scripts/extract_tags.py la noun > noun-tags-lat.tsv
uv run python scripts/extract_tags.py jpn verb   # fetches from GitHub
uv run python scripts/extract_tags.py file.tsv adj
```

The resulting TSV uses the same schema as the bundled `noun-tags.tsv` / `adj-tags.tsv`
(`tag` + UD feature columns). Edit it to prune unwanted slots, then drop it into
`src/unimorph_backend_eee/data/` and register the POS in `_POS_TSV`.

### verify_identity.py

Checks that `_build_tags()` round-trips correctly for every unique N/ADJ tag in a
bundled TSV. By default, verifies all six bundled languages; pass language codes to
restrict the check:

```bash
uv run python scripts/verify_identity.py              # all bundled languages
uv run python scripts/verify_identity.py rus lat      # Russian and Latin only
```

**Adding a new language:** extend `PROFILE_MAP` in `verify_identity.py` with entries for
the new language's POS (e.g. `("tur2", "N"): "standard_nominal"`), and if the tag
ordering differs from existing profiles, add a branch to `parse_features()`. Then pass
the new language code on the command line to verify it.

### reverse module

The UniMorph→UD reverse maps and `tag_to_ud()` parser live in the installable package
and can be imported directly by other programs:

```python
from unimorph_backend_eee.reverse import tag_to_ud, CASE_MAP_INV, NUMBER_MAP_INV

feats = tag_to_ud("N;GEN;PL")          # {"Case": "Gen", "Number": "Plur"}
feats = tag_to_ud("V;1;SG;IPFV;PRS")  # {"VerbForm": "Fin", "Person": "1", ...}
```

`tag_to_ud` handles N, ADJ, and V tags. Unknown tokens (compound gender, language
extensions) are silently ignored. Returns `{}` for unrecognised POS.


## Development

```bash
uv sync --dev
uv run pytest
```


## Status

v0.4.2


## References

- Kirov, C., Cotterell, R., Sylak-Glassman, J., Walther, G., Vylomova, E., Xia, P., Faruqui, M., Mielke, S., McCarthy, A., Kübler, S., Yarowsky, D., Eisner, J., & Hulden, M. (2018). **UniMorph 2.0: Universal Morphology**. In *Proceedings of the 11th Language Resources and Evaluation Conference (LREC)*. https://arxiv.org/abs/1810.11101

- Sylak-Glassman, J. (2016). **The Composition and Use of the Universal Morphological Feature Schema (UniMorph Schema)**. Technical Report. Johns Hopkins University. https://unimorph.github.io/doc/unimorph-schema.pdf
