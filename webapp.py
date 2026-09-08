"""Web entry point for the Travel Discovery Tool.

Usage:
    uvicorn webapp:app --reload --port 8000
    python webapp.py

Mirrors the role `app.py` plays for the CLI: a thin script that loads
`.env` and exposes the FastAPI `app` object built in
`travel_agent.web.app`. All business logic lives in `travel_agent/`;
this file only wires the server up.
"""

import os

from dotenv import load_dotenv

# Load .env as early as possible so ANTHROPIC_API_KEY (read lazily by
# travel_agent.sources.llm at call time) is available in os.environ
# before any request is handled.
load_dotenv()

from travel_agent.web.app import app  # noqa: E402  (import after load_dotenv)

DEFAULT_PORT = 8000

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
