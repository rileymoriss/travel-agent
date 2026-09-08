"""Generic, provider-agnostic file-based cache for LLM-backed features.

Each cache entry is a single JSON file under `.cache/`, named
`{feature}_{hash}.json`. The cache has no expiry: entries are valid
indefinitely until `clear_cache()` is called. `.cache/` is git-committed
(not git-ignored) so cached results are shared/inspectable like the rest
of the repo.

Weather is intentionally never cached here — it's tied to live,
date-specific forecasts that would go stale.
"""

import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


def cache_key(feature: str, **parts) -> str:
    """Build a stable cache key from a feature name and its query inputs.

    The key incorporates `feature` plus a canonical (sorted-keys) JSON
    encoding of `parts` (e.g. city + the relevant preferences slice), so
    changing any input naturally produces a different key rather than
    silently reusing a stale entry.
    """
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{feature}_{digest}"


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def get_cached(key: str):
    """Return the cached value for `key`, or None if not present/unreadable."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def set_cached(key: str, value) -> None:
    """Write/overwrite the cache entry for `key`."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(key)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def clear_cache() -> int:
    """Delete all files under `.cache/`. Returns the number of files removed."""
    if not CACHE_DIR.exists():
        return 0
    removed = 0
    for path in CACHE_DIR.glob("*.json"):
        path.unlink()
        removed += 1
    return removed
