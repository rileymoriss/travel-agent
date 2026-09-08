"""Unit tests for the FastAPI web layer (travel_agent.web).

These tests mock `travel_agent.core` functions (the boundary the web
layer calls into) to verify each `/api/*` endpoint's JSON shape and the
centralized exception -> HTTP status mapping, without making any real
network/LLM calls.
"""

from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from travel_agent.core import BookItem, FoodItem, WeatherDay
from travel_agent.sources.llm import LLMLookupError
from travel_agent.sources.weather import CityNotFoundError, WeatherLookupError
from travel_agent.web.app import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /api/welcome
# ---------------------------------------------------------------------------


@patch("travel_agent.web.api.core.get_welcome_message")
def test_welcome_returns_message(mock_get_welcome):
    mock_get_welcome.return_value = "Welcome to the Travel Discovery Tool! Let's explore Tokyo."

    response = client.get("/api/welcome", params={"city": "Tokyo"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Travel Discovery Tool! Let's explore Tokyo."
    }
    mock_get_welcome.assert_called_once_with("Tokyo")


# ---------------------------------------------------------------------------
# /api/weather
# ---------------------------------------------------------------------------


@patch("travel_agent.web.api.core.get_weekly_weather")
def test_weather_returns_expected_shape(mock_get_weather):
    mock_get_weather.return_value = [
        WeatherDay(
            date=date(2026, 9, 10),
            high_temp_c=20.0,
            low_temp_c=12.0,
            avg_temp_9am_9pm_c=16.5,
            condition="Clear sky",
            rain_chance="Low",
        )
    ]

    response = client.get("/api/weather", params={"city": "Tokyo"})

    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Tokyo"
    assert body["days"] == [
        {
            "date": "2026-09-10",
            "high_temp_c": 20.0,
            "low_temp_c": 12.0,
            "avg_temp_9am_9pm_c": 16.5,
            "condition": "Clear sky",
            "rain_chance": "Low",
        }
    ]
    mock_get_weather.assert_called_once_with("Tokyo", start_date=None, end_date=None)


@patch("travel_agent.web.api.core.get_weekly_weather")
def test_weather_passes_optional_date_params(mock_get_weather):
    mock_get_weather.return_value = []

    response = client.get(
        "/api/weather",
        params={"city": "Tokyo", "start_date": "2026-09-10", "end_date": "2026-09-12"},
    )

    assert response.status_code == 200
    mock_get_weather.assert_called_once_with(
        "Tokyo", start_date="2026-09-10", end_date="2026-09-12"
    )


@patch("travel_agent.web.api.core.get_weekly_weather")
def test_weather_invalid_date_range_returns_400(mock_get_weather):
    mock_get_weather.side_effect = ValueError("start_date must not be after end_date.")

    response = client.get("/api/weather", params={"city": "Tokyo"})

    assert response.status_code == 400
    assert response.json() == {"detail": "start_date must not be after end_date."}


@patch("travel_agent.web.api.core.get_weekly_weather")
def test_weather_city_not_found_returns_404(mock_get_weather):
    mock_get_weather.side_effect = CityNotFoundError("Could not find city 'Nowhereland'.")

    response = client.get("/api/weather", params={"city": "Nowhereland"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Could not find city 'Nowhereland'."}


@patch("travel_agent.web.api.core.get_weekly_weather")
def test_weather_lookup_error_returns_502(mock_get_weather):
    mock_get_weather.side_effect = WeatherLookupError("Forecast request failed.")

    response = client.get("/api/weather", params={"city": "Tokyo"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Forecast request failed."}


# ---------------------------------------------------------------------------
# /api/food
# ---------------------------------------------------------------------------


@patch("travel_agent.web.api.core.get_quintessential_foods")
def test_food_returns_expected_shape(mock_get_food):
    mock_get_food.return_value = [
        FoodItem(name="Ramen", restaurant="Ichiran", image_url="https://example.com/ramen.jpg")
    ]

    response = client.get("/api/food", params={"city": "Tokyo"})

    assert response.status_code == 200
    assert response.json() == {
        "city": "Tokyo",
        "items": [
            {
                "name": "Ramen",
                "restaurant": "Ichiran",
                "image_url": "https://example.com/ramen.jpg",
            }
        ],
    }
    mock_get_food.assert_called_once_with("Tokyo")


@patch("travel_agent.web.api.core.get_quintessential_foods")
def test_food_llm_error_returns_502(mock_get_food):
    mock_get_food.side_effect = LLMLookupError("Missing ANTHROPIC_API_KEY.")

    response = client.get("/api/food", params={"city": "Tokyo"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Missing ANTHROPIC_API_KEY."}


# ---------------------------------------------------------------------------
# /api/books
# ---------------------------------------------------------------------------


@patch("travel_agent.web.api.core.get_quintessential_books")
def test_books_returns_expected_shape(mock_get_books):
    mock_get_books.return_value = [
        BookItem(
            title="Norwegian Wood",
            author="Haruki Murakami",
            description="A coming-of-age novel set in Tokyo.",
            cover_url="https://example.com/cover.jpg",
        )
    ]

    response = client.get("/api/books", params={"city": "Tokyo"})

    assert response.status_code == 200
    assert response.json() == {
        "city": "Tokyo",
        "items": [
            {
                "title": "Norwegian Wood",
                "author": "Haruki Murakami",
                "description": "A coming-of-age novel set in Tokyo.",
                "cover_url": "https://example.com/cover.jpg",
            }
        ],
    }
    mock_get_books.assert_called_once_with("Tokyo")


@patch("travel_agent.web.api.core.get_quintessential_books")
def test_books_llm_error_returns_502(mock_get_books):
    mock_get_books.side_effect = LLMLookupError("Missing ANTHROPIC_API_KEY.")

    response = client.get("/api/books", params={"city": "Tokyo"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Missing ANTHROPIC_API_KEY."}


# ---------------------------------------------------------------------------
# / (index page)
# ---------------------------------------------------------------------------


def test_index_page_loads():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Travel Discovery Tool" in response.text
