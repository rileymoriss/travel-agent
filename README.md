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
│   ├── core.py              # Interface-agnostic application logic
│   └── sources/             # Data-fetching modules (food, books, POIs, etc.)
├── requirements.txt
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

This currently prints a welcome message for the city. More features
(personalized recommendations, data sources, and a web interface) are
coming soon.
