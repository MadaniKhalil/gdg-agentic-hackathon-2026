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
