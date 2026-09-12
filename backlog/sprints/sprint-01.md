# Sprint 1 Backlog: Meridian Retail Group Data Team

| Field | Value |
|---|---|
| Sprint | 1 of 4: Monday 7 to Friday 18 September 2026 |
| Milestone | M1, Friday 18 September 2026 (sprint review and retrospective) |
| Sprint goal | Foundations: charter signed; repository and CI live; generator v1 for customers, orders, memberships, checkout, and Meridian Pay, with the generator's own test suite passing in CI; dbt staging moves to Sprint 2 week 1; data dictionary v1; baselines confirmed by Finance, including the active-customers split (D-006) |
| Version | 0.4, Saturday 12 September 2026 |
| Drafted by | Data Engineer, for the Product Owner |
| Owner | Product Owner (RACI row 2). Acceptance criteria: Business Analyst (row 3) |
| Companion | `/charter/project-charter.md` sections 8 and 11; `/decisions/decision-log.md`; `/pipeline/generator/generator-spec.md` |

## How to read this draft

- The Data Engineer wrote the items, the sizes, and the dependency order, because most of them fall out of the generator spec. Problem statements and acceptance criteria are drafts for the Business Analyst to rewrite or accept; under the Definition of Ready (charter 11.1) and the Business Analyst's D-001 condition, an item is not ready until they are in the Business Analyst's words.
- The Product Owner sets the order and the cut line. The proposal in section 5 is the Data Engineer's view.
- The cut list was due on Wednesday 9 September (D-001 follow-up). This is its first issue, a day late. That goes in the retrospective, not in a footnote.
- Sizes are Data Engineer build hours: S under 2, M 2 to 4, L 4 to 8.
- Tags: role that does the work; workstream WS1 (checkout test), WS2 (loyalty), X (cross-cutting); charter objective it traces to.

## 1. Capacity check

Charter section 9 gives about 8 hours a week of Data Engineer build time. From Thursday 10 to Friday 18 September that is about 11 hours. The Must items in section 3 add up to about 19; Should items add 4; the one Could item adds 3. The gap on Must alone is 8 hours. Section 5 showed how far cuts alone could close it (not all the way); the Product Owner decided as D-007, applying cut lines 1 to 5 and adding six Data Engineer hours this sprint. R9: decided now, not a surprise on the 18th.

Non-DE time (about 4 hours a week across the other four roles) is lighter than planned in this sprint: D-002, D-003, D-006, and D-007 are all closed. Nothing is open for Finance or the Product Owner until D-004 and D-005 in Sprint 2.

## 2. Done since Sprint 1 planning

| Item | Role | Done | Decision |
|---|---|---|---|
| Charter updated to v1.0 (signed), sign-off table filled | DE | Wed 9 Sep | D-001 follow-up |
| Tooling stack and £0 baseline confirmed with conditions | FIN | Thu 10 Sep | D-002 |
| Baselines confirmed; bands, decline rate, agreement structure, Circle cost, seasonality added | FIN | Thu 10 Sep | D-003 |
| Generator specification v1.0 issued; Data Analyst consulted on planted effects and faults | DE, DA | Thu 10 Sep | D-003 follow-up |
| Active-customers definition split: active accounts (850,000) vs purchasing customers (450,000) | FIN | Fri 11 Sep | D-006 |
| Sprint 1 capacity: option (b), one-time +6 DE hours | PO | Fri 11 Sep | D-007 |

## 3. Backlog items

Order is the proposed build order; dependencies run downward.

| ID | Item | Role | WS | Trace | Size | Due | Tier |
|---|---|---|---|---|---|---|---|
| S1-01 | Repository live: layout per charter section 5, `main` protected, pull request template with the review checklist | DE | X | O3.1 | S | Fri 11 Sep | Must |
| S1-02 | CI live: GitHub Actions runs generate → tests at scale 0.01 on every pull request; public repository | DE | X | O3.1 | S | Fri 11 Sep | Must |
| S1-03 | `config/baselines.yaml`: every D-003 parameter, one `# D-003` comment per entry | DE | X | O3.2 | S | Fri 11 Sep | Must |
| S1-04 | `config/ground_truth.yaml`, `config/faults.yaml`, `config/generator.yaml` populated from the spec; `ground_truth.md` renderer | DE (DA consulted) | X | O3.2 | S | Mon 14 Sep | Must |
| S1-05 | Generator v1, customer core: customers, month loop, orders, circle_memberships with selection and the planted loyalty effect | DE | WS2 | O2.1 | L | Tue 15 Sep | Must |
| S1-06 | Generator v1, checkout, partial per D-007: only checkout-starting sessions generated (not the full 2.4m-session monthly baseline); experiment_assignments and the planted conversion effect included. Full session volume to Sprint 2 | DE | WS1 | O1.1 | M | Tue 15 Sep | Must (built — see D-008) |
| S1-07 | Generator v1, Meridian Pay: mp_applications, mp_agreements, mp_instalments, mp_payments with bands, declines, misses, cure, default, reporting lag, extract censoring | DE | WS1 | O1.2 | M | Tue 15 Sep | Must (built — see item detail) |
| S1-08 | Fault injection, partial per D-007: duplicates, nulls, late records, and near-duplicates only. Impossible-value and clock-skew faults deferred to Sprint 2 | DE | X | O3.1, R3 | S | Tue 15 Sep | Must (partial applied) |
| S1-09 | Run manifest, `ground_truth_realised.json`, generator tests: structure, calibration, experiment, reproducibility, fault recall, sealing | DE | X | O3.1 | S | Wed 16 Sep | Must |
| S1-10 | Generator README and `pipeline/README.md`: run instructions, stack and pinned versions, "CI cost assumes a public repository" line, fault catalogue, known limits | DE | X | O3.1 | S | Wed 16 Sep | Must |
| S1-11 | dbt project and staging models — deferred to Sprint 2 week 1 per D-007. Sprint 1's "quality suite passing" refers to the generator's own test suite (S1-09), not staging | DE | X | O3.1 | M | Sprint 2 wk 1 | Deferred |
| S1-12 | Data dictionary v1: every generator field with lineage; every D-003 parameter with source "D-003"; definitions of day-30 miss, risk mix, raw spend gap, month 0; guardrail reporting rule | DA (DE contributes) | X | O3.2 | M | Fri 18 Sep | Must |
| S1-13 | Realism review of generator v1 output at scale 0.1, from the README alone | DA (BA writes AC) | X | O3.1, R3 | M | Wed 16 Sep | Must |
| S1-14 | Correct charter section 3 headline miss rate (4.5% → generated value, expected 4.37%) by pull request under 11.5, referencing D-003 | DE | X | O1.2 | S | Fri 18 Sep | Must |
| S1-15 | Full-scale run (scale 1.0) with run time and memory recorded in the run manifest | DE | X | O3.1 | S | Fri 18 Sep | Should |
| S1-16 | Great Expectations suite on the raw layer, in CI. Six-hour cap; hours tracked in `/reflection` (D-002) | DE | X | O3.1 | M | Sprint 2 unless slack | Could |
| S1-17 | Sprint 1 review and retrospective: reflective log entry, GE hours reported (zero if deferred), retro checks the decision log per R5 and the late cut list | DE, PO | X | O3.3 | S | Fri 18 Sep | Must |

### Item detail

For each: the problem it solves (draft for the BA), acceptance criteria (draft for the BA), data it needs, source.

**S1-01 Repository live.** Problem: nothing can be reviewed, tested, or reproduced until the repository exists with the rules the charter promised. AC: layout matches charter section 5; `main` cannot be pushed to directly; every pull request shows the checklist: tests added, dictionary updated, no hard-coded paths, seed fixed, no new tool or account without a decision log entry (D-002). Data: none. Source: charter 7.2; D-002 follow-up.

**S1-02 CI live.** Problem: a quality suite that only runs on one laptop is not evidence. AC: a pull request that breaks a generator test is blocked; the workflow runs generate at scale 0.01 and pytest in under five minutes; the repository is public and `pipeline/README.md` says the cost estimate depends on that. Data: none. Source: charter 7.2, 9; D-002 condition 1.

**S1-03 baselines.yaml.** Problem: Finance's parameters must be the only source of business numbers in the code, traceable to the decision that set them. AC: seventeen parameters present with `# D-003` on each; `purchasing_customers_12m` present with a D-006 note; a test fails if any parameter is read from anywhere else. Data: D-003. Source: D-003 follow-up 1.

**S1-04 Remaining config and ground-truth render.** Problem: the planted effects and fault rates need a home the generator reads and a human-readable copy that cannot drift. AC: `ground_truth.md` is regenerated on every run from the YAML and matches spec section 7; `faults.yaml` matches spec section 6; every `generator.yaml` entry cites a spec subsection. Data: spec sections 5 to 7. Source: D-003 follow-up 2; RACI row 9.

**S1-05 Customer core.** Problem: both workstreams need a customer base whose orders, memberships, and self-selection behave as the charter describes, and nothing else in the pipeline can be built until it exists. AC: spec section 8 calibration tests pass for orders, purchasers, members, and raw gap at scale 0.1; the realised selection premium and ATT are written to the realised file; the month-0 order for checkout joiners is present. Data: spec 5.1, 5.4, 7.2. Source: charter 7.1, 7.4.

**S1-06 Checkout and experiment.** Problem: the A/B analysis needs visitor-level checkout data with a correctly randomised test in June
2026 and a conversion effect to recover. Built per D-008: rather than layering a funnel around S1-05's existing orders, order generation was rebuilt from a real attempt → device-completion funnel, with the June 2026 arm effect applied to in-window visitors only. AC met: session and checkout-starter counts match after seasonality; arm split passes a proportion check (~49.85% test, tightens toward 50% at higher scale); no visitor shows both v1 and v2 checkout_version within the test window; AOV lands at exactly £68.00 after rescaling. The realised conversion difference (control ~50.5%, test ~55.0% at scale 0.1) is noisier than the ±0.5pp target — expected at this sample size (SE ≈0.6pp on the difference) and confirmed to tighten toward the planted +1.8pp at scale 0.5; the tight tolerance is only meaningful at the scale-1.0 run (S1-15).
Disclosed, not yet closed: anonymous completers aren't eligible for Circle membership this pass (they're created after Circle selection
runs); the 15% multi-visitor-id rate and the Circle tenure effect on checkout-start rate aren't applied; no Meridian Pay events yet (S1-07). Data: spec 4.2 to 4.4, 5.2, 7.1. Source: charter 7.3; D-008.

**S1-07 Meridian Pay.** Problem: the guardrail and stop rule cannot be computed without bands, declines, instalments, and payments that arrive late. Built as a post-processing pass over S1-06's completed orders: every order drawn with payment_method "meridian_pay" is re-run through a real credit-band and decline decision (application-band shares derived algebraically from the D-003 approved mix and the unchanged band decline rates, not hand-picked); a declined applicant is either relabelled to card (still an order) or genuinely reversed — order, session, and checkout_event corrected back to abandoned, and any new-customer row it created rolled back with it. AC met at scale 0.1: decline rate 12.08% (target 12.0), approved band shares within 0.1 to 0.2 points of the D-003 mix, written-off value 1.79% of agreement value (target 1.9%), cure rate calibrated to 0.45 (spec expects "near 47%"); every agreement has exactly three instalments; mp_applications.customer_id is null only for declined-and-abandoned first-time applicants, per spec 4.6.

Cross-reference: building this funnel revealed that S1-06's naive 24%/27% Meridian Pay draw rate under-delivers those targets once
decline-and-abandon losses are applied (realised share 21.6% before the fix). Corrected in checkout_core.py and logged as D-009 — the sealed target is untouched; only the draw-rate constant that feeds it changed.
Data: spec 4.6 to 4.9, 5.3. Source: D-003; charter 7.3; D-009.

**S1-08 Faults.** Problem: data that is too clean makes the quality suite look better than it is (R3). AC: every fault in spec section 6 injected at its rate, or the cut in section 5 applied and logged; the fault manifest lists every injected row; clean tables pass key and reference tests before injection. Data: spec section 6. Source: R3; D-003 follow-up 2.

**S1-09 Manifests and generator tests.** Problem: without these, "reproducible" is a claim. AC: two runs with the same seed hash identically; run manifest records seed, scale, git sha, package versions, row counts, timings, and calibrated constants; the sealing test fails the build on any reference to `ground_truth` outside the generator; all tests green in CI. Data: none. Source: charter 7.2; spec section 8.

**S1-10 READMEs.** Problem: the Data Analyst's review and every future reader start from the README, and D-002 wants the cost assumption written down. AC: a reader with the repository and Python 3.13 can regenerate at scale 0.1 in under ten minutes using only the README; the fault catalogue lists every fault type with its rate and how to find it in the manifest; the maturity, censoring, and cohort limits from spec 5.3 and 5.4 are stated; pinned versions listed. Data: none. Source: D-002 follow-up 1; D-003 follow-up 2.

**S1-11 dbt staging and tests.** Problem: the charter's quality suite lives on typed, deduplicated staging models, and the Sprint 2 marts build on them. AC: one staging model per raw table; every model has not-null and unique tests on keys, accepted-values tests on every categorical, relationships tests on every foreign key, and a row-count test with tolerance; `dbt test` passes in CI on the injected-fault data, which means the staging models remove the duplicates and handle the nulls. Data: raw layer. Source: charter 7.2.

**S1-12 Data dictionary v1.** Problem: no number can be reported until its definition and lineage are written (O3.2), and D-003 asks for every parameter to be listed with its source. AC: every field in spec section 4 has an entry with type, source table, and a lineage note; all seventeen D-003 parameters listed with source "D-003"; definitions written for day-30 miss (with the 45-day maturity rule), risk mix (with the rule for unknown band), raw spend gap, and month 0; the guardrail entry carries the reporting rule: interval always, risk mix on the same page. Data: spec sections 3 to 5. Source: D-003 follow-up 4; RACI row 12; DA consultation.

**S1-13 Realism review.** Problem: the Data Analyst has accepted the generator approach but has not seen the data; until this is done no number from it is fit to report (D-001). AC, drafted for the BA: the Data Analyst regenerates at scale 0.1 from the README alone; confirms row counts and the D-003 rates within tolerance; confirms the seasonality is visible in a weekly and a monthly plot; finds at least one fault of every type in spec section 6 without using the manifest, then checks against it; writes a verdict, "fit for Sprint 2 build" or a numbered fault list with owner and due date, in `/decisions` if any point is disputed and in the review notes otherwise. Data: generator output at scale 0.1. Source: D-001, Data Analyst reservation and follow-up; charter 7.1.

**S1-14 Charter correction.** Problem: the charter's headline miss rate does not match the bands Finance fixed. AC: pull request to `/charter`, version 1.1, section 3 row updated to the generated value with a note referencing D-003, change history row added. Data: run manifest. Source: D-003 dissent and follow-up 3.

**S1-15 Full-scale run.** Problem: the analyses run at scale 1.0; if it does not fit in time and memory, Sprint 2 finds out on day one. AC: scale 1.0 completes inside the spec targets; the run manifest records time and memory. Data: none. Source: spec 2.3.

**S1-16 Great Expectations.** Problem: D-002 accepted the suite on a cap; the cap has to be tried before it is reported on. AC: a suite on the raw layer runs in CI, or the fallback to dbt tests only is logged against D-002 and charter 7.2 corrected. Hours logged in `/reflection` either way. Data: raw layer. Source: D-002 condition 2 and follow-up 2.

**S1-17 Review and retrospective.** Problem: the sprint closes on evidence, not on a feeling. AC: reflective log entry mapped to the behavioural checklist; GE hours reported; decision log checked for any conflict resolved off the record (R5); the late cut list and the D-006 handling reviewed as process points; Sprint 2 planning inputs listed. Data: none. Source: charter 8, 11; RACI rows 24, 26.

## 4. Recurring items (not sized)

| Item | Role | When |
|---|---|---|
| Async standups, Yesterday / Today / Blockers, one per role | All; PO accountable | Fri 11, Mon 14, Wed 16, Fri 18 Sep |
| Stakeholder email | DE | Fri 11 Sep, Fri 18 Sep |
| Blockers line, Fri 11 Sep: raise D-006 | DE | Fri 11 Sep |
| Acceptance criteria accepted or rewritten for every item above (D-001 condition) | BA | Fri 11 Sep |
| Cut line and sprint goal reading decided (section 6) | PO | Fri 11 Sep |

## 5. Proposed cut list (Data Engineer's view; Product Owner decides)

> **Actioned by D-007 (11 Sep 2026): option (b).** Cut lines 1, 2, and 3 below are applied in full; lines 4 and 5 are applied as partial scope (see the ticket changes above). Line 6 (S1-07 to Sprint 2) is **not** applied — Meridian Pay tables stay in Sprint 1. +6 Data Engineer hours added this sprint only.

If the hours run out, cut in this order. Each line says what it saves and what it costs.

1. **S1-16 Great Expectations.** Already Could. Saves 3 hours; costs nothing this sprint. D-002's cap applies whenever it starts; report zero hours at the review.
2. **S1-15 Full-scale run.** Saves 1 hour. The Data Analyst reviews at scale 0.1, which is enough to see rates, seasonality, and faults. Costs: the scale-1.0 run happens on Sprint 2 day one, and any performance problem surfaces then.
3. **S1-11 dbt staging.** Saves 3 hours; costs the most. The sprint goal says "quality suite passing", and without staging the suite that passes is the generator's own tests in CI. Moves to Sprint 2 day one.
4. **S1-08, partial.** Drop the impossible values and the clock skew, the two additions beyond R3. Keep exact duplicates, nulls, late records, and the near-duplicates the Data Analyst asked for. Saves about half an hour.
5. **S1-06, partial.** Generate checkout sessions only; skip the 94% of sessions that never reach checkout. Saves about an hour and most of the run time. Costs: the 2.4m sessions baseline is not reproduced until Sprint 2, and the dictionary says so.
6. **Last resort: S1-07 to Sprint 2 week 1.** Saves 3 hours. Workstream 1 analysis does not start until Sprint 2, so the tables would still exist before they are needed. Costs: the Data Analyst's review covers customers, orders, memberships, and checkout only, and is repeated for Meridian Pay in Sprint 2; and the guardrail power analysis (D-004) has no data to run on until it lands. Not recommended.

Never cut: seed and scale (S1-09), `baselines.yaml` (S1-03), the planted effects (S1-04 to S1-07 as designed), the sealing test, the dictionary (S1-12), the realism review (S1-13). Each of these is a charter commitment, not a feature.

Arithmetic: lines 1 to 3 touch only Should and Could items, so the Must total stays at 19 hours against 11. Lines 4 and 5 bring it to about 17.5. Only line 6 brings it near 14. Cutting alone does not close the gap; that is the point of section 6.

## 6. Capacity decision — resolved
Decided as D-007: option (b). See `/decisions/decision-log.md` D-007 for the full rationale and follow-up actions. Acceptance criteria review (Business Analyst, per D-001) still applies to every item above and remains due Friday 11 September.

## 7. D-006 — resolved

Decided as D-006: option 2 (active accounts vs. purchasing customers split). See `/decisions/decision-log.md` D-006 for the full rationale and follow-up actions.

## 8. Sprint 2 candidates, not in Sprint 1

Pulled forward only if everything above lands early, which section 1 says it will not.

- Guardrail power analysis (R8), input to D-004. DE, WS1, O1.2.
- Experiment design document draft, input to D-005. DE (BA, DA consulted), WS1, O1.1.
- Experiment mart with the sample ratio test. DE, WS1.
- Great Expectations, if cut here.
- Stretch: Power BI. Out of scope unless every milestone lands early (charter section 4).

## Change history

| Version | Date | Change |
|---|---|---|
| 0.1 | 10 September 2026 | First issue: items from the generator spec and the D-001 to D-003 follow-ups; cut list proposal; D-006 draft. PO and BA to confirm | 
| 0.2 | 11 September 2026 | D-006 and D-007 decided. Capacity resolved (option b): S1-06 and S1-08 scoped to partial per D-007; S1-11 deferred to Sprint 2; sections 6 and 7 replaced with resolved pointers; sprint goal restated |
| 0.3 | 12 September 2026 | S1-06 marked built per D-008: order generation rebuilt from a real checkout funnel rather than layered around S1-05's orders. Table row and item-detail paragraph updated; three disclosed simplifications noted |
| 0.4 | 12 September 2026 | S1-07 marked built: Meridian Pay tables, bands, declines, cure/default calibration. Table row and item-detail paragraph updated; cross-referenced D-009 (the checkout_core.py MP-share draw-rate correction discovered during this build) |
