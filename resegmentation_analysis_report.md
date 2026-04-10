# Resegmentation Analysis

Labels used below: `KORP = corporate segment`, `MSB = small-business segment`.

## Data Overview
- Rows: 755,217
- Unique clients: 82,070
- Month-end snapshots: 15 (2025-01-31 to 2026-03-31)
- `KORP->MSB` transfers observed: 680
- `MSB->KORP` transfers observed: 545

Most `KORP->MSB` transfers were concentrated in the expected resegmentation windows.

| Transfer month | Clients |
| --- | --- |
| 2025-02-28 | 56 |
| 2025-03-31 | 2 |
| 2025-04-30 | 2 |
| 2025-07-31 | 580 |
| 2026-02-28 | 40 |

## Hypothesis 1
`KORP` is transferring bad clients to `MSB`.

### Test 1A: Pre-transfer profile vs retained `KORP` clients
The comparison below uses the month immediately before transfer and compares it with `KORP` clients that stayed in `KORP` in the next month.

| Metric | Next month KORP->MSB | Retained in KORP |
| --- | --- | --- |
| Already NPL (class 3-5) | 5.44% | 3.49% |
| NPL within 3 months | 6.91% | 3.97% |
| Watchlist (class 1-2) | 28.68% | 20.07% |
| Any overdue debt | 29.56% | 19.66% |
| Turnover_y down vs 3 months earlier | 29.12% | 16.54% |
| Still satisfied formal KORP rule | 3.53% | 63.49% |

### Test 1B: Same comparison only among clients who no longer satisfied the formal `KORP` rule

| Metric | Next month KORP->MSB | Retained in KORP |
| --- | --- | --- |
| Already NPL (class 3-5) | 5.34% | 7.08% |
| NPL within 3 months | 6.71% | 8.03% |
| Watchlist (class 1-2) | 28.66% | 14.19% |
| Any overdue debt | 29.73% | 17.13% |
| Turnover_y down vs 3 months earlier | 29.42% | 10.07% |

Overdue amounts among non-rule clients with overdue debt:
- `KORP->MSB`: mean 11.29 bn, median 5.70 bn
- Retained `KORP`: mean 14.66 bn, median 8.86 bn

Breakdown of `KORP->MSB` transfers by rule/risk bucket (month before transfer):
| Bucket | Clients | Share |
| --- | --- | --- |
| No formal KORP rule, no risk flag | 432 | 63.53% |
| No formal KORP rule, risk flag present | 224 | 32.94% |
| Still formal KORP rule, no risk flag | 15 | 2.21% |
| Still formal KORP rule, risk flag present | 9 | 1.32% |

### Reading
- Partial support only. The transferred cohort is more stressed than the average retained `KORP` client on watchlist status, overdue incidence, and falling `turnover_y`.
- But this does not look like mass dumping of the worst current NPLs. Among clients who already failed the formal `KORP` rule, transferred clients had lower current NPL and lower overdue amounts than non-rule clients still kept in `KORP`.
- 96.47% of transfers happened after the client no longer met the formal `KORP` rule. Only 3.53% still met the rule one month before transfer.
- Bottom line: the pattern is more consistent with rule-based resegmentation plus some bias toward borderline deteriorating clients, not with systematically pushing out the worst NPL book.

## Hypothesis 2
`KORP` introduces mediocre clients for a short time to hit client-count KPI and then drops them or passes them to `MSB`.

Total `entry` + `re_entry` rows in `KORP`: 553

### Entry quality
| Metric | Share |
| --- | --- |
| Met formal KORP rule at entry | 51.18% |
| Group or official at entry | 50.63% |
| Turnover_y > 100 at entry | 0.18% |
| Loan amount > 100 at entry | 2.17% |
| Already NPL at entry | 0.00% |
| Watchlist (class 1-2) at entry | 3.62% |
| Any overdue at entry | 3.25% |
| Weak at entry: zero turnover_y, zero loan, not group, not official | 47.20% |

### Mature cohorts only
To avoid right-censoring, the tables below use only entry cohorts that had enough follow-up time in the dataset.

| Window | Mature entries | Left KORP | Moved to MSB | Dropped/closed | Weak at entry |
| --- | --- | --- | --- | --- | --- |
| Within 3 months | 365 | 10.96% | 6.85% | 4.11% | 38.08% |
| Within 6 months | 307 | 22.80% | 11.73% | 11.07% | 43.97% |

Six-month leave breakdown for mature entry cohorts:
| Outcome within 6 months | Clients |
| --- | --- |
| to_msb | 36 |
| drop_or_closed | 34 |

Weak vs non-weak mature 6-month entry cohorts:
| Entry type | Clients | Left within 6m | Moved to MSB within 6m |
| --- | --- | --- | --- |
| Weak at entry | 135 | 51.11% | 26.67% |
| Not weak at entry | 172 | 0.58% | 0.00% |

### Reading
- Strong support for this hypothesis in a specific sub-cohort: the weak `KORP` entrants.
- 47.20% of all `KORP` entrants were weak at entry and did not satisfy the formal `KORP` rule.
- In the mature 6-month cohort, weak entrants left `KORP` in 51.11% of cases, with 26.67% moving specifically to `MSB`.
- In the same mature 6-month cohort, non-weak entrants almost never left `KORP` early: 0.58%, and none moved to `MSB` within 6 months.
- This is hard to explain as normal onboarding noise. It is consistent with short-term inflation of the `KORP` client base using clients that do not look like durable `KORP` relationships.

## Could transferred clients have become better if they had not been moved to MSB?
This cannot be proven causally from this dataset alone, but we can compare post-event improvement rates.

### Risky clients before transfer vs risky clients retained in KORP
| Metric | KORP->MSB risky clients | Retained KORP risky clients |
| --- | --- | --- |
| Better credit class within 3 months | 10.30% | 10.25% |
| Better credit class within 6 months | 16.74% | 16.10% |
| Overdue debt decreased within 3 months | 75.11% | 65.76% |
| Turnover_y increased within 3 months | 50.21% | 51.20% |
Sample sizes: transferred risky clients = 233, retained risky clients = 6410

### NPL clients before transfer vs NPL clients retained in KORP
| Metric | KORP->MSB NPL clients | Retained KORP NPL clients |
| --- | --- | --- |
| Better credit class within 3 months | 13.51% | 11.97% |
| Better credit class within 6 months | 18.92% | 15.47% |
| Overdue debt decreased within 3 months | 48.65% | 41.31% |
Sample sizes: transferred NPL clients = 37, retained KORP NPL clients = 944

### Reading
- Transferred risky clients did improve sometimes, and their credit improvement rates were very similar to risky clients retained in `KORP`.
- That means the transferred cohort was not uniformly hopeless. Some clients still had recovery potential after the transfer.
- At the same time, the improvement gap is not large enough to claim that keeping them in `KORP` would have clearly produced better outcomes.
- The safest conclusion is: there is no strong evidence that transferred clients were beyond recovery, but this file alone cannot prove they would have improved more if they had stayed in `KORP`.

## Final Takeaway
- Hypothesis 1 is only partially supported. `KORP->MSB` transfers are somewhat more stressed than the average retained `KORP` client, especially on watchlist status and turnover decline, but they are mostly clients that already fail the formal `KORP` rule and they are not the worst current NPL cases.
- Hypothesis 2 is strongly supported for weak `KORP` entrants. A large weak sub-cohort enters `KORP` without clear rule support and then leaves quickly, most often by moving into `MSB` rather than by genuine closure.
- Recovery potential exists in part of the transferred population, so the transfer process may be moving some salvageable clients out of `KORP`, but the data is descriptive rather than causal.
