#!/usr/bin/env bash
# Double-click (or ./run.sh) launcher for the Travel Discovery Tool web UI.
#
# On first run, bootstraps a local venv/ with the project's dependencies
# and creates .env from .env.example, so no manual `pip install` step is
# required. Runs the server in the foreground: closing this
# terminal/console window, or pressing Ctrl+C, stops the server. There
# is no background/daemon mode, PID file, or separate stop script.
set -e

cd "$(dirname "$0")"

FIRST_RUN=0
if [ ! -d "venv" ]; then
  FIRST_RUN=1
  echo "First run detected: setting up a virtual environment and installing"
  echo "dependencies. This may take a minute..."
  python3 -m venv venv
fi

if [ $FIRST_RUN -eq 1 ]; then
  venv/bin/pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Add your ANTHROPIC_API_KEY there to"
  echo "enable the food/books features (weather works without it)."
fi

exec venv/bin/python webapp.py
