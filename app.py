"""Command-line entry point for the Travel Discovery Tool.

Usage:
    python app.py "San Francisco"
    python app.py "San Francisco" --weather
    python app.py "San Francisco" --weather --start-date 2026-09-10 --end-date 2026-09-12

This is a temporary interface. Once the core logic is fleshed out, a web
layer (Flask/FastAPI) will be added on top of the same `travel_agent`
package without needing to restructure this project.
"""

import argparse
import sys

from travel_agent.core import get_weekly_weather, get_welcome_message
from travel_agent.sources.weather import CityNotFoundError, WeatherLookupError


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


def main(argv=None):
    args = parse_args(argv)
    print(get_welcome_message(args.city))

    if args.weather:
        return print_weather(args.city, args.start_date, args.end_date)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
