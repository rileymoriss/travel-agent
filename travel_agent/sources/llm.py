"""Raw data access for LLM-generated recommendations via Claude.

This module is responsible only for talking to the Anthropic Claude API
and returning validated, structured data as plain dicts/lists. No further
business logic (image/cover enrichment, truncation rules, caching, etc.)
belongs here — see `travel_agent.core` for that.

Requires an `ANTHROPIC_API_KEY` environment variable (see .env.example).
"""

import json
import os

import anthropic

# Rolling alias (not a dated snapshot) so this doesn't silently break
# again when Anthropic retires a specific dated model version. Verified
# "Active" (current, non-legacy) against Anthropic's published model
# list/deprecations table as of implementation time.
MODEL = "claude-sonnet-5"
# Headroom for 5 items with longer, preference-driven descriptions;
# paired with tighter prompt wording below to keep per-item usage
# predictable, plus the stop_reason check in _call_claude as a backstop.
MAX_TOKENS = 2048

FOOD_PROMPT_TEMPLATE = (
    "List up to 5 of the most quintessential foods to try in {city}. "
    "The dish itself may be specific to {city} or, if the city doesn't "
    "have enough uniquely its own, drawn from its broader "
    "regional/national cuisine — but for each food, name one specific, "
    "real, recommended restaurant that is actually located IN {city} "
    "that serves it (not elsewhere in the country).\n"
    "{preferences_clause}\n\n"
    "Respond with ONLY a JSON array, no prose, no markdown code fences, "
    "in exactly this shape:\n"
    '[{{"food": "<food name>", "restaurant": "<restaurant name>"}}, ...]'
)

BOOK_PROMPT_TEMPLATE = (
    "List up to 5 books meaningfully connected to {city}. For each book, "
    "you may scope it to {city} specifically or broaden to its country "
    "if that yields more meaningful or well-known results — choose "
    "whichever gives the best picks for that particular book.\n"
    "{preferences_clause}\n\n"
    "Respond with ONLY a JSON array, no prose, no markdown code fences, "
    "in exactly this shape:\n"
    '[{{"title": "<book title>", "author": "<author name>", '
    '"description": "<1 concise sentence description>"}}, ...]'
)


def _food_preferences_clause(preferences) -> str:
    if preferences is None:
        return ""
    food = preferences.food
    lines = []
    if food.allergies:
        lines.append(f"Strictly avoid these allergens: {', '.join(food.allergies)}.")
    if food.dietary_restrictions:
        lines.append(
            f"Respect these dietary restrictions: {', '.join(food.dietary_restrictions)}."
        )
    if food.notes:
        lines.append(f"Additional preferences: {food.notes}")
    return " ".join(lines)


def _book_preferences_clause(preferences) -> str:
    if preferences is None:
        return ""
    books = preferences.books
    lines = []
    if books.favorite_genres:
        lines.append(f"Favor these genres where a good fit exists: {', '.join(books.favorite_genres)}.")
    if books.favorite_authors:
        lines.append(
            f"Favor these authors where a good fit exists: {', '.join(books.favorite_authors)}."
        )
    if books.notes:
        lines.append(f"Additional preferences: {books.notes}")
    return " ".join(lines)


class LLMLookupError(Exception):
    """Raised when the Claude API call fails or returns unusable output."""


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMLookupError(
            "ANTHROPIC_API_KEY is not set. Add it to your local .env file "
            "(see .env.example) to use LLM-backed features (--food, --books)."
        )
    return anthropic.Anthropic(api_key=api_key)


def _extract_text(message) -> str:
    parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    return "".join(parts).strip()


def _parse_json_array(raw_text: str, required_string_keys) -> list:
    """Parse `raw_text` as a JSON array of objects, validating that each
    object has all of `required_string_keys` as non-empty strings.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMLookupError(f"Model did not return valid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise LLMLookupError("Model response was not a JSON array.")

    items = []
    for entry in data:
        if not isinstance(entry, dict):
            raise LLMLookupError(f"Expected a JSON object per item, got: {entry!r}")

        item = {}
        for key in required_string_keys:
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise LLMLookupError(
                    f"Item missing a non-empty {key!r} string: {entry!r}"
                )
            item[key] = value.strip()
        items.append(item)

    return items


def _call_claude(prompt: str) -> str:
    client = _get_client()
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        raise LLMLookupError(f"Claude API request failed: {exc}") from exc

    if message.stop_reason == "max_tokens":
        raise LLMLookupError(
            "Response was truncated before completing — try shortening "
            "preferences.json notes or requesting fewer items."
        )
    return _extract_text(message)


def generate_food_recommendations(city: str, preferences=None) -> list:
    """Ask Claude for up to 5 (food, restaurant) pairs for `city`.

    Args:
        city: Name of the city to look up.
        preferences: Optional `travel_agent.preferences.Preferences`
            used to steer the prompt away from allergens/restrictions.

    Returns:
        A list of dicts: [{"food": ..., "restaurant": ...}, ...].

    Raises:
        LLMLookupError: if the API key is missing, the request fails, or
            the response cannot be parsed/validated as expected.
    """
    prompt = FOOD_PROMPT_TEMPLATE.format(
        city=city, preferences_clause=_food_preferences_clause(preferences)
    )
    raw_text = _call_claude(prompt)
    return _parse_json_array(raw_text, required_string_keys=["food", "restaurant"])


def generate_book_recommendations(city: str, preferences=None) -> list:
    """Ask Claude for up to 5 (title, author, description) triples for `city`.

    Args:
        city: Name of the city to look up.
        preferences: Optional `travel_agent.preferences.Preferences`
            used to steer the prompt toward favorite genres/authors.

    Returns:
        A list of dicts: [{"title": ..., "author": ..., "description": ...}, ...].

    Raises:
        LLMLookupError: if the API key is missing, the request fails, or
            the response cannot be parsed/validated as expected.
    """
    prompt = BOOK_PROMPT_TEMPLATE.format(
        city=city, preferences_clause=_book_preferences_clause(preferences)
    )
    raw_text = _call_claude(prompt)
    return _parse_json_array(
        raw_text, required_string_keys=["title", "author", "description"]
    )
