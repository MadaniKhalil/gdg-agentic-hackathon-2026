import copy
import json
from pathlib import Path

import pytest

from core.decay import apply_storage_drift
from core.optimizer import optimize_ration
from core.telemetry import parse_telemetry

DATA = json.loads((Path(__file__).parent.parent / "data" / "feeds.json").read_text(encoding="utf-8"))
FEEDS, TARGETS = DATA["feeds"], DATA["targets"]


def test_decay_leaves_feeds_unchanged_in_normal_storage():
    drifted = apply_storage_drift(FEEDS, days=0, temp_c=20, moisture_pct=60)
    assert drifted == FEEDS


def test_decay_lowers_silage_when_hot_and_wet():
    drifted = apply_storage_drift(FEEDS, days=45, temp_c=44, moisture_pct=74)["corn_silage"]
    base = FEEDS["corn_silage"]
    assert drifted["cp_pct_dm"] < base["cp_pct_dm"]
    assert drifted["nel_mj_per_kg_dm"] < base["nel_mj_per_kg_dm"]
    assert drifted["dm_pct"] < base["dm_pct"]


def test_decay_does_not_mutate_input_or_touch_other_feeds():
    before = copy.deepcopy(FEEDS)
    drifted = apply_storage_drift(FEEDS, days=45, temp_c=44, moisture_pct=74)
    assert FEEDS == before
    assert drifted["soybean_meal"] == FEEDS["soybean_meal"]


def test_optimizer_meets_dry_matter_protein_and_energy_targets():
    result = optimize_ration(FEEDS, TARGETS)
    assert result["feasible"]
    kg_dm = result["kg_dm"]
    assert sum(kg_dm.values()) == pytest.approx(TARGETS["dm_kg"], abs=0.1)
    protein = sum(kg_dm[n] * FEEDS[n]["cp_pct_dm"] / 100 for n in kg_dm)
    assert protein / TARGETS["dm_kg"] >= TARGETS["cp_fraction_min"] - 0.002
    energy = sum(kg_dm[n] * FEEDS[n]["nel_mj_per_kg_dm"] for n in kg_dm)
    assert energy / TARGETS["dm_kg"] >= TARGETS["nel_mj_per_kg_dm_min"] - 0.02


def test_optimizer_respects_min_and_max_limits():
    kg_dm = optimize_ration(FEEDS, TARGETS)["kg_dm"]
    for name, amount in kg_dm.items():
        assert FEEDS[name]["min_dm_kg"] - 0.01 <= amount <= FEEDS[name]["max_dm_kg"] + 0.01


def test_optimizer_reports_infeasible_when_limits_make_targets_impossible():
    squeezed = {name: {**feed, "max_dm_kg": 0.5} for name, feed in FEEDS.items()}
    squeezed["mineral_mix"]["min_dm_kg"] = 0.0
    assert optimize_ration(squeezed, TARGETS)["feasible"] is False


def test_spoiled_silage_costs_more_than_fresh():
    fresh = optimize_ration(FEEDS, TARGETS)["cost_per_day"]
    spoiled = optimize_ration(apply_storage_drift(FEEDS, 45, 40, 72), TARGETS)["cost_per_day"]
    assert spoiled > fresh


def test_telemetry_accepts_valid_json():
    assert parse_telemetry('{"days": 45, "temp_c": 40, "moisture_pct": 72}') == {
        "days": 45, "temp_c": 40.0, "moisture_pct": 72.0,
    }


@pytest.mark.parametrize("bad", ["nope", "[1]", '{"days": 1}', '{"days":1,"temp_c":"x","moisture_pct":5}',
                                 '{"days":1,"temp_c":500,"moisture_pct":5}'])
def test_telemetry_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_telemetry(bad)
