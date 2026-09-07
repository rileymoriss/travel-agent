"""Raw data access for weather forecasts via the Open-Meteo APIs.

This module is responsible only for talking to Open-Meteo's HTTP APIs
(geocoding and forecast) and returning their raw/parsed JSON responses. No
interpretation or business logic (e.g. condition text, rain-chance
bucketing, averaging) belongs here — see `travel_agent.core` for that.

Open-Meteo requires no API key: https://open-meteo.com/
"""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DAILY_FIELDS = "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
HOURLY_FIELDS = "temperature_2m"

REQUEST_TIMEOUT_SECONDS = 10

# WMO weather interpretation codes, as documented by Open-Meteo:
# https://open-meteo.com/en/docs
WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

UNKNOWN_CONDITION = "Unknown"


class CityNotFoundError(Exception):
    """Raised when a city name cannot be resolved to a location."""


class WeatherLookupError(Exception):
    """Raised when the weather forecast request fails."""


def describe_weather_code(code) -> str:
    """Translate a numeric WMO weather code into a human-readable string."""
    return WEATHER_CODE_DESCRIPTIONS.get(code, UNKNOWN_CONDITION)


def geocode_city(city: str):
    """Resolve a city name to (latitude, longitude, resolved_name).

    Raises:
        CityNotFoundError: if no matching location is found, or the
            request fails outright.
    """
    try:
        response = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise CityNotFoundError(f"Could not look up city '{city}': {exc}") from exc

    results = data.get("results") or []
    if not results:
        raise CityNotFoundError(f"No location found for city '{city}'.")

    match = results[0]
    return match["latitude"], match["longitude"], match["name"]


def fetch_forecast(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """Fetch daily and hourly forecast data for a location and date range.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        start_date: Inclusive start date, formatted as 'YYYY-MM-DD'.
        end_date: Inclusive end date, formatted as 'YYYY-MM-DD'.

    Returns:
        The parsed JSON response from Open-Meteo, containing 'daily' and
        'hourly' sections.

    Raises:
        WeatherLookupError: if the request fails.
    """
    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": DAILY_FIELDS,
                "hourly": HOURLY_FIELDS,
                "timezone": "auto",
                "temperature_unit": "celsius",
                "start_date": start_date,
                "end_date": end_date,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise WeatherLookupError(f"Could not fetch forecast: {exc}") from exc
