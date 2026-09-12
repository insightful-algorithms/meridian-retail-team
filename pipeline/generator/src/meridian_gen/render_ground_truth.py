"""Render ground_truth.yaml into ground_truth.md.

Called by generate.py at the end of every run (spec 2.1: "rendered from
config/ground_truth.yaml on every run"), so the Markdown copy can never
drift from the sealed YAML it's rendered from. Both files are sealed —
see the notice this script writes at the top of the output.

Standalone-runnable for testing before generate.py exists:
    python render_ground_truth.py
(reads ../config/ground_truth.yaml, writes ../ground_truth.md, relative
to this file, matching the layout in generator spec 2.1)
"""

from pathlib import Path
import yaml

SEAL_NOTICE = """> **Sealed.** This file is rendered from `config/ground_truth.yaml` on
> every run of `generate.py`. It is read by the Data Engineer and the
> Data Analyst only, until the final readout in Sprint 4 (charter 7.1;
> D-003). No file under `pipeline/dbt`, `pipeline/quality`, or
> `pipeline/analysis` may reference this file or the string
> `ground_truth` — CI checks this (generator spec section 8).
"""


def _fmt_pct(v) -> str:
    return f"{v}%" if not isinstance(v, str) else v


def render_workstream_1(ws1: dict) -> str:
    lines = ["## Workstream 1: the checkout redesign\n"]
    lines.append(f"- Experiment: `{ws1['experiment_id']}`")
    lines.append(f"- Window: {ws1['window_start']} to {ws1['window_end']}")
    lines.append(f"- Arm split: {ws1['arm_split']}\n")

    lines.append("| Quantity | Control (v1) | Test (v2) | Planted change |")
    lines.append("|---|---|---|---|")

    e = ws1["effects"]
    cc = e["checkout_completion_pct"]
    lines.append(
        f"| Visitor-level checkout completion | {cc['control']}% | {cc['test']}% "
        f"| **+{cc['planted_change_pp']} pp**, same on every device |"
    )
    aov = e["average_order_value_gbp"]
    lines.append(
        f"| Average order value | £{aov['control']:.2f} | £{aov['test']:.2f} "
        f"| None (planted null) |"
    )
    mps = e["mp_share_of_orders_pct"]
    lines.append(
        f"| Meridian Pay share of orders | {mps['control']}% | {mps['test']}% "
        f"| +{mps['planted_change_pp']} pp |"
    )
    bands_c = ", ".join(f"{k} {v}" for k, v in e["mp_band_shares_pct"]["control"].items())
    bands_t = ", ".join(f"{k} {v}" for k, v in e["mp_band_shares_pct"]["test"].items())
    lines.append(f"| Band shares of Meridian Pay orders | {bands_c} | {bands_t} | Mix shifts down the bands |")
    de = e["mp_share_bands_d_e_pct"]
    lines.append(
        f"| Share in bands D and E | {de['control']}% | {de['test']}% "
        f"| **+{de['planted_change_pp']} pp**: over the indicative 2-point trigger |"
    )
    miss = e["mp_day30_miss_rate_pct"]
    lines.append(
        f"| Day-30 miss rate | {miss['control']}% | {miss['test']}% "
        f"| **+{miss['planted_change_pp']} pp**, entirely through mix |"
    )
    dec = e["mp_decline_rate_pct"]
    lines.append(
        f"| Meridian Pay decline rate | {dec['control']}% | {dec['test']}% "
        f"| +{dec['planted_change_pp']} pp |"
    )
    lines.append("")
    lines.append(f"**Mechanism.** {ws1['mechanism'].strip()}\n")
    lines.append(f"**Why these values.** {ws1['why_these_values'].strip()}\n")
    return "\n".join(lines)


def render_workstream_2(ws2: dict) -> str:
    lines = ["## Workstream 2: Circle membership and spend\n"]
    lines.append("| Tenure | Effect on checkout-start rate |")
    lines.append("|---|---|")
    tenure = ws2["effect_on_checkout_start_rate_by_tenure"]
    label_map = {
        "month_0": "Month 0 (join month)",
        "months_1_to_3": "Months 1 to 3",
        "months_4_to_6": "Months 4 to 6",
        "months_7_onward": "Months 7 onward",
    }
    for key, label in label_map.items():
        v = tenure[key]
        note = f" — {v['note']}" if "note" in v else ""
        lines.append(f"| {label} | +{v['change_pct']}%{note} |")
    lines.append("")
    lines.append(
        f"**ATT on monthly spend, months 1 to 6: +{ws2['att_on_monthly_spend_months_1_to_6_pct']}%** "
        f"of counterfactual spend. {ws2['att_note'].strip()}\n"
    )
    sp = ws2["selection_premium"]
    lines.append(
        f"**Selection premium.** Calibrated to the {sp['calibrated_to_raw_gap_pct']}% raw gap; "
        f"expect about +{sp['expected_effect_on_latent_rate_pct']}% on the latent rate. {sp['note'].strip()}\n"
    )
    rg = ws2["raw_gap_decomposition"]
    lines.append(
        f"**Raw gap decomposition.** ~{rg['selection_points']} points selection, "
        f"~{rg['programme_points']} points programme. {rg['note'].strip()}\n"
    )
    lines.append(f"**Why these values.** {ws2['why_these_values'].strip()}\n")
    return "\n".join(lines)


def render(config_path: Path, output_path: Path) -> None:
    with open(config_path, "r", encoding="utf-8") as f:
        gt = yaml.safe_load(f)

    parts = [
        "# Ground Truth: Meridian Retail Group Data Generator\n",
        SEAL_NOTICE,
        render_workstream_1(gt["workstream_1_checkout_redesign"]),
        render_workstream_2(gt["workstream_2_circle_membership"]),
        "## Realised values\n",
        "See `_manifest/ground_truth_realised.json` for what this seed and "
        "scale actually produced — sampling noise moves the realised value "
        "off the parameter above; the final readout checks both.\n",
    ]

    output_path.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    generator_root = Path(__file__).resolve().parent.parent.parent
    config_path = generator_root / "config" / "ground_truth.yaml"
    output_path = generator_root / "ground_truth.md"
    render(config_path, output_path)
    print(f"Rendered {output_path} from {config_path}")
