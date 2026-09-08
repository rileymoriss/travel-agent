"""Unit tests for the quintessential-foods feature.

These tests exercise the JSON-parsing/validation logic in
`sources.llm`, the image-lookup fallback logic in `sources.images`, and
the orchestration logic in `core.get_quintessential_foods` — all without
making real network or LLM API calls.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from travel_agent import core
from travel_agent.preferences import BookPreferences, FoodPreferences, Preferences
from travel_agent.sources import images as images_source
from travel_agent.sources import llm as llm_source
from travel_agent.sources.llm import LLMLookupError


def _empty_preferences():
    return Preferences(food=FoodPreferences(), books=BookPreferences())


# ---------------------------------------------------------------------------
# sources.llm: JSON parsing / validation
# ---------------------------------------------------------------------------


FOOD_KEYS = ["food", "restaurant"]


def test_parse_food_items_valid_json():
    raw = '[{"food": "Sushi", "restaurant": "Sukiyabashi Jiro"}]'
    items = llm_source._parse_json_array(raw, required_string_keys=FOOD_KEYS)
    assert items == [{"food": "Sushi", "restaurant": "Sukiyabashi Jiro"}]


def test_parse_food_items_rejects_malformed_json():
    with pytest.raises(LLMLookupError):
        llm_source._parse_json_array("not json at all", required_string_keys=FOOD_KEYS)


def test_parse_food_items_rejects_non_array():
    with pytest.raises(LLMLookupError):
        llm_source._parse_json_array(
            '{"food": "Sushi", "restaurant": "Jiro"}', required_string_keys=FOOD_KEYS
        )


def test_parse_food_items_rejects_missing_food_key():
    with pytest.raises(LLMLookupError):
        llm_source._parse_json_array('[{"restaurant": "Jiro"}]', required_string_keys=FOOD_KEYS)


def test_parse_food_items_rejects_missing_restaurant_key():
    with pytest.raises(LLMLookupError):
        llm_source._parse_json_array('[{"food": "Sushi"}]', required_string_keys=FOOD_KEYS)


def test_parse_food_items_rejects_empty_string_values():
    with pytest.raises(LLMLookupError):
        llm_source._parse_json_array(
            '[{"food": "  ", "restaurant": "Jiro"}]', required_string_keys=FOOD_KEYS
        )


def _make_fake_message(text: str):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


@patch("travel_agent.sources.llm.anthropic.Anthropic")
def test_generate_food_recommendations_missing_api_key_raises(mock_anthropic_cls, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMLookupError):
        llm_source.generate_food_recommendations("Tokyo")
    mock_anthropic_cls.assert_not_called()


@patch("travel_agent.sources.llm.anthropic.Anthropic")
def test_generate_food_recommendations_success(mock_anthropic_cls, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_fake_message(
        '[{"food": "Ramen", "restaurant": "Ichiran"}]'
    )
    mock_anthropic_cls.return_value = mock_client

    result = llm_source.generate_food_recommendations("Tokyo")

    assert result == [{"food": "Ramen", "restaurant": "Ichiran"}]
    mock_client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# sources.images: direct lookup / search fallback / no-image-found
# ---------------------------------------------------------------------------


def _make_response(status_code=200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    return response


@patch("travel_agent.sources.images.requests.get")
def test_fetch_food_image_direct_hit(mock_get):
    mock_get.return_value = _make_response(
        200, {"thumbnail": {"source": "https://example.com/sushi.jpg"}}
    )
    result = images_source.fetch_food_image("Sushi")
    assert result == "https://example.com/sushi.jpg"
    mock_get.assert_called_once()


@patch("travel_agent.sources.images.requests.get")
def test_fetch_food_image_falls_back_to_search(mock_get):
    direct_miss = _make_response(404)
    search_hit = _make_response(200, {"query": {"search": [{"title": "Okonomiyaki"}]}})
    resolved_hit = _make_response(
        200, {"thumbnail": {"source": "https://example.com/okonomiyaki.jpg"}}
    )
    mock_get.side_effect = [direct_miss, search_hit, resolved_hit]

    result = images_source.fetch_food_image("Okonomiyaki (regional dish)")

    assert result == "https://example.com/okonomiyaki.jpg"
    assert mock_get.call_count == 3


@patch("travel_agent.sources.images.requests.get")
def test_fetch_food_image_returns_none_when_nothing_found(mock_get):
    direct_miss = _make_response(404)
    search_miss = _make_response(200, {"query": {"search": []}})
    mock_get.side_effect = [direct_miss, search_miss]

    result = images_source.fetch_food_image("Zzzznotarealfood12345")

    assert result is None


@patch("travel_agent.sources.images.requests.get")
def test_fetch_food_image_network_error_returns_none(mock_get):
    mock_get.side_effect = requests.ConnectionError("boom")
    result = images_source.fetch_food_image("Sushi")
    assert result is None


# ---------------------------------------------------------------------------
# core.get_quintessential_foods: orchestration (truncation, enrichment)
# ---------------------------------------------------------------------------


@patch("travel_agent.core.cache_module.set_cached")
@patch("travel_agent.core.cache_module.get_cached", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.images_source.fetch_food_image")
@patch("travel_agent.core.llm_source.generate_food_recommendations")
def test_get_quintessential_foods_truncates_to_five(
    mock_generate, mock_fetch_image, mock_load_prefs, mock_get_cached, mock_set_cached
):
    mock_generate.return_value = [
        {"food": f"Food{i}", "restaurant": f"Restaurant{i}"} for i in range(8)
    ]
    mock_fetch_image.return_value = "https://example.com/image.jpg"

    result = core.get_quintessential_foods("Tokyo")

    assert len(result) == core.MAX_QUINTESSENTIAL_FOODS
    assert [item.name for item in result] == [f"Food{i}" for i in range(5)]


@patch("travel_agent.core.cache_module.set_cached")
@patch("travel_agent.core.cache_module.get_cached", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.images_source.fetch_food_image")
@patch("travel_agent.core.llm_source.generate_food_recommendations")
def test_get_quintessential_foods_missing_image_is_none(
    mock_generate, mock_fetch_image, mock_load_prefs, mock_get_cached, mock_set_cached
):
    mock_generate.return_value = [{"food": "Sushi", "restaurant": "Jiro"}]
    mock_fetch_image.return_value = None

    result = core.get_quintessential_foods("Tokyo")

    assert len(result) == 1
    assert result[0].name == "Sushi"
    assert result[0].restaurant == "Jiro"
    assert result[0].image_url is None


@patch("travel_agent.core.cache_module.get_cached", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.llm_source.generate_food_recommendations")
def test_get_quintessential_foods_propagates_llm_error(
    mock_generate, mock_load_prefs, mock_get_cached
):
    mock_generate.side_effect = LLMLookupError("no key")
    with pytest.raises(LLMLookupError):
        core.get_quintessential_foods("Tokyo")


@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.llm_source.generate_food_recommendations")
def test_get_quintessential_foods_uses_cache_by_default(mock_generate, mock_load_prefs):
    cached_payload = [{"name": "Sushi", "restaurant": "Jiro", "image_url": None}]
    with patch("travel_agent.core.cache_module.get_cached", return_value=cached_payload):
        result = core.get_quintessential_foods("Tokyo")

    assert len(result) == 1
    assert result[0].name == "Sushi"
    mock_generate.assert_not_called()


@patch("travel_agent.core.cache_module.set_cached")
@patch("travel_agent.core.images_source.fetch_food_image", return_value=None)
@patch("travel_agent.core.preferences_module.load_preferences", side_effect=_empty_preferences)
@patch("travel_agent.core.llm_source.generate_food_recommendations")
def test_get_quintessential_foods_ignore_cache_skips_read(
    mock_generate, mock_load_prefs, mock_fetch_image, mock_set_cached
):
    mock_generate.return_value = [{"food": "Ramen", "restaurant": "Ichiran"}]
    cached_payload = [{"name": "Sushi", "restaurant": "Jiro", "image_url": None}]

    with patch("travel_agent.core.cache_module.get_cached", return_value=cached_payload) as mock_get_cached:
        result = core.get_quintessential_foods("Tokyo", ignore_cache=True)

    mock_get_cached.assert_not_called()
    mock_generate.assert_called_once()
    assert result[0].name == "Ramen"
    mock_set_cached.assert_called_once()
