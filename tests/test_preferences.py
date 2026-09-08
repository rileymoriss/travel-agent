"""Unit tests for travel_agent.preferences."""

import json

import pytest

from travel_agent.preferences import (
    BookPreferences,
    FoodPreferences,
    PreferencesError,
    load_preferences,
)


def test_load_preferences_creates_default_file_when_missing(tmp_path):
    path = tmp_path / "preferences.json"
    assert not path.exists()

    prefs = load_preferences(path=path)

    assert path.exists()
    assert prefs.food == FoodPreferences()
    assert prefs.books == BookPreferences()


def test_load_preferences_reads_existing_values(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text(
        json.dumps(
            {
                "food": {
                    "allergies": ["shellfish"],
                    "dietary_restrictions": ["vegetarian"],
                    "notes": "no offal",
                },
                "books": {
                    "favorite_genres": ["mystery"],
                    "favorite_authors": ["Agatha Christie"],
                    "notes": "prefer short novels",
                },
            }
        )
    )

    prefs = load_preferences(path=path)

    assert prefs.food.allergies == ["shellfish"]
    assert prefs.food.dietary_restrictions == ["vegetarian"]
    assert prefs.food.notes == "no offal"
    assert prefs.books.favorite_genres == ["mystery"]
    assert prefs.books.favorite_authors == ["Agatha Christie"]
    assert prefs.books.notes == "prefer short novels"


def test_load_preferences_rejects_malformed_json(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text("not json at all")

    with pytest.raises(PreferencesError):
        load_preferences(path=path)


def test_load_preferences_rejects_non_object_root(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text("[1, 2, 3]")

    with pytest.raises(PreferencesError):
        load_preferences(path=path)


def test_load_preferences_rejects_wrong_type_for_list_field(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text(json.dumps({"food": {"allergies": "shellfish"}}))

    with pytest.raises(PreferencesError):
        load_preferences(path=path)


def test_load_preferences_tolerates_missing_sections(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text(json.dumps({}))

    prefs = load_preferences(path=path)

    assert prefs.food == FoodPreferences()
    assert prefs.books == BookPreferences()
