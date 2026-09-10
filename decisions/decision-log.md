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
