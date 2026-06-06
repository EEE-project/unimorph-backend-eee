"""Fetch and register UniMorph TSVs from GitHub.

Public API:
  fetch_language_list(verbose)  — [{code, name}] from cache or GitHub
  fetch_tsv(code, verbose)      — download and cache a language TSV
  register_language(code, verbose) — ensure code is ready; return (index, pos_names)
  list_cached_terms(lang)       — terms-language codes cached for a language

CACHE_DIR, LANG_LIST_TTL_DAYS, ISO639_FALLBACK are exported for inspection.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import tomlkit
from eee_project._slot_template import SlotTemplate
from datetime import datetime, timezone
from pathlib import Path

from unimorph_backend_eee.backend import _INDEX_CACHE, _SUPPORTED_POS, _load_index
from unimorph_backend_eee.profiles import detect_profile, load_profiles
from unimorph_backend_eee.tags import LANGUAGE_CODE_MAP

CACHE_DIR = Path.home() / ".cache" / "eee" / "unimorph-backend-eee"
LANG_LIST_TTL_DAYS = 7

# ISO 639-3 display names for UniMorph language codes.
ISO639_FALLBACK: dict[str, str] = {
    "ady": "Adyghe", "afr": "Afrikaans", "aka": "Akan", "amh": "Amharic",
    "ang": "Old English", "ara": "Arabic", "aze": "Azerbaijani",
    "bak": "Bashkir", "bel": "Belarusian", "ben": "Bengali", "bod": "Tibetan",
    "bre": "Breton", "bul": "Bulgarian", "cat": "Catalan", "ces": "Czech",
    "chu": "Church Slavic", "ckb": "Central Kurdish", "cor": "Cornish",
    "crh": "Crimean Tatar", "csb": "Kashubian", "cym": "Welsh",
    "dan": "Danish", "deu": "German", "dsb": "Lower Sorbian",
    "ell": "Modern Greek", "eng": "English", "est": "Estonian",
    "eus": "Basque", "fao": "Faroese", "fas": "Persian", "fin": "Finnish",
    "fra": "French", "fry": "Western Frisian", "fur": "Friulian",
    "gle": "Irish", "glg": "Galician", "grc": "Ancient Greek",
    "gsw": "Alemannic German", "hbs": "Serbo-Croatian", "heb": "Hebrew",
    "hin": "Hindi", "hrv": "Croatian", "hsb": "Upper Sorbian",
    "hun": "Hungarian", "hye": "Armenian", "ind": "Indonesian",
    "isl": "Icelandic", "ita": "Italian", "izh": "Ingrian", "jpn": "Japanese",
    "kal": "Kalaallisut", "kan": "Kannada", "kat": "Georgian",
    "kaz": "Kazakh", "kbd": "Kabardian", "khm": "Khmer", "kjh": "Khakas",
    "klr": "Khaling", "kor": "Korean", "kpv": "Komi-Zyrian",
    "lat": "Latin", "lav": "Latvian", "lit": "Lithuanian", "liv": "Livonian",
    "lld": "Ladin", "mkd": "Macedonian", "mlt": "Maltese", "mon": "Mongolian",
    "msa": "Malay", "mwf": "Murrinh-Patha", "nld": "Dutch",
    "nno": "Norwegian Nynorsk", "nob": "Norwegian Bokmål",
    "oci": "Occitan", "orv": "Old Russian", "otk": "Old Turkish",
    "pol": "Polish", "por": "Portuguese", "ron": "Romanian",
    "rus": "Russian", "san": "Sanskrit", "slk": "Slovak",
    "slv": "Slovenian", "spa": "Spanish", "sqi": "Albanian",
    "srp": "Serbian", "swa": "Swahili", "swe": "Swedish",
    "syc": "Classical Syriac", "tat": "Tatar", "tel": "Telugu",
    "tgk": "Tajik", "tgl": "Tagalog", "tur": "Turkish",
    "uig": "Uyghur", "ukr": "Ukrainian", "urd": "Urdu",
    "uzb": "Uzbek", "vec": "Venetian", "vie": "Vietnamese",
    "vot": "Votic", "wol": "Wolof", "xcl": "Classical Armenian",
    "xho": "Xhosa", "yid": "Yiddish", "yor": "Yoruba",
    "zho": "Chinese", "zul": "Zulu",
}

_URL_PATTERNS = [
    "https://raw.githubusercontent.com/unimorph/{code}/master/{code}",
    "https://raw.githubusercontent.com/unimorph/{code}/main/{code}",
    "https://raw.githubusercontent.com/unimorph/{code}/master/{code}.tsv",
    "https://raw.githubusercontent.com/unimorph/{code}/main/{code}.tsv",
]

_POS_TOKEN = {"N": "noun", "ADJ": "adjective", "V": "verb"}


def fetch_language_list(verbose: bool = False) -> list[dict]:
    """Return [{code, name}] for all UniMorph repos, from cache or GitHub API.

    Result is cached in CACHE_DIR/languages.json for LANG_LIST_TTL_DAYS days.
    Returns [] on network failure (caller may fall back to bundled list).
    """
    _lang_list_cache = CACHE_DIR / "languages.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _lang_list_cache.exists():
        try:
            data = json.loads(_lang_list_cache.read_text())
            cached_at = datetime.fromisoformat(data["cached_at"])
            age = (datetime.now(timezone.utc) - cached_at).days
            if age < LANG_LIST_TTL_DAYS:
                return data["languages"]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

    if verbose:
        print("Fetching UniMorph language list from GitHub …", end="", flush=True)
    languages = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/unimorph/repos?per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                repos = json.loads(resp.read())
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            if verbose:
                print(f" failed ({e})")
            break
        if not repos:
            break
        for r in repos:
            code = r.get("name", "")
            if not code or code.startswith(".") or len(code) > 3:
                continue
            desc = (r.get("description") or "").strip()
            iso_name = ISO639_FALLBACK.get(code, "")
            if not iso_name and any(w in desc.lower() for w in ("test", "script", "tool", "repo for")):
                continue
            languages.append({"code": code, "name": desc or iso_name})
        page += 1
    languages.sort(key=lambda x: x["code"])
    tmp = _lang_list_cache.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "languages": languages,
    }))
    tmp.replace(_lang_list_cache)
    if verbose:
        print(f" ok ({len(languages)} languages)")
    return languages


def fetch_tsv(code: str, verbose: bool = False) -> Path:
    """Download and cache the UniMorph TSV for language code.

    Returns path to the cached file. Raises FileNotFoundError if not found
    on any of the known URL patterns.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / f"{code}.tsv"
    if cached.exists():
        return cached
    if verbose:
        print(f"  fetching {code} …", end="", flush=True)
    for pattern in _URL_PATTERNS:
        url = pattern.format(code=code)
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = resp.read()
            tmp = cached.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(cached)
            if verbose:
                print(f" ok ({len(data) // 1024} KB)")
            return cached
        except (urllib.error.URLError, OSError):
            pass
    if verbose:
        print(" not found")
    raise FileNotFoundError(
        f"No UniMorph TSV found for '{code}'. "
        "Check https://github.com/unimorph for the exact repo name."
    )


def _parse_tsv(path: Path) -> dict[tuple[str, str], set[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    index: dict[tuple[str, str], set[str]] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        lemma, form, tag = parts
        if lemma.startswith("'") or not form or form == "—":
            continue
        for raw in form.split(","):
            token = raw.strip()
            if " " in token:
                token = token.rsplit(" ", 1)[1]
            if token and token != "—":
                index.setdefault((lemma, tag), set()).add(token)
    return index


def register_language(code: str, verbose: bool = False) -> tuple[dict, list[str]]:
    """Ensure language code is registered and return (index, pos_names).

    pos_names uses UD convention: "noun", "adjective", "verb".
    For bundled languages (ell/grc/lat/rus/spa/tur) loads from package data.
    For all others, downloads the TSV from GitHub (cached in CACHE_DIR).

    Raises:
        FileNotFoundError: TSV not found on GitHub.
        ValueError: TSV is empty/malformed or contains no recognised POS tokens.
    """
    if code in _SUPPORTED_POS:
        return _load_index(code), list(_SUPPORTED_POS[code])

    tsv_path = fetch_tsv(code, verbose=verbose)
    index = _parse_tsv(tsv_path)
    if not index:
        tsv_path.unlink(missing_ok=True)
        raise ValueError("TSV appears empty or malformed. Corrupt cache deleted — retry to re-fetch.")

    pos_tokens = sorted({tag.split(";")[0] for (_, tag) in index} & _POS_TOKEN.keys())
    if not pos_tokens:
        tsv_path.unlink(missing_ok=True)
        raise ValueError("No recognised POS tokens (N / ADJ / V) found. Corrupt cache deleted — retry to re-fetch.")

    profile_name = detect_profile(code, str(tsv_path))
    profiles = load_profiles()
    if profile_name not in profiles.get("profiles", {}):
        raise ValueError(f"detect_profile returned unknown profile '{profile_name}'.")

    lang_cfg = profiles.setdefault("languages", {}).setdefault(code, {})
    pos_cfg = lang_cfg.setdefault("pos", {})
    for pt in pos_tokens:
        pos_cfg[_POS_TOKEN[pt]] = profile_name
    LANGUAGE_CODE_MAP[code] = code
    _INDEX_CACHE[code] = index
    return index, [_POS_TOKEN[pt] for pt in pos_tokens]


def load_slot_template(
    pos: str, terms_lang: str = "en", lang: str = ""
) -> list[SlotTemplate] | None:
    """Load slots for (lang, pos) from slots_{lang}_{terms_lang}.toml in CACHE_DIR.

    Falls back to slots_{lang}_en.toml when terms_lang != "en" and primary absent.
    Returns None if file does not exist or the pos section is absent/empty.
    Raises tomlkit.exceptions.ParseError for malformed TOML (not swallowed).
    """
    path = CACHE_DIR / f"slots_{lang}_{terms_lang}.toml"
    if not path.exists():
        if terms_lang != "en":
            path = CACHE_DIR / f"slots_{lang}_en.toml"
            if not path.exists():
                return None
        else:
            return None

    doc = tomlkit.loads(path.read_text(encoding="utf-8"))
    pos_section = doc.get(pos)
    if pos_section is None:
        return None
    raw_slots = pos_section.get("slots")
    if not raw_slots:
        return None

    result: list[SlotTemplate] = []
    for entry in raw_slots:
        try:
            features: dict[str, str] | None = None
            if "features" in entry:
                features = dict(entry["features"])
            result.append(SlotTemplate(
                label=str(entry["label"]),
                tag_type=str(entry["tag_type"]),
                tag=str(entry["tag"]),
                features=features,
            ))
        except KeyError as exc:
            raise ValueError(f"Slot entry in {path} missing required field {exc}") from exc
    return result if result else None


def save_slot_template(
    pos: str, terms_lang: str, lang: str, slots: list[SlotTemplate]
) -> None:
    """Write or update slots for (lang, pos) in slots_{lang}_{terms_lang}.toml.

    Replaces only the [pos] section; other POS sections and file-level comments
    are preserved. Empty slots list clears the POS section.
    Writes atomically via tmp-then-replace.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"slots_{lang}_{terms_lang}.toml"

    if path.exists():
        doc = tomlkit.loads(path.read_text(encoding="utf-8"))
    else:
        doc = tomlkit.document()

    if not slots:
        if pos in doc:
            del doc[pos]
    else:
        slots_aot = tomlkit.aot()
        for slot in slots:
            t = tomlkit.table()
            t.add("tag_type", slot.tag_type)
            t.add("label", slot.label)
            t.add("tag", slot.tag)
            if slot.features is not None:
                features_tbl = tomlkit.table()
                for k, v in slot.features.items():
                    features_tbl.add(k, v)
                t.add("features", features_tbl)
            slots_aot.append(t)

        pos_tbl = tomlkit.table()
        pos_tbl.add("slots", slots_aot)
        if pos in doc:
            doc[pos] = pos_tbl
        else:
            doc.add(pos, pos_tbl)

    tmp = path.with_suffix(".tmp")
    tmp.write_text(tomlkit.dumps(doc), encoding="utf-8")
    tmp.replace(path)


def list_cached_terms(lang: str) -> list[str]:
    """Return terms-language codes for which a slot template is cached for *lang*.

    Scans CACHE_DIR for files matching slots_{lang}_*.toml and returns the
    codes in sorted order with "en" first, e.g. ["en", "el", "ru"].
    """
    prefix = f"slots_{lang}_"
    codes = [
        f.stem[len(prefix):]
        for f in CACHE_DIR.glob(f"{prefix}*.toml")
        if f.stem[len(prefix):].isalpha()
    ]
    return sorted(codes, key=lambda c: (c != "en", c))
