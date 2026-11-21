"""Feed ration agent. Gemini decides which tools to call; the solver does all the math.

Run a quick test:  uv run python agent.py
Use from the app:  from agent import run_agent; result = run_agent(days, temp_c, moisture_pct)
"""
import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

from core.decay import apply_storage_drift
from core.optimizer import optimize_ration

ROOT = Path(__file__).parent
MAX_STEPS = 6
ATTEMPTS_PER_MODEL = 2
RETRY_WAIT_SECONDS = 2
HERD_SIZE = 200
STOCK_KG = {"soybean_meal": 1500.0}  # mock inventory for the demo
SMALL_DRIFT_CP_POINTS = 0.3

SYSTEM_PROMPT = f"""You are a dairy feed nutrition agent for a farm with {HERD_SIZE} cows.
Stored corn silage can lose protein and dry matter when hot or damp. Silo readings are SIMULATED telemetry.
Work step by step with your tools. Never invent numbers: every number must come from a tool result.
1. Call check_silo_drift first.
2. If the protein drop is small, say no change is needed and stop. Otherwise call rebalance_ration.
3. If rebalance_ration returns feasible=false, explain why and recommend an action (e.g. buy fresh silage).
4. After a rebalance, call check_inventory to see if soybean meal will run short.
Finish with a short plain-language farmer note: why the silage changed, the new mix in kg fresh per cow per day,
the cost change in EUR/day, and any reorder warning."""


def _load_env() -> None:
    """Read .env into os.environ (no extra library). Never prints values."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


_load_env()
FALLBACK_MODELS = ("gemini-3.7-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash")
MODELS = (os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"), *FALLBACK_MODELS)


def _load_data() -> tuple[dict, dict]:
    data = json.loads((ROOT / "data" / "feeds.json").read_text())
    return data["feeds"], data["targets"]


def _build_tools(days: int, temp_c: float, moisture_pct: float) -> dict:
    """Tools take no arguments, so the LLM can never pass wrong silo numbers."""
    base_feeds, targets = _load_data()
    drifted = apply_storage_drift(base_feeds, days, temp_c, moisture_pct)
    cache: dict = {}

    def check_silo_drift() -> dict:
        """Compare corn silage protein and dry matter now vs the lab baseline."""
        before, after = base_feeds["corn_silage"], drifted["corn_silage"]
        return {
            "simulated_conditions": {"days": days, "temp_c": temp_c, "moisture_pct": moisture_pct},
            "silage_cp_pct_dm": {"before": before["cp_pct_dm"], "now": round(after["cp_pct_dm"], 2)},
            "silage_dm_pct": {"before": before["dm_pct"], "now": round(after["dm_pct"], 2)},
            "cp_drop_points": round(before["cp_pct_dm"] - after["cp_pct_dm"], 2),
            "drift_is_small": before["cp_pct_dm"] - after["cp_pct_dm"] < SMALL_DRIFT_CP_POINTS,
        }

    def rebalance_ration() -> dict:
        """Find the cheapest recipe (kg per cow per day) that still meets protein and energy targets."""
        old = optimize_ration(base_feeds, targets)
        new = optimize_ration(drifted, targets)
        cache["new"] = new
        if not new["feasible"]:
            return {"feasible": False, "reason": "targets cannot be met with current feeds"}
        return {
            "feasible": True,
            "old_recipe_kg_fresh": old["kg_fresh"],
            "new_recipe_kg_fresh": new["kg_fresh"],
            "old_cost_eur_per_cow_day": old["cost_per_day"],
            "new_cost_eur_per_cow_day": new["cost_per_day"],
            "extra_cost_eur_per_day_herd": round((new["cost_per_day"] - old["cost_per_day"]) * HERD_SIZE, 2),
        }

    def check_inventory() -> dict:
        """Check whether soybean meal stock lasts with the new recipe. Call after rebalance_ration."""
        new = cache.get("new")
        if not new:
            return {"error": "run rebalance_ration first"}
        daily_use = new["kg_fresh"]["soybean_meal"] * HERD_SIZE
        stock = STOCK_KG["soybean_meal"]
        return {
            "soybean_meal_stock_kg": stock,
            "daily_use_kg_herd": round(daily_use, 1),
            "days_left": round(stock / daily_use, 1) if daily_use else None,
            "reorder_needed": daily_use > 0 and stock / daily_use < 7,
        }

    return {f.__name__: f for f in (check_silo_drift, rebalance_ration, check_inventory)}


def _execute_calls(calls, tools: dict, log: list) -> list:
    """Run each requested tool, append to the log, return function-response parts."""
    parts = []
    for call in calls:
        log.append({"type": "tool_call", "name": call.name})
        tool = tools.get(call.name)
        result = tool() if tool else {"error": f"unknown tool {call.name}"}
        log.append({"type": "tool_result", "name": call.name, "result": result})
        parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
    return parts


def _generate_with_retry(client, contents, config):
    """On Gemini overload (503), try each model in MODELS a couple of times, then move to the next."""
    last_error = None
    for model in MODELS:
        for attempt in range(ATTEMPTS_PER_MODEL):
            try:
                return client.models.generate_content(model=model, contents=contents, config=config)
            except errors.ServerError as error:
                last_error = error
                print(f"{model} busy (503). Attempt {attempt + 1}/{ATTEMPTS_PER_MODEL}.", flush=True)
                time.sleep(RETRY_WAIT_SECONDS)
    raise last_error


def run_agent(days: int, temp_c: float, moisture_pct: float) -> dict:
    """Run the agent loop. Returns {"ok": bool, "log": [...], "final": str}."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"ok": False, "log": [], "final": "GOOGLE_API_KEY missing. Add it to .env."}

    tools = _build_tools(days, temp_c, moisture_pct)
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=list(tools.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part(text="Check the silo and update the ration if needed.")])]
    log: list = []

    try:
        for _ in range(MAX_STEPS):
            response = _generate_with_retry(client, contents, config)
            calls = response.function_calls or []
            if not calls:
                log.append({"type": "final"})
                return {"ok": True, "log": log, "final": response.text or ""}
            contents.append(response.candidates[0].content)
            contents.append(types.Content(role="user", parts=_execute_calls(calls, tools, log)))
    except Exception as error:  # show a clear message in the UI instead of crashing the demo
        return {"ok": False, "log": log, "final": f"Agent error: {type(error).__name__}: {error}"}

    return {"ok": False, "log": log, "final": "Agent hit the step limit without finishing."}


if __name__ == "__main__":
    out = run_agent(days=45, temp_c=40, moisture_pct=72)
    for entry in out["log"]:
        print(entry)
    print("\n" + out["final"])
