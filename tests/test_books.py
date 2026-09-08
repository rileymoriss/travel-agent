"""Unit tests for the quintessential-books feature.

These tests exercise the JSON-parsing/validation logic in
`sources.llm`, the cover-lookup logic in `sources.covers`, and the
orchestration logic in `core.get_quintessential_books` — all without
making real network or LLM API calls.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from travel_agent import core
from travel_agent.preferences import BookPreferences, FoodPreferences, Preferences
from travel_agent.sources import covers as covers_source
from travel_agent.sources import llm as llm_source
from travel_agent.sources.llm import LLMLookupError


def _empty_preferences():
    return Preferences(food=FoodPreferences(), books=BookPreferences())


BOOK_KEYS = ["title", "author", "description"]


# ---------------------------------------------------------------------------
# sources.llm: JSON parsing / validation (shared _parse_json_array, book keys)
# ---------------------------------------------------------------------------


def test_parse_book_items_valid_json():
    raw = (
        '[{"title": "Dubliners", "author": "James Joyce", '
        '"description": "A short story collection set in Dublin."}]'
    )
    items = llm_source._parse_json_array(raw, required_string_keys=BOOK_KEYS)
    assert items == [
        {
            "title": "Dubliners",
            "author": "James Joyce",
            "description": "A short story collection set in Dublin.",
        }
    ]


def test_parse_book_items_rejects_malformed_json():
    with pytest.raises(LLMLookupError):
        llm_source._parse_json_array("not json at all", required_string_keys=BOOK_KEYS)


def test_parse_book_items_rejects_missing_description_key():
    with pytest.raises(LLMLookupError):
        llm_source._parse_json_array(
            '[{"title": "Dubliners", "author": "James Joyce"}]',
            required_string_keys=BOOK_KEYS,
        )


def _make_fake_message(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason
    )


@patch("travel_agent.sources.llm.anthropic.Anthropic")
def test_generate_book_recommendations_missing_api_key_raises(mock_anthropic_cls, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMLookupError):
        llm_source.generate_book_recommendations("Dublin")
    mock_anthropic_cls.assert_not_called()


@patch("travel_agent.sources.llm.anthropic.Anthropic")
def test_generate_book_recommendations_success(mock_anthropic_cls, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_fake_message(
        '[{"title": "Ulysses", "author": "James Joyce", '
        '"description": "A modernist novel set over one day in Dublin."}]'
    )
    mock_anthropic_cls.return_value = mock_client

    result = llm_source.generate_book_recommendations("Dublin")

    assert result == [
        {
            "title": "Ulysses",
            "author": "James Joyce",
            "description": "A modernist novel set over one day in Dublin.",
        }
    ]
    mock_client.messages.create.assert_called_once()


@patch("travel_agent.sources.llm.anthropic.Anthropic")
def test_generate_book_recommendations_truncated_response_raises_clear_error(
    mock_anthropic_cls, monkeypatch
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_fake_message(
        '[{"title": "Ulysses", "author": "James Joyce", "description": "Unterm',
        stop_reason="max_tokens",
    )
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(LLMLookupError, match="truncated"):
        llm_source.generate_book_recommendations("Dublin")


@patch("travel_agent.sources.llm.anthropic.Anthropic")
def test_generate_book_recommendations_includes_preferences_in_prompt(
    mock_anthropic_cls, monkeypatch
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_fake_message("[]")
    mock_anthropic_cls.return_value = mock_client

    prefs = Preferences(
        food=FoodPreferences(),
        books=BookPreferences(favorite_genres=["mystery"], favorite_authors=["Agatha Christie"]),
    )
    llm_source.generate_book_recommendations("Dublin", preferences=prefs)

    sent_prompt = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "mystery" in sent_prompt
    assert "Agatha Christie" in sent_prompt


# ---------------------------------------------------------------------------
# sources.covers: successful lookup / no-match / network error
# ---------------------------------------------------------------------------


def _make_response(status_code=200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    return response


@patch("travel_agent.sources.covers.requests.get")
def test_fetch_book_cover_success(mock_get):
    mock_get.return_value = _make_response(
        200, {"docs": [{"title": "Dubliners", "cover_i": 8216412}]}
    )
    result = covers_source.fetch_book_cover("Dubliners", "James Joyce")
    assert result == "https://covers.openlibrary.org/b/id/8216412-M.jpg"


@patch("travel_agent.sources.covers.requests.get")
def test_fetch_book_cover_returns_none_when_no_docs(mock_get):
    mock_get.return_value = _make_response(200, {"docs": []})
    result = covers_source.fetch_book_cover("Zzzznotarealbook", "Nobody")
    assert result is None


@patch("travel_agent.sources.covers.requests.get")
def test_fetch_book_cover_returns_none_when_no_cover_id(mock_get):
    mock_get.return_value = _make_response(200, {"docs": [{"title": "Dubliners"}]})
    result = covers_source.fetch_book_cover("Dubliners", "James Joyce")
    assert result is None


@patch("travel_agent.sources.covers.requests.get")
def test_fetch_book_cover_network_error_returns_none(mock_get):
    mock_get.side_effect = requests.ConnectionError("boom")
    result = covers_source.fetch_book_cover("Dubliners", "James Joyce")
    assert result is None


# ---------------------------------------------------------------------------
# core.get_quintessential_books: orchestration (truncation, enrichment, cache)
# ---------------------------------------------------------------------------


@patch("travel_agent.core.cache_module.set_cached")
@patch("travel_agent.core.cache_module.get_cached", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.covers_source.fetch_book_cover")
@patch("travel_agent.core.llm_source.generate_book_recommendations")
def test_get_quintessential_books_truncates_to_five(
    mock_generate, mock_fetch_cover, mock_load_prefs, mock_get_cached, mock_set_cached
):
    mock_generate.return_value = [
        {"title": f"Book{i}", "author": f"Author{i}", "description": f"Desc{i}"}
        for i in range(8)
    ]
    mock_fetch_cover.return_value = "https://example.com/cover.jpg"

    result = core.get_quintessential_books("Dublin")

    assert len(result) == core.MAX_QUINTESSENTIAL_BOOKS
    assert [item.title for item in result] == [f"Book{i}" for i in range(5)]


@patch("travel_agent.core.cache_module.set_cached")
@patch("travel_agent.core.cache_module.get_cached", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.covers_source.fetch_book_cover")
@patch("travel_agent.core.llm_source.generate_book_recommendations")
def test_get_quintessential_books_missing_cover_is_none(
    mock_generate, mock_fetch_cover, mock_load_prefs, mock_get_cached, mock_set_cached
):
    mock_generate.return_value = [
        {"title": "Dubliners", "author": "James Joyce", "description": "Short stories."}
    ]
    mock_fetch_cover.return_value = None

    result = core.get_quintessential_books("Dublin")

    assert len(result) == 1
    assert result[0].title == "Dubliners"
    assert result[0].author == "James Joyce"
    assert result[0].description == "Short stories."
    assert result[0].cover_url is None


@patch("travel_agent.core.cache_module.get_cached", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.llm_source.generate_book_recommendations")
def test_get_quintessential_books_propagates_llm_error(
    mock_generate, mock_load_prefs, mock_get_cached
):
    mock_generate.side_effect = LLMLookupError("no key")
    with pytest.raises(LLMLookupError):
        core.get_quintessential_books("Dublin")


@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.llm_source.generate_book_recommendations")
def test_get_quintessential_books_uses_cache_by_default(mock_generate, mock_load_prefs):
    cached_payload = [
        {
            "title": "Dubliners",
            "author": "James Joyce",
            "description": "Short stories.",
            "cover_url": None,
        }
    ]
    with patch("travel_agent.core.cache_module.get_cached", return_value=cached_payload):
        result = core.get_quintessential_books("Dublin")

    assert len(result) == 1
    assert result[0].title == "Dubliners"
    mock_generate.assert_not_called()


@patch("travel_agent.core.cache_module.set_cached")
@patch("travel_agent.core.covers_source.fetch_book_cover", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.llm_source.generate_book_recommendations")
def test_get_quintessential_books_ignore_cache_skips_read(
    mock_generate, mock_load_prefs, mock_fetch_cover, mock_set_cached
):
    mock_generate.return_value = [
        {"title": "Ulysses", "author": "James Joyce", "description": "A novel."}
    ]
    cached_payload = [
        {
            "title": "Dubliners",
            "author": "James Joyce",
            "description": "Short stories.",
            "cover_url": None,
        }
    ]

    with patch(
        "travel_agent.core.cache_module.get_cached", return_value=cached_payload
    ) as mock_get_cached:
        result = core.get_quintessential_books("Dublin", ignore_cache=True)

    mock_get_cached.assert_not_called()
    mock_generate.assert_called_once()
    assert result[0].title == "Ulysses"
    mock_set_cached.assert_called_once()
