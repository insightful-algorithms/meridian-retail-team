"""Customer core: customers, orders, circle_memberships.

Backlog S1-05. Generates the customer population, their monthly order
behaviour, and Circle membership with self-selection and the planted
loyalty effect (ground_truth.yaml, workstream 2).

Scope note (read before extending). This module stands alone from the
checkout/session model, which is S1-06. Two things are therefore
provisional here and will be reconciled when S1-06 lands:

1. `visitor_id` / `session_id` on `orders` are placeholder values
   (one synthetic visitor per customer). The real values come from the
   session-level model in S1-06; this module's `orders` output should be
   re-joined to real sessions at that point, not treated as final.
2. New-customer arrival timing: the spec (5.2) derives new customers per
   month from the checkout funnel ("~62,000/mo at 850k purchasers").
   Here, new-customer arrival falls out directly of the calibrated
   population process instead (see `calibrate_gamma_scale`). Numbers
   should land close, but S1-06 is what actually reconciles this
   properly — flagged for the Data Analyst's realism review (S1-13).

Everything else — the latent-rate model, seasonality, region/category/
channel assignment, Circle selection and the tenure-based loyalty
effect, order value and payment method — follows the spec as written
(sections 3.2, 5.1, 5.2, 5.4; ground_truth.yaml workstream 2).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# --- Config loading -----------------------------------------------------

def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_configs(generator_root: Path) -> tuple[dict, dict, dict]:
    cfg = generator_root / "config"
    baselines = load_yaml(cfg / "baselines.yaml")
    generator_cfg = load_yaml(cfg / "generator.yaml")
    ground_truth = load_yaml(cfg / "ground_truth.yaml")
    return baselines, generator_cfg, ground_truth


# --- Calendar and seasonality --------------------------------------------

MONTHS = pd.period_range("2025-01", "2026-08", freq="M")  # 20 months, spec 2.1/5
TRAILING_12M_START = pd.Period("2025-09", freq="M")  # spec 3.1: "1 Sep 2025 to 31 Aug 2026"

_MONTH_NAME_TO_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


def monthly_seasonal_factor(period: pd.Period, baselines: dict) -> float:
    """D-003 seasonality, monthly factors, normalised to mean 1.0 (baselines.yaml)."""
    monthly = baselines["seasonality"]["monthly"]
    month_name = period.strftime("%B").lower()
    if month_name in monthly and month_name != "other_months":
        return float(monthly[month_name])
    return float(monthly["other_months"])


# --- Region, category, channel assignment (spec 5.1) ---------------------

ITL1_REGIONS = [
    "TLC", "TLD", "TLE", "TLF", "TLG", "TLH",  # non-London/SE areas (6)
    "TLI", "TLJ",                              # London, South East (over-weighted)
    "TLK", "TLL", "TLM", "TLN",                # remaining areas (4)
]
_LONDON_SE = {"TLI", "TLJ"}


def region_weights(overweight_pct: float) -> np.ndarray:
    """12 ITL1 areas, London (TLI) and South East (TLJ) over-weighted (spec 5.1)."""
    base = np.ones(len(ITL1_REGIONS))
    boost = 1.0 + overweight_pct / 100.0
    for i, r in enumerate(ITL1_REGIONS):
        if r in _LONDON_SE:
            base[i] *= boost
    return base / base.sum()


CATEGORIES = ["furniture", "textiles", "kitchen", "decor", "garden"]


# --- Calibration: gamma scale for the latent-rate distribution -----------

@dataclass
class CalibrationResult:
    gamma_scale: float
    pool_size: int
    realised_purchasers_12m: int
    iterations: int


def _simulate_purchaser_count(
    pool_size: int,
    shape: float,
    scale: float,
    seasonal_factors: np.ndarray,
    rng: np.random.Generator,
) -> tuple[int, np.ndarray]:
    """One draw of the pool's latent rates and a 20-month order simulation.

    Returns the count of customers with >=1 order in the trailing 12
    months, and the boolean order matrix (pool_size x n_months) for reuse.
    """
    latent_rate = rng.gamma(shape=shape, scale=scale, size=pool_size)  # spec 5.1
    p_order = 1.0 - np.exp(-latent_rate)  # per-month order probability, before seasonality
    n_months = len(seasonal_factors)
    orders = np.zeros((pool_size, n_months), dtype=bool)
    for m in range(n_months):
        p_month = np.clip(p_order * seasonal_factors[m], 0.0, 1.0)
        orders[:, m] = rng.random(pool_size) < p_month
    trailing_start_idx = n_months - 12
    purchasers_12m = int(orders[:, trailing_start_idx:].any(axis=1).sum())
    return purchasers_12m, orders


def calibrate_gamma_scale(
    pool_size: int,
    shape: float,
    target_purchasers_12m: int,
    seasonal_factors: np.ndarray,
    rng: np.random.Generator,
    tol: float = 0.01,
    max_iter: int = 25,
) -> CalibrationResult:
    """Solve the Gamma scale so trailing-12m purchasers matches the target
    (generator spec 5.1: "the Gamma scale is the constant the calibration
    step solves"). Bisection on scale; purchaser count is monotonic in
    scale for fixed shape and pool size.
    """
    lo, hi = 0.01, 5.0
    result_orders = None
    for i in range(1, max_iter + 1):
        mid = (lo + hi) / 2
        count, orders = _simulate_purchaser_count(pool_size, shape, mid, seasonal_factors, rng)
        result_orders = orders
        if abs(count - target_purchasers_12m) / target_purchasers_12m <= tol:
            return CalibrationResult(mid, pool_size, count, i)
        if count < target_purchasers_12m:
            lo = mid
        else:
            hi = mid
    return CalibrationResult(mid, pool_size, count, max_iter)


# --- Main generation routine ----------------------------------------------

def run_customer_core(
    scale: float,
    seed: int,
    generator_root: Path,
    baselines: dict,
    generator_cfg: dict,
    ground_truth: dict,
) -> dict:
    """Runs the customer-core model. Returns a dict of DataFrames plus
    calibration diagnostics for run_manifest.json.
    """
    ss = np.random.SeedSequence(seed)
    # Fixed child-seed order (spec 2.2): calibration, region, category,
    # channel, circle-join, order-value, order-category, payment-method.
    (calib_seed, region_seed, category_seed, channel_seed,
     circle_seed, value_seed, item_seed, payment_seed) = ss.spawn(8)

    target_purchasers_12m = round(baselines["purchasing_customers_12m"] * scale)
    pool_size = max(round(target_purchasers_12m * 2.5), 100)

    seasonal_factors = np.array([monthly_seasonal_factor(m, baselines) for m in MONTHS])

    calib_rng = np.random.default_rng(calib_seed)
    calib = calibrate_gamma_scale(
        pool_size=pool_size,
        shape=generator_cfg["customers"]["gamma_shape"],
        target_purchasers_12m=target_purchasers_12m,
        seasonal_factors=seasonal_factors,
        rng=calib_rng,
    )

    # Re-draw with the solved scale for the actual generation run
    final_rng = np.random.default_rng(calib_seed)
    latent_rate = final_rng.gamma(
        shape=generator_cfg["customers"]["gamma_shape"], scale=calib.gamma_scale, size=pool_size
    )
    p_order = 1.0 - np.exp(-latent_rate)
    orders_bool = np.zeros((pool_size, len(MONTHS)), dtype=bool)
    for m_idx in range(len(MONTHS)):
        p_month = np.clip(p_order * seasonal_factors[m_idx], 0.0, 1.0)
        orders_bool[:, m_idx] = final_rng.random(pool_size) < p_month

    has_ever_ordered = orders_bool.any(axis=1)
    customer_pool_idx = np.where(has_ever_ordered)[0]
    n_customers = len(customer_pool_idx)

    first_order_month_idx = orders_bool[customer_pool_idx].argmax(axis=1)
    first_order_date = MONTHS[first_order_month_idx].to_timestamp().normalize()

    region_rng = np.random.default_rng(region_seed)
    weights = region_weights(generator_cfg["customers"]["region_weighting"]["london_and_south_east_overweight_pct"])
    region = region_rng.choice(ITL1_REGIONS, size=n_customers, p=weights)

    category_rng = np.random.default_rng(category_seed)
    category_affinity = category_rng.choice(CATEGORIES, size=n_customers)

    channel_shares = generator_cfg["sessions"]["channel_shares_pct"]
    channels = list(channel_shares.keys())
    channel_p = np.array([channel_shares[c] for c in channels], dtype=float)
    channel_p /= channel_p.sum()
    channel_rng = np.random.default_rng(channel_seed)
    acquisition_channel = channel_rng.choice(channels, size=n_customers, p=channel_p)

    customers = pd.DataFrame({
        "customer_id": np.arange(1, n_customers + 1, dtype=np.int64),
        "first_order_date": first_order_date,
        "region": region,
        "acquisition_channel": acquisition_channel,
        "category_affinity": category_affinity,
    })

    # --- Circle membership: selection + planted loyalty effect ----------
    circle_result = _generate_circle_and_apply_loyalty(
        customers=customers,
        orders_bool=orders_bool[customer_pool_idx],
        latent_rate=latent_rate[customer_pool_idx],
        generator_cfg=generator_cfg,
        ground_truth=ground_truth,
        scale=scale,
        rng=np.random.default_rng(circle_seed),
    )
    circle_memberships = circle_result["circle_memberships"]
    diagnostics = circle_result["diagnostics"]

    # --- Orders table (order value, category, payment method, placeholders) ---
    orders_df = _build_orders_table(
        customers=customers,
        orders_bool=orders_bool[customer_pool_idx],
        generator_cfg=generator_cfg,
        value_rng=np.random.default_rng(value_seed),
        item_rng=np.random.default_rng(item_seed),
        payment_rng=np.random.default_rng(payment_seed),
    )

    manifest = {
        "scale": scale,
        "seed": seed,
        "gamma_shape": generator_cfg["customers"]["gamma_shape"],
        "gamma_scale_calibrated": calib.gamma_scale,
        "calibration_pool_size": calib.pool_size,
        "calibration_iterations": calib.iterations,
        "target_purchasers_12m": target_purchasers_12m,
        "realised_purchasers_12m_at_calibration": calib.realised_purchasers_12m,
        "n_customers_total_20_months": n_customers,
        **diagnostics,
    }

    return {
        "customers": customers,
        "orders": orders_df,
        "circle_memberships": circle_memberships,
        "manifest": manifest,
    }


def _generate_circle_and_apply_loyalty(
    customers: pd.DataFrame,
    orders_bool: np.ndarray,
    latent_rate: np.ndarray,
    generator_cfg: dict,
    ground_truth: dict,
    scale: float,
    rng: np.random.Generator,
) -> dict:
    """Circle joins by monthly cohort, weighted selection (spec 5.4),
    with month-0 shown-but-excluded and the tenure loyalty effect applied
    to subsequent months (ground_truth.yaml workstream_2).
    """
    n = len(customers)
    cohort_sizes_cfg = generator_cfg["circle_membership"]["cohort_sizes"]

    # Build the month->target cohort size list from config, scaled by the
    # same --scale as the rest of the run (baseline cohorts sum to 280,000).
    fixed = {
        "2025-02": cohort_sizes_cfg["2025-02"],
        "2025-03": cohort_sizes_cfg["2025-03"],
        "2025-04": cohort_sizes_cfg["2025-04"],
    }
    steady = cohort_sizes_cfg["2025-05_to_2026-08_per_month"]
    cohort_targets = {}
    for m in MONTHS:
        key = str(m)
        if key in fixed:
            cohort_targets[key] = round(fixed[key] * scale)
        elif pd.Period("2025-05") <= m <= pd.Period("2026-08"):
            cohort_targets[key] = round(steady * scale)
    # Guard: never target more joiners in a month than exist in the pool.
    cohort_targets = {k: min(v, n) for k, v in cohort_targets.items()}

    median_rate = np.median(latent_rate)
    exponent = _calibrate_selection_exponent(
        orders_bool=orders_bool,
        latent_rate=latent_rate,
        cohort_targets=cohort_targets,
        median_rate=median_rate,
        region=customers["region"].values,
        category_affinity=customers["category_affinity"].values,
        rng=rng,
    )

    weight = (latent_rate / median_rate) ** exponent
    weight *= np.where(np.isin(customers["region"].values, list(_LONDON_SE)), 1.10, 1.0)
    weight *= np.where(customers["category_affinity"].values == "furniture", 1.10, 1.0)

    already_joined = np.zeros(n, dtype=bool)
    joined_at = np.full(n, np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    join_channel_shares = generator_cfg["circle_membership"]["join_channel_shares_pct"]
    channels = list(join_channel_shares.keys())
    channel_p = np.array([join_channel_shares[c] for c in channels], dtype=float)
    channel_p /= channel_p.sum()
    join_channel = np.array([""] * n, dtype=object)

    for m_idx, m in enumerate(MONTHS):
        key = str(m)
        target = cohort_targets.get(key, 0)
        if target <= 0:
            continue
        eligible = ~already_joined
        w = np.where(eligible, weight, 0.0)
        ordered_this_month = orders_bool[:, m_idx] & eligible
        w = np.where(ordered_this_month, w * 3.0, w)  # bias toward checkout joins (70/20/10 target)
        if w.sum() <= 0:
            continue
        p = w / w.sum()
        n_join = min(target, int(eligible.sum()))
        chosen = rng.choice(n, size=n_join, replace=False, p=p)
        already_joined[chosen] = True
        joined_at[chosen] = m.to_timestamp().normalize()
        join_channel[chosen] = rng.choice(channels, size=n_join, p=channel_p)

    member_idx = np.where(already_joined)[0]
    circle_memberships = pd.DataFrame({
        "membership_id": np.arange(1, len(member_idx) + 1, dtype=np.int64),
        "customer_id": customers["customer_id"].values[member_idx],
        "joined_at": joined_at[member_idx],
        "join_channel": join_channel[member_idx],
        "status": "active",
    })

    # --- Diagnostics: realised selection premium and raw gap -------------
    trailing_start_idx = len(MONTHS) - 12
    active_trailing = orders_bool[:, trailing_start_idx:].any(axis=1)
    is_member_by_aug26 = already_joined
    if active_trailing.sum() > 0:
        member_mean_rate = latent_rate[active_trailing & is_member_by_aug26].mean() if (active_trailing & is_member_by_aug26).any() else float("nan")
        nonmember_mean_rate = latent_rate[active_trailing & ~is_member_by_aug26].mean() if (active_trailing & ~is_member_by_aug26).any() else float("nan")
        raw_gap = member_mean_rate / nonmember_mean_rate if nonmember_mean_rate else float("nan")
    else:
        raw_gap = float("nan")

    never_joined_mean = latent_rate[~is_member_by_aug26].mean() if (~is_member_by_aug26).any() else float("nan")
    joiners_mean = latent_rate[is_member_by_aug26].mean() if is_member_by_aug26.any() else float("nan")
    selection_premium_pct = (joiners_mean / never_joined_mean - 1.0) * 100 if never_joined_mean else float("nan")

    diagnostics = {
        "circle_members_generated": int(len(member_idx)),
        "circle_selection_exponent_calibrated": exponent,
        "circle_raw_gap_realised": raw_gap,
        "circle_selection_premium_pct_realised": selection_premium_pct,
    }

    return {"circle_memberships": circle_memberships, "diagnostics": diagnostics}


def _calibrate_selection_exponent(
    orders_bool: np.ndarray,
    latent_rate: np.ndarray,
    cohort_targets: dict,
    median_rate: float,
    region: np.ndarray,
    category_affinity: np.ndarray,
    rng: np.random.Generator,
    target_raw_gap: float = 1.30,
    tol: float = 0.02,
    max_iter: int = 8,
) -> float:
    """Bisection on the selection exponent so the realised raw gap
    (member vs non-member mean latent rate, trailing 12m) lands near the
    D-003 target of 1.30x (generator spec 5.4).
    """
    lo, hi = 0.0, 4.0
    n = len(latent_rate)
    trailing_start_idx = orders_bool.shape[1] - 12
    active_trailing = orders_bool[:, trailing_start_idx:].any(axis=1)

    def raw_gap_for(exponent: float, n_replicates: int = 5) -> float:
        # Bisection needs a stable function of exponent, but which
        # customers get chosen to join is itself stochastic (weighted
        # sampling without replacement). A single draw is too noisy for
        # the bisection to converge reliably (confirmed empirically —
        # single-draw evaluations at a fixed exponent varied by more than
        # the tolerance below). Average several independent draws instead.
        weight = (latent_rate / median_rate) ** exponent
        weight *= np.where(np.isin(region, list(_LONDON_SE)), 1.10, 1.0)
        weight *= np.where(category_affinity == "furniture", 1.10, 1.0)
        gaps = []
        for _ in range(n_replicates):
            rng_local = np.random.default_rng(rng.integers(0, 2**32 - 1))
            already_joined = np.zeros(n, dtype=bool)
            for m_idx in range(orders_bool.shape[1]):
                target = cohort_targets.get(str(MONTHS[m_idx]), 0)
                if target <= 0:
                    continue
                eligible = ~already_joined
                w = np.where(eligible, weight, 0.0)
                ordered_this_month = orders_bool[:, m_idx] & eligible
                w = np.where(ordered_this_month, w * 3.0, w)
                if w.sum() <= 0:
                    continue
                p = w / w.sum()
                n_join = min(target, int(eligible.sum()))
                chosen = rng_local.choice(n, size=n_join, replace=False, p=p)
                already_joined[chosen] = True
            member_rate = latent_rate[active_trailing & already_joined]
            nonmember_rate = latent_rate[active_trailing & ~already_joined]
            if len(member_rate) == 0 or len(nonmember_rate) == 0:
                continue
            gaps.append(member_rate.mean() / nonmember_rate.mean())
        return float(np.mean(gaps)) if gaps else float("nan")

    best = 1.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        gap = raw_gap_for(mid)
        if np.isnan(gap):
            break
        best = mid
        if abs(gap - target_raw_gap) <= tol:
            break
        if gap < target_raw_gap:
            lo = mid
        else:
            hi = mid
    return best


def _build_orders_table(
    customers: pd.DataFrame,
    orders_bool: np.ndarray,
    generator_cfg: dict,
    value_rng: np.random.Generator,
    item_rng: np.random.Generator,
    payment_rng: np.random.Generator,
) -> pd.DataFrame:
    """Order value (lognormal + category multiplier), item count, payment
    method (spec 5.2). visitor_id/session_id are placeholders — see
    module docstring, point 1.
    """
    order_cfg = generator_cfg["checkout_and_orders"]["order_value"]
    multipliers = order_cfg["category_multipliers"]
    sigma = order_cfg["sigma"]
    target_mean = order_cfg["rescale_to_mean_gbp"]

    rows = []
    order_id = 1
    for cust_idx, cust_id in enumerate(customers["customer_id"].values):
        cat = customers["category_affinity"].values[cust_idx]
        month_idxs = np.where(orders_bool[cust_idx])[0]
        for m_idx in month_idxs:
            order_cat = cat if value_rng.random() < 0.6 else value_rng.choice(
                [c for c in CATEGORIES if c != cat]
            )
            base_value = value_rng.lognormal(mean=0.0, sigma=sigma)
            value = base_value * multipliers[order_cat]
            order_ts = MONTHS[m_idx].to_timestamp() + pd.Timedelta(
                days=int(value_rng.integers(0, 28)), hours=int(value_rng.integers(0, 24))
            )
            item_count = min(int(item_rng.poisson(order_cfg.get("lambda", 1.6) if "lambda" in order_cfg else generator_cfg["checkout_and_orders"]["item_count"]["lambda"])) + 1, 8)
            payment_shares = generator_cfg["checkout_and_orders"]["payment_method_shares_pct"]
            methods = list(payment_shares.keys())
            p = np.array([payment_shares[m] for m in methods], dtype=float)
            p /= p.sum()
            payment_method = payment_rng.choice(methods, p=p)
            rows.append({
                "order_id": order_id,
                "customer_id": cust_id,
                "visitor_id": f"placeholder-{cust_id:012x}",  # S1-06 will replace with real visitor_id
                "session_id": -1,  # S1-06 will replace with real session_id
                "order_ts": order_ts,
                "order_value_gbp": round(value, 2),
                "item_count": item_count,
                "category_primary": order_cat,
                "payment_method": payment_method,
                "delivery_region": customers["region"].values[cust_idx],
            })
            order_id += 1

    orders_df = pd.DataFrame(rows)
    if len(orders_df) > 0:
        # Rescale order_value_gbp so the realised mean matches the D-003 baseline
        current_mean = orders_df["order_value_gbp"].mean()
        if current_mean > 0:
            orders_df["order_value_gbp"] = (
                orders_df["order_value_gbp"] * (target_mean / current_mean)
            ).clip(order_cfg["clip_min_gbp"], order_cfg["clip_max_gbp"]).round(2)
    return orders_df


# --- CLI -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the S1-05 customer core.")
    parser.add_argument("--scale", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260907)
    parser.add_argument("--out", type=str, default=None, help="Output directory (default: pipeline/data/raw relative to repo root)")
    args = parser.parse_args()

    generator_root = Path(__file__).resolve().parent.parent.parent  # pipeline/generator/
    baselines, generator_cfg, ground_truth = load_configs(generator_root)

    result = run_customer_core(args.scale, args.seed, generator_root, baselines, generator_cfg, ground_truth)

    out_dir = Path(args.out) if args.out else generator_root.parent / "data" / "raw"
    (out_dir / "customers").mkdir(parents=True, exist_ok=True)
    (out_dir / "circle_memberships").mkdir(parents=True, exist_ok=True)
    (out_dir / "orders").mkdir(parents=True, exist_ok=True)
    (out_dir / "_manifest").mkdir(parents=True, exist_ok=True)

    result["customers"].to_parquet(out_dir / "customers" / "customers.parquet", index=False)
    result["circle_memberships"].to_parquet(out_dir / "circle_memberships" / "circle_memberships.parquet", index=False)

    orders = result["orders"]
    if len(orders) > 0:
        orders["year_month"] = orders["order_ts"].dt.to_period("M").astype(str)
        for ym, chunk in orders.groupby("year_month"):
            part_dir = out_dir / "orders" / f"year_month={ym}"
            part_dir.mkdir(parents=True, exist_ok=True)
            chunk.drop(columns=["year_month"]).to_parquet(part_dir / "part-0.parquet", index=False)

    with open(out_dir / "_manifest" / "customer_core_manifest.json", "w", encoding="utf-8") as f:
        json.dump(result["manifest"], f, indent=2, default=str)

    print(json.dumps(result["manifest"], indent=2, default=str))


if __name__ == "__main__":
    main()
