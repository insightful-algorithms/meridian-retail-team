# RACI Matrix: Meridian Retail Group Data Team

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | Monday 7 September 2026 |
| Author | Data Engineer |
| Approver | Product Owner |
| Companion | `/charter/project-charter.md` |

## How to read it

- **R** Responsible: does the work.
- **A** Accountable: one per row. Signs it off and answers for it.
- **C** Consulted: gives input before the work is done or the decision is made. Two-way.
- **I** Informed: told afterwards. One-way.
- **A/R** Accountable and does the work.
- **-** Not involved.

Rules:

1. Exactly one A per row. A row with none or two is a fault in the matrix and is fixed through a decision log entry.
2. C means asked before, not told after. If a role marked C first learns of a decision from the weekly email, that is a process failure and goes in the retrospective.
3. Changing a row needs a decision log entry.

Columns: **FIN** Finance representative, **BA** Business Analyst, **PO** Product Owner, **DA** Data Analyst, **DE** Data Engineer.

## Matrix

### Governance and planning

| # | Activity | FIN | BA | PO | DA | DE |
|---|---|---|---|---|---|---|
| 1 | Project charter, scope, success criteria | C | R | A | I | R |
| 2 | Backlog prioritisation and sprint goals | C | C | A/R | C | C |
| 3 | Requirements and acceptance criteria | C | A/R | C | C | C |
| 4 | Scope change requests | C | R | A | I | C |
| 5 | Tooling and infrastructure choices, with cost and benefit stated | A | I | C | I | R |
| 6 | Definition of Ready and Definition of Done | I | C | A/R | C | C |
| 7 | Decision log | C | C | A | C | R |

### Data and pipeline

| # | Activity | FIN | BA | PO | DA | DE |
|---|---|---|---|---|---|---|
| 8 | Baseline business parameters for the synthetic data | A | C | I | C | R |
| 9 | Synthetic data generator, including planted effects and injected faults | I | I | I | C | A/R |
| 10 | Pipeline build: raw, staging, marts | I | I | I | C | A/R |
| 11 | Automated data quality tests and CI, including the sample ratio mismatch test | I | I | I | C | A/R |
| 12 | Data dictionary and lineage notes | I | C | I | A/R | R |
| 13 | Code review notes, merge to `main`, reproducible environment | - | - | I | C | A/R |

### Workstream 1: Checkout A/B test

| # | Activity | FIN | BA | PO | DA | DE |
|---|---|---|---|---|---|---|
| 14 | Experiment design: hypothesis, metrics, minimum detectable effect, sample size, duration, randomisation unit | C | C | A | C | R |
| 15 | Guardrail metric, threshold, and stop rule for Meridian Pay | A/R | I | C | C | C |
| 16 | Statistical analysis of the test | I | I | I | C | A/R |
| 17 | Quality check of results before anything is reported | I | I | I | A/R | C |
| 18 | Ship / no-ship recommendation | C | C | A | R | C |

### Workstream 2: Loyalty causal inference

| # | Activity | FIN | BA | PO | DA | DE |
|---|---|---|---|---|---|---|
| 19 | The causal question in business terms, and the estimand | C | A | C | C | R |
| 20 | Method selection and identification assumptions | I | C | C | C | A/R |
| 21 | Causal analysis build, diagnostics, placebo, sensitivity | I | I | I | C | A/R |
| 22 | Plain-language interpretation and readout | C | C | I | A/R | C |
| 23 | £ impact and programme return on investment | A/R | I | C | C | C |

### Communication

| # | Activity | FIN | BA | PO | DA | DE |
|---|---|---|---|---|---|---|
| 24 | Async standups, Monday, Wednesday, Friday | R | R | A/R | R | R |
| 25 | Weekly stakeholder email, Fridays | I | I | I | I | A/R |
| 26 | Sprint planning, review, retrospective | C | C | A/R | C | C |
| 27 | Final README and close-out report | C | C | C | C | A/R |

Row 25: recipients reply in the thread, and the replies are kept in `/emails`.

## Accountability spread

| Role | Rows where accountable | Count |
|---|---|---|
| Finance representative | 5, 8, 15, 23 | 4 |
| Business Analyst | 3, 19 | 2 |
| Product Owner | 1, 2, 4, 6, 7, 14, 18, 24, 26 | 9 |
| Data Analyst | 12, 17, 22 | 3 |
| Data Engineer | 9, 10, 11, 13, 16, 20, 21, 25, 27 | 9 |

The Product Owner and Data Engineer carry the most accountability, which is expected: one owns priorities, the other owns the build. What keeps the matrix honest is that Finance, the Business Analyst, and the Data Analyst each hold a veto in their own domain (rows 15 and 23; 3 and 19; 17), so the build cannot route around them.

## Decision rights

| Decision | Final say | Must be consulted first | Recorded in |
|---|---|---|---|
| Priority order and sprint goals | Product Owner | All roles | `/backlog`, `/decisions` |
| Whether a request is in scope | Product Owner, on the Business Analyst's assessment | Data Engineer (effort); Finance (cost, risk) | `/decisions` |
| Guardrail thresholds, stop rule, any £ figure, any tool with a price | Finance representative | Data Engineer, Product Owner | `/decisions` |
| Technical design; branching, testing, and environment standards | Data Engineer | Data Analyst | `/pipeline/README.md`; `/decisions` if disputed |
| Whether a number is fit to report | Data Analyst | Data Engineer | Data dictionary; `/decisions` if disputed |
| Ship / no-ship on the checkout redesign | Product Owner | Finance (guardrail), Data Analyst, Data Engineer, Business Analyst | `/decisions` |
| Causal method and identification assumptions | Data Engineer | Data Analyst, Business Analyst | `/decisions` |

## Escalation path

1. Raise it in the Blockers line of the next standup.
2. If it is still open at the following standup, each side writes one paragraph: position and evidence.
3. The Product Owner decides within the sprint. Finance holds a veto only on guardrail thresholds, £ figures, and tooling cost. The Data Analyst can hold back a number that fails a quality check, and the Data Engineer fixes the cause in the same sprint.
4. The decision goes in the log with the dissent noted. It is reopened only with new evidence.

## Note on the simulation

One person plays all five roles. The matrix still binds. Each standup, email, and decision entry names the role speaking. A conflict is not resolved until both sides have been written down in their own voice and the accountable role has decided on the record. Resolving it silently, in the author's head, breaks objective O3.3 of the charter and is checked at every retrospective.

## Change history

| Version | Date | Change | Decision |
|---|---|---|---|
| 1.0 | 7 September 2026 | First issue for sign-off | D-001 |
