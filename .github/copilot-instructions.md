# Context for Copilot (read this first)

Hackathon: GDG Agentic AI Hackathon, University of Debrecen. Track: Autonomous Agents & Intelligent Systems.
Deadline is short: a working demo beats a complex idea. Keep code simple, every teammate must be able to explain it to judges.

## Project: Feed Ration Agent
Stored silage loses protein and dry matter when hot or damp. Farmers only learn from old lab tests, so they overfeed
expensive protein or lose milk. This app predicts the drift and an LLM agent rebalances the cheapest cow feed mix.

Flow: simulated silo sliders -> `apply_storage_drift` -> `optimize_ration` (scipy linprog) -> LLM agent explains and
writes a farmer mixing sheet + reorder alert.

The silo readings are SIMULATED. Label them "Simulated Silo Telemetry" in the UI. Never present them as live sensors.

## Layout
- `core/decay.py`: `apply_storage_drift(feeds, days, temp_c, moisture_pct) -> dict` (returns a NEW dict, never mutates). OWNED BY KHALIL. Do not edit.
- `core/optimizer.py`: `optimize_ration(feeds, targets) -> {"kg_dm": {...}, "kg_fresh": {...}, "cost_per_day": float, "feasible": bool}`. OWNED BY KHALIL. Do not edit.
- `data/feeds.json`: feeds + cow targets. Agri students own it. Values are placeholders until sourced.
- `app.py`: Streamlit dashboard, 3 columns (sliders / agent log / old vs new recipe). Middle column agent log is a TODO.
- `agent.py`: DOES NOT EXIST YET. This is the teammate's job.

## Status
`agent.py` is DONE (owned by Khalil). `run_agent(days, temp_c, moisture_pct)` returns `{"ok": bool, "log": list, "final": str}`.
Tools: `check_silo_drift`, `rebalance_ration`, `check_inventory`. The farmer note is the final LLM message (there is no
`draft_alert` tool, that is intended). The solver is the agent's calculator, so math never comes from the LLM.
Log entries: `{"type": "tool_call", "name"}`, `{"type": "tool_result", "name", "result": dict}`, `{"type": "final"}`.

## Teammate's task: ALL of app.py (not started)
1. "Run Nutrition Agent" button calling `run_agent(...)`; show a spinner while it runs.
2. Middle column: render `result["log"]` as readable steps (tool name, then key values of its result).
3. Show `result["final"]` as the farmer note; if `ok` is False show it as an error.
4. "Auto mode" toggle: re-run the agent when a slider changes.
5. Right column: old vs new recipe table, cost per cow and per herd (200 cows) per day, from the `rebalance_ration` result in the log.
6. Chart: silage crude protein baseline vs now, and a before/after cost bar.
7. Preset buttons: "Normal", "Hot summer silo", "Wet and spoiled" that set the sliders.
8. Label sliders "Simulated Silo Telemetry". Clean, demo-ready look (judges score what they see).
9. Take clear screenshots at code freeze for the pitch deck.

## Rules
- Python with `uv` (`uv add <pkg>`, `uv run ...`). No plain pip.
- API keys only in `.env` (never committed, never printed or hard-coded). `.env.example` lists names.
- Run app: `uv run streamlit run app.py`.
- Immutable style: return new objects, do not mutate inputs.
- Work on branch `agent-ui`, `git pull --rebase origin main` often, small commits (`feat:`, `fix:`).
- Before adding a library, say which one and why in one sentence.
- Keep a working demo at all times. If a change breaks it, revert first.
