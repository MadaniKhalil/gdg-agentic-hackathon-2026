# Feed Ration Agent

**GDG Debrecen Agentic AI Hackathon 2026 (University of Debrecen)**

**Track:** Autonomous Agents & Intelligent Systems

An AI agent for dairy farmers that predicts nutrient loss in stored corn silage from silo conditions (days stored, temperature, moisture), then automatically recalculates the cheapest Total Mixed Ration (TMR) that still meets a cow's daily needs.

> **Transparency & Known Limits:** The current outdoor air temperature in Debrecen can be loaded live from the **Open-Meteo API** (ambient air, not silo temperature), while silo temperature, moisture, and storage duration inputs are **Simulated Silo Telemetry** (controlled via dashboard sliders, not physical farm hardware). Warehouse soybean meal stock ($1{,}500\text{ kg}$) is a mock inventory value, the spoilage engine is a simplified rule-based model applied to corn silage only (not a lab-validated biological simulation), and the ration optimizer is a **real linear-programming solver** (`scipy.optimize.linprog`).

## The Problem

Feed accounts for $50\%$–$70\%$ of daily operating costs on a dairy farm. Corn silage stored in a hot or wet bunker silo quietly loses dry matter, crude protein, and energy. Because farmers usually rely on lab tests done months earlier, they either lose milk production or waste money overfeeding expensive protein supplements like soybean meal.

## How It Works

1. **Simulated Silo Telemetry (`app.py`):** A Streamlit dashboard with simulated silo telemetry sliders (storage duration in days, silo temperature, and silage moisture) and three presets. A button can load the live outdoor air temperature for Debrecen from the **Open-Meteo API** (clamped to the slider range, and labelled as air temperature, not silo temperature).

2. **Silage Spoilage Model (`core/decay.py`):** Reduces corn silage's Dry Matter (DM), Crude Protein (CP), and Net Energy for Lactation ($NE_L$) as a relative percentage loss per month of storage (capped at $50\%$ max loss):

   * **Baseline (always):** $-1.0\%$ DM/month

   * **Heat ($>35^\circ\text{C}$):** extra $-4.5\%$ DM/month and $-6.0\%$ $NE_L$/month (aerobic spoilage)

   * **Severe Heat ($>42^\circ\text{C}$):** extra $-15.0\%$ CP/month (Maillard heat damage)

   * **Wet Storage ($>70\%$ moisture):** extra $-6.0\%$ DM/month and $-17.5\%$ CP/month (wet/clostridial spoilage)

3. **Constrained Linear Ration Optimizer (`core/optimizer.py`):** Uses `scipy.optimize.linprog` to calculate the lowest-cost combination of 5 feeds that satisfies exact cow targets and safe daily intake limits. Cost per kg of dry matter is calculated as fresh price divided by $\text{DM}\%$.

4. **Autonomous AI Agent (`agent.py`):** Powered by the **Google Gemini API**, the agent decides which tools to call—`check_silo_drift`, `rebalance_ration`, and `check_inventory`—and writes a plain-language action note for the farmer. **The LLM never performs the math; the linear solver is its calculator.**

   * If drift is minimal, the agent reports *"no change needed."*

   * If spoilage is too severe for a safe diet, the agent flags that no feasible ration exists.

   * **Resilient Fallbacks:** If the primary Gemini model is overloaded or rate-limited, the app automatically falls back to backup Gemini models $\rightarrow$ replays the last cached result for identical inputs $\rightarrow$ or generates an offline templated farmer note.

## Demo Scenarios (200-Cow Dairy Herd)

* **Normal Storage ($0$ days, $20^\circ\text{C}$, $60\%$ moisture):** Minimal drift detected; agent advises **"no change needed."**

* **Heat & Wet Spoilage ($45$ days, $40^\circ\text{C}$, $72\%$ moisture):**

  * Corn silage crude protein drops from $7.8\%$ to $\approx 5.75\%$ of DM, and energy drops by $\approx 9\%$.

  * Ration cost rises from $\approx \text{€}6.12$ to $\approx \text{€}6.60$ per cow/day ($\approx +\text{€}96/\text{day}$ across $200$ cows) to maintain milk output.

  * Increased soybean meal demand reduces the mock $1{,}500\text{ kg}$ warehouse stock to $\approx 3$ days remaining, triggering an automatic reorder warning.

## Project Structure

```text
gdg-agentic-hackathon-2026/
├── core/
│   ├── decay.py        # Rule-based corn silage nutrient decay model
│   ├── optimizer.py    # Linear programming TMR solver (scipy linprog)
│   ├── telemetry.py    # Validated "sensor-ready" JSON input for silo readings
│   └── weather.py      # Live air temperature from Open-Meteo
├── data/
│   └── feeds.json      # Feed nutritional composition, limits, prices & spoilage rules
├── tests/              # Unit tests (decay, optimizer, telemetry)
├── agent.py            # Google Gemini tool-calling agent & fallback handler
├── app.py              # Interactive Streamlit dashboard (Simulated Telemetry + Open-Meteo API)
├── pyproject.toml      # Project metadata and dependencies
├── uv.lock             # Locked Python dependency versions
└── .env.example        # Environment variable template
```

## How to Run Locally

### Prerequisites

* Python 3.10+

* [`uv`](https://docs.astral.sh/uv/) package manager

* A Google Gemini API key *(Open-Meteo requires no API key)*

### Setup & Launch

1. **Clone the repository:**

   ```bash
   git clone https://github.com/MadaniKhalil/gdg-agentic-hackathon-2026.git
   cd gdg-agentic-hackathon-2026
   ```

2. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Open `.env` and add your `GOOGLE_API_KEY` (a free key from aistudio.google.com/apikey). Optionally add a second key from another Google project as `GOOGLE_API_KEY_2`; it is used when the first runs out of free quota.

3. **Install dependencies:**

   ```bash
   uv sync
   ```

4. **Launch the dashboard:**

   ```bash
   uv run streamlit run app.py
   ```

5. **Run the tests (optional):**

   ```bash
   uv run pytest
   ```

## Sensor-Ready Input

The pipeline needs three numbers: storage days, silo temperature and moisture. In the demo they come from sliders. A real silo probe would send the same JSON, validated by `core/telemetry.py`:

```json
{"days": 45, "temp_c": 40, "moisture_pct": 72}
```

No hardware is connected in this demo; this is the documented interface a probe would plug into.

## Agronomic Baseline & Open Data Sources

### Reference Dairy Cow Profile

* **Animal:** $\approx 650\text{ kg}$ lactating Holstein producing $\approx 30\text{ L}$ milk/day

* **Daily Targets:** $22.0\text{ kg}$ Dry Matter Intake (DMI), $\ge 15.8\%$ Crude Protein (CP of DM), $\ge 6.5\text{ MJ/kg DM}$ Net Energy for Lactation ($NE_L$)

### Feed Composition, Hungarian Prices & Safe Intake Limits

| Feed | DM (%) | CP (% DM) | $NE_L$ (MJ/kg DM) | Price (€/kg fresh) | Safe Daily Bounds (kg DM) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Corn Silage** | $33.0\%$ | $7.8\%$ | $6.5$ | €0.09 | $0.0 - 12.5$ |
| **Alfalfa Hay** | $88.0\%$ | $17.5\%$ | $5.4$ | €0.20 | $2.0 - 7.5$ |
| **Soybean Meal** | $89.0\%$ | $51.5\%$ | $8.5$ | €0.45 | $0.0 - 3.5$ |
| **Barley Grain (rolled)** | $88.0\%$ | $12.0\%$ | $8.1$ | €0.18 | $0.0 - 5.5$ |
| **Dairy Mineral Mix** | $96.0\%$ | $0.0\%$ | $0.0$ | €1.80 | $0.25 - 0.45$ |

### Scientific & Market References

* **Feed Composition & Cow Requirements:** Feedipedia (INRAE, CIRAD, AFZ & FAO); DLG *Futterwerttabellen Wiederkäuer*; NRC (2001) / NASEM (2021) *Nutrient Requirements of Dairy Cattle*.

* **Silage Spoilage Thresholds:** Penn State Extension (*Silage Fermentation, Heating, and Aerobic Spoilage*); University of Wisconsin–Madison Extension (*Silage Moisture and Clostridial Fermentation*).

* **Hungarian Feed Prices (2026 Fresh Basis):** AKI PÁIR (Institute of Agricultural Economics, Hungary — Week 43, 2026) and Agroinform.hu local farm-gate listings (converted at $\approx 368\text{ HUF/EUR}$).

## Tools, APIs & AI Assistants Used

In accordance with hackathon transparency rules, all external tools, APIs, and AI assistants used during this event are listed below:

* **Core Stack:** Python, `uv`, SciPy (`scipy.optimize.linprog`), Streamlit

* **External APIs:**
  * **Google Gemini API** (tool calling in `agent.py`)
  * **Open-Meteo API** (current outdoor air temperature for Debrecen; free and requires no API key)

* **AI Assistants Used During Development:**

  * **Claude (Claude Code):** Code scaffolding, solver/agent implementation, tests, and debugging

  * **GitHub Copilot:** Streamlit dashboard implementation

  * **Gemini:** Open-source agronomic data verification, architecture planning, and documentation drafting

* **Starter Kits / Templates:** None — built from scratch during the hackathon

## Next Steps

* Replace the simulated silo telemetry sliders with live bunker IoT temperature and moisture probes.
* Connect real farm feed-mixer wagon software and live warehouse weigh-scale inventory feeds.

## Team

* **Nurmanbet Askerbekov** — Agricultural Engineering (Dairy Nutrition Modeling, Domain Validation, Documentation)

* **Mohamed Ouroufi** — Agricultural Engineering (Agronomy Validation, Farm Impact & Presentation)

* **Madani Khalil** — Computer Science (Backend Architecture, Linear Solver, Gemini Tool-Calling Agent)

* **Saad Ali** — Computer Science (Frontend Dashboard, Pitch Deck & Engineering Support)