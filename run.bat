@echo off
REM Double-click (or run.bat) launcher for the Travel Discovery Tool web UI.
REM
REM On first run, bootstraps a local venv\ with the project's dependencies
REM and creates .env from .env.example, so no manual "pip install" step is
REM required. Runs the server in the foreground: closing this console
REM window, or pressing Ctrl+C, stops the server. There is no
REM background/daemon mode, PID file, or separate stop script.

cd /d "%~dp0"

set FIRST_RUN=0
if not exist "venv" (
  set FIRST_RUN=1
  echo First run detected: setting up a virtual environment and installing
  echo dependencies. This may take a minute...
  python -m venv venv
)

if %FIRST_RUN%==1 (
  venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist ".env" (
  copy .env.example .env >nul
  echo Created .env from .env.example. Add your ANTHROPIC_API_KEY there to
  echo enable the food/books features (weather works without it).
)

venv\Scripts\python.exe webapp.py
