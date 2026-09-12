# Generator Specification: `pipeline/generator/`

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | Thursday 10 September 2026 |
| Author | Data Engineer (RACI row 9, A/R) |
| Consulted | Data Analyst, Thursday 10 September 2026 — record in section 10 |
| Informed | Product Owner, Business Analyst, Finance representative (stakeholder email, Friday 11 September 2026). Section 7 is sealed: see the notice there |
| Status | Issued. Changes go through a pull request to `/pipeline/generator` under charter 11.5 |
| Related | `/charter/project-charter.md` sections 3, 7.1, 7.3, 7.4, 10; `/decisions/decision-log.md` D-002, D-003; `/backlog/sprints/sprint-01.md` |

## 1. Purpose

The generator produces every dataset the project uses: a fictional UK retailer, January 2025 to August 2026, with a checkout A/B test in June 2026 and a loyalty programme that customers join over time. It is seeded, so anyone who clones the repository regenerates the same files byte for byte. It reproduces the baselines Finance confirmed in D-003, plants four effects for the analyses to recover (conversion, repayment, loyalty, self-selection), and injects the faults R3 asks for. Its outputs are the raw layer of the pipeline; everything downstream reads them and nothing else.

Two things the generator is not. It is not a simulation of how Meridian Retail Group would run its business; the customer model is the simplest one that reproduces the baselines. And it is not a source of truth for the analyses: the pipeline has to work as if `ground_truth.md` did not exist, and section 8 describes the test that enforces that.

## 2. Running it

### 2.1 Layout

```
pipeline/generator/
├── README.md                 # how to run; the fault catalogue; realism notes and known limits
├── generator-spec.md         # this document
├── ground_truth.md           # rendered from config/ground_truth.yaml on every run; SEALED
├── config/
│   ├── baselines.yaml        # every D-003 parameter, one comment per entry citing D-003
│   ├── generator.yaml        # structural and nuisance choices (section 5)
│   ├── faults.yaml           # fault rates (R3), documented in README.md
│   └── ground_truth.yaml     # planted effects; SEALED; read by the generator only
├── src/meridian_gen/         # one module per table group; numpy, pandas, pyarrow
├── tests/                    # pytest: structure, calibration, experiment, reproducibility, fault recall, sealing
└── generate.py               # entry point
```

Outputs go to `pipeline/data/raw/`, which is git-ignored. Nothing generated is committed; CI regenerates it.

```
pipeline/data/raw/
├── customers/customers.parquet
├── circle_memberships/circle_memberships.parquet
├── experiment_assignments/experiment_assignments.parquet
├── sessions/year_month=YYYY-MM/part-0.parquet
├── checkout_events/year_month=YYYY-MM/part-0.parquet
├── orders/year_month=YYYY-MM/part-0.parquet
├── mp_applications/year_month=YYYY-MM/part-0.parquet
├── mp_agreements/year_month=YYYY-MM/part-0.parquet
├── mp_instalments/year_month=YYYY-MM/part-0.parquet      # partitioned by due month
├── mp_payments/year_month=YYYY-MM/part-0.parquet         # partitioned by recorded month
└── _manifest/
    ├── run_manifest.json          # seed, scale, git sha, package versions, row counts, timings, calibrated constants
    ├── fault_manifest.parquet     # every injected fault: table, key, fault_type, detail (used by tests only)
    └── ground_truth_realised.json # the planted effects as they came out under this seed; SEALED
```

### 2.2 Command

```
python generate.py --scale 1.0 --seed 20260907 --extract-at 2026-08-31T23:59:59Z
```

- `--scale` multiplies every population and volume (customers, visitors, sessions, joins). Rates, shares, effects, and dates never change with scale. Default 0.1 for local development; 1.0 for the run the analyses use; 0.01 in CI.
- `--seed` is the master seed. Each table draws from a child seed spawned from it (`numpy.random.SeedSequence.spawn`) in a fixed order, so adding a table later does not change earlier ones. Default 20260907.
- `--extract-at` is the moment the raw files were "pulled". Any record whose `recorded_at` is later than this is absent (section 5.3). Default 31 August 2026, end of day, UTC.

The same seed and scale produce identical files, checked by hashing in CI (section 8). Timestamps are UTC. Day-of-week seasonality is computed on the Europe/London date.

### 2.3 Targets

| Scale | Sessions | Orders | Run time | Peak memory |
|---|---|---|---|---|
| 1.0 | ≈ 46m | ≈ 1.41m | under 15 minutes on a laptop | under 4 GB |
| 0.1 | ≈ 4.6m | ≈ 141k | under 2 minutes | under 1 GB |
| 0.01 (CI) | ≈ 460k | ≈ 14k | under 1 minute | — |

The month loop writes each month's Parquet files before starting the next, so memory does not grow with the date range. Twenty months at the D-003 seasonality sum to 19.3 baseline-month equivalents, which is why the totals above are not 20 × the baseline.

## 3. Baselines and parameters from D-003

Every value below is in `config/baselines.yaml`, one entry each, with the comment `# D-003` and the parameter's "Needed by" reference. The generator reads that file and no other source for these numbers.

### 3.1 The ten charter baselines, confirmed unchanged (D-003, option 3)

| Parameter | Value | How the generator uses it |
|---|---|---|
| Sessions per month | 2,400,000 | Monthly mean; seasonality applied around it (3.2) |
| Visitors starting checkout per month | 140,000 | Distinct visitors with at least one `checkout_started` event in the month |
| Checkout completion rate | 52% | Visitor-level: visitors with an order / visitors starting checkout, per month. Drawn per visitor-month, so it holds by construction |
| Average order value | £68.00 | Mean of `order_value_gbp`; lognormal with category multipliers (5.2) |
| Meridian Pay share of orders | 24% | Orders paid with Meridian Pay / all orders |
| Meridian Pay day-30 instalment miss rate | 4.5% (see 3.4: generates 4.37%) | Instalment 2 unpaid on its due date / Meridian Pay agreements |
| Meridian Pay 90-day default rate | 1.9% of order value | Value written off at day 90 / agreement value |
| Active customers (last 12 months) | 850,000 | Customers with at least one order 1 September 2025 to 31 August 2026. See 3.4: blocker raised |
| Circle members | 280,000, joined February 2025 to August 2026 | Exact count at 31 August 2026; monthly cohort profile in 5.4 |
| Raw spend gap, members vs non-members | Members spend about 30% more per month | Calibration target, defined in 5.4 |

### 3.2 Parameters Finance added (D-003)

| Parameter | Value | Encoding |
|---|---|---|
| Credit bands, share of Meridian Pay orders | A 30%, B 30%, C 22%, D 12%, E 6% | Share of *approved* agreements. Application shares are derived (5.3) |
| Day-30 miss rate by band | A 1.5%, B 3.0%, C 5.0%, D 9.0%, E 14.0% | Probability instalment 2 is unpaid on its due date, by band |
| Meridian Pay decline rate | 12% of applications | Overall rate; band-level rates in 5.3 |
| Agreement structure | Value follows the order value distribution; three equal instalments due day 0, 30, 60 | `mp_instalments`: three rows per agreement, `amount_gbp` = agreement value / 3, rounded to the penny with the remainder on instalment 1 |
| 90-day default rate by band | Proportional to the band's day-30 miss rate; overall 1.9% of value | Common cure probability across bands (5.3), calibrated so total written-off value is 1.9% |
| Circle programme cost | Points worth 1.5% of member spend, 70% redeemed; £0.15 per member per month | Not generated. Stored in `baselines.yaml` for the marts to apply in Sprint 4 (O2.3) |
| Seasonality, weekly | Sunday and Monday +15%, Friday and Saturday −10% | Daily factors normalised to mean 1.0 across the week: Sun/Mon 1.15, Tue–Thu 0.967, Fri/Sat 0.90 |
| Seasonality, monthly | November and December +40%, January and February −15% | Monthly factors normalised to mean 1.0 across the year: Nov/Dec 1.40, Jan/Feb 0.85, all other months 0.9375 |

**Interpretation choice, seasonality.** D-003 states the peaks and troughs relative to "the monthly mean". Read literally, the eight unlabelled months sit at 0.9375 of the mean so that the mean is the baseline. The alternative, eight months at 1.0, would put the annual mean 4% above the baselines Finance confirmed. I have taken the literal reading. It means June 2026, the test month, runs at 0.9375 × 140,000 = 131,250 checkout-starting visitors, and the two-week test window holds about 61,250 of them, around 30,600 per arm. Finance owns baselines (RACI row 8); if Finance prefers the other reading it is a one-line change to `baselines.yaml` and this paragraph.

### 3.3 Derived quantities (scale 1.0, per baseline month)

| Quantity | Value | From |
|---|---|---|
| Orders | 72,800 | 140,000 × 52%; one order per completing visitor-month (5.2) |
| Revenue | £4.95m per month, £59.4m per year | 72,800 × £68. Matches "about £60m" in charter section 1 |
| Meridian Pay agreements | 17,472 | 24% of orders |
| Meridian Pay applications | 19,855 | Agreements / (1 − 12%) |
| Headline day-30 miss rate | 4.37% | Weighted band rates: 0.45 + 0.90 + 1.10 + 1.08 + 0.84 |
| Share of Meridian Pay orders in bands D and E | 18% | The stop rule's risk-mix measure, charter 7.3 |
| Checkout-starting visitors, test window (1 to 14 June 2026) | ≈ 61,250 | 140,000 × 0.9375 × 14/30 |

### 3.4 Two consequences that need a decision

**Headline miss rate.** As the Data Analyst noted under D-003, the band shares and band rates give 4.37%, not 4.5%. Finance ruled that bands are fixed and the headline is what falls out. The generator therefore produces 4.37%, the calibration test asserts 4.37 ± 0.15 points, and the D-003 follow-up (correct charter section 3 by pull request at the Sprint 1 review) is backlog item S1-14.

**Active customers. Blocker, raised for the Friday 11 September standup.** 140,000 checkout starters × 52% × 12 months = 873,600 orders a year. If "active customers (last 12 months)" means customers who placed an order, then 850,000 of them placed 873,600 orders: 1.03 orders per customer per year, with roughly 97 in 100 buying once. That is reproducible, but it has a consequence Finance should see before the generator bakes it in. Repeat spend per existing customer comes out under £1 a month, so the Circle programme (280,000 members, £0.15 per member per month in communications alone) cannot break even under any effect size the analysis could find. Sprint 4's readout would be decided by this baseline, not by the method.

The generator does not resolve this. `baselines.yaml` carries `active_customers_12m: 850000` as D-003 states it, and one more line, `purchasing_customers_12m`, which is the number the customer model actually calibrates to. Until Finance decides, it is set to 850,000, the letter of D-003. Options for Finance (RACI row 8; proposed D-006, drafted in `/backlog/sprints/sprint-01.md` section 7):

1. 850,000 is purchasers. Keep it; accept the consequence above and state it in every report.
2. 850,000 is active accounts (a logged-in session in the year), and purchasers is a separate baseline Finance sets. For illustration only: 450,000 purchasers gives 1.94 orders per customer per year and about £11 of spend per active customer per month, which is the kind of base a loyalty programme is usually run on.
3. Finance revises the figure.

The change is one line in `baselines.yaml` either way. What matters is that Finance decides before the Data Analyst's realism review on Wednesday 16 September, so the review is done on the right data.

## 4. Tables

Ten tables. Keys are surrogate integers, except `visitor_id`, which is a 16-character hex string like a first-party cookie. There are no free-text fields and no personal data (charter C4). Types are DuckDB types. Null rates given are injected from `faults.yaml`; clean data has no nulls except where marked "may be null".

### 4.1 `customers` — one row per customer, created at first order

| Field | Type | Notes |
|---|---|---|
| customer_id | BIGINT | Primary key |
| first_order_date | DATE | Acquisition date; a customer exists from their first order |
| region | VARCHAR | One of the twelve ITL1 areas, coded TLC to TLN. Null 1.5% |
| acquisition_channel | VARCHAR | organic, paid_search, email, social, direct, affiliate |
| category_affinity | VARCHAR | furniture, textiles, kitchen, decor, garden. Drives category mix, a matching covariate (charter 7.4) |

The customer's latent spend rate and latent credit band are generator state and are never written. The analyst sees only what they produce.

### 4.2 `sessions` — one row per site session

| Field | Type | Notes |
|---|---|---|
| session_id | BIGINT | Primary key |
| visitor_id | VARCHAR | Cookie-style identifier; a customer can have two (15% do) |
| customer_id | BIGINT | May be null: set only when the visitor was logged in |
| session_start_ts | TIMESTAMP | UTC |
| device | VARCHAR | mobile 62%, desktop 30%, tablet 8%. Null 2% overall, concentrated in the affiliate channel |
| channel | VARCHAR | organic 32%, paid_search 25%, direct 15%, email 12%, social 10%, affiliate 6%. Null 3% |
| landing_category | VARCHAR | The five order categories plus `home` |

### 4.3 `checkout_events` — one row per event in a checkout

| Field | Type | Notes |
|---|---|---|
| event_id | BIGINT | Primary key |
| session_id | BIGINT | → sessions |
| visitor_id | VARCHAR | Denormalised from the session |
| event_ts | TIMESTAMP | UTC |
| event_type | VARCHAR | checkout_started, payment_method_selected, mp_application_submitted, mp_decision, order_placed, checkout_abandoned |
| checkout_version | VARCHAR | v1 or v2, on `checkout_started` only; v2 is the redesign, served to test-arm visitors 1 to 14 June 2026 |
| payment_method | VARCHAR | On `payment_method_selected` and `order_placed`. Null on 0.8% of `order_placed` rows |
| order_id | BIGINT | On `order_placed` → orders |
| application_id | BIGINT | On `mp_application_submitted` and `mp_decision` → mp_applications |
| mp_decision | VARCHAR | approved or declined, on `mp_decision` only |

Every checkout session has exactly one `checkout_started` and exactly one of `order_placed` or `checkout_abandoned` in clean data. About 3.5 events per checkout session.

### 4.4 `experiment_assignments` — one row per visitor in the test

| Field | Type | Notes |
|---|---|---|
| visitor_id | VARCHAR | Primary key |
| experiment_id | VARCHAR | `checkout_redesign_2026_06` |
| arm | VARCHAR | control or test; deterministic hash of visitor_id and experiment_id, 50/50 |
| assigned_at | TIMESTAMP | The visitor's first `checkout_started` in the window |

Only visitors who started checkout between 1 and 14 June 2026 appear: about 61,250 rows at scale 1.0. Sessions and events do not carry the arm; the pipeline joins on visitor_id. `checkout_version` on the events is what the visitor was served, so the two can be checked against each other.

### 4.5 `orders` — one row per order

| Field | Type | Notes |
|---|---|---|
| order_id | BIGINT | Primary key |
| customer_id | BIGINT | → customers |
| visitor_id | VARCHAR | |
| session_id | BIGINT | → sessions |
| order_ts | TIMESTAMP | UTC. 0.1% of rows are up to two minutes before their session start (clock-skew fault) |
| order_value_gbp | DECIMAL(10,2) | Mean £68. 0.05% of rows ≤ 0 (impossible-value fault) |
| item_count | SMALLINT | 1 to 8 |
| category_primary | VARCHAR | Null 1.0% |
| payment_method | VARCHAR | card, meridian_pay, paypal, other |
| delivery_region | VARCHAR | Equals the customer's region 97% of the time |

### 4.6 `mp_applications` — one row per Meridian Pay application at checkout

| Field | Type | Notes |
|---|---|---|
| application_id | BIGINT | Primary key |
| session_id | BIGINT | → sessions |
| customer_id | BIGINT | → customers. May be null: see note |
| visitor_id | VARCHAR | |
| applied_at | TIMESTAMP | UTC |
| requested_value_gbp | DECIMAL(10,2) | The basket value |
| credit_band | VARCHAR | A to E, the internal band assigned at application. Null 0.5% |
| decision | VARCHAR | approved or declined |
| order_id | BIGINT | → orders when the visitor went on to order (approved, or declined and paid another way); null when declined and abandoned |

Note on `customer_id`: a first-time visitor who applies, is declined, and abandons never becomes a customer. Their application still exists. This is the only table where a row can have no customer, and the referential integrity test allows it.

### 4.7 `mp_agreements` — one row per approved application that became an order

| Field | Type | Notes |
|---|---|---|
| agreement_id | BIGINT | Primary key |
| application_id | BIGINT | → mp_applications, unique |
| order_id | BIGINT | → orders, unique |
| customer_id | BIGINT | → customers |
| agreement_value_gbp | DECIMAL(10,2) | Equals the order value |
| start_date | DATE | Order date; instalment 1 is taken on this date |
| status_at_extract | VARCHAR | active, settled, defaulted |
| written_off_value_gbp | DECIMAL(10,2) | 0 unless defaulted |

### 4.8 `mp_instalments` — three rows per agreement

| Field | Type | Notes |
|---|---|---|
| instalment_id | BIGINT | Primary key |
| agreement_id | BIGINT | → mp_agreements |
| instalment_no | SMALLINT | 1, 2, 3 |
| due_date | DATE | start_date + 0, 30, 60 days |
| amount_gbp | DECIMAL(10,2) | Agreement value / 3; penny remainder on instalment 1 |

### 4.9 `mp_payments` — one row per payment received

| Field | Type | Notes |
|---|---|---|
| payment_id | BIGINT | Primary key |
| instalment_id | BIGINT | → mp_instalments, unique in clean data |
| agreement_id | BIGINT | → mp_agreements |
| paid_at | TIMESTAMP | UTC |
| amount_gbp | DECIMAL(10,2) | Always the full instalment amount in v1 |
| recorded_at | TIMESTAMP | When the record reached the data platform: paid_at plus the reporting lag in 5.3. Rows recorded after `--extract-at` are not in the extract |

An instalment with no payment row is unpaid as far as the extract can tell. Whether that is a miss or a record that has not arrived yet depends on how old the due date is, which is why the pipeline needs a maturity rule (5.3).

### 4.10 `circle_memberships` — one row per member

| Field | Type | Notes |
|---|---|---|
| membership_id | BIGINT | Primary key |
| customer_id | BIGINT | → customers, unique in clean data |
| joined_at | DATE | February 2025 onward |
| join_channel | VARCHAR | checkout 70%, account 20%, email 10% |
| status | VARCHAR | active. No leaving in v1 |

### 4.11 Row counts, scale 1.0

| Table | Rows | Table | Rows |
|---|---|---|---|
| customers | ≈ 1.2m at 850k purchasers; ≈ 0.66m at the illustrative 450k | mp_applications | ≈ 384k |
| sessions | ≈ 46m | mp_agreements | ≈ 338k |
| checkout_events | ≈ 10.9m | mp_instalments | ≈ 1.01m |
| experiment_assignments | ≈ 61k | mp_payments | ≈ 0.96m |
| orders | ≈ 1.41m | circle_memberships | 280,000 exactly |

## 5. Generation model

The generator runs one loop over the twenty months. Each month, in order: customers' rates for the month; who starts checkout; who completes, with the experiment applied in June; orders and their payment method; Meridian Pay applications, agreements, and instalments; Circle joins; then the treatment multiplier for next month. Sessions and events are built around the visitor-months after the loop; payments are settled after the loop because they depend on later dates; faults are applied last. Constants below that are not from D-003 live in `config/generator.yaml`, each with a comment naming the subsection it comes from.

### 5.1 Customers and their rates

- Each customer has a latent monthly checkout-start rate, drawn once from a Gamma distribution with shape 0.8 (a few frequent buyers, many occasional ones). The Gamma scale is the constant the calibration step solves so that purchasers in the trailing twelve months match `purchasing_customers_12m`. New customers per month then fall out of 5.2: about 62,000 a month at 850,000 purchasers, about 33,000 at the illustrative 450,000. Both go in `run_manifest.json`.
- `region` is population-weighted across the twelve ITL1 areas, with London and the South East over-weighted by 10% for online retail. `category_affinity` is drawn once; 60% of a customer's orders are in their affinity category and the rest spread over the other four.
- 15% of customers use two visitor IDs (a phone and a laptop). Visitors who browse but never order have visitor IDs and no customer ID.

### 5.2 Checkout and orders

- Checkout starters in a month are existing customers who start (a Bernoulli draw at their rate × the month's seasonal factor × the loyalty multiplier in 5.4) plus anonymous visitors, filled so that the distinct starter count matches the baseline for the month.
- Completion is drawn per starter at the device rate: mobile 50%, desktop 56%, tablet 52%, which weight to 52.0% at the device mix. One order per completing visitor-month. A completing anonymous visitor becomes a new customer at that order.
- Checkout sessions in the month: completers have one (85%) or two, the first abandoned (15%); non-completers have one (80%) or two (20%). Non-checkout sessions are then added to reach the month's session total, at 1.6 sessions per visitor-month.
- Order value: lognormal with σ = 0.6, times a category multiplier (furniture 1.8, garden 1.2, kitchen 0.9, textiles 0.7, decor 0.6), rescaled so the overall mean is £68.00; clipped to £5 to £2,000. Item count is Poisson(1.6) + 1, capped at 8.
- Payment method for a completed order: meridian_pay 24%, card 58%, paypal 12%, other 6%.
- Daily volumes within a month follow the weekly factors in 3.2. Timestamps are spread through the day with a peak between 19:00 and 22:00 local time.

**June 2026.** The month runs in two halves. In 1 to 14 June, every visitor starting checkout is assigned an arm (hash, 50/50) and the test arm's completion, payment mix, and band mix follow section 7. From 15 June everyone sees v1 again; the redesign did not ship during the data period.

### 5.3 Meridian Pay

- Applications are made by visitors who selected Meridian Pay. Each application is assigned a band. Band decline rates are A 4%, B 7%, C 12%, D 24%, E 36%; application shares are set so that approved agreements land at the D-003 shares, which puts applications at A 27.5%, B 28.4%, C 22.0%, D 13.9%, E 8.3% and the overall decline rate at 12.0%.
- A declined applicant pays by card and completes (45%) or abandons (55%). Both are inside the 52% completion rate, not on top of it.
- Instalment 1 is paid at `start_date`. Instalment 2 is unpaid on its due date with the band's miss rate. Instalment 3: if instalment 2 was paid on time, half the band rate; if instalment 2 was missed and later paid, the band rate; if instalment 2 is still unpaid, instalment 3 is not paid.
- A missed instalment is either cured (paid late, between day +1 and day +59, weighted to the first fortnight) or never paid. The cure probability is the same for every band, which is what makes default proportional to the miss rate as D-003 requires, and it is calibrated so that written-off value at day 90 is 1.9% of agreement value. It comes out near 47%: roughly half the customers who miss day 30 default. The calibrated value is written to `run_manifest.json`.
- At day 90 after `start_date`, any agreement with an unpaid instalment is `defaulted` and the unpaid amount is `written_off_value_gbp`. Agreements not yet 90 days old at the extract are `active`.
- Reporting lag: `recorded_at` = `paid_at` + 0 days (85%), 1 to 3 days (10%), 4 to 14 days (4%), 15 to 45 days (1%). Payments recorded after the extract are absent from it.

Consequences the pipeline must handle:

- **Maturity.** An instalment can be called missed only when `due_date` + 45 days ≤ `extract_at`; before that, a missing payment row may be a late record. For the test window, instalment 2 is due by 14 July 2026, so all of them are mature at the 31 August extract. Instalments due in August 2026 are not, and a naive August miss rate will read high.
- **90-day status is censored for the test.** An order placed on 14 June 2026 reaches day 90 on 12 September, after the extract. The 90-day default rate cannot be computed for the test window. This is why the charter's guardrail is the day-30 miss rate, and the experiment mart must not compute a 90-day rate for the test.

### 5.4 Meridian Circle and self-selection

- Members are added in fixed monthly cohorts totalling 280,000: February 2025 24,000; March 20,000; April 16,000; then 13,750 in every month from May 2025 to August 2026 (16 × 13,750 = 220,000). A launch bump, then a steady state.
- Who joins in a month is a weighted draw from customers who have not yet joined. The weight is (latent rate / median latent rate) raised to a selection exponent, times 1.10 for London and 1.10 for furniture affinity, and weighted towards customers who placed an order that month so that 70% of joins are at the checkout, 20% from the account page, 10% from an email campaign.
- The selection exponent is the one constant in this section the calibration step solves. Its target is the D-003 raw gap: among customers with an order in the trailing twelve months, mean monthly spend of members (joined by 31 August 2026) is 1.30 × that of non-members, ± 0.03. With the planted effect fixed (section 7), the exponent absorbs whatever is left of the 30%. The realised selection premium (mean latent rate of joiners / mean latent rate of never-joiners) is written to `ground_truth_realised.json`; expect around +20%.
- After joining, a member's checkout-start rate is multiplied by the effect in section 7, by months since joining. The effect is on frequency only. Order value and category mix do not change on joining.

Consequences for Sprint 3:

- **The join month is not a treatment month.** Seven in ten members join while placing an order, so month 0 always contains an order for them. That is selection, not the programme. The estimand in charter 7.4 counts months 1 to 6 after joining; month 0 is shown in the event study and excluded from the ATT.
- **Early cohorts have short pre-periods.** Data starts January 2025. Members who joined February to June 2025 have 1 to 5 pre-months, and the placebo test (fake join dates six months earlier) is only defined for cohorts from July 2025. The diagnostic sample is cohorts July 2025 to February 2026: six full months either side, 110,000 members. The full sample is still used for the estimate.

### 5.5 Seasonality

Monthly factors from 3.2 apply to sessions, checkout starters, and existing customers' rates alike. Weekly factors apply within the month. Circle cohort sizes are fixed and not seasonal. The checkout completion rate does not vary by season in v1.

## 6. Injected faults (R3)

Faults are applied to the finished clean tables, last, so that every fault is a known deviation from a consistent dataset. Every injected fault is logged in `_manifest/fault_manifest.parquet` (table, key, fault_type, detail). The manifest is used by the generator's own tests to check that the staging layer catches what was planted; dbt models never read it. Rates are in `config/faults.yaml` and documented in the generator README, which is where D-003 said they go.

| Table | Fault | Rate | What it tests downstream |
|---|---|---|---|
| sessions | Exact duplicate rows | 0.5% | Deduplication on `session_id` |
| sessions | `device` null | 2.0% overall: 8% in the affiliate channel, 1.5% elsewhere | Not-null tests; nulls that are not random |
| sessions | `channel` null | 3.0% | Not-null tests |
| checkout_events | Exact duplicate rows | 1.0% | Deduplication on `event_id` |
| checkout_events | Near-duplicates: new `event_id`, same session and type, `event_ts` + 1 second | 0.3% | Deduplication that keys on content, not just the id |
| checkout_events | `payment_method` null on `order_placed` | 0.8% | Backfill from `orders` |
| orders | Exact duplicate rows | 0.2% | Deduplication on `order_id`; the visitor-level completion count must not double-count |
| orders | `category_primary` null | 1.0% | Not-null; category mix as a matching covariate |
| orders | `order_value_gbp` ≤ 0 | 0.05% | Accepted-range test; AOV must exclude these |
| orders | `order_ts` up to two minutes before `session_start_ts` | 0.1% | Ordering assumptions in the funnel |
| customers | `region` null | 1.5% | Matching covariate with missing values |
| mp_applications | `credit_band` null | 0.5% | The risk-mix guardrail needs a rule for unknown band |
| mp_agreements | Exact duplicate rows | 0.1% | Deduplication |
| mp_payments | Exact duplicate rows | 0.5% | Duplicate payments would understate misses |
| mp_payments | Late-arriving records | Lag distribution in 5.3; rows past the extract absent | Maturity rule |
| circle_memberships | Duplicate rows | 1.0% | One membership per customer |
| circle_memberships | `joined_at` before `first_order_date` | 0.3% | Referential logic test |

Two of these, the impossible values and the clock skew, are additions to the list in R3 (duplicates, missing values, late records, seasonality). They are cheap, they give the accepted-range tests something to catch, and the Data Analyst can strike them at the realism review.

## 7. Planted ground truth

> **Sealed.** This section, `config/ground_truth.yaml`, `ground_truth.md`, and `_manifest/ground_truth_realised.json` are read by the Data Engineer and the Data Analyst only, until the final readout in Sprint 4 (charter 7.1; D-003). In a public repository this is a discipline, not a secret. It is enforced where it can be: the analysis and dbt code may not reference any of these files, and CI checks that (section 8). The analyses are written from the diagnostics, as a real one would be.

### 7.1 Workstream 1: the checkout redesign

| Quantity | Control (v1) | Test (v2) | Planted change |
|---|---|---|---|
| Visitor-level checkout completion | 52.0% | 53.8% | **+1.8 percentage points**, the same on every device |
| Average order value | £68.00 | £68.00 | None. A planted null |
| Meridian Pay share of orders | 24.0% | 27.0% | +3.0 points |
| Band shares of Meridian Pay orders | A 30, B 30, C 22, D 12, E 6 | A 28, B 29, C 22, D 14, E 7 | Mix shifts down the bands |
| Share in bands D and E | 18.0% | 21.0% | **+3.0 points**: over the indicative 2-point trigger in charter 7.3 |
| Day-30 miss rate | 4.37% | 4.63% | **+0.26 points**, entirely through the mix; band rates unchanged (D-003) |
| Meridian Pay decline rate | 12.0% | 12.8% | +0.8 points; band decline rates unchanged |
| Arm split | 50 / 50 | | No sample ratio mismatch planted. Randomisation is correct (A4) |

Why these values. The conversion lift sits above the 1.5 points the charter wants to detect and below the 2 points that would make the test trivial. The repayment effect is real and below the indicative 0.5-point threshold, because the point of R8 is that a two-week test cannot see a rise of this size on the miss rate: with about 4,000 Meridian Pay orders per arm, the 90% interval on the difference is roughly ± 0.75 points, wider than the threshold itself. The same shift is visible in the risk mix, where a 3-point move against an 18% base has a standard error under a point. So the planted world is one where the primary metric says ship, the miss-rate guardrail says "cannot tell", and the risk-mix rule says Finance reviews. That is the decision the charter was written to practise, and it lands in Sprint 3 with real numbers attached.

Mechanism: in the test arm, completion is drawn at 53.8%; completers choose Meridian Pay at 27%; and Meridian Pay applications in the test arm are drawn from band shares that, after the unchanged band decline rates, leave the approved mix at 28/29/22/14/7. Everything else is identical between arms.

### 7.2 Workstream 2: Circle membership and spend

| Quantity | Value | Notes |
|---|---|---|
| Effect on checkout-start rate, month 0 (join month) | +4% | Partial month; excluded from the ATT |
| Months 1 to 3 | +12% | Novelty |
| Months 4 to 6 | +8% | |
| Months 7 onward | +6% | Persists; no decay to zero in the data period |
| **ATT on monthly spend, months 1 to 6** | **+10.0%** of counterfactual spend | The estimand in charter 7.4. In £: 10% of the joiners' counterfactual monthly spend, which depends on D-006 (3.4); the realised figure is in `ground_truth_realised.json` |
| Effect on order value, category mix | None | Planted nulls |
| Selection premium | Calibrated to the 30% raw gap; expect about +20% on the latent rate | Time-invariant, so customer fixed effects absorb it (DiD works); pre-join spend is a noisy proxy for it (matching gets close, not all the way) |
| Raw gap decomposition | ≈ 20 points selection, ≈ 10 points programme | 1.20 × 1.08 ≈ 1.30, where 1.08 is the average multiplier across members' post-join months in the trailing year |

Why these values. The effect is dynamic on purpose. With staggered joining and an effect that changes with time since joining, a plain two-way fixed effects regression uses already-joined members as controls for later joiners and is biased; that is R7, and the comparison in charter 7.4 needs something to show. The effect is homogeneous across cohorts, regions, and categories, so the heterogeneity-robust estimator has one number to recover. Selection is on a fixed customer trait, so parallel trends hold before joining and the placebo comes out clean, apart from the month-0 order that joining at the checkout guarantees.

### 7.3 Realised values

Parameters are what the generator aims at; a finite sample lands nearby. After every run the generator writes `ground_truth_realised.json` with, under that seed and scale, the actual completion rates by arm, band mix by arm, miss rate by arm, the realised ATT in £ and in %, and the realised selection premium. The final readout compares each estimate with both the parameter and the realised value, because a method that recovers the realised value has done its job even when sampling noise moved it off the parameter.

## 8. Tests shipped with the generator

`pytest pipeline/generator/tests` runs in CI on every pull request at scale 0.01, and locally at scale 0.1 before a pull request is opened. These are the generator's tests; the data quality suite on the pipeline (dbt tests, Great Expectations) is separate and is backlog items S1-11 and S1-16.

| Test | Asserts |
|---|---|
| Structure | Every table has exactly the fields and types in section 4; every partition is readable by DuckDB |
| Keys and references | Primary keys unique and referential integrity intact **before** faults are applied; the fault manifest accounts for every violation after |
| Calibration (scale ≥ 0.1) | Monthly sessions and checkout starters within ±2% of target after seasonality; completion 52.0 ± 0.3 points; AOV £68 ± £0.50; Meridian Pay share 24.0 ± 0.3; band shares ± 0.5; decline 12.0 ± 0.3; day-30 miss 4.37 ± 0.15; written-off value 1.9 ± 0.1; members exactly 280,000 × scale; raw gap 1.30 ± 0.03; purchasers in trailing 12 months within ±2% of `purchasing_customers_12m`. Tolerances widen by 1/√scale below 1.0 |
| Experiment | Arm split passes a sample ratio test at p > 0.01; no visitor with both v1 and v2 `checkout_started` events in the window; realised conversion difference within ±0.5 points of the planted +1.8 |
| Reproducibility | Two runs with the same seed and scale produce identical file hashes |
| Fault recall | Every entry in `fault_manifest.parquet` is present in the raw files; the count per fault type matches `faults.yaml` within ±10% |
| Sealing | No file under `pipeline/dbt`, `pipeline/quality`, or `pipeline/analysis` contains the string `ground_truth`. Fails the build if one does |
| Run time | Scale 0.01 completes inside 60 seconds in CI |

## 9. What goes where

D-003's follow-up actions name three places. This is the split, and the rule for each.

| Place | Holds | Rule |
|---|---|---|
| `config/baselines.yaml` | The seventeen D-003 parameters (3.1, 3.2), the seasonality normalisation note, `purchasing_customers_12m` with its D-006 note | Every entry carries `# D-003`. Nothing enters without a decision ID. Changing a value is a decision, not a commit |
| `config/generator.yaml` | Scale and seed defaults, extract date, distributions, funnel constants, device, channel, region, and category shares, category multipliers, band decline rates, cure model, cohort sizes, selection weights (section 5) | Every entry cites the subsection of this spec it comes from. The Data Engineer's call (RACI row 9), Data Analyst consulted |
| `config/faults.yaml` | Every fault in section 6 with its rate | Documented in the generator README (D-003). Open to all roles |
| `config/ground_truth.yaml` → `ground_truth.md`, `ground_truth_realised.json` | Section 7 | Sealed until the readout. `ground_truth.md` is rendered from the YAML on every run so the two cannot drift; this spec quotes the values at the time of writing |
| `README.md` (generator) | How to run and reproduce; seeds and scale; the output layout; the fault catalogue and how to find each fault in the manifest; the maturity and censoring notes from 5.3; the cohort notes from 5.4; a line that every business parameter comes from `baselines.yaml` and D-003; the sealing convention | Written for someone who has never seen the repository. The Data Analyst's realism review (S1-13) is done from the README alone |
| Data dictionary (Data Analyst, RACI row 12) | Every field in section 4 with a lineage note; every D-003 parameter with source "D-003"; the definitions of day-30 miss, risk mix, raw spend gap, and month 0 | The field tables above are the Data Engineer's input. The dictionary is the Data Analyst's document |

## 10. Consultation record: Data Analyst, Thursday 10 September 2026

RACI row 9 makes the Data Analyst consulted on the generator, and D-003 names the planted effects and fault rates as the two things to consult on. Notes in the Data Analyst's words; responses in mine.

**On the conversion effect.** "Plus 1.8 points is fine. It is above the 1.5 we said we could detect and below the 2 that would make the whole test too easy. Keep it the same on every device, or someone will ask for a mobile breakdown in Sprint 3 and we are into R4." Response: kept homogeneous; recorded in 7.1.

**On the repayment effect.** "A rise of 0.26 points worries me, but not for Finance's reason. In two weeks we cannot tell 0.26 from zero or from 0.5. So the readout will say no evidence of a rise, and someone will read that as no rise. I want the interval printed next to every guardrail estimate, never a p-value on its own, and the risk-mix result on the same page as the miss rate. That is a reporting rule and I will put it in the dictionary entry for the guardrail." Response: agreed. The experiment mart's output format is Sprint 2 work, but the rule goes in the dictionary now (S1-12).

**On the loyalty effect.** "A 30-point gap that is 20 selection and 10 real is the right story, because it is the one Marketing will not want to hear. One thing: seven in ten members join at the checkout, so their join month always has an order in it. That month will look like a spike and it is not the programme doing anything. Call it month 0 and keep it out of the six months, or the number is wrong before anyone runs a regression." Response: done. Month 0 is shown and excluded (5.4, 7.2).

**On the placebo.** "The placebo uses a fake join date six months before the real one. Data starts in January 2025, so for everyone who joined before July 2025 the fake date is before the data. Say that now, so nobody discovers it in Sprint 4." Response: stated in 5.4 as the diagnostic sample.

**On the customer numbers.** "850,000 active customers and 874,000 orders a year means nearly everyone buys once. That looks odd for a retailer that runs a loyalty programme. But I do not have a number to put against it, only a feeling, so I am not asking to reopen D-003 myself. Put the arithmetic to Finance and put the answer in the dictionary; I will look at what it does to the spend panel in my review either way." Response: raised as a blocker for Friday's standup and drafted as D-006 (3.4).

**On the faults.** "If every duplicate is an exact copy, deduplication is one line and we learn nothing. Keep the near-duplicates. And do not spread the nulls evenly; real gaps come in clumps." Response: near-duplicates stay, and they stay off the cut list; device nulls are concentrated in the affiliate channel (section 6).

**Closing.** "I have not seen any data. Nothing here is fit to report until the realism review on Wednesday 16 September, and that review is done from the README, not from this document." Response: that is the acceptance criterion for S1-13.

## 11. Choices in this document that other roles may want to see

Listed for the Friday 11 September email, so that nobody marked C or I in the RACI learns of them from the data.

1. Seasonality normalised so the baselines are the annual and weekly means (3.2). Finance can object; one line to change.
2. Active customers: blocker raised, D-006 drafted, generator carries the letter of D-003 until Finance decides (3.4). Finance decides.
3. Band-level decline rates and a common cure rate are the Data Engineer's constants, not Finance's (5.3). They reproduce the D-003 aggregates and nothing depends on them individually. Finance is informed.
4. Two fault types added beyond R3's list (section 6). The Data Analyst can strike them.
5. The 90-day default rate cannot be computed for the test window (5.3). Not a choice, a consequence of A2; stated so it is not asked for in Sprint 3.
6. Section 7 is sealed from the Product Owner, Business Analyst, and Finance until the readout. The email says so and asks them not to open it.

## 12. Change history

| Version | Date | Change | Decision |
|---|---|---|---|
| 1.0 | 10 September 2026 | First issue, Data Analyst consulted | D-003 follow-up |
