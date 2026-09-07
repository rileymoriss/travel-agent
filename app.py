"""Command-line entry point for the Travel Discovery Tool.

Usage:
    python app.py "San Francisco"

This is a temporary interface. Once the core logic is fleshed out, a web
layer (Flask/FastAPI) will be added on top of the same `travel_agent`
package without needing to restructure this project.
"""

import argparse
import sys

from travel_agent.core import get_welcome_message


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Get personalized travel recommendations for a city."
    )
    parser.add_argument("city", help="Name of the city to explore")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print(get_welcome_message(args.city))


if __name__ == "__main__":
    main(sys.argv[1:])
