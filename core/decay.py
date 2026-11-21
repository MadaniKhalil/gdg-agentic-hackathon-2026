"""Storage decay model. PLACEHOLDER formulas: agri students must validate and cite."""

HEAT_THRESHOLD_C = 35.0
WET_THRESHOLD_PCT = 68.0
MAX_DM_LOSS_PCT = 15.0
CP_LOSS_POINTS_PER_STRESS_MONTH = 1.8
DM_LOSS_PCT_PER_STRESS_MONTH = 4.0
SPOILING_FEEDS = ("corn_silage",)


def apply_storage_drift(feeds: dict, days: int, temp_c: float, moisture_pct: float) -> dict:
    """Return a NEW feeds dict with silage nutrients degraded by heat/moisture over time."""
    stress = max(0.0, temp_c - HEAT_THRESHOLD_C) / 10 + max(0.0, moisture_pct - WET_THRESHOLD_PCT) / 10
    months = days / 30
    result = {}
    for name, feed in feeds.items():
        if name not in SPOILING_FEEDS:
            result[name] = dict(feed)
            continue
        dm_loss = min(MAX_DM_LOSS_PCT, DM_LOSS_PCT_PER_STRESS_MONTH * stress * months)
        cp_loss = CP_LOSS_POINTS_PER_STRESS_MONTH * stress * months
        result[name] = {
            **feed,
            "dm_pct": max(0.0, feed["dm_pct"] - dm_loss),
            "cp_pct_dm": max(0.0, feed["cp_pct_dm"] - cp_loss),
        }
    return result
