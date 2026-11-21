"""Streamlit dashboard. Run: uv run streamlit run app.py"""
import json
from pathlib import Path

import streamlit as st

from agent import HERD_SIZE, run_agent
from core.decay import apply_storage_drift


def render_values(values, indent=0):
    for key, value in values.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(value, dict):
            st.markdown(f"{'  ' * indent}- **{label}**")
            render_values(value, indent + 1)
        else:
            st.markdown(f"{'  ' * indent}- **{label}:** {value}")


def get_ration_result(result):
    if not result:
        return None
    return next(
        (
            step.get("result", {})
            for step in result.get("log", [])
            if step.get("type") == "tool_result" and step.get("name") == "rebalance_ration"
        ),
        None,
    )


st.set_page_config(page_title="Feed Ration Agent", page_icon="🐄", layout="wide")
st.markdown(
    """<style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {background: #f5f8f3; padding: 1rem; border-radius: 0.6rem;}
    </style>""",
    unsafe_allow_html=True,
)

data = json.loads((Path(__file__).parent / "data" / "feeds.json").read_text())
base_feeds, targets = data["feeds"], data["targets"]

st.title("Feed Ration Agent")
st.caption("Silage monitoring and least-cost ration recommendations")
left, mid, right = st.columns([1, 1.15, 1.35], gap="large")

with left:
    st.subheader("Simulated Silo Telemetry")
    st.caption("Demo inputs only — these are not live sensor readings.")
    for key, default in (("storage_days", 0), ("silo_temp", 20), ("moisture", 60)):
        st.session_state.setdefault(key, default)

    presets = st.columns(3)
    if presets[0].button("Normal", width="stretch"):
        st.session_state["storage_days"] = 0
        st.session_state["silo_temp"] = 20
        st.session_state["moisture"] = 60
    if presets[1].button("Hot summer silo", width="stretch"):
        st.session_state["storage_days"] = 45
        st.session_state["silo_temp"] = 44
        st.session_state["moisture"] = 60
    if presets[2].button("Wet and spoiled", width="stretch"):
        st.session_state["storage_days"] = 45
        st.session_state["silo_temp"] = 30
        st.session_state["moisture"] = 74

    days = st.slider("Storage days", 0, 60, key="storage_days")
    temp = st.slider("Silo temp (°C)", 15, 45, key="silo_temp")
    moisture = st.slider("Moisture (%)", 50, 75, key="moisture")
    auto_mode = st.toggle("Auto mode", value=False)
    run_clicked = st.button("Run Nutrition Agent", type="primary", width="stretch")

drifted = apply_storage_drift(base_feeds, days, temp, moisture)
baseline_cp = base_feeds["corn_silage"]["cp_pct_dm"]
now_cp = drifted["corn_silage"]["cp_pct_dm"]
telemetry = (days, temp, moisture)
previous_telemetry = st.session_state.get("last_telemetry")
telemetry_changed = previous_telemetry is not None and telemetry != previous_telemetry
auto_run = auto_mode and telemetry_changed

if run_clicked or auto_run:
    with st.spinner("Nutrition agent is checking the silo and ration..."):
        st.session_state["agent_result"] = run_agent(days, temp, moisture)
elif telemetry_changed:
    st.session_state.pop("agent_result", None)
st.session_state["last_telemetry"] = telemetry

result = st.session_state.get("agent_result")
ration_result = get_ration_result(result)

with mid:
    st.subheader("Agent log")
    st.caption("Silage crude protein (% dry matter): baseline vs current")
    st.bar_chart({"Baseline": [baseline_cp], "Current": [now_cp]}, horizontal=True)
    st.caption(f"{baseline_cp:.1f}% baseline → {now_cp:.1f}% current")

    if result:
        mode, color = {
            "gemini": ("Live Gemini", "green"),
            "replay": ("Replay", "orange"),
            "offline": ("Offline", "gray"),
        }.get(result.get("mode"), ("Unknown mode", "gray"))
        st.badge(mode, color=color)
        for step in result.get("log", []):
            name = step.get("name", "Agent step")
            if step.get("type") == "tool_call":
                st.markdown(f"**Calling `{name}`**")
            elif step.get("type") == "tool_result":
                st.markdown(f"**`{name}` result**")
                details = step.get("result", {})
                if isinstance(details, dict):
                    render_values(details)
                else:
                    st.write(details)
        st.subheader("Farmer note")
        if result.get("ok"):
            st.success(result.get("final") or "Agent completed without a farmer note.")
        else:
            st.error(result.get("final") or "The nutrition agent could not complete.")
    else:
        st.info("Select a silo preset or adjust the telemetry, then run the agent.")

with right:
    st.subheader("Old vs new recipe")
    st.caption("kg fresh feed per cow per day")
    if not result:
        st.info("Run the agent to compare the old and adjusted ration.")
    elif ration_result is None:
        st.info("The agent did not request a ration adjustment for these conditions.")
    elif ration_result.get("feasible") is False:
        st.error(ration_result.get("reason", "No feasible adjusted ration."))
    elif all(
        key in ration_result
        for key in (
            "old_recipe_kg_fresh",
            "new_recipe_kg_fresh",
            "old_cost_eur_per_cow_day",
            "new_cost_eur_per_cow_day",
        )
    ):
        old_recipe = ration_result["old_recipe_kg_fresh"]
        new_recipe = ration_result["new_recipe_kg_fresh"]
        rows = [
            {
                "Feed": name.replace("_", " ").title(),
                "Old (kg)": old_kg,
                "Adjusted (kg)": new_recipe.get(name, 0),
                "Change (kg)": round(new_recipe.get(name, 0) - old_kg, 2),
            }
            for name, old_kg in old_recipe.items()
        ]
        st.dataframe(rows, hide_index=True, width="stretch")
        old_cow_cost = ration_result["old_cost_eur_per_cow_day"]
        new_cow_cost = ration_result["new_cost_eur_per_cow_day"]
        old_herd_cost = old_cow_cost * HERD_SIZE
        new_herd_cost = new_cow_cost * HERD_SIZE
        cost_cow, cost_herd = st.columns(2)
        cost_cow.metric(
            "Cost per cow/day",
            f"€{new_cow_cost:,.2f}",
            f"€{new_cow_cost - old_cow_cost:+,.2f} vs old",
            delta_color="inverse",
        )
        cost_herd.metric(
            f"Cost per herd/day ({HERD_SIZE} cows)",
            f"€{new_herd_cost:,.2f}",
            f"€{new_herd_cost - old_herd_cost:+,.2f} vs old",
            delta_color="inverse",
        )
        st.caption("Daily feed cost per herd")
        st.bar_chart(
            {"Old (€)": [old_herd_cost], "Adjusted (€)": [new_herd_cost]},
            horizontal=True,
        )
    else:
        st.error("The agent's ration result is missing recipe or cost details.")
