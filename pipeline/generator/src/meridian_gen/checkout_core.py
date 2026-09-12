"""Checkout, sessions, experiment_assignments, and orders (S1-06, D-008).

Consumes `customer_core.py`'s customers + checkout_attempts (a long table
of customer_id/year_month pairs -- the propensity to *start* checkout, not
to complete it) and runs the real funnel this project's charter describes:
a device-level completion draw turns attempts into orders, and the
June 2026 test window applies the planted arm effects on top.

Partial scope, per D-007 (S1-06 cut line 5). This module generates
checkout-STARTING sessions only -- not the full 2.4m-session/month
baseline (site browsing that never reaches checkout). That fuller session
volume is explicitly deferred to Sprint 2. One session is generated per
checkout-starting visitor per month; the "completers sometimes have two
sessions" nuance in spec 5.2 is folded into that same deferral.

Anonymous checkout starters (visitors with no prior customer_id) are
generated to fill each month's starter count up to the D-003 baseline,
since most monthly checkout starters are not existing customers. An
anonymous starter who completes becomes a new customer at that order,
per spec 5.2; one who doesn't remains anonymous and leaves no other trace.

Known, disclosed simplifications (not hidden, flagged for a follow-up):
1. Each customer/visitor attempts checkout at most once per month
   (matches customer_core.py's boolean attempt model) -- the "some
   visitors have two checkout sessions" texture in spec 5.2 is not
   modelled; out of scope for the partial S1-06 cut.
2. The 15% multi-visitor-id rate (spec 5.1) is not applied; each customer
   has exactly one stable visitor_id.
3. Anonymous visitors who convert become new customers *after*
   customer_core.py's own Circle-membership selection has already run, so
   they are not eligible for Circle membership in this pass. A real
   single-pass generator would interleave these; this two-module split
   trades that fidelity for keeping customer_core.py self-contained and
   independently testable (D-008).
4. mp_applications / mp_agreements / mp_decision events are not emitted
   here -- Meridian Pay's own tables are S1-07. `payment_method` on
   `orders` and the `checkout_events.payment_method` field are set, but
   the Meridian-Pay-specific events (mp_application_submitted, mp_decision)
   wait for S1-07 to exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from customer_core import (
    MONTHS,
    ITL1_REGIONS,
    CATEGORIES,
    _LONDON_SE,
    region_weights,
    monthly_seasonal_factor,
    load_configs,
    run_customer_core,
)

EXPERIMENT_WINDOW_START = pd.Timestamp("2026-06-01")
EXPERIMENT_WINDOW_END = pd.Timestamp("2026-06-14")  # inclusive
EXPERIMENT_MONTH = pd.Period("2026-06", freq="M")

WEEKDAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _weekly_factor_array(baselines: dict) -> np.ndarray:
    """Index 0 = Monday ... 6 = Sunday, matching pandas .dayofweek."""
    weekly = baselines["seasonality"]["weekly"]
    return np.array([weekly[day] for day in WEEKDAY_KEYS], dtype=float)


def _visitor_id_for_customer(customer_id: int, seed: int) -> str:
    """Stable, deterministic 16-hex-char visitor_id for an existing customer."""
    h = hashlib.sha256(f"{seed}-cust-{customer_id}".encode()).hexdigest()
    return h[:16]


def _hash_arm(visitor_id: str, experiment_id: str) -> str:
    """Deterministic hash(visitor_id, experiment_id), 50/50 (spec 4.4)."""
    h = hashlib.md5(f"{visitor_id}-{experiment_id}".encode()).hexdigest()
    return "test" if int(h, 16) % 2 == 0 else "control"


def _draw_days_in_month(period: pd.Period, n: int, weekly_factor: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Vectorised weighted day-of-month draw, weighted by weekday seasonality."""
    days_in_month = period.days_in_month
    day_dates = pd.date_range(period.to_timestamp(), periods=days_in_month, freq="D")
    weights = weekly_factor[day_dates.dayofweek.values]
    p = weights / weights.sum()
    return rng.choice(np.arange(1, days_in_month + 1), size=n, p=p)


def _payment_method_probs(mp_share_pct: float, baseline_shares_pct: dict) -> tuple[list[str], np.ndarray]:
    """Scale non-MP shares proportionally so they sum to 100 - mp_share_pct
    (spec 7.1: only the Meridian Pay share moves; the mechanism note says
    "everything else is identical between arms" in relative proportion)."""
    methods = list(baseline_shares_pct.keys())
    other_methods = [m for m in methods if m != "meridian_pay"]
    other_baseline_sum = sum(baseline_shares_pct[m] for m in other_methods)
    remaining = 100.0 - mp_share_pct
    p = []
    for m in methods:
        if m == "meridian_pay":
            p.append(mp_share_pct)
        else:
            p.append(baseline_shares_pct[m] / other_baseline_sum * remaining)
    p = np.array(p, dtype=float)
    p /= p.sum()
    return methods, p


def run_checkout_core(
    scale: float,
    seed: int,
    baselines: dict,
    generator_cfg: dict,
    ground_truth: dict,
    customer_result: dict,
) -> dict:
    customers = customer_result["customers"].copy()
    attempts = customer_result["checkout_attempts"]
    next_customer_id = int(customers["customer_id"].max()) + 1 if len(customers) else 1

    attempts_by_month: dict[str, set] = {}
    for ym, grp in attempts.groupby("year_month"):
        attempts_by_month[ym] = set(grp["customer_id"].tolist())

    customer_visitor_id = {
        cid: _visitor_id_for_customer(cid, seed) for cid in customers["customer_id"].values
    }

    weekly_factor = _weekly_factor_array(baselines)
    checkout_starters_target = baselines["checkout_starters_per_month"]
    experiment_id = generator_cfg["experiment"]["experiment_id"]

    device_shares_pct = generator_cfg["sessions"]["device_shares_pct"]
    devices = list(device_shares_pct.keys())
    device_p = np.array([device_shares_pct[d] for d in devices], dtype=float)
    device_p /= device_p.sum()

    channel_shares_pct = generator_cfg["sessions"]["channel_shares_pct"]
    channels = list(channel_shares_pct.keys())
    channel_p = np.array([channel_shares_pct[c] for c in channels], dtype=float)
    channel_p /= channel_p.sum()

    completion_control_pct = generator_cfg["checkout_and_orders"]["completion_rate_by_device_pct"]
    conversion_effect = ground_truth["workstream_1_checkout_redesign"]["effects"]["checkout_completion_pct"]["planted_change_pp"]
    completion_test_pct = {d: completion_control_pct[d] + conversion_effect for d in devices}

    mp_control_pct = ground_truth["workstream_1_checkout_redesign"]["effects"]["mp_share_of_orders_pct"]["control"]
    mp_test_pct = ground_truth["workstream_1_checkout_redesign"]["effects"]["mp_share_of_orders_pct"]["test"]
    baseline_payment_shares = generator_cfg["checkout_and_orders"]["payment_method_shares_pct"]

    order_cfg = generator_cfg["checkout_and_orders"]["order_value"]
    item_cfg = generator_cfg["checkout_and_orders"]["item_count"]
    multipliers = order_cfg["category_multipliers"]
    sigma = order_cfg["sigma"]

    ss = np.random.SeedSequence(seed + 1)  # offset from customer_core's seed use
    month_seeds = ss.spawn(len(MONTHS))

    session_rows = []
    event_rows = []
    order_rows = []  # raw_value not yet rescaled
    assignment_rows = []
    new_customer_rows = []

    session_id = 1
    event_id = 1
    order_id = 1

    for m_idx, period in enumerate(MONTHS):
        ym = str(period)
        rng = np.random.default_rng(month_seeds[m_idx])

        existing_ids = sorted(attempts_by_month.get(ym, set()))
        seasonal_factor = monthly_seasonal_factor(period, baselines)
        target = round(checkout_starters_target * seasonal_factor * scale)
        n_anon = max(target - len(existing_ids), 0)

        starter_customer_ids = list(existing_ids) + [None] * n_anon
        n_starters = len(starter_customer_ids)
        if n_starters == 0:
            continue

        visitor_ids = []
        for cid in starter_customer_ids:
            if cid is not None:
                visitor_ids.append(customer_visitor_id[cid])
            else:
                visitor_ids.append(rng.bytes(8).hex())

        days = _draw_days_in_month(period, n_starters, weekly_factor, rng)
        hours = rng.integers(0, 24, size=n_starters)
        minutes = rng.integers(0, 60, size=n_starters)
        session_start_ts = [
            period.to_timestamp() + pd.Timedelta(days=int(d) - 1, hours=int(h), minutes=int(mn))
            for d, h, mn in zip(days, hours, minutes)
        ]

        device_draw = rng.choice(devices, size=n_starters, p=device_p)
        channel_draw = rng.choice(channels, size=n_starters, p=channel_p)
        landing_options = CATEGORIES + ["home"]
        landing_draw = rng.choice(landing_options, size=n_starters)

        in_window = np.array([
            period == EXPERIMENT_MONTH and EXPERIMENT_WINDOW_START.day <= d <= EXPERIMENT_WINDOW_END.day
            for d in days
        ])
        arms = np.array([
            _hash_arm(vid, experiment_id) if w else "n/a"
            for vid, w in zip(visitor_ids, in_window)
        ])

        completion_prob = np.empty(n_starters)
        mp_share_pct = np.empty(n_starters)
        for i in range(n_starters):
            dev = device_draw[i]
            if in_window[i] and arms[i] == "test":
                completion_prob[i] = completion_test_pct[dev] / 100.0
                mp_share_pct[i] = mp_test_pct
            else:
                completion_prob[i] = completion_control_pct[dev] / 100.0
                mp_share_pct[i] = mp_control_pct
        completed = rng.random(n_starters) < completion_prob

        checkout_version = np.where(in_window, np.where(arms == "test", "v2", "v1"), "v1")

        for i in range(n_starters):
            sid = session_id
            session_id += 1
            cid = starter_customer_ids[i]
            session_rows.append({
                "session_id": sid,
                "visitor_id": visitor_ids[i],
                "customer_id": cid if cid is not None else None,
                "session_start_ts": session_start_ts[i],
                "device": device_draw[i],
                "channel": channel_draw[i],
                "landing_category": landing_draw[i],
            })

            event_rows.append({
                "event_id": event_id,
                "session_id": sid,
                "visitor_id": visitor_ids[i],
                "event_ts": session_start_ts[i],
                "event_type": "checkout_started",
                "checkout_version": checkout_version[i],
                "payment_method": None,
                "order_id": None,
                "application_id": None,
                "mp_decision": None,
            })
            event_id += 1

            if in_window[i]:
                assignment_rows.append({
                    "visitor_id": visitor_ids[i],
                    "experiment_id": experiment_id,
                    "arm": arms[i],
                    "assigned_at": session_start_ts[i],
                })

            if completed[i]:
                final_cid = cid
                if final_cid is None:
                    final_cid = next_customer_id
                    next_customer_id += 1
                    new_customer_rows.append({
                        "customer_id": final_cid,
                        "first_order_date": session_start_ts[i].normalize(),
                        "region_seed_i": i,  # placeholder, filled below
                        "month_idx": m_idx,
                    })

                methods, probs = _payment_method_probs(mp_share_pct[i], baseline_payment_shares)
                payment_method = rng.choice(methods, p=probs)

                cat = rng.choice(CATEGORIES)
                base_value = rng.lognormal(mean=0.0, sigma=sigma)
                raw_value = base_value * multipliers[cat]
                item_count = min(int(rng.poisson(item_cfg["lambda"])) + 1, item_cfg["cap"])

                oid = order_id
                order_id += 1
                order_rows.append({
                    "order_id": oid,
                    "customer_id": final_cid,
                    "visitor_id": visitor_ids[i],
                    "session_id": sid,
                    "order_ts": session_start_ts[i],
                    "order_value_gbp_raw": raw_value,
                    "item_count": item_count,
                    "category_primary": cat,
                    "payment_method": payment_method,
                })

                event_rows.append({
                    "event_id": event_id,
                    "session_id": sid,
                    "visitor_id": visitor_ids[i],
                    "event_ts": session_start_ts[i] + pd.Timedelta(minutes=3),
                    "event_type": "order_placed",
                    "checkout_version": None,
                    "payment_method": payment_method,
                    "order_id": oid,
                    "application_id": None,
                    "mp_decision": None,
                })
                event_id += 1
            else:
                event_rows.append({
                    "event_id": event_id,
                    "session_id": sid,
                    "visitor_id": visitor_ids[i],
                    "event_ts": session_start_ts[i] + pd.Timedelta(minutes=2),
                    "event_type": "checkout_abandoned",
                    "checkout_version": None,
                    "payment_method": None,
                    "order_id": None,
                    "application_id": None,
                    "mp_decision": None,
                })
                event_id += 1

    sessions = pd.DataFrame(session_rows)
    checkout_events = pd.DataFrame(event_rows)
    experiment_assignments = pd.DataFrame(assignment_rows).drop_duplicates(subset=["visitor_id"], keep="first")
    orders = pd.DataFrame(order_rows)

    # Region/category/channel for newly-acquired anonymous customers (spec 5.1
    # shares), appended to `customers`. Known limitation: not eligible for
    # Circle membership in this pass (module docstring point 3).
    if new_customer_rows:
        gen_rng = np.random.default_rng(seed + 2)
        n_new = len(new_customer_rows)
        weights = region_weights(generator_cfg["customers"]["region_weighting"]["london_and_south_east_overweight_pct"])
        new_region = gen_rng.choice(ITL1_REGIONS, size=n_new, p=weights)
        new_category = gen_rng.choice(CATEGORIES, size=n_new)
        chshares = generator_cfg["sessions"]["channel_shares_pct"]
        chnames = list(chshares.keys())
        chp = np.array([chshares[c] for c in chnames], dtype=float)
        chp /= chp.sum()
        new_channel = gen_rng.choice(chnames, size=n_new, p=chp)
        new_customers_df = pd.DataFrame({
            "customer_id": [r["customer_id"] for r in new_customer_rows],
            "first_order_date": [r["first_order_date"] for r in new_customer_rows],
            "region": new_region,
            "acquisition_channel": new_channel,
            "category_affinity": new_category,
        })
        customers = pd.concat([customers, new_customers_df], ignore_index=True)

    # Rescale order value to the D-003 mean, clip, round (same approach as
    # the superseded customer_core.py order builder)
    if len(orders) > 0:
        target_mean = order_cfg["rescale_to_mean_gbp"]
        current_mean = orders["order_value_gbp_raw"].mean()
        scale_factor = target_mean / current_mean if current_mean > 0 else 1.0
        orders["order_value_gbp"] = (
            orders["order_value_gbp_raw"] * scale_factor
        ).clip(order_cfg["clip_min_gbp"], order_cfg["clip_max_gbp"]).round(2)
        orders = orders.drop(columns=["order_value_gbp_raw"])
        orders["delivery_region"] = orders["customer_id"].map(
            customers.set_index("customer_id")["region"]
        )

    # --- Diagnostics -------------------------------------------------------
    n_control_starters = int((arms != "test").sum()) if len(assignment_rows) else 0  # last month only; see below
    diagnostics = _compute_diagnostics(sessions, checkout_events, orders, experiment_assignments)

    manifest = {
        "scale": scale,
        "seed": seed,
        "n_sessions": len(sessions),
        "n_checkout_events": len(checkout_events),
        "n_orders": len(orders),
        "n_experiment_assignments": len(experiment_assignments),
        "n_new_customers_from_anonymous_completers": len(new_customer_rows),
        **diagnostics,
    }

    return {
        "customers": customers,
        "sessions": sessions,
        "checkout_events": checkout_events,
        "experiment_assignments": experiment_assignments,
        "orders": orders,
        "manifest": manifest,
    }


def _compute_diagnostics(sessions, checkout_events, orders, experiment_assignments) -> dict:
    """All diagnostics are scoped to the experiment window itself: a visitor's
    checkout_started events (and any resulting order) OUTSIDE the window are
    irrelevant to whether their in-window checkout converted or which arm's
    checkout_version they saw. Session-level, not visitor-level lifetime
    membership -- a visitor who orders in some other month is not "completed"
    for the purposes of their June test-window session.
    """
    diag = {}
    if len(experiment_assignments) == 0:
        return diag

    starters = checkout_events[checkout_events["event_type"] == "checkout_started"].copy()
    starters["event_ts"] = pd.to_datetime(starters["event_ts"])
    in_window_mask = (starters["event_ts"] >= EXPERIMENT_WINDOW_START) & (
        starters["event_ts"] < EXPERIMENT_WINDOW_END + pd.Timedelta(days=1)
    )
    window_starters = starters[in_window_mask].copy()

    assign = experiment_assignments.set_index("visitor_id")["arm"]
    window_starters = window_starters[window_starters["visitor_id"].isin(assign.index)].copy()
    window_starters["arm"] = window_starters["visitor_id"].map(assign)

    order_placed = checkout_events[checkout_events["event_type"] == "order_placed"]
    sessions_with_order = set(order_placed["session_id"].unique())
    window_starters["completed"] = window_starters["session_id"].isin(sessions_with_order)

    for arm in ["control", "test"]:
        arm_starters = window_starters[window_starters["arm"] == arm]
        n = len(arm_starters)
        n_completed = int(arm_starters["completed"].sum())
        diag[f"{arm}_starters"] = n
        diag[f"{arm}_completion_rate_pct"] = round(100 * n_completed / n, 3) if n else None

    n_test = diag.get("test_starters", 0)
    n_control = diag.get("control_starters", 0)
    diag["arm_split_test_pct"] = round(100 * n_test / (n_test + n_control), 2) if (n_test + n_control) else None

    # Scoped to the window only: a visitor appearing in both v1 and v2 among
    # their in-window checkout_started events would be a real violation.
    dual_arm_visitors = window_starters.groupby("visitor_id")["checkout_version"].nunique()
    diag["visitors_with_multiple_versions_in_window"] = int((dual_arm_visitors > 1).sum())

    return diag


# --- CLI -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate S1-06 checkout/sessions/experiment/orders (D-008).")
    parser.add_argument("--scale", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260907)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    generator_root = Path(__file__).resolve().parent.parent.parent
    baselines, generator_cfg, ground_truth = load_configs(generator_root)

    customer_result = run_customer_core(args.scale, args.seed, generator_root, baselines, generator_cfg, ground_truth)
    result = run_checkout_core(args.scale, args.seed, baselines, generator_cfg, ground_truth, customer_result)

    out_dir = Path(args.out) if args.out else generator_root.parent / "data" / "raw"
    for sub in ["customers", "sessions", "checkout_events", "experiment_assignments", "orders", "_manifest"]:
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    result["customers"].to_parquet(out_dir / "customers" / "customers.parquet", index=False)
    result["sessions"].to_parquet(out_dir / "sessions" / "sessions.parquet", index=False)
    result["checkout_events"].to_parquet(out_dir / "checkout_events" / "checkout_events.parquet", index=False)
    result["experiment_assignments"].to_parquet(out_dir / "experiment_assignments" / "experiment_assignments.parquet", index=False)
    result["orders"].to_parquet(out_dir / "orders" / "orders.parquet", index=False)

    with open(out_dir / "_manifest" / "checkout_core_manifest.json", "w", encoding="utf-8") as f:
        json.dump(result["manifest"], f, indent=2, default=str)

    print(json.dumps(result["manifest"], indent=2, default=str))


if __name__ == "__main__":
    main()
