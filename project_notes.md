# Resegmentation Project Notes

## Goal
Analyze `df_all.csv` for active legal-entity base dynamics and test these hypotheses:

1. `KORP -> MSB`: `KORP` may be transferring bad or deteriorating clients to `MSB`.
2. `KORP` may be temporarily onboarding mediocre clients to improve KPI on client count, then dropping or pushing them to `MSB`.
3. `MSB -> KORP`: stronger clients may be getting pulled from `MSB` into `KORP`.

## Data Used
- Source file: `df_all.csv`
- Coverage: `2025-01-31` to `2026-03-31`
- Rows: about `755k`
- Unique clients: about `82k`

## Business Rules Used
- A client belongs to `KORP` if any of these are true:
  - `is_official = 1`
  - `is_group = 1`
  - `turnover_y_bn > 100`
  - `loan > 100`
- Otherwise, if not closed, the client belongs to `MSB`.
- `credit_class` 3, 4, 5 are treated as NPL.
- Big resegmentation is expected mainly twice a year:
  - beginning of the year
  - middle of the year

## Field Definitions
- `eomonth`
  - Month-end snapshot date for the client record.

- `client_code`
  - Client identifier.

- `segment`
  - Current client segment in that snapshot.
  - Main values:
    - `KORP`
    - `MSB`

- `status`
  - Event or state label for the client in that snapshot.
  - Current source format uses:
    - `KORP`
    - `MSB`
    - `entry`
    - `re_entry`
    - `exit_ahd`
    - `re_exit_ahd`
    - `KORP->MSB`
    - `MSB->KORP`

- `is_closed`
  - Boolean flag for a closed client record.
  - `1` means closed in that snapshot.
  - For initial closed clients, use:
    - `df[(df["eomonth"] == df["eomonth"].min()) & (df["is_closed"] == 1)]`

- `turnover_bn`
  - Monthly turnover in billion UZS.

- `turnover_y_bn`
  - Yearly turnover in billion UZS.
  - Defined as the sum of `turnover_bn` for the last 12 months.

- `credit_class`
  - Loan quality / overdue bucket.
  - Meaning of values:
    - `0`: no loans
    - `1`: up to 30 days overdue
    - `2`: overdue from 30 to 60 days
    - `3`: overdue from 60 to 180 days
    - `4`: overdue from 180 to 365 days
    - `5`: overdue 365+ days
  - NPL classes:
    - `3`, `4`, `5`

- `debt`
  - Debt amount in billion UZS.

- `loan`
  - Loan amount in billion UZS.

- `is_group`
  - Boolean flag.
  - `1` means the client is a group client.
  - `0` means not a group client.

- `is_official`
  - Boolean flag.
  - `1` means the client is an official client.
  - `0` means not an official client.

## Status Value Meanings
- `MSB`
  - Client is in the active `MSB` base.

- `KORP`
  - Client is in the active `KORP` base.

- `entry`
  - Entry event for the row segment.

- `re_entry`
  - Re-entry event for the row segment.

- `exit_ahd`
  - Exit event for the row segment.

- `re_exit_ahd`
  - Re-exit event for the row segment.

- `MSB->KORP`
  - Client transferred from `MSB` to `KORP`.

- `KORP->MSB`
  - Client transferred from `KORP` to `MSB`.

## Main Findings

### Hypothesis 1
Partial support.

- Clients moved from `KORP` to `MSB` were somewhat weaker than average retained `KORP` clients:
  - higher watchlist share
  - more overdue debt incidence
  - more turnover decline
- But most transferred clients already did **not** meet the formal `KORP` rule.
- This looked more like rule-based resegmentation with some bias toward borderline deterioration, not a clean pattern of dumping the worst NPL book.

### Hypothesis 2
Strong support for a weak entrant subgroup.

- A large share of `KORP` entrants had:
  - zero `turnover_y_bn`
  - zero `loan`
  - not `is_group`
  - not `is_official`
- In mature follow-up windows, many of these weak entrants left `KORP` quickly, and a meaningful share moved to `MSB`.
- This is consistent with short-term inflation of the `KORP` client base.

### Hypothesis 3
Test added in dashboard as an interactive view.

- The dashboard compares `MSB -> KORP` transfers against retained `MSB` clients under live filters.
- It now shows a dynamic verdict plus KPI cards for:
  - meeting formal `KORP` rule
  - good-upgrade-candidate share
  - no overdue debt
  - median `turnover_y_bn`

## Files Created
- `analyze_resegmentation.py`
  - Main analysis script.
  - Loads `df_all.csv`, computes cohorts, tests hypotheses, and writes markdown report.

- `resegmentation_analysis_report.md`
  - Generated written report with findings and tables.

- `streamlit_app.py`
  - Interactive dashboard.
  - Includes overview charts, hypothesis pages, client explorer, and report view.

- `requirements_streamlit.txt`
  - Minimal dependencies for dashboard.

## Dashboard Features
- Overview page:
  - active base composition by segment
  - inflows/outflows and net change
  - turnover trends
  - credit-class distribution over time
- Hypothesis 1 page:
  - `KORP -> MSB` comparison vs retained `KORP`
- Hypothesis 2 page:
  - `KORP` entrant quality and short-term exits
- Hypothesis 3 page:
  - `MSB -> KORP` quality comparison with live verdict
- Client Explorer:
  - full monthly history for selected client

## How To Run

Install dashboard dependencies:

```powershell
pip install -r requirements_streamlit.txt
```

Run analysis script:

```powershell
python analyze_resegmentation.py
```

Run dashboard:

```powershell
streamlit run streamlit_app.py
```

If `streamlit` is not recognized:

```powershell
python -m streamlit run streamlit_app.py
```

## Notes
- Local `pandas` required a compatibility workaround because of deprecated NumPy aliases in the environment. The workaround is included inside `analyze_resegmentation.py`.
- The analysis is descriptive, not causal.
- Some conclusions depend on limited follow-up windows, so mature-cohort logic was used where possible.
