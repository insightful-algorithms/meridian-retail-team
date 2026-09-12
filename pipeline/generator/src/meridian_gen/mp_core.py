"""Meridian Pay: mp_applications, mp_agreements, mp_instalments, mp_payments
(S1-07). Spec 4.6 to 4.9, 5.3.

Post-processes `checkout_core.py`'s (S1-06) output. Spec 5.3 describes the
Meridian Pay application as part of the same checkout attempt, resolved
*before* completion is finalised: a visitor who selects Meridian Pay
applies; a DECLINED applicant either still completes by card (45%) or
abandons (55%) -- both inside the 52% completion rate, not on top of it.

checkout_core.py already drew `payment_method` for every completed
session, including "meridian_pay" at a flat share, with no
application/decline step behind it. This module re-processes every such
order: draws a credit band and a decision (using the same
approved-share -> application-share algebra the spec's own generator.yaml
values were derived from, so this reproduces those figures rather than
just assuming them); approved orders get an agreement built; declined
orders are either relabelled to "card" (order survives) or REVERSED --
turned back into an abandoned checkout, with the order, any new-customer
row it created, and the application's own `order_id` all rolled back
together, consistently.

Disclosed simplification. This is algebraically equivalent to running the
application step inline during checkout (the spec's stated order), but
implemented as a correction pass over already-completed sessions rather
than one interleaved loop -- so S1-06 and S1-07 stay independently
buildable and testable (same trade as D-008's module split). Practical
effect: a small share of S1-06's "completed" sessions
(~12% decline x 24% MP share x 55% abandon =~ 1.6% of MP-selecting
starters) get demoted to abandoned here. So this module's realised
overall completion rate runs a little below S1-06's own raw figure --
expected, and checked in THIS module's tests, not S1-06's.

Not yet modelled (flagged, not required for S1-07's stated scope): the
`payment_method_selected` event type (spec 4.3's event list) is not
emitted; only `checkout_started`, `order_placed`/`checkout_abandoned`,
and now `mp_application_submitted`/`mp_decision` are.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from customer_core import load_configs, run_customer_core
from checkout_core import run_checkout_core

BANDS = ["A", "B", "C", "D", "E"]


def _application_shares_from_approved_target(approved_pct: dict, decline_pct: dict) -> dict:
    """Back out application-band shares from a target APPROVED mix and the
    (unchanged) band decline rates: application_share ∝ approved_share /
    (1 - decline_rate), normalised to 100. This is the same algebra that
    produced generator.yaml's control application shares (27.5/28.4/22.0/
    13.9/8.3) from the D-003 approved mix (30/30/22/12/6) -- reusing it for
    the test arm's shifted approved mix (28/29/22/14/7) reproduces the
    ground-truth test decline rate (12.8%) without hand-coding it.
    """
    raw = {b: approved_pct[b] / (1 - decline_pct[b] / 100.0) for b in BANDS}
    total = sum(raw.values())
    return {b: raw[b] / total * 100.0 for b in BANDS}


def _weighted_cure_day(rng: np.random.Generator, n: int) -> np.ndarray:
    """Cure day in [1, 59], weighted toward the first fortnight (spec 5.3).
    Simplification, disclosed: a Beta(2, 5) shape scaled to the window
    approximates "weighted to the first fortnight" without trying to match
    an unspecified exact distribution.
    """
    return np.clip((rng.beta(2, 5, size=n) * 59).astype(int) + 1, 1, 59)


def _reporting_lag_days(rng: np.random.Generator, n: int) -> np.ndarray:
    """Spec 5.3: 0 days 85%, 1-3 days 10%, 4-14 days 4%, 15-45 days 1%."""
    bucket = rng.choice([0, 1, 2, 3], size=n, p=[0.85, 0.10, 0.04, 0.01])
    lag = np.zeros(n, dtype=int)
    lag[bucket == 1] = rng.integers(1, 4, size=(bucket == 1).sum())
    lag[bucket == 2] = rng.integers(4, 15, size=(bucket == 2).sum())
    lag[bucket == 3] = rng.integers(15, 46, size=(bucket == 3).sum())
    return lag


def _calibrate_cure_rate(
    band_labels: np.ndarray,
    day30_miss_by_band_frac: dict,
    target_default_pct_of_value: float,
    agreement_values: np.ndarray,
    rng: np.random.Generator,
    tol: float = 0.05,
    max_iter: int = 20,
) -> float:
    """Bisection on a single, band-independent cure probability so overall
    written-off value lands near the D-003 target (1.9% of agreement
    value). Spec 5.3: cure probability is common across bands by design,
    which is what keeps default proportional to the miss rate.

    Mirrors the FULL default mechanic used in the actual generation loop
    (instalment 2 missed-and-never-cured, OR instalment 2 cured but
    instalment 3 missed-and-never-cured) -- an earlier version of this
    function modelled only the instalment-2 path and under-counted
    defaults, which silently pushed the realised write-off rate above
    target even at a near-zero cure probability. Fixed before handoff by
    testing against the actual figures, not assuming the simplified proxy
    was equivalent.
    """
    n = len(agreement_values)
    miss2_prob = np.array([day30_miss_by_band_frac[b] for b in band_labels])
    amt2 = agreement_values / 3.0
    amt3 = agreement_values / 3.0  # approximation: ignores the penny remainder on instalment 1, immaterial here

    lo, hi = 0.0, 1.0

    def written_off_pct(p_cure: float, n_replicates: int = 5) -> float:
        """Averaged over several fresh draws (same fix customer_core.py's
        selection-exponent calibration already needed once: a single noisy
        draw at this population size has more sampling noise than the
        convergence tolerance itself, which can lock the bisection onto a
        wrong value from bad luck rather than the true relationship).
        """
        pct_draws = []
        for _ in range(n_replicates):
            inst2_missed = rng.random(n) < miss2_prob
            inst2_cured = inst2_missed & (rng.random(n) < p_cure)
            never_cured_at_2 = inst2_missed & ~inst2_cured

            inst3_prob = np.where(never_cured_at_2, 0.0, np.where(inst2_cured, miss2_prob, miss2_prob / 2.0))
            inst3_missed = (rng.random(n) < inst3_prob) & ~never_cured_at_2
            inst3_cured = inst3_missed & (rng.random(n) < p_cure)
            never_cured_at_3 = inst3_missed & ~inst3_cured

            written_off = np.where(never_cured_at_2, amt2 + amt3, np.where(never_cured_at_3, amt3, 0.0))
            pct_draws.append(100.0 * written_off.sum() / agreement_values.sum() if agreement_values.sum() > 0 else 0.0)
        return float(np.mean(pct_draws))

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        wo = written_off_pct(mid)
        if abs(wo - target_default_pct_of_value) <= tol:
            return mid
        if wo > target_default_pct_of_value:
            lo = mid  # write-off too high -> more cures needed -> raise cure prob
        else:
            hi = mid
    return mid


def run_mp_core(
    scale: float,
    seed: int,
    baselines: dict,
    generator_cfg: dict,
    ground_truth: dict,
    checkout_result: dict,
) -> dict:
    sessions = checkout_result["sessions"].copy()
    checkout_events = checkout_result["checkout_events"].copy()
    orders = checkout_result["orders"].copy()
    customers = checkout_result["customers"].copy()
    experiment_assignments = checkout_result["experiment_assignments"]

    decline_pct = generator_cfg["meridian_pay"]["band_decline_rates_pct"]
    control_approved_pct = {
        b: baselines["credit_bands_approved_share"][b] * 100 if baselines["credit_bands_approved_share"][b] <= 1
        else baselines["credit_bands_approved_share"][b]
        for b in BANDS
    }
    test_approved_pct = ground_truth["workstream_1_checkout_redesign"]["effects"]["mp_band_shares_pct"]["test"]

    control_app_shares = _application_shares_from_approved_target(control_approved_pct, decline_pct)
    test_app_shares = _application_shares_from_approved_target(test_approved_pct, decline_pct)

    ss = np.random.SeedSequence(seed + 3)  # offset from customer_core (seed) and checkout_core (seed+1, +2)
    rng = np.random.default_rng(ss)

    mp_orders_mask = orders["payment_method"] == "meridian_pay"
    mp_orders = orders[mp_orders_mask].copy()
    n_mp = len(mp_orders)

    assign = experiment_assignments.set_index("visitor_id")["arm"] if len(experiment_assignments) else pd.Series(dtype=object)
    mp_orders["arm"] = mp_orders["visitor_id"].map(assign).fillna("control")

    is_test = (mp_orders["arm"] == "test").values
    credit_band = np.empty(n_mp, dtype=object)
    if is_test.any():
        p_test = np.array([test_app_shares[b] for b in BANDS])
        p_test /= p_test.sum()
        credit_band[is_test] = rng.choice(BANDS, size=is_test.sum(), p=p_test)
    if (~is_test).any():
        p_control = np.array([control_app_shares[b] for b in BANDS])
        p_control /= p_control.sum()
        credit_band[~is_test] = rng.choice(BANDS, size=(~is_test).sum(), p=p_control)
    mp_orders["credit_band"] = credit_band

    decline_prob = mp_orders["credit_band"].map(lambda b: decline_pct[b] / 100.0).values
    declined = rng.random(n_mp) < decline_prob

    declined_outcome_cfg = generator_cfg["meridian_pay"]["declined_applicant_outcome"]
    still_completes_prob = declined_outcome_cfg["pays_by_card_and_completes_pct"] / 100.0
    outcome_roll = rng.random(n_mp)
    reroute_to_card = declined & (outcome_roll < still_completes_prob)
    abandon = declined & ~reroute_to_card
    approved = ~declined

    mp_orders["decision"] = np.where(approved, "approved", "declined")
    mp_orders["applied_at"] = pd.to_datetime(mp_orders["order_ts"]) - pd.Timedelta(minutes=1)

    application_ids = np.arange(1, n_mp + 1, dtype=np.int64)
    mp_applications = pd.DataFrame({
        "application_id": application_ids,
        "session_id": mp_orders["session_id"].values,
        "customer_id": mp_orders["customer_id"].values,
        "visitor_id": mp_orders["visitor_id"].values,
        "applied_at": mp_orders["applied_at"].values,
        "requested_value_gbp": mp_orders["order_value_gbp"].values,
        "credit_band": mp_orders["credit_band"].values,
        "decision": mp_orders["decision"].values,
        "order_id": np.where(abandon, np.nan, mp_orders["order_id"].values),
    })
    mp_applications["order_id"] = mp_applications["order_id"].astype("Int64")

    # --- Reroute declined-but-still-completing orders to card -----------
    reroute_order_ids = set(mp_orders.loc[reroute_to_card, "order_id"])
    orders.loc[orders["order_id"].isin(reroute_order_ids), "payment_method"] = "card"

    # --- Reverse declined-and-abandoned orders ---------------------------
    abandon_order_ids = set(mp_orders.loc[abandon, "order_id"])
    abandon_session_ids = set(mp_orders.loc[abandon, "session_id"])
    abandon_new_customer_ids = set(mp_orders.loc[abandon, "customer_id"]) if abandon.any() else set()

    orders = orders[~orders["order_id"].isin(abandon_order_ids)].copy()

    is_abandon_event = checkout_events["order_id"].isin(abandon_order_ids)
    checkout_events.loc[is_abandon_event, "event_type"] = "checkout_abandoned"
    checkout_events.loc[is_abandon_event, "order_id"] = pd.NA
    checkout_events.loc[is_abandon_event, "payment_method"] = None

    sessions.loc[sessions["session_id"].isin(abandon_session_ids), "customer_id"] = None

    # Roll back new-customer rows created for now-abandoned orders. A new
    # customer created by checkout_core.py exists ONLY because this order
    # completed; if it's reversed, that customer never existed.
    surviving_orders_customer_ids = set(orders["customer_id"].unique())
    customer_ids_to_drop = {
        cid for cid in abandon_new_customer_ids if cid not in surviving_orders_customer_ids
    }
    customers = customers[~customers["customer_id"].isin(customer_ids_to_drop)].copy()

    # A rolled-back customer_id must not survive anywhere else that
    # referenced it -- including the application row itself (spec 4.6:
    # a declined-and-abandoned first-time applicant never becomes a
    # customer, and this is the one table where customer_id may be null).
    mp_applications.loc[mp_applications["customer_id"].isin(customer_ids_to_drop), "customer_id"] = pd.NA
    mp_applications["customer_id"] = mp_applications["customer_id"].astype("Int64")

    # --- Build agreements, instalments, payments for approved orders -----
    approved_orders = mp_orders.loc[approved].copy()
    n_approved = len(approved_orders)
    agreement_ids = np.arange(1, n_approved + 1, dtype=np.int64)
    approved_app_ids = application_ids[approved]

    order_cfg = generator_cfg["checkout_and_orders"]
    day30_miss_by_band_frac = {
        b: (baselines["mp_day30_miss_rate_by_band"][b] if baselines["mp_day30_miss_rate_by_band"][b] <= 1
            else baselines["mp_day30_miss_rate_by_band"][b] / 100.0)
        for b in BANDS
    }
    extract_at = pd.Timestamp(generator_cfg["run_defaults"]["extract_at"].replace("Z", ""))

    start_dates = pd.to_datetime(approved_orders["order_ts"].values).normalize()
    agreement_values = approved_orders["order_value_gbp"].values
    bands_approved = approved_orders["credit_band"].values

    cure_rate = _calibrate_cure_rate(
        band_labels=bands_approved,
        day30_miss_by_band_frac=day30_miss_by_band_frac,
        target_default_pct_of_value=baselines["mp_90day_default_rate_of_value"] * 100,
        agreement_values=agreement_values,
        rng=np.random.default_rng(rng.integers(0, 2**32 - 1)),
    )

    mp_agreements_rows = []
    mp_instalments_rows = []
    mp_payments_rows = []
    instalment_id = 1
    payment_id = 1

    for i in range(n_approved):
        band = bands_approved[i]
        miss2_prob = day30_miss_by_band_frac[band]
        start_date = start_dates[i]
        value = agreement_values[i]
        amt = round(value / 3, 2)
        amounts = [round(value - 2 * amt, 2), amt, amt]  # remainder on instalment 1
        due_dates = [start_date, start_date + pd.Timedelta(days=30), start_date + pd.Timedelta(days=60)]

        inst2_missed = rng.random() < miss2_prob
        inst2_cured = inst2_missed and (rng.random() < cure_rate)
        if inst2_missed and not inst2_cured:
            inst3_prob = None  # not paid, per spec
        elif inst2_missed and inst2_cured:
            inst3_prob = miss2_prob
        else:
            inst3_prob = miss2_prob / 2.0
        inst3_missed = (inst3_prob is not None) and (rng.random() < inst3_prob)
        inst3_cured = inst3_missed and (rng.random() < cure_rate)

        agreement_id = agreement_ids[i]
        for inst_no in (1, 2, 3):
            iid = instalment_id
            instalment_id += 1
            mp_instalments_rows.append({
                "instalment_id": iid,
                "agreement_id": agreement_id,
                "instalment_no": inst_no,
                "due_date": due_dates[inst_no - 1],
                "amount_gbp": amounts[inst_no - 1],
            })

            paid_at = None
            if inst_no == 1:
                paid_at = due_dates[0]
            elif inst_no == 2:
                if not inst2_missed:
                    paid_at = due_dates[1]
                elif inst2_cured:
                    paid_at = due_dates[1] + pd.Timedelta(days=int(_weighted_cure_day(rng, 1)[0]))
            elif inst_no == 3:
                if inst3_prob is None:
                    paid_at = None  # instalment 2 never cured -> instalment 3 not paid
                elif not inst3_missed:
                    paid_at = due_dates[2]
                elif inst3_cured:
                    paid_at = due_dates[2] + pd.Timedelta(days=int(_weighted_cure_day(rng, 1)[0]))

            if paid_at is not None:
                lag_days = int(_reporting_lag_days(rng, 1)[0])
                recorded_at = paid_at + pd.Timedelta(days=lag_days)
                if recorded_at <= extract_at:
                    mp_payments_rows.append({
                        "payment_id": payment_id,
                        "instalment_id": iid,
                        "agreement_id": agreement_id,
                        "paid_at": paid_at,
                        "amount_gbp": amounts[inst_no - 1],
                        "recorded_at": recorded_at,
                    })
                    payment_id += 1

        # True status at extract (see module docstring: reflects the actual
        # underlying state, not what reporting lag lets the payments table
        # show -- that gap is the maturity rule's whole point downstream).
        never_paid_amounts = 0.0
        if inst2_missed and not inst2_cured:
            never_paid_amounts += amounts[1] + amounts[2]  # inst 3 also never paid, per spec
        elif inst3_missed and not inst3_cured:
            never_paid_amounts += amounts[2]

        matured = (start_date + pd.Timedelta(days=90)) <= extract_at
        if never_paid_amounts > 0 and matured:
            status = "defaulted"
            written_off = round(never_paid_amounts, 2)
        elif never_paid_amounts > 0 and not matured:
            status = "active"
            written_off = 0.0
        else:
            status = "settled" if matured else "active"
            written_off = 0.0

        mp_agreements_rows.append({
            "agreement_id": agreement_id,
            "application_id": int(approved_app_ids[i]),
            "order_id": int(approved_orders["order_id"].values[i]),
            "customer_id": int(approved_orders["customer_id"].values[i]),
            "agreement_value_gbp": value,
            "start_date": start_date.date(),
            "status_at_extract": status,
            "written_off_value_gbp": written_off,
        })

    mp_agreements = pd.DataFrame(mp_agreements_rows)
    mp_instalments = pd.DataFrame(mp_instalments_rows)
    mp_payments = pd.DataFrame(mp_payments_rows)

    diagnostics = _compute_diagnostics(
        mp_applications, mp_agreements, mp_instalments, orders, checkout_events
    )
    manifest = {
        "scale": scale,
        "seed": seed,
        "n_mp_applications": len(mp_applications),
        "n_mp_agreements": len(mp_agreements),
        "n_mp_instalments": len(mp_instalments),
        "n_mp_payments": len(mp_payments),
        "n_declined_rerouted_to_card": int(reroute_to_card.sum()),
        "n_declined_abandoned": int(abandon.sum()),
        "cure_rate_calibrated": cure_rate,
        **diagnostics,
    }

    return {
        "customers": customers,
        "sessions": sessions,
        "checkout_events": checkout_events,
        "orders": orders,
        "mp_applications": mp_applications,
        "mp_agreements": mp_agreements,
        "mp_instalments": mp_instalments,
        "mp_payments": mp_payments,
        "manifest": manifest,
    }


def _compute_diagnostics(mp_applications, mp_agreements, mp_instalments, orders, checkout_events) -> dict:
    diag = {}
    n_apps = len(mp_applications)
    if n_apps == 0:
        return diag
    n_declined = int((mp_applications["decision"] == "declined").sum())
    diag["realised_decline_rate_pct"] = round(100 * n_declined / n_apps, 3)

    band_counts = mp_applications.loc[mp_applications["decision"] == "approved", "credit_band"].value_counts(normalize=True) * 100
    diag["realised_approved_band_shares_pct"] = {b: round(band_counts.get(b, 0.0), 2) for b in BANDS}

    orders_after = orders[orders["payment_method"] == "meridian_pay"]
    diag["n_orders_paid_by_mp"] = int(len(orders_after))
    if len(orders) > 0:
        diag["realised_mp_share_of_orders_pct"] = round(100 * len(orders_after) / len(orders), 3)

    inst2 = mp_instalments[mp_instalments["instalment_no"] == 2]
    if len(inst2) > 0:
        # A row counts as "missed" if it has no matching payment (regardless
        # of censoring -- this diagnostic is on TRUE state, matching status_at_extract's own basis).
        pass  # left to mp_agreements-level diagnostics below for simplicity

    n_defaulted = int((mp_agreements["status_at_extract"] == "defaulted").sum())
    total_value = mp_agreements["agreement_value_gbp"].sum()
    written_off = mp_agreements["written_off_value_gbp"].sum()
    diag["realised_written_off_pct_of_value"] = round(100 * written_off / total_value, 3) if total_value else None
    diag["n_agreements_defaulted"] = n_defaulted
    diag["n_agreements_settled"] = int((mp_agreements["status_at_extract"] == "settled").sum())
    diag["n_agreements_active"] = int((mp_agreements["status_at_extract"] == "active").sum())

    return diag


# --- CLI ---------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate S1-07 Meridian Pay tables.")
    parser.add_argument("--scale", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260907)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    generator_root = Path(__file__).resolve().parent.parent.parent
    baselines, generator_cfg, ground_truth = load_configs(generator_root)

    customer_result = run_customer_core(args.scale, args.seed, generator_root, baselines, generator_cfg, ground_truth)
    checkout_result = run_checkout_core(args.scale, args.seed, baselines, generator_cfg, ground_truth, customer_result)
    result = run_mp_core(args.scale, args.seed, baselines, generator_cfg, ground_truth, checkout_result)

    out_dir = Path(args.out) if args.out else generator_root.parent / "data" / "raw"
    for sub in ["customers", "sessions", "checkout_events", "orders", "mp_applications",
                "mp_agreements", "mp_instalments", "mp_payments", "_manifest"]:
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    result["customers"].to_parquet(out_dir / "customers" / "customers.parquet", index=False)
    result["sessions"].to_parquet(out_dir / "sessions" / "sessions.parquet", index=False)
    result["checkout_events"].to_parquet(out_dir / "checkout_events" / "checkout_events.parquet", index=False)
    result["orders"].to_parquet(out_dir / "orders" / "orders.parquet", index=False)
    result["mp_applications"].to_parquet(out_dir / "mp_applications" / "mp_applications.parquet", index=False)
    result["mp_agreements"].to_parquet(out_dir / "mp_agreements" / "mp_agreements.parquet", index=False)
    result["mp_instalments"].to_parquet(out_dir / "mp_instalments" / "mp_instalments.parquet", index=False)
    result["mp_payments"].to_parquet(out_dir / "mp_payments" / "mp_payments.parquet", index=False)

    with open(out_dir / "_manifest" / "mp_core_manifest.json", "w", encoding="utf-8") as f:
        json.dump(result["manifest"], f, indent=2, default=str)

    print(json.dumps(result["manifest"], indent=2, default=str))


if __name__ == "__main__":
    main()
