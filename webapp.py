"""Web entry point for the Travel Discovery Tool.

Usage:
    uvicorn webapp:app --reload --port 8000   # development, no auto-open
    python webapp.py                          # normal run, opens browser

Mirrors the role `app.py` plays for the CLI: a thin script that loads
`.env` and exposes the FastAPI `app` object built in
`travel_agent.web.app`. All business logic lives in `travel_agent/`;
this file only wires the server up.

`run.sh`/`run.bat` both launch this file directly (`python webapp.py`),
which is the only path that auto-opens the browser.
"""

import os

from dotenv import load_dotenv

# Load .env as early as possible so ANTHROPIC_API_KEY (read lazily by
# travel_agent.sources.llm at call time) is available in os.environ
# before any request is handled.
load_dotenv()

from travel_agent.web.app import app  # noqa: E402  (import after load_dotenv)

DEFAULT_PORT = 8000
BROWSER_OPEN_DELAY_SECONDS = 1

if __name__ == "__main__":
    import threading
    import webbrowser

    import uvicorn

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    url = f"http://127.0.0.1:{port}"

    threading.Timer(BROWSER_OPEN_DELAY_SECONDS, webbrowser.open, args=(url,)).start()

    # Runs in the foreground: closing the terminal or pressing Ctrl+C
    # stops the server, with no background process or PID file.
    uvicorn.run(app, host="127.0.0.1", port=port)
