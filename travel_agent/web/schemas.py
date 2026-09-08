"""Pydantic response models for the web API.

These mirror the dataclasses defined in `travel_agent.core`, adapted for
JSON serialization over HTTP. No business logic lives here.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict


class WelcomeResponse(BaseModel):
    message: str


class WeatherDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    high_temp_c: float
    low_temp_c: float
    avg_temp_9am_9pm_c: float | None = None
    condition: str
    rain_chance: str


class WeatherResponse(BaseModel):
    city: str
    days: list[WeatherDayOut]


class FoodItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    restaurant: str
    image_url: str | None = None


class FoodResponse(BaseModel):
    city: str
    items: list[FoodItemOut]


class BookItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    author: str
    description: str
    cover_url: str | None = None


class BooksResponse(BaseModel):
    city: str
    items: list[BookItemOut]


class ErrorResponse(BaseModel):
    detail: str
