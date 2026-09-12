# Decision Log: Meridian Retail Group Data Team

| Field | Value |
|---|---|
| Accountable | Product Owner |
| Records | Data Engineer |
| Companion | `/charter/project-charter.md` section 11.3; `/charter/raci-matrix.md` row 7 and the decision rights table |

## How to use this log

Every conflict between roles ends here (charter objective O3.3). Each entry records the ID, date, the conflict, the options, the decision, the rationale, who decided, who was consulted, any dissent, and follow-up. Dissent is recorded, not smoothed over.

Rules:

1. IDs are sequential and never reused.
2. Status is one of Open, Decided, Reopened, Superseded.
3. A decision is reopened only with new evidence, and only as a new entry that references the old one. The old entry is marked Superseded and left as written.
4. If a role marked C in the RACI first learns of a decision from the weekly email, that is logged here as a process failure and raised at the retrospective.
5. One person plays all five roles. An entry is not complete until each side of a conflict has been written in its own voice.

## Index

| ID | Date | Decision | Status | Decided by |
|---|---|---|---|---|
| D-001 | 7 Sep 2026 | Charter v1.0 and RACI matrix v1.0 approved with recorded reservations | Decided | Product Owner |
| D-002 | 10 Sep 2026 | Tooling stack accepted as in charter section 9; £0 holds while the repository is public; six-hour cap on Great Expectations setup | Decided | Finance representative |
| D-003 | 10 Sep 2026 | Ten charter baselines confirmed unchanged; credit bands, band-level miss rates, decline rate, agreement structure, and Circle programme cost added | Decided | Finance representative |
| D-004 | | Guardrail threshold, stop rule, and how to handle the underpowered guardrail (R8) | Open, Sprint 2 | Finance representative |
| D-005 | | Experiment design document signed before results are seen | Open, Sprint 2 | Product Owner and Finance representative |
| D-006 | 11 Sep 2026 | Definition of "active customers": split into active accounts (850,000) and purchasing customers (450,000), superseding one line of D-003 | Decided | Finance representative |
| D-007 | 11 Sep 2026 | Sprint 1 capacity: option (b), one-time +6 Data Engineer hours; cut lines 1 to 5 applied; S1-07 stays in Sprint 1; S1-11 moves to Sprint 2 | Decided | Product Owner |
| D-008 | 12 Sep 2026 | Rebuild order generation from a real checkout-completion funnel, superseding S1-05's direct order draw | Decided | Product Owner |

---

## D-001: Charter v1.0 and RACI matrix v1.0 approved with recorded reservations

| Field | Value |
|---|---|
| Date | Monday 7 September 2026, Sprint 1 planning |
| Status | Decided |
| Raised by | Data Engineer (author of both documents) |
| Decided by | Product Owner |
| Consulted | Finance representative, Business Analyst, Data Analyst, Data Engineer |
| Informed | None. All roles present. |

**Question.** Are the charter and the RACI matrix fit to govern the project as written, or do they need changes before Sprint 1 build work starts?

**Options.**

1. Approve both as written.
2. Approve both at v1.0 with reservations recorded here, each tied to an open decision that resolves it.
3. Send both back for revision. No build work until re-issued.

**Decision.** Option 2. Both documents are approved at version 1.0. The reservations below are recorded, each with an owner and a decision ID, so nothing is lost and nothing blocks Sprint 1.

**Rationale (Product Owner).** The reservations are real but none changes the scope, the dates, or the method. Every one of them already has a decision slot in the charter (D-002 to D-005). Holding the whole charter back for them would cost a week of Sprint 1 to fix things that are scheduled to be fixed inside Sprint 1 and 2 anyway. Dates are fixed, scope flexes.

**Reservations recorded, in each role's words.**

- **Finance representative.** "The 0.5 point guardrail and the 2 point risk-mix threshold in section 7.3 are indicative and I have not agreed them. R8 says the guardrail is underpowered on a two-week test. I will not treat any threshold as final until I have seen the power analysis for the guardrail, not just the primary metric. That is D-004. Baselines in section 3 are also unconfirmed. That is D-003. Both stay open until I close them."
- **Business Analyst.** "No objection to scope. One condition: the Definition of Ready in 11.1 is applied from the first backlog item, not from Sprint 2. If an item enters Sprint 1 without acceptance criteria in my words, I will raise it as a blocker."
- **Data Analyst.** "I accept the generator approach but I have not seen the data. Section 7.1 says I review realism in Sprint 1. I want that as a named backlog item with a due date, not an assumption. Until I have done it, no number from the generator is fit to report."
- **Data Engineer.** "Eight hours a week of build time against the Sprint 1 goal (repository, CI, generator v1, quality suite passing, dictionary v1) is tight. I want the Product Owner to hold a cut list from day one so that if something slips it is a decision and not a surprise. R9."

**Follow-up.**

| Action | Owner | Due |
|---|---|---|
| Update the charter status field from "draft for sign-off" to "approved", fill in the sign-off table in section 12, bump to v1.0 (signed) through a pull request | Data Engineer | Wednesday 9 September 2026 |
| Add the Data Analyst's realism review to the Sprint 1 backlog with acceptance criteria | Product Owner, Business Analyst | Sprint 1 backlog |
| Open a Sprint 1 cut list in `/backlog/sprints/sprint-01.md` | Product Owner | Wednesday 9 September 2026 |
| Close D-002 and D-003 | Finance representative | Before Friday 18 September 2026 (M1) |
| Close D-004 and D-005 | Finance representative, Product Owner | Sprint 2 |

---

## D-002: Tooling stack and the £0 direct cost baseline

| Field | Value |
|---|---|
| Date | Thursday 10 September 2026 |
| Status | Decided |
| Raised by | Data Engineer, in the Blockers line of the Wednesday 9 September standup |
| Decided by | Finance representative |
| Consulted | Product Owner, Data Engineer |
| Informed | Business Analyst, Data Analyst |

**Question.** Whether the stack in charter section 9 (local DuckDB; dbt with dbt-duckdb; dbt tests and a Great Expectations suite; GitHub Actions on a public repository; Python with pandas, statsmodels, scikit-learn, scipy; Markdown reports with matplotlib) is accepted with the alternatives rejected as stated, and on what conditions the £0 direct cost baseline holds.

**Options.**

1. Accept the stack as written in section 9.
2. Accept it but drop Great Expectations and rely on dbt tests alone, to save setup time.
3. Move to a cloud sandbox (BigQuery free tier) for a more production-like environment.

**Decision.** Option 1, with three conditions.

1. The £0 figure depends on the repository staying public. GitHub Actions minutes on a private repository are metered. If the repository goes private, Finance is told before it happens and the cost estimate is redone.
2. Time is a cost. Great Expectations gets a six-hour setup cap. If it is not producing a passing suite in CI within that, the Data Engineer falls back to dbt tests only, logs the fallback against this entry, and the charter's section 7.2 is corrected by pull request under 11.5. Revisit in Sprint 3 if there is slack.
3. Nothing with a price is installed, trialled, or signed up to without an entry in this log. That includes free tiers that ask for a card.

**Rationale (Finance representative).** "Direct cost is £0 and the alternatives are named with reasons, which is what I asked for in section 9. Option 3 buys realism nobody has asked me to pay for: time, account administration, and the risk of something left running. Option 2 saves hours now and costs evidence later; a quality suite that runs in CI is the thing I can point to in the close-out report, and assertions in a notebook are not. So the stack stands. The conditions are there because £0 is a claim about today, not a guarantee, and I want to know the moment it stops being true."

**Dissent.** Data Engineer: "Four hours was the first figure offered for the Great Expectations cap. On a first setup with dbt-duckdb that is tight. I asked for eight." Finance: "Six. Not eight. If six is not enough, that tells us something about the tool." Settled at six hours, recorded above.

**Follow-up.**

| Action | Owner | Due |
|---|---|---|
| Record the stack, versions, and pinned dependencies in `pipeline/README.md`, with a line that the CI cost assumes a public repository | Data Engineer | Sprint 1 |
| Track hours spent on Great Expectations setup in `/reflection` and report the figure at the Sprint 1 review | Data Engineer | Friday 18 September 2026 |
| Add a check to the pull request checklist: "no new tool, service, or account without a decision log entry" | Data Engineer | Sprint 1 |

---

## D-003: Baseline parameters for the synthetic data generator

| Field | Value |
|---|---|
| Date | Thursday 10 September 2026 |
| Status | Decided |
| Raised by | Data Engineer, in the Blockers line of the Wednesday 9 September standup |
| Decided by | Finance representative |
| Consulted | Business Analyst, Data Analyst, Data Engineer |
| Informed | Product Owner |

**Question.** Whether the ten baselines in charter section 3 stand, and what the generator needs that the table does not give it. Section 7.3 names guardrails (Meridian Pay decline rate, risk mix by internal credit band) and objective O2.3 needs a programme cost, and none of these has a baseline.

**Options.**

1. Confirm the ten baselines as stated.
2. Revise one or more figures.
3. Confirm the ten and add the parameters the guardrails and the ROI calculation need but the table omits.

**Decision.** Option 3. The ten baselines in charter section 3 are confirmed unchanged. Finance adds the parameters below. Like the rest, they are plausible, not sourced. They bind the generator from v1.

| Parameter | Value | Needed by |
|---|---|---|
| Internal credit bands, share of Meridian Pay orders | A 30%, B 30%, C 22%, D 12%, E 6% | O1.2 risk mix. D and E are the two highest-risk bands named in the stop rule, section 7.3 |
| Day-30 instalment miss rate by band | A 1.5%, B 3.0%, C 5.0%, D 9.0%, E 14.0% | O1.2 guardrail. The planted repayment effect works through the band mix, not through a uniform shift |
| Meridian Pay decline rate | 12% of applications at checkout | Guardrail, section 7.3 |
| Meridian Pay agreement structure | Agreement value follows the order value distribution (£68 mean); three equal instalments due at day 0, 30, and 60 | Repayment records; late-arriving repayment faults (R3) |
| 90-day default rate by band | Proportional to the band's day-30 miss rate, calibrated so that the overall rate is 1.9% of order value | Baseline table, section 3 |
| Circle programme cost | Points worth 1.5% of member spend, of which 70% are redeemed, plus £0.15 per member per month for communications | O2.3 return on investment |
| Seasonality | Weekly: Sunday and Monday 15% above the daily mean, Friday and Saturday 10% below. Monthly: November and December 40% above the monthly mean, January and February 15% below | R3 realism; the A/B test window (1 to 14 June) sits in a flat month by design |

**Rationale (Finance representative).** "The headline numbers are the ones the board sees, so I confirm them as they stand. What the table lacks is anything a guardrail could be computed from. A stop rule on the two highest-risk bands means nothing until the bands exist and each has a miss rate, so I have given them. A return on investment for Circle means nothing until the programme has a cost, so I have given it. The figures are round and plausible and I will not defend them further than that. Their job is to give the generator something to reproduce and the methods something to recover."

**Dissent.** Data Analyst: "The weighted average of the band miss rates is about 4.4%, not the 4.5% in the charter. Either the headline is fixed and the band rates float to fit, or the bands are fixed and the headline is whatever falls out. Not both stated as fixed." Finance: "Band shares and band rates are fixed. The headline is what falls out. If the generator produces 4.4%, then 4.4% is the baseline and the charter table is corrected by pull request under 11.5, referencing this entry." Decision stands as written.

**Out of scope for this entry.** The planted effect sizes (conversion, repayment, loyalty, self-selection) and the fault injection rates (duplicates, missing values, late records) are the Data Engineer's call under RACI row 9, with the Data Analyst consulted. They are recorded in `pipeline/generator/ground_truth.md` and the generator README, not here. Finance sees the ground truth only in the final readout, with everyone else.

**Follow-up.**

| Action | Owner | Due |
|---|---|---|
| Encode every confirmed and added parameter in a generator config file, each with a comment citing this entry | Data Engineer | Sprint 1 |
| Set the planted effect sizes and fault rates with the Data Analyst; record in `pipeline/generator/ground_truth.md` (effects) and the generator README (faults) | Data Engineer, Data Analyst | Sprint 1 |
| If the generated headline miss rate differs from 4.5%, correct charter section 3 by pull request under 11.5, referencing this entry | Data Engineer | Sprint 1 review, Friday 18 September 2026 |
| Data dictionary v1 lists every parameter above with source "D-003" | Data Analyst | Friday 18 September 2026 |

---

## D-004: Guardrail threshold, stop rule, and the underpowered guardrail

| Field | Value |
|---|---|
| Date | |
| Status | Open, Sprint 2 |
| Raised by | Data Engineer |
| Decided by | Finance representative |
| Consulted | Product Owner, Data Analyst, Data Engineer |

**Question.** The final day-30 miss-rate threshold and the risk-mix threshold for the checkout test, and how R8 is handled: a longer test, the risk-mix proxy, or accepting a wide interval on the guardrail.

Entry to be completed when decided.

---

## D-005: Experiment design document signed before results are seen

| Field | Value |
|---|---|
| Date | |
| Status | Open, Sprint 2 |
| Raised by | Data Engineer |
| Decided by | Product Owner and Finance representative |
| Consulted | Business Analyst, Data Analyst |

**Question.** Whether the experiment design document (hypotheses, primary and secondary metrics, guardrails, minimum detectable effect, sample size, duration, randomisation unit, stop rules, single fixed-horizon readout) is signed, so that no result is read before the plan is locked (R6).

Entry to be completed when decided.

---

## D-006: Definition of "active customers" for the generator

| Field | Value |
|---|---|
| Date | Friday 11 September 2026 |
| Status | Decided. Supersedes one line of D-003; D-003 itself stands |
| Raised by | Data Engineer, Blockers line, Friday 11 September standup |
| Decided by | Finance representative |
| Consulted | Data Analyst, Business Analyst |
| Informed | Product Owner |

**Question.** What does "active customers (last 12 months): 850,000" in charter section 3 / D-003 actually mean for the generator? The arithmetic in the generator spec (section 3.4) shows 140,000 checkout starters a month at 52% completion gives about 873,600 orders a year. If 850,000 are distinct purchasers, each buys about once a year, and the Circle loyalty programme cannot break even under any effect size the analysis could find — which would decide the Sprint 4 readout before the method runs.

**Options.**

1. 850,000 is purchasers. Keep it; state the consequence in every report.
2. 850,000 is active accounts (a logged-in session in the year); purchasing customers is a separate, smaller baseline Finance sets.
3. Finance revises the 850,000 figure itself.

**Decision.** Option 2. "Active customers (last 12 months): 850,000" is redefined as active accounts. A new parameter, `purchasing_customers_12m: 450,000`, is added to `config/baselines.yaml` and is what the generator's repeat-purchase and loyalty behaviour actually calibrates to. At 450,000 purchasers, that is about 1.94 orders per customer per year and roughly £11 of spend per active customer per month — a base a loyalty programme can plausibly be run on.

**Rationale (Finance representative).** "850,000 is a number I recognise — it is close to the kind of account base a business our size would report to the board, and I do not want to lose it from the story. But the Data Engineer's arithmetic is right: if all 850,000 buy, the programme is dead before the analysis starts, and that is not a finding, it is a modelling mistake. Splitting the definition keeps both things true at once: a board-sized active base, and a purchaser base the generator and the loyalty analysis can actually work with. 450,000 is a round illustrative figure, not a researched one, same as everything else in D-003."

**Dissent.** None recorded. The Data Analyst and Business Analyst were consulted and raised no objection to the split; the Data Analyst noted only that they will check what the new purchaser figure does to the spend panel during the realism review.

**Relationship to D-003.** This does not reopen D-003. The ten confirmed baselines and the parameters Finance added there stand unchanged. This entry adds one new parameter and re-labels one existing one, per the decision log's own rule that a superseding entry references the original rather than editing it.

**Follow-up.**

| Action | Owner | Due |
|---|---|---|
| Add `purchasing_customers_12m: 450000` to `config/baselines.yaml`, with a comment citing D-006, alongside the existing `active_customers_12m: 850000` (D-003) | Data Engineer | Before S1-03 is marked done |
| Data dictionary entry distinguishing "active accounts" from "purchasing customers", both sourced | Data Analyst | S1-12 |
| Realism review (S1-13) checks the purchaser figure against the generated spend panel | Data Analyst | Wed 16 Sep |
| If the generated repeat-purchase rate looks wrong at scale 0.1, raise as a new decision rather than adjusting `purchasing_customers_12m` silently | Data Engineer | Ongoing |

---

## D-007: Sprint 1 capacity — hold, add hours, or partial

| Field | Value |
|---|---|
| Date | Friday 11 September 2026 |
| Status | Decided |
| Raised by | Data Engineer, `backlog/sprints/sprint-01.md` section 6 |
| Decided by | Product Owner (RACI row 2, sprint goals) |
| Consulted | Data Engineer |
| Informed | Finance representative, Business Analyst, Data Analyst |

**Question.** About 19 hours of Must-tier Data Engineer work are backlogged for Sprint 1 against roughly 11 hours of available capacity by Friday 18 September. Which of the three options in the backlog's section 6 closes the gap.

**Options.**

- (a) Hold at 8 hours a week. Apply cut lines 1 to 6. S1-07 (Meridian Pay tables) and S1-11 (dbt staging) both move to Sprint 2.
- (b) Add about 6 Data Engineer hours this sprint, once. Cut lines 1 to 5 only. S1-07 stays in Sprint 1; only S1-11 moves to Sprint 2.
- (c) Add about 3 hours and apply cut line 6 anyway. Keeps neither benefit fully.

**Decision.** Option (b). The Sprint 1 goal is restated: "generator v1 for customers, orders, memberships, checkout, and Meridian Pay, with the generator's own test suite passing in CI; dbt staging models move to Sprint 2 week 1." Cut lines applied: S1-16 (Great Expectations) deferred, S1-15 (full-scale run) deferred, S1-11 (dbt staging) deferred, S1-08 (fault injection) partial — impossible-value and clock-skew faults dropped, duplicates/nulls/late-records/near-duplicates kept, S1-06 (checkout generation) partial — only checkout-starting sessions generated, not the full 2.4m-session baseline.

**Rationale (Product Owner).** "The Data Engineer's own recommendation was (b), and the reasoning holds: Meridian Pay data landing in Sprint 1 protects Sprint 2's critical path, since the guardrail power analysis (D-004) and the experiment design document (D-005) both need it. Losing dbt staging for one sprint is a smaller cost — the generator's own test suite is still real evidence, just not the full pipeline yet. Six hours once is a one-time trade, not a new standing expectation; it does not reset what 'available capacity' means for Sprint 2 onward."

**Dissent.** None recorded.

**Follow-up.**

| Action | Owner | Due |
|---|---|---|
| Restate the Sprint 1 goal in `backlog/sprints/sprint-01.md` per the wording above | Data Engineer | Immediately |
| Apply cut lines 1 to 5 in the backlog: mark S1-16, S1-15 deferred to Sprint 2; note S1-08 and S1-06 as partial scope with the specific faults/sessions dropped | Data Engineer | Immediately |
| Confirm S1-11 (dbt staging) is Sprint 2 week 1's first item | Product Owner | Sprint 2 planning |
| The six added hours are tracked in `/reflection` against R9 (workload pressure), same as the Great Expectations hours under D-002 | Data Engineer | Sprint 1 review |
| This is a one-off addition. Sprint 2 capacity planning starts from 8 hours a week again unless a new decision changes it | Product Owner | Sprint 2 planning |

---

## D-008: Rebuild order generation from a real checkout-completion funnel

| Field | Value |
|---|---|
| Date | Saturday 12 September 2026|
| Status | Decided |
| Raised by | Data Engineer, scoping S1-06 |
| Decided by | Product Owner |
| Consulted | Data Engineer |
| Informed | Finance representative, Business Analyst, Data Analyst |

**Question.** `customer_core.py` (S1-05) draws `orders` directly from each
customer's latent monthly rate, with no checkout-completion step between
attempt and order. S1-06 needs a real completion rate (52.0% control,
53.8% test — the planted conversion effect) and the 140,000/month
checkout-starter baseline, neither of which can be represented honestly
without a funnel layer. Two ways to close the gap: treat S1-05's orders as
fixed and build a funnel around them (Option A), or rebuild order
generation from an actual attempt-to-completion funnel (Option B).

**Options.**

1. Keep S1-05's orders as ground truth; fabricate a funnel that explains
   them after the fact, adding anonymous non-converting traffic to hit
   volume targets.
2. Rebuild order generation properly: `customer_core.py` produces a
   checkout-attempt propensity only; `checkout_core.py` (S1-06) applies a
   real, device-level completion draw, with the June arm effect layered
   on top for in-window visitors, to produce the actual orders.

**Decision.** Option 2. `customer_core.py` no longer produces `orders`.
The Circle loyalty effect and the completion effect both act on a
checkout-attempt rate, consistent with charter 7.4's own language
("effect on checkout-start rate").

**Rationale (Product Owner).** The charter's own objectives (O1.1, O1.2)
are about a completion rate and a conversion effect; a model that skips
straight to orders can't represent either honestly. Option 1 would have
been faster, but it means the "completion rate" in every downstream
report is fabricated scaffolding around numbers that were never actually
subject to a completion draw. That's a bigger integrity problem than
redoing calibration once, now, while only two backlog items depend on it.

**Consequence, logged plainly.** S1-05's calibration test results
(purchasers 44,620/45,000, raw gap 1.308) are **superseded, not
repeated** — they were measured on a model with no completion step and
no longer describe what the pipeline does. `customer_core.py`'s own
purchaser/raw-gap figures are now explicitly approximate (a flat 0.52
completion stand-in, for its own fast calibration only);
`checkout_core.py` computes the authoritative, completion-based figures.

**Dissent.** None recorded — raised and decided in the same sitting.

**Follow-up.**

| Action | Owner | Due |
|---|---|---|
| Revise `customer_core.py`: drop order generation, expose `checkout_attempts` | Data Engineer | Done, this entry |
| Build `checkout_core.py`: sessions, checkout_events, experiment_assignments, orders, from a real completion funnel | Data Engineer | Done, this entry |
| Update both test suites to match the new module boundary | Data Engineer | Done, this entry |
| Data dictionary note distinguishing attempt-rate from completion-rate calibration | Data Analyst | S1-12 |
| Realism review (S1-13) checks the real, completion-based purchaser/raw-gap figures, not the approximate ones in `customer_core.py`'s own manifest | Data Analyst | Wed 16 Sep |