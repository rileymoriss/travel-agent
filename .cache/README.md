# LLM response cache

This directory holds cached results for LLM-backed features (currently
food and book recommendations), one JSON file per unique
`(feature, city, relevant preferences)` combination. It is intentionally
git-committed (not git-ignored) — see `travel_agent/cache.py`.

There is no expiry. To force a fresh LLM call for one invocation, pass
`--ignore-cache`. To wipe all cached entries, run
`python app.py --clear-cache`.
