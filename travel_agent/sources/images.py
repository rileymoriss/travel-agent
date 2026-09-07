"""Raw data access for representative food images via Wikipedia.

This module is responsible only for talking to Wikipedia's public REST
and search APIs to resolve a best-effort thumbnail image URL for a given
food name. It is intentionally forgiving: any failure (network error,
missing page, missing thumbnail) results in `None` rather than an
exception, since a missing picture should never break the broader
"quintessential foods" feature.
"""

import requests

SUMMARY_URL_TEMPLATE = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
SEARCH_URL = "https://en.wikipedia.org/w/api.php"

REQUEST_TIMEOUT_SECONDS = 10

# Wikipedia's API rejects requests without a descriptive User-Agent
# (returns 403), per https://meta.wikimedia.org/wiki/User-Agent_policy.
REQUEST_HEADERS = {
    "User-Agent": "travel-agent/0.1 (https://github.com/rileymoriss/travel-agent)"
}


def _fetch_thumbnail(title: str):
    """Return the thumbnail URL for a Wikipedia page title, or None."""
    try:
        response = requests.get(
            SUMMARY_URL_TEMPLATE.format(title=title),
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers=REQUEST_HEADERS,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    thumbnail = data.get("thumbnail") or {}
    return thumbnail.get("source")


def _search_page_title(query: str):
    """Return the closest matching Wikipedia page title for `query`, or None."""
    try:
        response = requests.get(
            SEARCH_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 1,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers=REQUEST_HEADERS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    results = data.get("query", {}).get("search") or []
    if not results:
        return None
    return results[0].get("title")


def fetch_food_image(food_name: str):
    """Best-effort lookup of a representative image URL for `food_name`.

    Tries a direct Wikipedia summary lookup first; if that doesn't yield
    a thumbnail, falls back to Wikipedia's search API to resolve the
    closest matching page title and retries once.

    Returns:
        The thumbnail image URL as a string, or `None` if no image could
        be found. Never raises.
    """
    thumbnail = _fetch_thumbnail(food_name)
    if thumbnail:
        return thumbnail

    resolved_title = _search_page_title(food_name)
    if not resolved_title or resolved_title == food_name:
        return None

    return _fetch_thumbnail(resolved_title)
