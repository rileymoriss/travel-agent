"""Raw data access for LLM-generated food recommendations via Claude.

This module is responsible only for talking to the Anthropic Claude API
and returning validated, structured (food, restaurant) pairs as plain
dicts. No further business logic (image enrichment, truncation rules,
etc.) belongs here — see `travel_agent.core` for that.

Requires an `ANTHROPIC_API_KEY` environment variable (see .env.example).
"""

import json
import os

import anthropic

MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 1024

PROMPT_TEMPLATE = (
    "List up to 5 of the most quintessential foods to try in {city}. "
    "For each food, name one specific, real, recommended restaurant in "
    "{city} that serves it.\n\n"
    "Respond with ONLY a JSON array, no prose, no markdown code fences, "
    "in exactly this shape:\n"
    '[{{"food": "<food name>", "restaurant": "<restaurant name>"}}, ...]'
)


class LLMLookupError(Exception):
    """Raised when the Claude API call fails or returns unusable output."""


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMLookupError(
            "ANTHROPIC_API_KEY is not set. Add it to your local .env file "
            "(see .env.example) to use the quintessential-foods feature."
        )
    return anthropic.Anthropic(api_key=api_key)


def _extract_text(message) -> str:
    parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    return "".join(parts).strip()


def _parse_food_items(raw_text: str) -> list:
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

        food = entry.get("food")
        restaurant = entry.get("restaurant")
        if not isinstance(food, str) or not food.strip():
            raise LLMLookupError(f"Item missing a non-empty 'food' string: {entry!r}")
        if not isinstance(restaurant, str) or not restaurant.strip():
            raise LLMLookupError(f"Item missing a non-empty 'restaurant' string: {entry!r}")

        items.append({"food": food.strip(), "restaurant": restaurant.strip()})

    return items


def generate_food_recommendations(city: str) -> list:
    """Ask Claude for up to 5 (food, restaurant) pairs for `city`.

    Returns:
        A list of dicts: [{"food": ..., "restaurant": ...}, ...].

    Raises:
        LLMLookupError: if the API key is missing, the request fails, or
            the response cannot be parsed/validated as expected.
    """
    client = _get_client()

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(city=city)}],
        )
    except anthropic.APIError as exc:
        raise LLMLookupError(f"Claude API request failed: {exc}") from exc

    raw_text = _extract_text(message)
    return _parse_food_items(raw_text)
