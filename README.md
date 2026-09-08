# Travel Agent

A local Python-based travel discovery tool that gives personalized
recommendations for a city. This project is being built incrementally —
today it's a simple command-line script, but the structure is designed so
a web interface (Flask/FastAPI) can be added later without reorganizing
the codebase.

## Project structure

```
travel-agent/
├── app.py                 # CLI entry point (temporary interface)
├── travel_agent/           # Core application package
│   ├── core.py              # Interface-agnostic application logic (weather, food, books)
│   ├── preferences.py        # Loads preferences.json (allergies, favorite genres, etc.)
│   ├── cache.py              # Generic file-based cache for LLM-backed features
│   └── sources/             # Data-fetching modules
│       ├── weather.py         # Open-Meteo geocoding + forecast HTTP calls
│       ├── llm.py             # Claude API calls for food/book recommendations
│       ├── images.py          # Wikipedia image lookups (food)
│       └── covers.py          # Open Library cover lookups (books)
├── preferences.json        # Your personal food/book preferences (hand-edited, committed)
├── .cache/                 # Cached LLM results, one JSON file per query (committed)
├── tests/                  # Unit tests
├── requirements.txt
├── requirements-dev.txt    # Adds pytest for running the test suite
├── .env.example
└── .gitignore
```

## Installation

1. (Recommended) Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in any API keys you have:

   ```bash
   cp .env.example .env
   ```

## Usage

Run the script with a city name:

```bash
python app.py "San Francisco"
```

This prints a welcome message for the city.

### Weather forecast

Add `--weather` to see a daily forecast for the next 7 days (high/low
temperature, average temperature between 9am-9pm, general condition, and
chance of rain). No API key is required — it uses the free
[Open-Meteo](https://open-meteo.com/) APIs.

```bash
python app.py "San Francisco" --weather
```

You can also request an explicit date range (max ~16 days):

```bash
python app.py "San Francisco" --weather --start-date 2026-09-10 --end-date 2026-09-12
```

### Quintessential foods

Add `--food` to see up to 5 quintessential foods for a city, each with a
recommended restaurant and (best-effort) a representative image. This
feature uses the Claude API and **requires an `ANTHROPIC_API_KEY`**:

1. Get a key at <https://console.anthropic.com/>.
2. Add it to your local `.env` file (never commit this key or paste it
   into chat):

   ```
   ANTHROPIC_API_KEY=your_real_key_here
   ```

```bash
python app.py "Tokyo" --food
```

### Quintessential books

Add `--books` to see up to 5 books meaningfully connected to a city (the
model may scope individual picks to the city or its country, whichever
gives better results), each with author, a short description, and a
best-effort cover image. Also requires `ANTHROPIC_API_KEY` (see above).

```bash
python app.py "Dublin" --books
```

### Personalizing results

Both `--food` and `--books` read `preferences.json` at the repo root and
factor it into the prompt sent to Claude. Edit it directly — it's a
plain, git-committed JSON file (no secrets), e.g.:

```json
{
  "food": {
    "allergies": ["shellfish"],
    "dietary_restrictions": ["vegetarian"],
    "notes": "I love street food"
  },
  "books": {
    "favorite_genres": ["mystery"],
    "favorite_authors": ["Agatha Christie"],
    "notes": ""
  }
}
```

A default (empty) file is created automatically if it's missing, so the
app still works out of the box.

### Caching

`--food` and `--books` results are cached under `.cache/` (one JSON file
per unique city + relevant preferences combination), so repeat requests
reuse the prior LLM output by default instead of re-spending tokens.
There is no expiry — editing `preferences.json` naturally produces a new
cache entry for affected features, since preferences are part of the
cache key.

- `--ignore-cache` forces a fresh LLM call for that one invocation
  (overwriting the cache entry with the new result):

  ```bash
  python app.py "Tokyo" --food --ignore-cache
  ```

- `--clear-cache` wipes all cached results and exits immediately (no
  city required, no LLM call made):

  ```bash
  python app.py --clear-cache
  ```

Weather is intentionally never cached — forecasts are date-specific and
would go stale.

More features (additional data sources and a web interface) are coming
soon.

## Running tests

Install the dev dependencies and run `pytest`:

```bash
pip install -r requirements-dev.txt
pytest
```
