"""Cheapest ration that meets dry matter, protein and energy targets (linear programming)."""
from scipy.optimize import linprog


def optimize_ration(feeds: dict, targets: dict) -> dict:
    """Return {"kg_dm": {...}, "kg_fresh": {...}, "cost_per_day": float, "feasible": bool}."""
    names = list(feeds)
    dm_total = targets["dm_kg"]
    cost = [feeds[n]["eur_per_kg_fresh"] / (feeds[n]["dm_pct"] / 100) for n in names]
    cp = [feeds[n]["cp_pct_dm"] / 100 for n in names]
    nel = [feeds[n]["nel_mj_per_kg_dm"] for n in names]

    res = linprog(
        c=cost,
        A_ub=[[-v for v in cp], [-v for v in nel]],
        b_ub=[-targets["cp_fraction_min"] * dm_total, -targets["nel_mj_per_kg_dm_min"] * dm_total],
        A_eq=[[1] * len(names)],
        b_eq=[dm_total],
        bounds=[(feeds[n]["min_dm_kg"], feeds[n]["max_dm_kg"]) for n in names],
    )
    if not res.success:
        return {"kg_dm": {}, "kg_fresh": {}, "cost_per_day": 0.0, "feasible": False}

    kg_dm = {n: round(float(x), 2) for n, x in zip(names, res.x)}
    kg_fresh = {n: round(kg_dm[n] / (feeds[n]["dm_pct"] / 100), 2) for n in names}
    return {"kg_dm": kg_dm, "kg_fresh": kg_fresh, "cost_per_day": round(float(res.fun), 2), "feasible": True}
