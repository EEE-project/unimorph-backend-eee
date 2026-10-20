"""Tests for fetch_language_list: a failed fetch is never cached."""
from __future__ import annotations

import json
import re
import urllib.error
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from unimorph_backend_eee import fetch

BEL = [{"code": "bel", "name": "Belarusian"}]


class _Resp:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


@pytest.fixture
def github(monkeypatch, tmp_path):
    """Fake GitHub org listing: `pages` maps a page number to its repos, `fail_on` holds the pages that raise, `calls` the pages asked for."""
    state = SimpleNamespace(pages={1: [{"name": "bel", "description": "Belarusian"}], 2: []}, fail_on=set(), calls=[], cache_file=tmp_path / "languages.json")

    def fake_urlopen(req, timeout=None):
        page = int(re.search(r"[?&]page=(\d+)", req.full_url).group(1))
        state.calls.append(page)
        if page in state.fail_on:
            raise urllib.error.URLError("offline")
        return _Resp(state.pages[page])

    monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    return state


def test_failed_fetch_returns_empty_and_writes_no_cache(github):
    github.fail_on = {1}
    assert fetch.fetch_language_list() == []
    assert not github.cache_file.exists()


def test_failure_on_a_later_page_returns_empty_and_writes_no_cache(github):
    github.fail_on = {2}
    assert fetch.fetch_language_list() == []
    assert not github.cache_file.exists()


def test_next_call_after_a_failure_fetches_again(github):
    github.fail_on = {1}
    assert fetch.fetch_language_list() == []
    github.fail_on = set()
    assert fetch.fetch_language_list() == BEL


def test_success_is_cached_and_reused(github):
    assert fetch.fetch_language_list() == BEL
    github.calls.clear()
    assert fetch.fetch_language_list() == BEL
    assert github.calls == []


def test_cached_empty_list_is_ignored(github):
    github.cache_file.write_text(json.dumps({"cached_at": datetime.now(timezone.utc).isoformat(), "languages": []}))
    assert fetch.fetch_language_list() == BEL
