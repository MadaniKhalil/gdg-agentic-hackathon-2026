"""Streamlit dashboard. Run: uv run streamlit run app.py"""
import json
from pathlib import Path

import streamlit as st

from core.decay import apply_storage_drift
from core.optimizer import optimize_ration

data = json.loads((Path(__file__).parent / "data" / "feeds.json").read_text())
base_feeds, targets = data["feeds"], data["targets"]

st.title("Feed Ration Agent")
left, mid, right = st.columns(3)

with left:
    st.subheader("Simulated Silo Telemetry")
    days = st.slider("Storage days", 0, 60, 0)
    temp = st.slider("Silo temp (°C)", 15, 45, 20)
    moisture = st.slider("Moisture (%)", 50, 75, 60)

drifted = apply_storage_drift(base_feeds, days, temp, moisture)
old = optimize_ration(base_feeds, targets)
new = optimize_ration(drifted, targets)

with mid:
    st.subheader("Agent log")
    st.write("TODO: agent steps go here (CS 2).")
    st.write(f"Silage CP: {base_feeds['corn_silage']['cp_pct_dm']}% -> {drifted['corn_silage']['cp_pct_dm']:.1f}%")

with right:
    st.subheader("Old vs new recipe (kg fresh/cow/day)")
    if new["feasible"]:
        st.table({"old": old["kg_fresh"], "new": new["kg_fresh"]})
        st.metric("Cost €/day", new["cost_per_day"], round(new["cost_per_day"] - old["cost_per_day"], 2), delta_color="inverse")
    else:
        st.error("No feasible ration. Targets cannot be met.")
