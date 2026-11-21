# Feed Ration Agent

Agentic AI Hackathon, University of Debrecen. Track: Autonomous Agents & Intelligent Systems.

An AI agent that rebalances cow feed recipes when stored silage loses nutrients. Silo readings are
**simulated** ("Simulated Silo Telemetry"); the optimizer is a real linear solver.

## Run
```bash
uv sync
cp .env.example .env   # add GOOGLE_API_KEY
uv run streamlit run app.py
```

## AI tools used
- Claude Code (scaffolding, code assistance)
- Gemini API (agent reasoning, tool calling)
- GitHub Copilot (code assistance)

## Sensor-ready input
The pipeline takes three numbers: storage days, silo temperature and moisture. In the demo they come from
sliders ("Simulated Silo Telemetry"). A real silo probe would send the same JSON, validated by
`core/telemetry.py`:

```json
{"days": 45, "temp_c": 40, "moisture_pct": 72}
```

No hardware is connected in this demo. The optional "live air temperature" button uses Open-Meteo
(ambient air in Debrecen, not silo temperature).

## Data sources
Feed values and spoilage rules were supplied by the agriculture team. Sources are listed in `data/feeds.json`
(Feedipedia, DLG tables, NRC 2001 / NASEM 2021, Penn State and UW-Madison Extension, Agroinform.hu, AKI PAIR).
The decay model is a simplified rule-based model, not a validated simulation.

## Reliability
Gemini's free tier is rate-limited, so `agent.py` never depends on a single call: it tries several Gemini models
(and an optional second key, `GOOGLE_API_KEY_2`), then replays the last good run for the same inputs, then writes a
templated offline note. The dashboard shows which one was used (Live Gemini / Replay / Offline). The soybean meal
stock and herd size are demo values.

## Tests
```bash
uv run pytest
```
Covers the decay model, the ration optimizer and the telemetry validation.
