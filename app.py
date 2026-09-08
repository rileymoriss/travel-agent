"""Command-line entry point for the Travel Discovery Tool.

Usage:
    python app.py "San Francisco"
    python app.py "San Francisco" --weather
    python app.py "San Francisco" --weather --start-date 2026-09-10 --end-date 2026-09-12
    python app.py "Tokyo" --food
    python app.py "Dublin" --books
    python app.py "Tokyo" --food --ignore-cache
    python app.py --clear-cache

This is a temporary interface. Once the core logic is fleshed out, a web
layer (Flask/FastAPI) will be added on top of the same `travel_agent`
package without needing to restructure this project.
"""

import argparse
import sys

from dotenv import load_dotenv

from travel_agent.cache import clear_cache
from travel_agent.core import (
    get_quintessential_books,
    get_quintessential_foods,
    get_weekly_weather,
    get_welcome_message,
)
from travel_agent.sources.llm import LLMLookupError
from travel_agent.sources.weather import CityNotFoundError, WeatherLookupError

# Load .env as early as possible so ANTHROPIC_API_KEY (read lazily by
# travel_agent.sources.llm at call time) is available in os.environ
# before any command is executed.
load_dotenv()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Get personalized travel recommendations for a city."
    )
    parser.add_argument(
        "city",
        nargs="?",
        help="Name of the city to explore (not required with --clear-cache)",
    )
    parser.add_argument(
        "--weather",
        action="store_true",
        help="Show a daily weather forecast for the city",
    )
    parser.add_argument(
        "--start-date",
        metavar="YYYY-MM-DD",
        help="Inclusive start date for the weather forecast (defaults to today)",
    )
    parser.add_argument(
        "--end-date",
        metavar="YYYY-MM-DD",
        help="Inclusive end date for the weather forecast (defaults to 7 days from start)",
    )
    parser.add_argument(
        "--food",
        action="store_true",
        help="Show up to 5 quintessential foods for the city, with a "
        "recommended restaurant and image for each (requires "
        "ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--books",
        action="store_true",
        help="Show up to 5 books connected to the city, with author, "
        "description, and cover image for each (requires "
        "ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Force a fresh LLM call for --food/--books instead of "
        "reusing a cached result, overwriting the cache with the new result",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete all cached LLM results and exit immediately "
        "(no city or other flags are processed)",
    )

    args = parser.parse_args(argv)
    if not args.clear_cache and not args.city:
        parser.error("the following arguments are required: city")
    return args


def print_weather(city: str, start_date=None, end_date=None) -> int:
    """Print a per-day weather forecast for `city`. Returns a process exit code."""
    try:
        forecast_days = get_weekly_weather(city, start_date, end_date)
    except ValueError as exc:
        print(f"Invalid date range: {exc}")
        return 1
    except CityNotFoundError as exc:
        print(f"Could not find that city: {exc}")
        return 1
    except WeatherLookupError as exc:
        print(f"Could not fetch weather: {exc}")
        return 1

    print(f"\nWeather forecast for {city}:")
    for day in forecast_days:
        avg_temp = (
            round(day.avg_temp_9am_9pm_c, 1)
            if day.avg_temp_9am_9pm_c is not None
            else "N/A"
        )
        print(
            f"\n{day.date.isoformat()}\n"
            f"  High/Low: {round(day.high_temp_c, 1)}\u00b0C / {round(day.low_temp_c, 1)}\u00b0C\n"
            f"  Avg 9am-9pm: {avg_temp}\u00b0C\n"
            f"  Condition: {day.condition}\n"
            f"  Chance of rain: {day.rain_chance}"
        )
    return 0


def print_food(city: str, ignore_cache: bool = False) -> int:
    """Print up to 5 quintessential foods for `city`. Returns a process exit code."""
    try:
        foods = get_quintessential_foods(city, ignore_cache=ignore_cache)
    except LLMLookupError as exc:
        print(f"Could not get food recommendations: {exc}")
        return 1

    if not foods:
        print(f"\nNo food recommendations available for {city}.")
        return 0

    print(f"\nQuintessential foods in {city}:")
    for i, food in enumerate(foods, start=1):
        image_line = food.image_url if food.image_url else "N/A"
        print(
            f"\n{i}. {food.name}\n"
            f"   Restaurant: {food.restaurant}\n"
            f"   Image: {image_line}"
        )
    return 0


def print_books(city: str, ignore_cache: bool = False) -> int:
    """Print up to 5 quintessential books for `city`. Returns a process exit code."""
    try:
        books = get_quintessential_books(city, ignore_cache=ignore_cache)
    except LLMLookupError as exc:
        print(f"Could not get book recommendations: {exc}")
        return 1

    if not books:
        print(f"\nNo book recommendations available for {city}.")
        return 0

    print(f"\nQuintessential books connected to {city}:")
    for i, book in enumerate(books, start=1):
        cover_line = book.cover_url if book.cover_url else "N/A"
        print(
            f"\n{i}. {book.title} by {book.author}\n"
            f"   {book.description}\n"
            f"   Cover: {cover_line}"
        )
    return 0


def main(argv=None):
    args = parse_args(argv)

    if args.clear_cache:
        removed = clear_cache()
        print(f"Cleared {removed} cached file(s).")
        return 0

    print(get_welcome_message(args.city))

    exit_code = 0
    if args.weather:
        exit_code = print_weather(args.city, args.start_date, args.end_date) or exit_code
    if args.food:
        exit_code = print_food(args.city, ignore_cache=args.ignore_cache) or exit_code
    if args.books:
        exit_code = print_books(args.city, ignore_cache=args.ignore_cache) or exit_code
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
