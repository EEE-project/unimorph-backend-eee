"""Tests for load_slot_template and save_slot_template."""
from __future__ import annotations

import pytest
import tomlkit
from unittest.mock import patch

from eee._slot_template import SlotTemplate
from unimorph_backend_eee.fetch import load_slot_template, save_slot_template

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_UNIMORPH = """\
[[verb.slots]]
tag_type = "unimorph"
label = "Hab. Pres. 3sg Direct"
tag = "V;HAB;PRS;3;SG;DIR"

[[verb.slots]]
tag_type = "unimorph"
label = "Hab. Pres. 3sg Indirect"
tag = "V;HAB;PRS;3;SG;IND"
"""

FIXTURE_UD = """\
[[noun.slots]]
tag_type = "ud"
label = "Nominative Singular"
tag = "Nom;Sing"

[noun.slots.features]
Case = "Nom"
Number = "Sing"
"""

FIXTURE_FALLBACK = """\
[[verb.slots]]
tag_type = "unimorph"
label = "Hab. Pres. 3sg Direct"
tag = "V;HAB;PRS;3;SG;DIR"
"""

FIXTURE_TWO_POS = """\
# file-level comment
[[noun.slots]]
tag_type = "unimorph"
label = "Nom Sg"
tag = "N;NOM;SG"

[[verb.slots]]
tag_type = "unimorph"
label = "Old verb slot"
tag = "V;OLD"
"""

# ---------------------------------------------------------------------------
# load_slot_template tests
# ---------------------------------------------------------------------------

def test_load_returns_none_when_file_absent(tmp_path):
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        result = load_slot_template("verb", "en", "ail")
    assert result is None


def test_load_unimorph_slots(tmp_path):
    (tmp_path / "slots_ail_en.toml").write_text(FIXTURE_UNIMORPH)
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        slots = load_slot_template("verb", "en", "ail")
    assert slots is not None
    assert len(slots) == 2
    assert slots[0].tag_type == "unimorph"
    assert slots[0].label == "Hab. Pres. 3sg Direct"
    assert slots[0].tag == "V;HAB;PRS;3;SG;DIR"
    assert slots[0].features is None


def test_load_ud_slots(tmp_path):
    (tmp_path / "slots_ell_en.toml").write_text(FIXTURE_UD)
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        slots = load_slot_template("noun", "en", "ell")
    assert slots is not None
    assert len(slots) == 1
    assert slots[0].tag_type == "ud"
    assert slots[0].features == {"Case": "Nom", "Number": "Sing"}
    assert slots[0].tag == "Nom;Sing"


def test_load_falls_back_to_en(tmp_path):
    (tmp_path / "slots_ail_en.toml").write_text(FIXTURE_FALLBACK)
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        slots = load_slot_template("verb", "el", "ail")
    assert slots is not None
    assert slots[0].label == "Hab. Pres. 3sg Direct"


def test_no_fallback_when_en_is_primary(tmp_path):
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        result = load_slot_template("verb", "en", "ail")
    assert result is None


def test_load_returns_none_when_pos_absent(tmp_path):
    (tmp_path / "slots_ail_en.toml").write_text(FIXTURE_UNIMORPH)
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        result = load_slot_template("noun", "en", "ail")
    assert result is None


def test_malformed_toml_raises(tmp_path):
    (tmp_path / "slots_ail_en.toml").write_text("[[verb.slots]\nbroken")
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        with pytest.raises(tomlkit.exceptions.ParseError):
            load_slot_template("verb", "en", "ail")


# ---------------------------------------------------------------------------
# save_slot_template tests
# ---------------------------------------------------------------------------

def test_save_creates_file(tmp_path):
    slots = [SlotTemplate(tag_type="unimorph", label="Test slot", tag="V;PRS;3;SG")]
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        save_slot_template("verb", "en", "ail", slots)
    assert (tmp_path / "slots_ail_en.toml").exists()


def test_save_preserves_other_pos_and_comments(tmp_path):
    (tmp_path / "slots_ail_en.toml").write_text(FIXTURE_TWO_POS)
    new_slots = [SlotTemplate(tag_type="unimorph", label="New verb slot", tag="V;NEW")]
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        save_slot_template("verb", "en", "ail", new_slots)
        content = (tmp_path / "slots_ail_en.toml").read_text()
    assert "file-level comment" in content
    assert "Nom Sg" in content
    assert "Old verb slot" not in content
    assert "New verb slot" in content


def test_round_trip(tmp_path):
    slots = [
        SlotTemplate(tag_type="unimorph", label="Hab. 3sg", tag="V;HAB;3;SG"),
        SlotTemplate(tag_type="unimorph", label="Pfv. 3sg", tag="V;PFV;3;SG"),
    ]
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        save_slot_template("verb", "en", "ail", slots)
        loaded = load_slot_template("verb", "en", "ail")
    assert loaded == slots


def test_round_trip_ud_slots(tmp_path):
    slots = [
        SlotTemplate(
            tag_type="ud",
            label="Nominative Singular",
            tag="Nom;Sing",
            features={"Case": "Nom", "Number": "Sing"},
        )
    ]
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        save_slot_template("noun", "en", "ell", slots)
        loaded = load_slot_template("noun", "en", "ell")
    assert loaded == slots


def test_save_empty_slots_clears_pos_section(tmp_path):
    (tmp_path / "slots_ail_en.toml").write_text(FIXTURE_TWO_POS)
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        save_slot_template("verb", "en", "ail", [])
        loaded = load_slot_template("verb", "en", "ail")
    assert loaded is None
    content = (tmp_path / "slots_ail_en.toml").read_text()
    assert "Nom Sg" in content


def test_load_returns_none_when_slots_empty_in_file(tmp_path):
    (tmp_path / "slots_ail_en.toml").write_text("[verb]\nslots = []\n")
    with patch("unimorph_backend_eee.fetch.CACHE_DIR", tmp_path):
        result = load_slot_template("verb", "en", "ail")
    assert result is None
