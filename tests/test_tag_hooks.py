"""Tests for the hook system in profiles.py."""
import pytest
from unittest.mock import patch

from unimorph_backend_eee.profiles import (
    register_tag_hook,
    _clear_all_hooks,
    _build_tags,
)
from unimorph_backend_eee.backend import UniMorphBackend
from unimorph_backend_eee._exceptions import (
    UnsupportedLanguageError,
    PosNotSupportedError,
)


@pytest.fixture(autouse=True)
def clean_hooks():
    _clear_all_hooks()
    yield
    _clear_all_hooks()


def test_registered_hook_is_called():
    called = []
    register_tag_hook("ell", "noun", lambda f: called.append(f) or ["N;NOM;SG"])
    _build_tags("ell", "noun", {"Case": "Nom", "Number": "Sing"})
    assert len(called) == 1


def test_hook_return_value_used_as_tag_list():
    register_tag_hook("ell", "noun", lambda f: ["CUSTOM;TAG"])
    result = _build_tags("ell", "noun", {"Case": "Nom", "Number": "Sing"})
    assert result == ["CUSTOM;TAG"]


def test_hook_not_called_for_different_language():
    hook_called = []
    register_tag_hook("ell", "noun", lambda f: hook_called.append(1) or ["HOOK"])
    # grc/noun should go to profile, not hook
    result = _build_tags("grc", "noun", {"Case": "Nom", "Number": "Sing"})
    assert hook_called == []
    assert result == ["N;NOM;SG"]


def test_hook_not_called_for_different_pos():
    hook_called = []
    register_tag_hook("ell", "noun", lambda f: hook_called.append(1) or ["HOOK"])
    # ell/adjective should go to profile, not hook
    result = _build_tags("ell", "adjective", {"Case": "Nom", "Number": "Sing"})
    assert hook_called == []
    assert result == ["ADJ;NOM;SG"]


@pytest.mark.parametrize("short_code,long_code", [("ru", "rus"), ("la", "lat"), ("el", "ell")])
def test_alias_same_slot(short_code, long_code):
    first = lambda f: ["FIRST"]
    second = lambda f: ["SECOND"]
    register_tag_hook(short_code, "noun", first)
    register_tag_hook(long_code, "noun", second)
    # second registration should win (same slot)
    result = _build_tags(long_code, "noun", {"Case": "Nom", "Number": "Sing"})
    assert result == ["SECOND"]


def test_verb_hook_dispatched():
    register_tag_hook("ell", "verb", lambda f: ["VERB;HOOK"])
    result = _build_tags("ell", "verb", {})
    assert result == ["VERB;HOOK"]


def test_unknown_language_raises():
    with pytest.raises(UnsupportedLanguageError):
        register_tag_hook("xyz", "noun", lambda f: [])


def test_unknown_pos_raises():
    with pytest.raises(PosNotSupportedError):
        register_tag_hook("ell", "verb_bad", lambda f: [])


def test_hook_registered_after_cache_loaded():
    # Load profiles first
    from unimorph_backend_eee.profiles import load_profiles
    load_profiles()
    # Register hook after cache is warm
    register_tag_hook("ell", "noun", lambda f: ["LATE;HOOK"])
    result = _build_tags("ell", "noun", {"Case": "Nom", "Number": "Sing"})
    assert result == ["LATE;HOOK"]


def test_clear_all_hooks_restores_profile_dispatch():
    register_tag_hook("ell", "noun", lambda f: ["CUSTOM;TAG"])
    assert _build_tags("ell", "noun", {"Case": "Nom", "Number": "Sing"}) == ["CUSTOM;TAG"]
    _clear_all_hooks()
    assert _build_tags("ell", "noun", {"Case": "Nom", "Number": "Sing"}) == ["N;NOM;SG"]


def test_hook_result_passes_through_inflect():
    custom_tag = "N;NOM;SG"
    register_tag_hook("ell", "noun", lambda f: [custom_tag])
    with patch("unimorph_backend_eee.backend._lookup", return_value={"αγάπη"}):
        backend = UniMorphBackend()
        result = backend.inflect("αγάπη", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert "αγάπη" in result
