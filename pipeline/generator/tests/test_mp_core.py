"""Tests for S1-07 (mp_core.py): mp_applications, mp_agreements,
mp_instalments, mp_payments, and the corrections mp_core.py makes back
into checkout_core.py's orders/sessions/checkout_events/customers.
"""

from pathlib import Path

import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "meridian_gen"))
import customer_core as cc  # noqa: E402
import checkout_core as ck  # noqa: E402
import mp_core as mp  # noqa: E402

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
def checkout_result(configs, customer_result):
    baselines, generator_cfg, ground_truth = configs
    return ck.run_checkout_core(SCALE, SEED, baselines, generator_cfg, ground_truth, customer_result)


@pytest.fixture(scope="module")
def result(configs, checkout_result):
    baselines, generator_cfg, ground_truth = configs
    return mp.run_mp_core(SCALE, SEED, baselines, generator_cfg, ground_truth, checkout_result)


def test_structure_mp_applications(result):
    expected = {"application_id", "session_id", "customer_id", "visitor_id", "applied_at",
                "requested_value_gbp", "credit_band", "decision", "order_id"}
    assert set(result["mp_applications"].columns) == expected


def test_structure_mp_agreements(result):
    expected = {"agreement_id", "application_id", "order_id", "customer_id",
                "agreement_value_gbp", "start_date", "status_at_extract", "written_off_value_gbp"}
    assert set(result["mp_agreements"].columns) == expected


def test_structure_mp_instalments(result):
    expected = {"instalment_id", "agreement_id", "instalment_no", "due_date", "amount_gbp"}
    assert set(result["mp_instalments"].columns) == expected


def test_structure_mp_payments(result):
    expected = {"payment_id", "instalment_id", "agreement_id", "paid_at", "amount_gbp", "recorded_at"}
    assert set(result["mp_payments"].columns) == expected


def test_keys_unique(result):
    assert result["mp_applications"]["application_id"].is_unique
    assert result["mp_agreements"]["agreement_id"].is_unique
    assert result["mp_instalments"]["instalment_id"].is_unique
    assert result["mp_payments"]["payment_id"].is_unique
    assert result["mp_agreements"]["application_id"].is_unique
    assert result["mp_agreements"]["order_id"].is_unique
    assert result["mp_payments"]["instalment_id"].is_unique  # unique in clean data, per spec 4.9


def test_every_agreement_has_three_instalments(result):
    counts = result["mp_instalments"].groupby("agreement_id").size()
    assert (counts == 3).all()
    assert len(counts) == len(result["mp_agreements"])


def test_customer_id_null_only_for_declined_abandoned(result):
    """Spec 4.6: the only table where a row may have no customer -- a
    first-time applicant, declined, who abandons and never becomes one."""
    apps = result["mp_applications"]
    null_apps = apps[apps["customer_id"].isna()]
    assert len(null_apps) > 0  # this scenario should actually occur at this scale
    assert (null_apps["decision"] == "declined").all()
    assert null_apps["order_id"].isna().all()
    non_null_ids = apps.loc[apps["customer_id"].notna(), "customer_id"]
    assert set(non_null_ids) <= set(result["customers"]["customer_id"])


def test_mp_orders_match_agreements_exactly(result):
    mp_orders = result["orders"][result["orders"]["payment_method"] == "meridian_pay"]
    assert set(mp_orders["order_id"]) == set(result["mp_agreements"]["order_id"])


def test_order_placed_events_match_orders_exactly(result):
    """Confirms the declined-and-abandoned reversal kept checkout_events,
    orders, and sessions consistent with each other."""
    placed = result["checkout_events"][result["checkout_events"]["event_type"] == "order_placed"]
    assert len(placed) == len(result["orders"])
    assert set(placed["order_id"].dropna()) == set(result["orders"]["order_id"])


def test_decline_rate_within_tolerance(result, configs):
    diag = result["manifest"]
    # Widened vs. the spec's scale-1.0 tolerance (12.0 +/- 0.3), consistent
    # with "tolerances widen by 1/sqrt(scale) below 1.0" (spec section 8).
    assert abs(diag["realised_decline_rate_pct"] - 12.0) <= 0.3 / (SCALE ** 0.5)


def test_mp_share_of_orders_within_tolerance(result):
    diag = result["manifest"]
    assert abs(diag["realised_mp_share_of_orders_pct"] - 24.0) <= 0.3 / (SCALE ** 0.5)


def test_written_off_value_within_tolerance(result):
    diag = result["manifest"]
    assert abs(diag["realised_written_off_pct_of_value"] - 1.9) <= 0.1 / (SCALE ** 0.5)


def test_approved_band_shares_within_tolerance(result):
    target = {"A": 30, "B": 30, "C": 22, "D": 12, "E": 6}
    realised = result["manifest"]["realised_approved_band_shares_pct"]
    for band in target:
        assert abs(realised[band] - target[band]) <= 0.5 / (SCALE ** 0.5)


def test_reproducibility(configs, checkout_result):
    baselines, generator_cfg, ground_truth = configs
    result_a = mp.run_mp_core(SCALE, SEED, baselines, generator_cfg, ground_truth, checkout_result)
    result_b = mp.run_mp_core(SCALE, SEED, baselines, generator_cfg, ground_truth, checkout_result)
    assert result_a["mp_agreements"].equals(result_b["mp_agreements"])
    assert result_a["mp_payments"].equals(result_b["mp_payments"])
