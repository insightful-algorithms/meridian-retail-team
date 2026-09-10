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
| D-002 | | Tooling stack and the £0 direct cost baseline | Open, Sprint 1 | Finance representative |
| D-003 | | Baseline parameters for the synthetic data generator | Open, Sprint 1 | Finance representative |
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
| Date | |
| Status | Open, Sprint 1 |
| Raised by | Data Engineer |
| Decided by | Finance representative |
| Consulted | Product Owner, Data Engineer |

**Question.** Whether the stack in charter section 9 (local DuckDB, dbt with dbt-duckdb, dbt tests and Great Expectations, GitHub Actions on a public repository, Python analysis libraries, Markdown reports) is accepted, with the alternatives rejected as stated.

Entry to be completed when decided.

---

## D-003: Baseline parameters for the synthetic data generator

| Field | Value |
|---|---|
| Date | |
| Status | Open, Sprint 1 |
| Raised by | Data Engineer |
| Decided by | Finance representative |
| Consulted | Business Analyst, Data Analyst, Data Engineer |

**Question.** Whether the baseline assumptions table in charter section 3 (140,000 checkout visitors a month, 52% completion, £68 average order value, 24% Meridian Pay share, 4.5% day-30 miss rate, and the rest) stands, or which values change before generator v1 is built.

Entry to be completed when decided.

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
