"""Live ambient air temperature from Open-Meteo (free, no API key).

This is AIR temperature, not the temperature inside a silo. Label it that way in the UI.
"""
import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DEBRECEN_LAT, DEBRECEN_LON = 47.53, 21.63
REQUEST_TIMEOUT_SECONDS = 8


def get_ambient_temp_c(lat: float = DEBRECEN_LAT, lon: float = DEBRECEN_LON) -> float | None:
    """Return the current air temperature in C, or None if the service is unreachable."""
    try:
        response = httpx.get(
            OPEN_METEO_URL,
            params={"latitude": lat, "longitude": lon, "current": "temperature_2m"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return float(response.json()["current"]["temperature_2m"])
    except (httpx.HTTPError, KeyError, ValueError):
        return None
