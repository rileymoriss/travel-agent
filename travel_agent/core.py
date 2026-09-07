"""Core application logic for the travel discovery tool.

This module is the entry point for interface-agnostic logic. Both the
current CLI (app.py) and any future web layer should call into functions
defined here, rather than duplicating logic in the interface layer.
"""


def get_welcome_message(city: str) -> str:
    """Build the welcome message shown for a given city.

    Args:
        city: Name of the city the user wants recommendations for.

    Returns:
        A friendly welcome message referencing the city.
    """
    return f"Welcome to the Travel Discovery Tool! Let's explore {city}."
