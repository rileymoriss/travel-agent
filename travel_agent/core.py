"""Core application logic for the travel discovery tool.

This module is the entry point for interface-agnostic logic. Both the
current CLI (app.py) and any future web layer should call into functions
defined here, rather than duplicating logic in the interface layer.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from travel_agent import cache as cache_module
from travel_agent import preferences as preferences_module
from travel_agent.sources import covers as covers_source
from travel_agent.sources import images as images_source
from travel_agent.sources import llm as llm_source
from travel_agent.sources import weather as weather_source

# Maximum number of quintessential foods/books returned per city,
# enforced defensively here even though the LLM prompt already asks for
# at most this many.
MAX_QUINTESSENTIAL_FOODS = 5
MAX_QUINTESSENTIAL_BOOKS = 5

DATE_FORMAT = "%Y-%m-%d"

# Open-Meteo's forecast API supports at most ~16 days in a single request.
MAX_FORECAST_SPAN_DAYS = 16

# Default lookup window when no explicit date range is given.
DEFAULT_FORECAST_DAYS = 7

# Thresholds (in percent) used to bucket `precipitation_probability_max`
# into a plain-language rain chance. Named constants so they're easy to
# tune later.
RAIN_CHANCE_LOW_MAX = 30
RAIN_CHANCE_MEDIUM_MAX = 60

AVG_WINDOW_START_HOUR = 9
AVG_WINDOW_END_HOUR = 21


@dataclass
class WeatherDay:
    """A single day's weather forecast summary."""

    date: date
    high_temp_c: float
    low_temp_c: float
    avg_temp_9am_9pm_c: float
    condition: str
    rain_chance: str


@dataclass
class FoodItem:
    """A single quintessential food recommendation for a city."""

    name: str
    restaurant: str
    image_url: str = None


@dataclass
class BookItem:
    """A single quintessential book recommendation for a city."""

    title: str
    author: str
    description: str
    cover_url: str = None


def get_welcome_message(city: str) -> str:
    """Build the welcome message shown for a given city.

    Args:
        city: Name of the city the user wants recommendations for.

    Returns:
        A friendly welcome message referencing the city.
    """
    return f"Welcome to the Travel Discovery Tool! Let's explore {city}."


def _to_date(value) -> date:
    """Normalize a date-like value (str 'YYYY-MM-DD' or date) to a date."""
    if isinstance(value, date):
        return value
    return datetime.strptime(value, DATE_FORMAT).date()


def _rain_chance_from_probability(probability) -> str:
    """Bucket a precipitation probability percentage into Low/Medium/High."""
    if probability is None:
        return "Unknown"
    if probability < RAIN_CHANCE_LOW_MAX:
        return "Low"
    if probability <= RAIN_CHANCE_MEDIUM_MAX:
        return "Medium"
    return "High"


def _average_hourly_window(hourly_times, hourly_temps, target_date: date) -> float:
    """Average hourly temperatures for `target_date` between the configured
    9am-21pm window (inclusive), matching entries by their ISO timestamp.
    """
    window_temps = []
    for time_str, temp in zip(hourly_times, hourly_temps):
        timestamp = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        if timestamp.date() != target_date:
            continue
        if AVG_WINDOW_START_HOUR <= timestamp.hour <= AVG_WINDOW_END_HOUR:
            window_temps.append(temp)

    if not window_temps:
        return None
    return sum(window_temps) / len(window_temps)


def get_weekly_weather(city: str, start_date=None, end_date=None) -> list:
    """Get a daily weather forecast summary for a city.

    Args:
        city: Name of the city to look up.
        start_date: Optional inclusive start date ('YYYY-MM-DD' string or
            `datetime.date`). Defaults to today.
        end_date: Optional inclusive end date ('YYYY-MM-DD' string or
            `datetime.date`). Defaults to `start_date` + 6 days (a 7-day
            forecast).

    Returns:
        A list of `WeatherDay` objects, one per day in the requested range.

    Raises:
        ValueError: if the date range is invalid (start after end, or the
            range spans more days than the forecast provider supports).
        travel_agent.sources.weather.CityNotFoundError: if the city cannot
            be resolved to a location.
        travel_agent.sources.weather.WeatherLookupError: if the forecast
            request fails.
    """
    resolved_start = _to_date(start_date) if start_date is not None else date.today()
    resolved_end = (
        _to_date(end_date)
        if end_date is not None
        else resolved_start + timedelta(days=DEFAULT_FORECAST_DAYS - 1)
    )

    if resolved_start > resolved_end:
        raise ValueError(
            f"start_date ({resolved_start}) must not be after end_date ({resolved_end})."
        )

    span_days = (resolved_end - resolved_start).days + 1
    if span_days > MAX_FORECAST_SPAN_DAYS:
        raise ValueError(
            f"Date range spans {span_days} days, which exceeds the "
            f"maximum supported span of {MAX_FORECAST_SPAN_DAYS} days."
        )

    lat, lon, _resolved_name = weather_source.geocode_city(city)
    forecast = weather_source.fetch_forecast(
        lat, lon, resolved_start.strftime(DATE_FORMAT), resolved_end.strftime(DATE_FORMAT)
    )

    daily = forecast.get("daily", {})
    hourly = forecast.get("hourly", {})
    hourly_times = hourly.get("time", [])
    hourly_temps = hourly.get("temperature_2m", [])

    daily_dates = daily.get("time", [])
    daily_max = daily.get("temperature_2m_max", [])
    daily_min = daily.get("temperature_2m_min", [])
    daily_weathercode = daily.get("weathercode", [])
    daily_precip_prob = daily.get("precipitation_probability_max", [])

    results = []
    for i, day_str in enumerate(daily_dates):
        day = _to_date(day_str)
        results.append(
            WeatherDay(
                date=day,
                high_temp_c=daily_max[i],
                low_temp_c=daily_min[i],
                avg_temp_9am_9pm_c=_average_hourly_window(hourly_times, hourly_temps, day),
                condition=weather_source.describe_weather_code(daily_weathercode[i]),
                rain_chance=_rain_chance_from_probability(daily_precip_prob[i]),
            )
        )

    return results


def get_quintessential_foods(city: str, ignore_cache: bool = False) -> list:
    """Get up to 5 quintessential foods for a city, each with a recommended
    restaurant and a best-effort representative image.

    Results are cached (keyed by city + the relevant food preferences)
    so repeat requests reuse prior LLM output by default.

    Args:
        city: Name of the city to look up.
        ignore_cache: If True, skip the cache read and force a fresh LLM
            call, overwriting any existing cache entry with the result.

    Returns:
        A list of `FoodItem` objects (0-5 items). An empty list is
        returned if the LLM legitimately provides no usable
        recommendations, rather than raising.

    Raises:
        travel_agent.sources.llm.LLMLookupError: if the API key is
            missing, the request fails, or the response cannot be
            parsed/validated as expected.
    """
    prefs = preferences_module.load_preferences()
    key = cache_module.cache_key(
        "food",
        city=city,
        allergies=prefs.food.allergies,
        dietary_restrictions=prefs.food.dietary_restrictions,
        notes=prefs.food.notes,
    )

    if not ignore_cache:
        cached = cache_module.get_cached(key)
        if cached is not None:
            return [FoodItem(**item) for item in cached]

    raw_items = llm_source.generate_food_recommendations(city, preferences=prefs)
    raw_items = raw_items[:MAX_QUINTESSENTIAL_FOODS]

    foods = []
    for entry in raw_items:
        image_url = images_source.fetch_food_image(entry["food"])
        foods.append(
            FoodItem(
                name=entry["food"],
                restaurant=entry["restaurant"],
                image_url=image_url,
            )
        )

    cache_module.set_cached(key, [asdict(food) for food in foods])
    return foods


def get_quintessential_books(city: str, ignore_cache: bool = False) -> list:
    """Get up to 5 books meaningfully connected to a city, each with an
    author, short description, and a best-effort cover image.

    Results are cached (keyed by city + the relevant book preferences)
    so repeat requests reuse prior LLM output by default.

    Args:
        city: Name of the city to look up.
        ignore_cache: If True, skip the cache read and force a fresh LLM
            call, overwriting any existing cache entry with the result.

    Returns:
        A list of `BookItem` objects (0-5 items). An empty list is
        returned if the LLM legitimately provides no usable
        recommendations, rather than raising.

    Raises:
        travel_agent.sources.llm.LLMLookupError: if the API key is
            missing, the request fails, or the response cannot be
            parsed/validated as expected.
    """
    prefs = preferences_module.load_preferences()
    key = cache_module.cache_key(
        "books",
        city=city,
        favorite_genres=prefs.books.favorite_genres,
        favorite_authors=prefs.books.favorite_authors,
        notes=prefs.books.notes,
    )

    if not ignore_cache:
        cached = cache_module.get_cached(key)
        if cached is not None:
            return [BookItem(**item) for item in cached]

    raw_items = llm_source.generate_book_recommendations(city, preferences=prefs)
    raw_items = raw_items[:MAX_QUINTESSENTIAL_BOOKS]

    books = []
    for entry in raw_items:
        cover_url = covers_source.fetch_book_cover(entry["title"], entry["author"])
        books.append(
            BookItem(
                title=entry["title"],
                author=entry["author"],
                description=entry["description"],
                cover_url=cover_url,
            )
        )

    cache_module.set_cached(key, [asdict(book) for book in books])
    return books
