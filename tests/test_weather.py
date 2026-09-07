"""Unit tests for the weather-forecast feature.

These tests exercise the pure computation logic (weathercode mapping,
rain-chance bucketing, 9am-9pm averaging, and date validation) without
making real network calls, by mocking `sources.weather.geocode_city` and
`sources.weather.fetch_forecast`.
"""

from datetime import date
from unittest.mock import patch

import pytest

from travel_agent import core
from travel_agent.sources import weather as weather_source


# ---------------------------------------------------------------------------
# weathercode -> condition mapping
# ---------------------------------------------------------------------------


def test_describe_weather_code_known_codes():
    assert weather_source.describe_weather_code(0) == "Clear sky"
    assert weather_source.describe_weather_code(2) == "Partly cloudy"
    assert weather_source.describe_weather_code(95) == "Thunderstorm"


def test_describe_weather_code_unknown_code_falls_back():
    assert weather_source.describe_weather_code(12345) == weather_source.UNKNOWN_CONDITION


# ---------------------------------------------------------------------------
# rain-chance bucketing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "probability,expected",
    [
        (0, "Low"),
        (29, "Low"),
        (30, "Medium"),
        (45, "Medium"),
        (60, "Medium"),
        (61, "High"),
        (100, "High"),
    ],
)
def test_rain_chance_from_probability_boundaries(probability, expected):
    assert core._rain_chance_from_probability(probability) == expected


def test_rain_chance_from_probability_none_is_unknown():
    assert core._rain_chance_from_probability(None) == "Unknown"


# ---------------------------------------------------------------------------
# 9am-9pm averaging
# ---------------------------------------------------------------------------


def test_average_hourly_window_only_includes_target_date_and_hours():
    hourly_times = [
        "2026-09-10T08:00",
        "2026-09-10T09:00",
        "2026-09-10T15:00",
        "2026-09-10T21:00",
        "2026-09-10T22:00",
        "2026-09-11T12:00",
    ]
    hourly_temps = [10.0, 20.0, 30.0, 40.0, 999.0, 999.0]
    avg = core._average_hourly_window(hourly_times, hourly_temps, date(2026, 9, 10))
    # Only 09:00, 15:00, 21:00 fall within the 9am-9pm window on the target date.
    assert avg == pytest.approx((20.0 + 30.0 + 40.0) / 3)


def test_average_hourly_window_no_matching_hours_returns_none():
    hourly_times = ["2026-09-10T22:00", "2026-09-10T23:00"]
    hourly_temps = [1.0, 2.0]
    avg = core._average_hourly_window(hourly_times, hourly_temps, date(2026, 9, 10))
    assert avg is None


# ---------------------------------------------------------------------------
# get_weekly_weather: date validation
# ---------------------------------------------------------------------------


def test_get_weekly_weather_start_after_end_raises():
    with pytest.raises(ValueError):
        core.get_weekly_weather("San Francisco", start_date="2026-09-15", end_date="2026-09-10")


def test_get_weekly_weather_range_too_long_raises():
    with pytest.raises(ValueError):
        core.get_weekly_weather("San Francisco", start_date="2026-09-01", end_date="2026-09-20")


# ---------------------------------------------------------------------------
# get_weekly_weather: end-to-end with mocked sources
# ---------------------------------------------------------------------------


FAKE_FORECAST_RESPONSE = {
    "daily": {
        "time": ["2026-09-10", "2026-09-11"],
        "temperature_2m_max": [25.0, 22.0],
        "temperature_2m_min": [15.0, 14.0],
        "weathercode": [0, 61],
        "precipitation_probability_max": [10, 70],
    },
    "hourly": {
        "time": [
            "2026-09-10T09:00",
            "2026-09-10T21:00",
            "2026-09-11T09:00",
            "2026-09-11T21:00",
        ],
        "temperature_2m": [18.0, 22.0, 16.0, 18.0],
    },
}


@patch("travel_agent.core.weather_source.fetch_forecast")
@patch("travel_agent.core.weather_source.geocode_city")
def test_get_weekly_weather_end_to_end(mock_geocode, mock_fetch_forecast):
    mock_geocode.return_value = (37.7749, -122.4194, "San Francisco")
    mock_fetch_forecast.return_value = FAKE_FORECAST_RESPONSE

    result = core.get_weekly_weather(
        "San Francisco", start_date="2026-09-10", end_date="2026-09-11"
    )

    assert len(result) == 2

    day1 = result[0]
    assert day1.date == date(2026, 9, 10)
    assert day1.high_temp_c == 25.0
    assert day1.low_temp_c == 15.0
    assert day1.avg_temp_9am_9pm_c == pytest.approx((18.0 + 22.0) / 2)
    assert day1.condition == "Clear sky"
    assert day1.rain_chance == "Low"

    day2 = result[1]
    assert day2.date == date(2026, 9, 11)
    assert day2.condition == "Slight rain"
    assert day2.rain_chance == "High"

    mock_geocode.assert_called_once_with("San Francisco")
    mock_fetch_forecast.assert_called_once_with(
        37.7749, -122.4194, "2026-09-10", "2026-09-11"
    )
