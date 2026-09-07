"""Data-fetching sources for the travel agent.

Each module in this package is responsible for fetching data from a single
external source (e.g. food recommendations, books set in a city, points of
interest). Keeping these isolated from the core application logic makes it
easy to add new sources or swap implementations without touching the rest
of the app.
"""
