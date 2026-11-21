"""Storage decay model. Rules come from data/feeds.json (silage_spoilage_rules), supplied by the agri team.

Each rule is a loss in percent per month, applied as a relative reduction (e.g. 15% of the crude protein per month).
"""
import json
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "feeds.json"
DAYS_PER_MONTH = 30
MAX_LOSS_FRACTION = 0.5  # safety cap: a nutrient never loses more than half its value
SPOILING_FEEDS = ("corn_silage",)


def _load_rules() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))["silage_spoilage_rules"]


def _monthly_losses(rules: dict, temp_c: float, moisture_pct: float) -> dict:
    """Percent lost per month for dry matter (dm), crude protein (cp) and energy (nel)."""
    normal = rules["normal_loss_per_month"]
    losses = {"dm": normal["dm_pct"], "cp": normal["cp_pct"], "nel": normal["nel_pct"]}
    if temp_c > rules["heat_trigger_c"]:
        heat = rules["heat_loss_per_month"]
        losses["dm"] += heat["dm_pct"]
        losses["nel"] += heat["nel_pct"]
    if temp_c > rules["maillard_protein_trigger_c"]:
        losses["cp"] += rules["heat_loss_per_month"]["cp_pct_above_42c"]
    if moisture_pct > rules["wet_trigger_moisture_pct"]:
        wet = rules["wet_loss_per_month"]
        losses["dm"] += wet["dm_pct"]
        losses["cp"] += wet["cp_pct"]
    return losses


def _remaining(loss_pct_per_month: float, months: float) -> float:
    return 1 - min(MAX_LOSS_FRACTION, loss_pct_per_month / 100 * months)


def apply_storage_drift(feeds: dict, days: int, temp_c: float, moisture_pct: float) -> dict:
    """Return a NEW feeds dict with silage dry matter, protein and energy degraded by heat/moisture over time."""
    losses = _monthly_losses(_load_rules(), temp_c, moisture_pct)
    months = days / DAYS_PER_MONTH
    result = {}
    for name, feed in feeds.items():
        if name not in SPOILING_FEEDS:
            result[name] = dict(feed)
            continue
        result[name] = {
            **feed,
            "dm_pct": feed["dm_pct"] * _remaining(losses["dm"], months),
            "cp_pct_dm": feed["cp_pct_dm"] * _remaining(losses["cp"], months),
            "nel_mj_per_kg_dm": feed["nel_mj_per_kg_dm"] * _remaining(losses["nel"], months),
        }
    return result
