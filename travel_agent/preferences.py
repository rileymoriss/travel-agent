"""Loading and validating the user's personal preferences file.

`preferences.json` lives at the repo root and is git-committed (this is
a personal tool, not a multi-user product, so there's no secret data in
it — only the user's own tastes/restrictions). LLM-backed features read
it to personalize prompts (e.g. excluding allergens, favoring genres).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

PREFERENCES_PATH = Path(__file__).resolve().parent.parent / "preferences.json"

DEFAULT_PREFERENCES_DICT = {
    "food": {
        "allergies": [],
        "dietary_restrictions": [],
        "notes": "",
    },
    "books": {
        "favorite_genres": [],
        "favorite_authors": [],
        "notes": "",
    },
}


class PreferencesError(Exception):
    """Raised when preferences.json exists but cannot be parsed."""


@dataclass
class FoodPreferences:
    allergies: list = field(default_factory=list)
    dietary_restrictions: list = field(default_factory=list)
    notes: str = ""


@dataclass
class BookPreferences:
    favorite_genres: list = field(default_factory=list)
    favorite_authors: list = field(default_factory=list)
    notes: str = ""


@dataclass
class Preferences:
    food: FoodPreferences
    books: BookPreferences


def _write_default_preferences(path: Path) -> None:
    path.write_text(json.dumps(DEFAULT_PREFERENCES_DICT, indent=2) + "\n")


def _coerce_str_list(value) -> list:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PreferencesError(f"Expected a list of strings, got: {value!r}")
    return value


def load_preferences(path: Path = None) -> Preferences:
    """Load `preferences.json`, creating a default empty file if missing.

    Args:
        path: Optional override of the preferences file location
            (primarily for testing). Defaults to `preferences.json` at
            the repo root.

    Returns:
        A `Preferences` dataclass with `.food` and `.books` sections.

    Raises:
        PreferencesError: if the file exists but is not valid JSON, or
            has fields of the wrong type.
    """
    resolved_path = path if path is not None else PREFERENCES_PATH

    if not resolved_path.exists():
        _write_default_preferences(resolved_path)

    try:
        raw = json.loads(resolved_path.read_text())
    except json.JSONDecodeError as exc:
        raise PreferencesError(
            f"{resolved_path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise PreferencesError(f"{resolved_path} must contain a JSON object.")

    food_raw = raw.get("food", {}) or {}
    books_raw = raw.get("books", {}) or {}

    food = FoodPreferences(
        allergies=_coerce_str_list(food_raw.get("allergies")),
        dietary_restrictions=_coerce_str_list(food_raw.get("dietary_restrictions")),
        notes=food_raw.get("notes") or "",
    )
    books = BookPreferences(
        favorite_genres=_coerce_str_list(books_raw.get("favorite_genres")),
        favorite_authors=_coerce_str_list(books_raw.get("favorite_authors")),
        notes=books_raw.get("notes") or "",
    )

    return Preferences(food=food, books=books)
