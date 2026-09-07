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
│   ├── core.py              # Interface-agnostic application logic (e.g. weather forecasting)
│   └── sources/             # Data-fetching modules (food, books, POIs, weather, etc.)
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

More features (personalized recommendations, additional data sources, and
a web interface) are coming soon.

## Running tests

Install the dev dependencies and run `pytest`:

```bash
pip install -r requirements-dev.txt
pytest
```
