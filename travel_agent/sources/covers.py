"""Raw data access for book cover images via Open Library.

This module is responsible only for talking to Open Library's public
search and covers APIs to resolve a best-effort cover image URL for a
given (title, author) pair. Like `sources.images`, it is intentionally
forgiving: any failure (network error, no match, no cover) results in
`None` rather than an exception.
"""

import requests

SEARCH_URL = "https://openlibrary.org/search.json"
COVER_URL_TEMPLATE = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

REQUEST_TIMEOUT_SECONDS = 10


def fetch_book_cover(title: str, author: str):
    """Best-effort lookup of a cover image URL for `title` by `author`.

    Returns:
        The cover image URL as a string, or `None` if no match/cover
        could be found. Never raises.
    """
    try:
        response = requests.get(
            SEARCH_URL,
            params={
                "q": f"{title} {author}",
                "limit": 1,
                "fields": "title,author_name,cover_i",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    docs = data.get("docs") or []
    if not docs:
        return None

    cover_id = docs[0].get("cover_i")
    if not cover_id:
        return None

    return COVER_URL_TEMPLATE.format(cover_id=cover_id)
