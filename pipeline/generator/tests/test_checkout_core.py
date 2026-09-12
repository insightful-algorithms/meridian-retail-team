"""Tests for S1-06 (checkout_core.py, D-008): sessions, checkout_events,
experiment_assignments, orders -- the real completion funnel.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "meridian_gen"))
import customer_core as cc  # noqa: E402
import checkout_core as ck  # noqa: E402

SCALE = 0.1
SEED = 20260907


@pytest.fixture(scope="module")
def configs():
    generator_root = Path(__file__).resolve().parent.parent
    return cc.load_configs(generator_root)


@pytest.fixture(scope="module")
def customer_result(configs):
    generator_root = Path(__file__).resolve().parent.parent
    baselines, generator_cfg, ground_truth = configs
    return cc.run_customer_core(SCALE, SEED, generator_root, baselines, generator_cfg, ground_truth)


@pytest.fixture(scope="module")
def result(configs, customer_result):
    baselines, generator_cfg, ground_truth = configs
    return ck.run_checkout_core(SCALE, SEED, baselines, generator_cfg, ground_truth, customer_result)


def test_structure_sessions(result):
    expected = {"session_id", "visitor_id", "customer_id", "session_start_ts", "device", "channel", "landing_category"}
    assert set(result["sessions"].columns) == expected


def test_structure_checkout_events(result):
    expected = {"event_id", "session_id", "visitor_id", "event_ts", "event_type",
                "checkout_version", "payment_method", "order_id", "application_id", "mp_decision"}
    assert set(result["checkout_events"].columns) == expected


def test_structure_experiment_assignments(result):
    expected = {"visitor_id", "experiment_id", "arm", "assigned_at"}
    assert set(result["experiment_assignments"].columns) == expected


def test_structure_orders(result):
    expected = {"order_id", "customer_id", "visitor_id", "session_id", "order_ts",
                "order_value_gbp", "item_count", "category_primary", "payment_method", "delivery_region"}
    assert set(result["orders"].columns) == expected


def test_keys_unique(result):
    assert result["sessions"]["session_id"].is_unique
    assert result["orders"]["order_id"].is_unique
    assert result["experiment_assignments"]["visitor_id"].is_unique


def test_every_session_has_one_checkout_started(result):
    starts = result["checkout_events"][result["checkout_events"]["event_type"] == "checkout_started"]
    counts = starts.groupby("session_id").size()
    assert (counts == 1).all()
    assert len(counts) == len(result["sessions"])


def test_every_session_resolves_once(result):
    resolving = result["checkout_events"][
        result["checkout_events"]["event_type"].isin(["order_placed", "checkout_abandoned"])
    ]
    counts = resolving.groupby("session_id").size()
    assert (counts == 1).all()
    assert len(counts) == len(result["sessions"])


def test_order_value_mean_near_target(result, configs):
    baselines, _, _ = configs
    aov = result["orders"]["order_value_gbp"].mean()
    assert abs(aov - baselines["average_order_value_gbp"]) <= 1.0


def test_order_value_never_non_positive(result):
    assert (result["orders"]["order_value_gbp"] > 0).all()


def test_no_visitor_in_both_arms(result):
    """No visitor's in-window checkout_started events show more than one
    checkout_version -- the real requirement (generator spec section 8),
    scoped to the experiment window itself."""
    events = result["checkout_events"].copy()
    events["event_ts"] = pd.to_datetime(events["event_ts"])
    starts = events[events["event_type"] == "checkout_started"]
    window = starts[
        (starts["event_ts"] >= ck.EXPERIMENT_WINDOW_START)
        & (starts["event_ts"] < ck.EXPERIMENT_WINDOW_END + pd.Timedelta(days=1))
    ]
    assert set(window["visitor_id"]) == set(result["experiment_assignments"]["visitor_id"])
    versions_per_visitor = window.groupby("visitor_id")["checkout_version"].nunique()
    assert (versions_per_visitor == 1).all()


def test_sample_ratio_not_mismatched(result):
    """Arm split close to 50/50 -- a simple proportion check standing in
    for the sample-ratio-mismatch test (full statistical SRM test is
    Sprint 2's experiment-mart work); no planted mismatch (A4)."""
    n_test = (result["experiment_assignments"]["arm"] == "test").sum()
    n_total = len(result["experiment_assignments"])
    assert n_total > 0
    p = n_test / n_total
    assert abs(p - 0.5) < 0.03  # loose bound at scale 0.1; tightens with scale


def test_reproducibility(configs, customer_result):
    baselines, generator_cfg, ground_truth = configs
    result_a = ck.run_checkout_core(SCALE, SEED, baselines, generator_cfg, ground_truth, customer_result)
    result_b = ck.run_checkout_core(SCALE, SEED, baselines, generator_cfg, ground_truth, customer_result)
    assert result_a["orders"].equals(result_b["orders"])
    assert result_a["sessions"].equals(result_b["sessions"])
