"""JSON API endpoints exposing `travel_agent.core` over HTTP.

Each route is a thin translation layer: it calls straight into
`travel_agent.core` and returns Pydantic-validated data. Domain
exceptions raised by `core` (ValueError, CityNotFoundError,
WeatherLookupError, LLMLookupError) are intentionally not caught here —
they propagate up to the centralized exception handlers registered in
`travel_agent.web.app`.
"""

from fastapi import APIRouter

from travel_agent import core
from travel_agent.web.schemas import (
    BooksResponse,
    FoodResponse,
    WeatherResponse,
    WelcomeResponse,
)

router = APIRouter(prefix="/api")


@router.get("/welcome", response_model=WelcomeResponse)
def get_welcome(city: str):
    return WelcomeResponse(message=core.get_welcome_message(city))


@router.get("/weather", response_model=WeatherResponse)
def get_weather(city: str, start_date: str | None = None, end_date: str | None = None):
    days = core.get_weekly_weather(city, start_date=start_date, end_date=end_date)
    return WeatherResponse(city=city, days=days)


@router.get("/food", response_model=FoodResponse)
def get_food(city: str):
    items = core.get_quintessential_foods(city)
    return FoodResponse(city=city, items=items)


@router.get("/books", response_model=BooksResponse)
def get_books(city: str):
    items = core.get_quintessential_books(city)
    return BooksResponse(city=city, items=items)
