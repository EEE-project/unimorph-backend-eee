# Changelog

## 1.0.5 - 2026-10-20
- `fetch_language_list()` no longer caches a failed fetch. A network error used to end the paging loop, and the
  function then wrote `languages.json` anyway, with the current time and an empty list (or a partial one after a
  failure on a later page). One offline run therefore left the language list empty for the whole 7-day cache time,
  even when the network was back. It now returns `[]` on any network failure, as its docstring says, and writes no
  cache file. A cached list that is empty (written by 1.0.4 and earlier) is ignored, so such a cache file heals at once.

## 1.0.4 - 2026-08-14
- `get_slot_templates()` now caches its result per `pos` (module-level
  `_SLOT_CACHE`, matching the existing `_TAGS_CACHE` convention) --
  `get_tags(pos)` was already cached, but the `SlotTemplate` list built from
  it was rebuilt from scratch on every call. The unsupported-`pos` early
  return (`None`) is deliberately not cached, since it's already a cheap
  no-op.

## 1.0.3 - 2026-07-29
- Declare `eee-project` as a real runtime dependency, not dev-only:
  `unimorph_backend_eee` imports from `eee_project` at runtime
  (`_exceptions.py`, `fetch.py`), but `eee-project` was only listed under
  `[dependency-groups] dev`, so a plain `pip install unimorph-backend-eee`
  crashed on import with `ModuleNotFoundError`. Verified fixed against a
  real install.
- Add a manual PyPI Trusted Publishing workflow.

## 1.0.2 - 2026-07-29
- Add `LICENSE` (Apache-2.0), author, and project URLs to `pyproject.toml`.

## 1.0.1 - 2026-07-29
- Add `readme` field to `pyproject.toml` so PyPI shows the project
  description.

## 1.0.0 - 2026-07-29
- First PyPI release: switch the `eee-project` git dependency to a PyPI
  version constraint, add PyPI install instructions to the README.

## 0.7.0 - 2026-07-26
- Disambiguate `ell.tsv`'s imperative aspect via cross-reference: each
  ambiguous `IMP` row's surface form is checked against the same lemma's
  own already-tagged `IPFV`/`PFV` rows (imperative singular frequently
  coincides with 3rd-singular past). Resolves 1,923 of 3,748 bare rows
  (~51%, ~1,080/1,106 lemmas) via exact match only, no guessing -- purely
  additive, existing rows untouched. `ud_to_unimorph_tag()`'s `Imp` branch
  now accepts an explicit `Aspect` instead of discarding it, mirroring the
  `Sub` branch's own pattern. Plural imperatives mostly don't coincide with
  another cell and remain unresolved.
- Extract a shared `_aspect_token()` helper (backed by a new `ASPECT_MAP`
  in `tags.py`) for the `Imp`/`Sub` mood branches in `ud_to_unimorph_tag()`,
  which each had their own 4-way UD-Aspect-to-UniMorph-token mapping
  differing only in what an absent `Aspect` means for that mood.
- Add prod/dev/community links to the README; remove its 2-entry `##
  Status` changelog stub (superseded by this file).
- Not tagged in git: `pyproject.toml`'s own `version` field reached 0.7.0
  at this point in history, but no corresponding `v0.7.0` git tag was ever
  created.

## 0.6.0 - 2026-07-25
- Add `analyze()`, reverse lookup from a surface form to candidate
  analyses -- inverts the same `(lemma, tag) -> forms` index `inflect()`
  already reads (`_load_reverse_index`), reusing its existing form-cleaning
  (particle stripping, comma-variant splitting, sentinel filtering) rather
  than re-parsing the raw TSV. Converts each raw UniMorph tag to UD FEATS
  via `reverse.py`'s `tag_to_ud()`, a general tag-string parser that
  already existed and was tested (`test_extract_tags.py`) but had never
  been wired into anything. Covers verbs too, unlike
  `get_slot_templates()`'s TSV table (no `verb-tags.tsv` exists). Requires
  a language bound at construction (`UniMorphBackend("el")`), matching
  `list_lemmas()`'s existing resolution requirement. No `eee-project`
  changes needed -- `analyze_traced()`/`analyze()` there already dispatch
  generically via `getattr(b, "analyze", None)`.
- Not tagged in git (same situation as 0.7.0 above).

## 0.5.0 - 2026-07-20
- Add `gender.py`: `infer_noun_gender()`/`gender_from_ending()` for grc and
  ell. UniMorph tags never carry noun gender (a fixed lexical property, not
  inflectional) -- `infer_noun_gender()` reads the article off the bundled
  TSV's raw `N;NOM;SG` form when present (grc only; ell's data has no
  articles), falling back to `gender_from_ending()`'s suffix heuristic for
  both languages. The suffix heuristic runs a small accent-sensitive pass
  first (e.g. paroxytone -ύτης abstract nouns like βαρύτης vs. oxytone -ής
  agent nouns like θεραπευτής), then a fully accent-blind pass over plain
  declension-class endings. Validated against grc's ~1,746 article-bearing
  nouns: 97.4% accuracy on the 74% where a guess is made; the rest
  correctly return `None` rather than guess wrong.

## 0.4.3 - 2026-07-11
- Add period/coverage notes for `grc.tsv` and `ell.tsv` to the README
  (grc's Koine/NT skew vs. Classical/Homeric gaps; ell = Demotic) and
  document four previously-undocumented `ell.tsv` limitations: imperative
  aspect tagging, perfect-cells-as-verbal-adjective, the aorist 3pl -αν
  variant, and the particle-prefix stripping mechanism. Content moved here
  from `eee-project`'s `docs/backends.md`, now split across each backend's
  own README. No functional change.
- Not tagged in git (same situation as 0.7.0 above).

## 0.4.2 - 2026-06-14
- Dedupe tests: merge three structurally-identical alias tests
  (`test_alias_{ru_and_rus,la_and_lat,el_and_ell}_same_slot`) into one
  `test_alias_same_slot`, parametrized over `(short_code, long_code)`; fold
  a duplicate token-order assertion in `test_tag_order_verb` into
  `test_verb_pres_act_1sg`.

## 0.4.1 - 2026-06-14
- Derive `get_slot_templates()` from the bundled TSV directly instead of a
  hand-maintained table; update docs and tests to match.
- Add the `reverse` module (`CASE_MAP_INV` etc. and `tag_to_ud()`), shared
  by tooling and importable by third parties; add `scripts/extract_tags.py`
  (extracts unique UniMorph tags from any language TSV and writes a
  starter `*-tags.tsv` with UD columns reverse-mapped); give
  `scripts/verify_identity.py` CLI args for language codes, importing the
  inverse maps from the library instead of rebuilding them inline. Add
  `Dual` -> `DU` to `NUMBER_MAP` (previously only patched post-hoc in
  `reverse.py` and hardcoded in `extract_tags.py`). Remove
  `tools/unimorph_slot_editor.py`, superseded by `extract_tags.py`.

## 0.4.0 - 2026-06-06
- Add slot templates, a slot editor, a fetch API, 6 bundled languages, and
  a pip-compatible `eee` dependency.
- Add a UniMorph schema gaps doc and named-lexicon support.
- Two git tags exist for this version's history: `v0.4.0` (the initial
  commit above, 2026-06-06) and `v0.3.0` (a follow-up commit six days
  later, 2026-06-12, adding the schema-gaps doc and named-lexicon support
  above) -- despite the lower tag name, `pyproject.toml` already read
  `0.4.0` at the `v0.3.0` tag too, so both commits are folded into this
  single entry; no `0.3.0` package was ever actually shipped. The tag
  naming itself predates this changelog and isn't resolved here.

## 0.1.0 - 2026-05-28
- Initial release.
