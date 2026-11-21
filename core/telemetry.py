"""Sensor-ready input: one validated format for silo readings.

A real silo probe (or a logger export) would send exactly this JSON:
    {"days": 45, "temp_c": 40, "moisture_pct": 72}
The sliders in the demo produce the same three numbers, so the rest of the pipeline is identical.
"""
import json

LIMITS = {"days": (0, 365), "temp_c": (-20, 80), "moisture_pct": (0, 100)}


def parse_telemetry(raw: str | dict) -> dict:
    """Return {"days": int, "temp_c": float, "moisture_pct": float}, or raise ValueError with a clear message."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as error:
        raise ValueError(f"Not valid JSON: {error.msg}") from error
    if not isinstance(data, dict):
        raise ValueError("Telemetry must be a JSON object")

    values = {}
    for field, (low, high) in LIMITS.items():
        if field not in data:
            raise ValueError(f"Missing field: {field}")
        try:
            value = float(data[field])
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a number") from None
        if not low <= value <= high:
            raise ValueError(f"{field} must be between {low} and {high}")
        values[field] = value
    return {"days": int(values["days"]), "temp_c": values["temp_c"], "moisture_pct": values["moisture_pct"]}
