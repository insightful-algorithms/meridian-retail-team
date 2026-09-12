"""Tests for the revised S1-05 customer core (D-008): customers,
checkout_attempts, circle_memberships. No `orders` table here anymore --
see test_checkout_core.py for order/session/experiment tests, which run
against the real completion funnel.
"""

from pathlib import Path

import numpy as np
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "meridian_gen"))
import customer_core as cc  # noqa: E402

SCALE = 0.1
SEED = 20260907


@pytest.fixture(scope="module")
def result():
    generator_root = Path(__file__).resolve().parent.parent
    baselines, generator_cfg, ground_truth = cc.load_configs(generator_root)
    return cc.run_customer_core(SCALE, SEED, generator_root, baselines, generator_cfg, ground_truth)


@pytest.fixture(scope="module")
def baselines():
    generator_root = Path(__file__).resolve().parent.parent
    b, _, _ = cc.load_configs(generator_root)
    return b


def test_structure_customers(result):
    expected_cols = {"customer_id", "first_order_date", "region", "acquisition_channel", "category_affinity"}
    assert set(result["customers"].columns) == expected_cols


def test_structure_circle_memberships(result):
    expected_cols = {"membership_id", "customer_id", "joined_at", "join_channel", "status"}
    assert set(result["circle_memberships"].columns) == expected_cols


def test_structure_checkout_attempts(result):
    expected_cols = {"customer_id", "year_month"}
    assert set(result["checkout_attempts"].columns) == expected_cols
    # every attempting customer_id must exist in customers
    assert set(result["checkout_attempts"]["customer_id"]) <= set(result["customers"]["customer_id"])


def test_keys_unique(result):
    assert result["customers"]["customer_id"].is_unique
    assert result["circle_memberships"]["membership_id"].is_unique
    assert result["circle_memberships"]["customer_id"].is_unique


def test_circle_members_exact_count(result, baselines):
    expected = round(280_000 * SCALE)
    assert len(result["circle_memberships"]) == expected


def test_purchasers_approx_within_tolerance(result, baselines):
    # NOTE (D-008): this module's own purchaser figure is approximate --
    # it uses a flat 0.52 completion stand-in, not the real device-level
    # funnel. Widened tolerance vs. the original (which measured actual
    # completions directly); checkout_core.py re-checks the REAL figure.
    target = baselines["purchasing_customers_12m"] * SCALE
    realised = result["manifest"]["realised_purchasers_12m_at_calibration_approx"]
    assert abs(realised - target) / target <= 0.03


def test_raw_gap_approx_within_tolerance(result, baselines):
    # NOTE (D-008): computed on attempt-rate, not completions. Widened
    # tolerance for the same reason as above; checkout_core.py has the
    # authoritative, completion-based figure.
    target = baselines["raw_spend_gap_members_vs_nonmembers"] + 1.0
    tol = 0.05 / (SCALE ** 0.5)
    realised = result["manifest"]["circle_raw_gap_realised_on_attempts_approx"]
    assert abs(realised - target) <= tol


def test_reproducibility(result):
    generator_root = Path(__file__).resolve().parent.parent
    baselines, generator_cfg, ground_truth = cc.load_configs(generator_root)
    result2 = cc.run_customer_core(SCALE, SEED, generator_root, baselines, generator_cfg, ground_truth)
    assert result["customers"]["customer_id"].tolist() == result2["customers"]["customer_id"].tolist()
    assert result["manifest"]["gamma_scale_calibrated"] == result2["manifest"]["gamma_scale_calibrated"]
    assert result["circle_memberships"]["customer_id"].tolist() == result2["circle_memberships"]["customer_id"].tolist()
    assert result["checkout_attempts"].equals(result2["checkout_attempts"])
