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

## Teammate's task (agent.py + agent log in app.py)
Build a real agent loop with Gemini tool calling (`google-genai` SDK, key in env var `GOOGLE_API_KEY`).
The LLM must DECIDE which tools to call, not follow a fixed script. Tools wrapping existing code:
1. `check_silo_drift(days, temp_c, moisture_pct)`: drifted nutrients vs baseline.
2. `optimize_ration()`: new cheapest recipe (skip if drift is small).
3. `check_inventory()`: soybean meal stock vs new daily use (mock stock number is fine).
4. `draft_alert()`: farmer mixing sheet + reorder warning.
Show every tool call and result in the agent log column. If the optimizer returns `feasible: False`, the agent should
explain and suggest an action (e.g. buy fresh silage). Add an "Auto mode" toggle so the agent re-runs when sliders move.
The solver is the agent's calculator, so math never comes from the LLM.

## Rules
- Python with `uv` (`uv add <pkg>`, `uv run ...`). No plain pip.
- API keys only in `.env` (never committed, never printed or hard-coded). `.env.example` lists names.
- Run app: `uv run streamlit run app.py`.
- Immutable style: return new objects, do not mutate inputs.
- Work on branch `agent-ui`, `git pull --rebase origin main` often, small commits (`feat:`, `fix:`).
- Before adding a library, say which one and why in one sentence.
- Keep a working demo at all times. If a change breaks it, revert first.
