# Travel Agent

A local Python-based travel discovery tool that gives personalized
recommendations for a city. It's built incrementally, with a
command-line interface (`app.py`) and a FastAPI-based web UI
(`webapp.py`) both sitting on top of the same core `travel_agent`
package.

## Project structure

```
travel-agent/
├── app.py                 # CLI entry point (temporary interface)
├── webapp.py               # Web entry point (FastAPI app; opens a browser when run directly)
├── run.sh                  # Double-click launcher (Linux/macOS): bootstraps venv + runs webapp.py
├── run.bat                 # Double-click launcher (Windows): same as run.sh
├── travel_agent/           # Core application package
│   ├── core.py              # Interface-agnostic application logic (weather, food, books)
│   ├── preferences.py        # Loads preferences.json (allergies, favorite genres, etc.)
│   ├── cache.py              # Generic file-based cache for LLM-backed features
│   ├── sources/             # Data-fetching modules
│   │   ├── weather.py         # Open-Meteo geocoding + forecast HTTP calls
│   │   ├── llm.py             # Claude API calls for food/book recommendations
│   │   ├── images.py          # Wikipedia image lookups (food)
│   │   └── covers.py          # Open Library cover lookups (books)
│   └── web/                 # FastAPI web layer (JSON API + single-page frontend)
│       ├── app.py              # App factory: static/templates mounting, exception handlers
│       ├── api.py              # /api/* JSON endpoints, thin wrappers around core.py
│       ├── schemas.py          # Pydantic response models
│       ├── templates/          # Jinja2 page shell (index.html)
│       └── static/             # Vanilla JS/CSS driving the page (app.js, styles.css)
├── preferences.json        # Your personal food/book preferences (hand-edited, committed)
├── .cache/                 # Cached LLM results, one JSON file per query (committed)
├── tests/                  # Unit tests
├── requirements.txt
├── requirements-dev.txt    # Adds pytest + httpx for running the test suite
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

More features (additional data sources) are coming soon.

## Web UI

In addition to the CLI, a FastAPI-based web UI is available: a single
page where entering a city populates weather, quintessential foods, and
quintessential books sections independently (each loads and can fail on
its own, so a slow/missing-API-key food or books lookup never blocks the
weather section).

### Quickest way to run it (double-click)

- **Linux (e.g. Fedora):** double-click `run.sh`, or run `./run.sh` from
  a terminal.
- **Windows:** double-click `run.bat`.

On first run, the script creates a local `venv/`, installs
`requirements.txt` into it, and copies `.env.example` to `.env` if one
doesn't already exist — no manual `pip install` step required (this may
take a minute the first time; subsequent runs are fast). It then starts
the server and automatically opens the page in your default browser.

The server runs in the foreground of that same terminal/console window:
closing the window, or pressing Ctrl+C, stops it. There's no
background/daemon mode, PID file, or separate stop script — if the
window is open, the server is running.

> **Linux double-click note:** GNOME Files (Nautilus, Fedora's default
> file manager) doesn't execute `.sh` scripts on a plain double-click
> by default. If double-clicking `run.sh` does nothing or opens it as
> text, either choose **Run in Terminal** from the prompt it shows, or
> right-click the file → Properties → Permissions → enable "Allow
> executing file as program" first.

### Manual way to run it

Install dependencies (already covered by `requirements.txt`), then run
the server with `uvicorn`:

```bash
uvicorn webapp:app --reload
```

or, for a run that also auto-opens your browser (reads `PORT` from the
environment, defaulting to 8000):

```bash
python webapp.py
```

Then open <http://localhost:8000> in a browser and enter a city (if it
wasn't opened for you automatically).

Relevant environment variables (set in `.env`, same as the CLI):

- `ANTHROPIC_API_KEY` — required for the food/books sections; if unset,
  those sections show an error state while weather still loads normally.
- `PORT` — optional, only used by the `python webapp.py` / `run.sh` /
  `run.bat` path (defaults to 8000). When running `uvicorn` directly,
  pick the port with `--port` instead.

The web UI is a thin layer over the same `travel_agent` package used by
the CLI (`travel_agent/core.py`, `travel_agent/sources/`) — it exposes
`GET /api/welcome`, `GET /api/weather`, `GET /api/food`, and
`GET /api/books` as JSON endpoints, consumed by the single page via
`fetch`. As with the CLI, preferences and cache management remain
CLI/manual-file-only for now (edit `preferences.json` directly, or use
`python app.py --clear-cache`) — there's no settings page in the UI yet.

## Running tests

Install the dev dependencies and run `pytest`:

```bash
pip install -r requirements-dev.txt
pytest
```
