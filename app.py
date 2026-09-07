"""Command-line entry point for the Travel Discovery Tool.

Usage:
    python app.py "San Francisco"
    python app.py "San Francisco" --weather
    python app.py "San Francisco" --weather --start-date 2026-09-10 --end-date 2026-09-12
    python app.py "Tokyo" --food

This is a temporary interface. Once the core logic is fleshed out, a web
layer (Flask/FastAPI) will be added on top of the same `travel_agent`
package without needing to restructure this project.
"""

import argparse
import sys

from dotenv import load_dotenv

from travel_agent.core import get_quintessential_foods, get_weekly_weather, get_welcome_message
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
    parser.add_argument("city", help="Name of the city to explore")
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
    return parser.parse_args(argv)


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


def print_food(city: str) -> int:
    """Print up to 5 quintessential foods for `city`. Returns a process exit code."""
    try:
        foods = get_quintessential_foods(city)
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


def main(argv=None):
    args = parse_args(argv)
    print(get_welcome_message(args.city))

    exit_code = 0
    if args.weather:
        exit_code = print_weather(args.city, args.start_date, args.end_date) or exit_code
    if args.food:
        exit_code = print_food(args.city) or exit_code
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
