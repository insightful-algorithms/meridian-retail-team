"""Customer core: customers, circle_memberships, and raw checkout attempts.

Backlog S1-05, revised under D-008. Generates the customer population and
their monthly *checkout-attempt* propensity, and Circle membership with
self-selection. This module no longer produces `orders` — that table now
depends on a real checkout-completion funnel (device-level completion
rates, the June A/B arm effect), which lives in `checkout_core.py` (S1-06).

D-008 background. The previous version of this module drew `orders`
directly from each customer's latent monthly rate, with no completion
step in between. That made the charter's checkout completion rate (52%,
53.8% in the test arm) and the 140,000/month starter baseline impossible
to represent honestly. D-008 rebuilds this: latent_rate here is a
*checkout-attempt* rate, not a purchase rate. An attempt becomes an order
only after `checkout_core.py` applies a real per-device completion draw
(with the June arm effect layered on top for in-window visitors).

Consequence: the purchaser-count and raw-gap calibration targets in this
module are necessarily approximate. Both are ultimately about completed
orders, not attempts, but this module has no completion model of its own
to stay a self-contained, fast-to-calibrate unit — it uses a flat,
device-mix-weighted completion rate (0.52, matching the D-003 baseline)
as a stand-in during its own bisection search. `checkout_core.py` runs the
real, device-level, arm-aware completion draw and re-checks the realised
purchaser count and raw gap against that; small drift between this
module's approximate figures and checkout_core's real ones is expected
and is checked there, not here.

Still-open items, not required for this pass: the 15% multi-visitor-id
rate (spec 5.1) and the Circle tenure effect on checkout-start rate (spec
5.4, ground_truth workstream_2) are not yet applied to the attempt draws
here. Both are flagged for a follow-up rather than silently assumed away.
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

# Flat stand-in completion rate used ONLY for this module's own calibration
# (see module docstring / D-008). checkout_core.py uses the real,
# device-level, arm-aware rate for actual generation.
CALIBRATION_COMPLETION_RATE = 0.52


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
    completion_rate: float = CALIBRATION_COMPLETION_RATE,
) -> tuple[int, np.ndarray]:
    """One draw of the pool's latent attempt rates and a 20-month simulation
    of checkout attempts, thinned by a flat completion rate to approximate
    actual purchases (D-008: the real, device-level completion model lives
    in checkout_core.py; this is a calibration-time stand-in only).

    Returns the count of customers with >=1 *completed* order in the
    trailing 12 months, and the boolean attempt matrix (pool_size x
    n_months) for reuse.
    """
    latent_rate = rng.gamma(shape=shape, scale=scale, size=pool_size)  # spec 5.1
    p_attempt = 1.0 - np.exp(-latent_rate)  # per-month attempt probability, before seasonality
    n_months = len(seasonal_factors)
    attempts = np.zeros((pool_size, n_months), dtype=bool)
    for m in range(n_months):
        p_month = np.clip(p_attempt * seasonal_factors[m], 0.0, 1.0)
        attempts[:, m] = rng.random(pool_size) < p_month
    # Thin attempts into completions at a flat rate (D-008 calibration stand-in)
    completions = attempts & (rng.random((pool_size, n_months)) < completion_rate)
    trailing_start_idx = n_months - 12
    purchasers_12m = int(completions[:, trailing_start_idx:].any(axis=1).sum())
    return purchasers_12m, attempts


def calibrate_gamma_scale(
    pool_size: int,
    shape: float,
    target_purchasers_12m: int,
    seasonal_factors: np.ndarray,
    rng: np.random.Generator,
    tol: float = 0.01,
    max_iter: int = 25,
) -> CalibrationResult:
    """Solve the Gamma scale so trailing-12m *completed purchasers* matches
    the target, using the flat completion-rate stand-in (D-008). Bisection
    on scale; purchaser count is monotonic in scale for fixed shape, pool
    size, and completion rate.
    """
    lo, hi = 0.01, 8.0
    for i in range(1, max_iter + 1):
        mid = (lo + hi) / 2
        count, _ = _simulate_purchaser_count(pool_size, shape, mid, seasonal_factors, rng)
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
    """Runs the customer-core model. Returns customers, circle_memberships,
    a long-format `checkout_attempts` table (customer_id, year_month), and
    calibration diagnostics for run_manifest.json. No `orders` table (D-008).
    """
    ss = np.random.SeedSequence(seed)
    (calib_seed, region_seed, category_seed, channel_seed, circle_seed) = ss.spawn(5)

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
    p_attempt = 1.0 - np.exp(-latent_rate)
    attempts_bool = np.zeros((pool_size, len(MONTHS)), dtype=bool)
    for m_idx in range(len(MONTHS)):
        p_month = np.clip(p_attempt * seasonal_factors[m_idx], 0.0, 1.0)
        attempts_bool[:, m_idx] = final_rng.random(pool_size) < p_month

    has_ever_attempted = attempts_bool.any(axis=1)
    customer_pool_idx = np.where(has_ever_attempted)[0]
    n_customers = len(customer_pool_idx)

    first_attempt_month_idx = attempts_bool[customer_pool_idx].argmax(axis=1)
    first_attempt_date = MONTHS[first_attempt_month_idx].to_timestamp().normalize()

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
        "first_order_date": first_attempt_date,  # note: first *attempt*; may predate first completed order
        "region": region,
        "acquisition_channel": acquisition_channel,
        "category_affinity": category_affinity,
    })

    # --- Circle membership: selection on attempt propensity --------------
    circle_result = _generate_circle_and_apply_loyalty(
        customers=customers,
        attempts_bool=attempts_bool[customer_pool_idx],
        latent_rate=latent_rate[customer_pool_idx],
        generator_cfg=generator_cfg,
        ground_truth=ground_truth,
        scale=scale,
        rng=np.random.default_rng(circle_seed),
    )
    circle_memberships = circle_result["circle_memberships"]
    diagnostics = circle_result["diagnostics"]

    # --- Long-format checkout attempts, for checkout_core.py to consume ---
    attempt_rows = []
    pool_attempts = attempts_bool[customer_pool_idx]
    for i, cust_id in enumerate(customers["customer_id"].values):
        month_idxs = np.where(pool_attempts[i])[0]
        for m_idx in month_idxs:
            attempt_rows.append((cust_id, str(MONTHS[m_idx])))
    checkout_attempts = pd.DataFrame(attempt_rows, columns=["customer_id", "year_month"])

    manifest = {
        "scale": scale,
        "seed": seed,
        "gamma_shape": generator_cfg["customers"]["gamma_shape"],
        "gamma_scale_calibrated": calib.gamma_scale,
        "calibration_pool_size": calib.pool_size,
        "calibration_iterations": calib.iterations,
        "target_purchasers_12m": target_purchasers_12m,
        "realised_purchasers_12m_at_calibration_approx": calib.realised_purchasers_12m,
        "calibration_completion_rate_stand_in": CALIBRATION_COMPLETION_RATE,
        "n_customers_total_20_months": n_customers,
        **diagnostics,
    }

    return {
        "customers": customers,
        "checkout_attempts": checkout_attempts,
        "circle_memberships": circle_memberships,
        "latent_rate": latent_rate[customer_pool_idx],  # aligned to `customers` row order
        "manifest": manifest,
    }


def _generate_circle_and_apply_loyalty(
    customers: pd.DataFrame,
    attempts_bool: np.ndarray,
    latent_rate: np.ndarray,
    generator_cfg: dict,
    ground_truth: dict,
    scale: float,
    rng: np.random.Generator,
) -> dict:
    """Circle joins by monthly cohort, weighted selection (spec 5.4).

    NOTE (still open, see module docstring): the tenure-based loyalty effect
    on checkout-start rate (ground_truth workstream_2) is not yet applied to
    `attempts_bool` here. Selection (who joins, and the raw-gap calibration)
    is implemented; the dynamic post-join effect on subsequent attempt rates
    is a follow-up, not required for S1-06's conversion-effect scope.
    """
    n = len(customers)
    cohort_sizes_cfg = generator_cfg["circle_membership"]["cohort_sizes"]

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
    cohort_targets = {k: min(v, n) for k, v in cohort_targets.items()}

    median_rate = np.median(latent_rate)
    exponent = _calibrate_selection_exponent(
        attempts_bool=attempts_bool,
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
        attempted_this_month = attempts_bool[:, m_idx] & eligible
        w = np.where(attempted_this_month, w * 3.0, w)  # bias toward checkout joins (70/20/10 target)
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

    # --- Diagnostics: realised selection premium and raw gap (on ATTEMPTS,
    # not completions -- see module docstring; checkout_core.py re-checks
    # the real, completion-based raw gap) -------------------------------
    trailing_start_idx = attempts_bool.shape[1] - 12
    active_trailing = attempts_bool[:, trailing_start_idx:].any(axis=1)
    is_member_by_aug26 = already_joined
    if active_trailing.sum() > 0 and (active_trailing & is_member_by_aug26).any() and (active_trailing & ~is_member_by_aug26).any():
        member_mean_rate = latent_rate[active_trailing & is_member_by_aug26].mean()
        nonmember_mean_rate = latent_rate[active_trailing & ~is_member_by_aug26].mean()
        raw_gap = member_mean_rate / nonmember_mean_rate if nonmember_mean_rate else float("nan")
    else:
        raw_gap = float("nan")

    never_joined_mean = latent_rate[~is_member_by_aug26].mean() if (~is_member_by_aug26).any() else float("nan")
    joiners_mean = latent_rate[is_member_by_aug26].mean() if is_member_by_aug26.any() else float("nan")
    selection_premium_pct = (joiners_mean / never_joined_mean - 1.0) * 100 if never_joined_mean else float("nan")

    diagnostics = {
        "circle_members_generated": int(len(member_idx)),
        "circle_selection_exponent_calibrated": exponent,
        "circle_raw_gap_realised_on_attempts_approx": raw_gap,
        "circle_selection_premium_pct_realised": selection_premium_pct,
    }

    return {"circle_memberships": circle_memberships, "diagnostics": diagnostics}


def _calibrate_selection_exponent(
    attempts_bool: np.ndarray,
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
    """Bisection on the selection exponent so the realised raw gap (member
    vs non-member mean latent attempt-rate, trailing 12m) lands near the
    D-003 target of 1.30x (generator spec 5.4). Uses attempt-rate as the
    proxy, same caveat as elsewhere in this module (D-008).
    """
    lo, hi = 0.0, 4.0
    n = len(latent_rate)
    trailing_start_idx = attempts_bool.shape[1] - 12
    active_trailing = attempts_bool[:, trailing_start_idx:].any(axis=1)

    def raw_gap_for(exponent: float, n_replicates: int = 5) -> float:
        weight = (latent_rate / median_rate) ** exponent
        weight *= np.where(np.isin(region, list(_LONDON_SE)), 1.10, 1.0)
        weight *= np.where(category_affinity == "furniture", 1.10, 1.0)
        gaps = []
        for _ in range(n_replicates):
            rng_local = np.random.default_rng(rng.integers(0, 2**32 - 1))
            already_joined = np.zeros(n, dtype=bool)
            for m_idx in range(attempts_bool.shape[1]):
                target = cohort_targets.get(str(MONTHS[m_idx]), 0)
                if target <= 0:
                    continue
                eligible = ~already_joined
                w = np.where(eligible, weight, 0.0)
                attempted_this_month = attempts_bool[:, m_idx] & eligible
                w = np.where(attempted_this_month, w * 3.0, w)
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


# --- CLI -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the S1-05 customer core (revised, D-008).")
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
    (out_dir / "_manifest").mkdir(parents=True, exist_ok=True)
    (out_dir / "_intermediate").mkdir(parents=True, exist_ok=True)

    result["customers"].to_parquet(out_dir / "customers" / "customers.parquet", index=False)
    result["circle_memberships"].to_parquet(out_dir / "circle_memberships" / "circle_memberships.parquet", index=False)
    # Internal only -- not one of the ten spec tables; checkout_core.py's own
    # run consumes this in-memory when called as a library, this file is for
    # standalone CLI runs / debugging only.
    result["checkout_attempts"].to_parquet(out_dir / "_intermediate" / "checkout_attempts.parquet", index=False)

    with open(out_dir / "_manifest" / "customer_core_manifest.json", "w", encoding="utf-8") as f:
        json.dump(result["manifest"], f, indent=2, default=str)

    print(json.dumps(result["manifest"], indent=2, default=str))


if __name__ == "__main__":
    main()
