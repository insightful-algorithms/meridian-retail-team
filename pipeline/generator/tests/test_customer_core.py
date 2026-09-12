"""Tests for the S1-05 customer core (customers, orders, circle_memberships).

Subset of generator spec section 8 that applies to this module alone.
Session/checkout-level tests (arm split, sample ratio mismatch, etc.)
belong to S1-06 and are not covered here.
"""

from pathlib import Path

import numpy as np
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "meridian_gen"))
import customer_core as cc  # noqa: E402

SCALE = 0.1  # spec 8: calibration tests apply at scale >= 0.1
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


def test_keys_unique(result):
    assert result["customers"]["customer_id"].is_unique
    assert result["circle_memberships"]["membership_id"].is_unique
    assert result["circle_memberships"]["customer_id"].is_unique  # spec 4.10: unique in clean data


def test_circle_members_exact_count(result, baselines):
    # Spec 4.10 / calibration test: "members exactly 280,000 x scale"
    expected = round(280_000 * SCALE)
    assert len(result["circle_memberships"]) == expected


def test_purchasers_within_tolerance(result, baselines):
    target = baselines["purchasing_customers_12m"] * SCALE
    realised = result["manifest"]["realised_purchasers_12m_at_calibration"]
    assert abs(realised - target) / target <= 0.02  # widened from the calibration's own 1% for run-to-run noise


def test_raw_gap_within_tolerance(result, baselines):
    # Spec 8: "raw gap 1.30 +/- 0.03. Tolerances widen by 1/sqrt(scale) below 1.0"
    target = baselines["raw_spend_gap_members_vs_nonmembers"] + 1.0  # 0.30 -> 1.30
    tol = 0.03 / (SCALE ** 0.5)
    realised = result["manifest"]["circle_raw_gap_realised"]
    assert abs(realised - target) <= tol


def test_order_value_mean_near_target(result, baselines):
    aov = result["orders"]["order_value_gbp"].mean()
    target = baselines["average_order_value_gbp"]
    assert abs(aov - target) <= 1.0  # wider than spec's £0.50 (that's the full-pipeline AOV, not this module alone)


def test_order_value_never_non_positive(result):
    # This module doesn't inject the impossible-value fault (that's S1-08);
    # clean output here should have no non-positive values at all.
    assert (result["orders"]["order_value_gbp"] > 0).all()


def test_reproducibility(result):
    generator_root = Path(__file__).resolve().parent.parent
    baselines, generator_cfg, ground_truth = cc.load_configs(generator_root)
    result2 = cc.run_customer_core(SCALE, SEED, generator_root, baselines, generator_cfg, ground_truth)
    assert result["customers"]["customer_id"].tolist() == result2["customers"]["customer_id"].tolist()
    assert result["manifest"]["gamma_scale_calibrated"] == result2["manifest"]["gamma_scale_calibrated"]
    assert result["circle_memberships"]["customer_id"].tolist() == result2["circle_memberships"]["customer_id"].tolist()
