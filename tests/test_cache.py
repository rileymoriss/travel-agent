"""Unit tests for travel_agent.cache.

All tests redirect CACHE_DIR to a temporary directory so they never
touch the repo's real, git-committed `.cache/` folder.
"""

from travel_agent import cache as cache_module


def test_cache_key_is_stable_for_identical_inputs():
    key1 = cache_module.cache_key("food", city="Tokyo", allergies=[])
    key2 = cache_module.cache_key("food", city="Tokyo", allergies=[])
    assert key1 == key2


def test_cache_key_changes_when_preferences_differ():
    key1 = cache_module.cache_key("food", city="Tokyo", allergies=[])
    key2 = cache_module.cache_key("food", city="Tokyo", allergies=["shellfish"])
    assert key1 != key2


def test_cache_key_changes_when_feature_differs():
    key1 = cache_module.cache_key("food", city="Tokyo")
    key2 = cache_module.cache_key("books", city="Tokyo")
    assert key1 != key2


def test_get_cached_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    assert cache_module.get_cached("nonexistent_key") is None


def test_set_then_get_cached_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    key = cache_module.cache_key("food", city="Tokyo")

    cache_module.set_cached(key, [{"name": "Sushi"}])

    assert cache_module.get_cached(key) == [{"name": "Sushi"}]


def test_set_cached_overwrites_existing_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    key = cache_module.cache_key("food", city="Tokyo")

    cache_module.set_cached(key, [{"name": "Sushi"}])
    cache_module.set_cached(key, [{"name": "Ramen"}])

    assert cache_module.get_cached(key) == [{"name": "Ramen"}]


def test_get_cached_returns_none_for_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    key = cache_module.cache_key("food", city="Tokyo")
    (tmp_path / f"{key}.json").write_text("not json")

    assert cache_module.get_cached(key) is None


def test_clear_cache_removes_all_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path)
    key1 = cache_module.cache_key("food", city="Tokyo")
    key2 = cache_module.cache_key("books", city="Dublin")
    cache_module.set_cached(key1, [{"name": "Sushi"}])
    cache_module.set_cached(key2, [{"title": "Dubliners"}])

    removed = cache_module.clear_cache()

    assert removed == 2
    assert cache_module.get_cached(key1) is None
    assert cache_module.get_cached(key2) is None


def test_clear_cache_on_missing_directory_returns_zero(tmp_path, monkeypatch):
    missing_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr(cache_module, "CACHE_DIR", missing_dir)

    assert cache_module.clear_cache() == 0
