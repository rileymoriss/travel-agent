"""FastAPI application factory for the Travel Discovery Tool web UI.

Mounts static assets, configures Jinja2 templates, includes the `/api`
router, registers centralized exception handlers that translate
`travel_agent.core` domain exceptions into JSON error responses, and
serves the single-page frontend at `/`.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from travel_agent.sources.llm import LLMLookupError
from travel_agent.sources.weather import CityNotFoundError, WeatherLookupError
from travel_agent.web.api import router as api_router

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    app = FastAPI(title="Travel Discovery Tool")

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(api_router)

    @app.exception_handler(CityNotFoundError)
    def handle_city_not_found(request: Request, exc: CityNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(WeatherLookupError)
    def handle_weather_lookup_error(request: Request, exc: WeatherLookupError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(LLMLookupError)
    def handle_llm_lookup_error(request: Request, exc: LLMLookupError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    def handle_value_error(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(request, "index.html", {})

    return app


app = create_app()
