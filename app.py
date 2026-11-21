"""Streamlit dashboard. Run: uv run streamlit run app.py"""
import json
from pathlib import Path

import streamlit as st

from agent import HERD_SIZE, run_agent
from core.decay import apply_storage_drift
from core.optimizer import optimize_ration


def render_values(values, indent=0):
    for key, value in values.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(value, dict):
            st.markdown(f"{'  ' * indent}- **{label}**")
            render_values(value, indent + 1)
        else:
            st.markdown(f"{'  ' * indent}- **{label}:** {value}")


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
    presets = st.columns(3)
    if presets[0].button("Normal", use_container_width=True):
        st.session_state["storage_days"] = 0
        st.session_state["silo_temp"] = 20
        st.session_state["moisture"] = 60
    if presets[1].button("Hot summer silo", use_container_width=True):
        st.session_state["storage_days"] = 45
        st.session_state["silo_temp"] = 40
        st.session_state["moisture"] = 60
    if presets[2].button("Wet and spoiled", use_container_width=True):
        st.session_state["storage_days"] = 45
        st.session_state["silo_temp"] = 30
        st.session_state["moisture"] = 74

    days = st.slider("Storage days", 0, 60, 0, key="storage_days")
    temp = st.slider("Silo temp (°C)", 15, 45, 20, key="silo_temp")
    moisture = st.slider("Moisture (%)", 50, 75, 60, key="moisture")
    auto_mode = st.toggle("Auto mode", value=False)
    run_clicked = st.button("Run Nutrition Agent", type="primary", use_container_width=True)

drifted = apply_storage_drift(base_feeds, days, temp, moisture)
old = optimize_ration(base_feeds, targets)
new = optimize_ration(drifted, targets)
baseline_cp = base_feeds["corn_silage"]["cp_pct_dm"]
now_cp = drifted["corn_silage"]["cp_pct_dm"]

if run_clicked or auto_mode:
    with st.spinner("Nutrition agent is checking the silo and ration..."):
        st.session_state["agent_result"] = run_agent(days, temp, moisture)

with mid:
    st.subheader("Agent log")
    st.caption("Silage crude protein (% dry matter): baseline vs current")
    st.bar_chart({"Baseline": [baseline_cp], "Current": [now_cp]}, horizontal=True)
    st.caption(f"{baseline_cp:.1f}% baseline → {now_cp:.1f}% current")

    result = st.session_state.get("agent_result")
    if result:
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
    if new["feasible"]:
        rows = [
            {
                "Feed": name.replace("_", " ").title(),
                "Old (kg)": old["kg_fresh"][name],
                "Adjusted (kg)": new["kg_fresh"][name],
                "Change (kg)": round(new["kg_fresh"][name] - old["kg_fresh"][name], 2),
            }
            for name in base_feeds
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        old_herd_cost = old["cost_per_day"] * HERD_SIZE
        new_herd_cost = new["cost_per_day"] * HERD_SIZE
        st.metric(
            f"Adjusted daily cost ({HERD_SIZE} cows)",
            f"€{new_herd_cost:,.2f}",
            f"€{new_herd_cost - old_herd_cost:+,.2f} vs old",
            delta_color="inverse",
        )
    else:
        st.error("No feasible adjusted ration. The current feed limits cannot meet the targets.")
        if old["feasible"]:
            st.metric(f"Old daily cost ({HERD_SIZE} cows)", f"€{old['cost_per_day'] * HERD_SIZE:,.2f}")
