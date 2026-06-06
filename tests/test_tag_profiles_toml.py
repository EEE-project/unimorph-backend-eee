"""Structural validation tests for tag_profiles.toml.

These tests only use tomllib + importlib.resources — no project code needed.
They validate the TOML file structure independently of the profile interpreter.
"""
import importlib.resources
import tomllib

KNOWN_SLOTS = {"pos", "case", "number", "?gender", "?gender_if_singular", "?degree"}
KNOWN_PROFILE_FLAGS = {"animacy_acc", "masc_fem_combined_fallback"}
KNOWN_LANGUAGE_FLAGS = {
    "noun_strip_gender",
    "adjective_drop_gender_fallback",
    "adjective_masc_fem_combined_fallback",
}
KNOWN_POS_KEYS = {"noun", "adjective"}
EXPECTED_PROFILES = {"standard_nominal", "latin_nominal", "slavic_nominal", "caseless_nominal"}
EXPECTED_LANGUAGES = {"ell", "grc", "lat", "rus", "spa", "tur"}


def _load_toml() -> dict:
    data = importlib.resources.files("unimorph_backend_eee.data").joinpath("tag_profiles.toml")
    return tomllib.loads(data.read_text(encoding="utf-8"))


def test_toml_parses():
    cfg = _load_toml()
    assert isinstance(cfg, dict)


def test_all_profiles_present():
    cfg = _load_toml()
    assert set(cfg["profiles"].keys()) >= EXPECTED_PROFILES


def test_all_languages_present():
    cfg = _load_toml()
    assert set(cfg["languages"].keys()) >= EXPECTED_LANGUAGES


def test_language_profile_references_valid():
    cfg = _load_toml()
    defined = set(cfg["profiles"].keys())
    for lang, lang_cfg in cfg["languages"].items():
        for pos, profile_name in lang_cfg.get("pos", {}).items():
            assert pos in KNOWN_POS_KEYS, (
                f"Language '{lang}' has unknown POS key '{pos}'"
            )
            assert profile_name in defined, (
                f"Language '{lang}' POS '{pos}' references undefined profile '{profile_name}'"
            )


def test_slot_keywords_valid():
    cfg = _load_toml()
    for name, profile in cfg["profiles"].items():
        for slot in profile.get("slots", []):
            assert slot in KNOWN_SLOTS, f"Profile '{name}' has unknown slot '{slot}'"


def test_profiles_have_nonempty_slots():
    cfg = _load_toml()
    for name, profile in cfg["profiles"].items():
        assert profile.get("slots"), f"Profile '{name}' has empty or missing slots list"


def test_profile_flag_names_valid():
    cfg = _load_toml()
    for name, profile in cfg["profiles"].items():
        for flag in profile.get("flags", {}).keys():
            assert flag in KNOWN_PROFILE_FLAGS, (
                f"Profile '{name}' has unknown flag '{flag}'"
            )


def test_language_flag_names_valid():
    cfg = _load_toml()
    for lang, lang_cfg in cfg["languages"].items():
        for flag in lang_cfg.get("flags", {}).keys():
            assert flag in KNOWN_LANGUAGE_FLAGS, (
                f"Language '{lang}' has unknown flag '{flag}'"
            )


def test_tur_has_no_adjective():
    # tur backend only supports noun; no adjective entry should exist
    cfg = _load_toml()
    assert "adjective" not in cfg["languages"]["tur"].get("pos", {})
