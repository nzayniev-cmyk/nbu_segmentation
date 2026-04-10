# Project Context

## Repository Purpose
This repository contains a local analysis + Streamlit dashboard for resegmentation between `КОРП` and `МСБ` using monthly client snapshots from `df_all.csv`.

Primary deliverables:
- analysis script: `analyze_resegmentation.py`
- interactive dashboard: `streamlit_app.py`
- generated markdown report: `resegmentation_analysis_report.md`

Absolute repo path on the current machine:
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis`

Important file paths:
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\analyze_resegmentation.py`
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\streamlit_app.py`
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\df_all.csv`
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\requirements_streamlit.txt`
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\project_notes.md`
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\resegmentation_analysis_report.md`
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\Segmentation.ipynb`

## Current Repository Shape

Top-level files currently present:
- `analyze_resegmentation.py`
- `streamlit_app.py`
- `df_all.csv`
- `requirements_streamlit.txt`
- `project_notes.md`
- `resegmentation_analysis_report.md`
- `Segmentation.ipynb`
- `credits.xlsx`
- `result.xlsx`
- `streamlit_stdout.log`
- `streamlit_stderr.log`

No formal repo metadata was found:
- no `README.md`
- no `pyproject.toml`
- no `setup.py`
- no `Makefile`
- no `Dockerfile`
- no CI config
- no test folder

## Runtime / Tooling

Observed local runtime:
- Python `3.14.3`
- OS `Windows 11`

Python packages explicitly declared in repo:
- `pandas`
- `numpy`
- `streamlit>=1.32`
- `plotly>=5.17`

## Data Contract

Current `df_all.csv` header on disk:
- `eomonth`
- `client_code`
- `segment`
- `status`
- `is_closed`
- `turnover_bn`
- `turnover_y_bn`
- `credit_class`
- `loan`
- `debt`
- `is_group`
- `is_official`

Current business terminology used in the dashboard:
- current source format uses native statuses `entry`, `re_entry`, `exit_ahd`, `re_exit_ahd` plus `is_closed`
- `debt` is displayed as `Долг`
- `loan` is treated as `Сумма кредита`

Compatibility behavior in [analyze_resegmentation.py](C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\analyze_resegmentation.py):
- if an older file still has `overdue_debt_bn`, it is mapped to `debt`
- if an older file has `loan_amount_bn`, it is mapped to `loan`
- segment labels and transfer labels are normalized to `КОРП`, `МСБ`, `КОРП->МСБ`, `МСБ->КОРП`

Removed field:
- `loan_rest_bn` is no longer used by the dashboard UI

## Main Entry Points

### 1. Analysis Script
File:
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\analyze_resegmentation.py`

Behavior:
- reads `df_all.csv`
- computes cohort features and summary tables
- writes `resegmentation_analysis_report.md`

Main command:
```powershell
Set-Location "C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis"
python .\analyze_resegmentation.py
```

### 2. Streamlit Dashboard
File:
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis\streamlit_app.py`

Behavior:
- loads analysis bundle from `df_all.csv`
- renders pages:
  - `Обзор`
  - `Гипотеза 1`
  - `Гипотеза 2`
  - `Гипотеза 3`
  - `Клиенты`

Current navigation note:
- `Отчет` page was removed from sidebar navigation
- `render_report()` still exists in code but is no longer routed from the sidebar

Main command:
```powershell
Set-Location "C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis"
python -m streamlit run .\streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
```

Local URL:
- `http://127.0.0.1:8501`

LAN URL pattern:
- `http://<machine-ip>:8501`

Note:
- on the old machine this was manually served on `10.10.168.77:8501`
- that IP is machine/network-specific and should not be reused blindly after migration

## Current Functional State

### Localization and UI
- dashboard UI is mostly Russian
- abbreviations like `PL`, `NPL`, `KPI` were intentionally kept untranslated
- page-level `Вывод` / `Ключевые инсайты` blocks were added at the top of working pages

### Color / design rules currently implemented
- fixed palette based on user-provided hex colors
- positive comparison color generally uses `#D7B56D`
- negative / comparison color generally uses `#193F72`
- credit class colors:
  - `class (1)` `#149FA8`
  - `class (2)` `#7688A1`
  - `class (3)` `#2957A2`
  - `class (4)` `#193F72`
  - `class (5)` `#2B2A29`

### Business logic currently implemented
- active client logic:
  - active means positive `turnover_bn` in current month or prior 2 months present in data
- debt logic:
  - `debt > 0` is treated as presence of debt
- `loan` is treated as `Сумма кредита`
- NPL:
  - `credit_class` `3`, `4`, `5`
- PL:
  - `credit_class` `1`, `2`

### Hypothesis 1 notable state
- credit class dynamics around transfer:
  - shown as side-by-side subplots for `КОРП→МСБ` and `Остались в КОРП`
  - window `t-5 ... t+5`
  - hover shows both share and absolute client count
- yearly turnover:
  - zeros excluded from boxplot
  - cohorts split into separate panels
  - share of zero yearly turnover shown as KPI above chart
- debt:
  - zeros excluded from debt boxplot
  - cohorts split into separate panels
  - share of zero debt shown as KPI above chart
- NPL monthly KORP chart:
  - uses current-month logic, not next-month outcome logic

## Validation Commands

There is no formal test suite. The practical checks used in this repo are:

Syntax check:
```powershell
Set-Location "C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis"
python -m py_compile .\analyze_resegmentation.py .\streamlit_app.py
```

Load-data smoke test:
```powershell
Set-Location "C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis"
@'
import sys
sys.path.insert(0, r"C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis")
from analyze_resegmentation import load_data
df = load_data()
print(df.head(2).to_string())
print(df.columns.tolist())
'@ | python -
```

Dashboard HTTP smoke test after startup:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8501" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

## Lint / Build / Deploy Status

Lint:
- no linter config found
- no `ruff`, `flake8`, `black`, or `pylint` config found in repo

Build:
- no build step exists
- this is a script + dashboard repo, not a packaged application

Deploy:
- no deployment automation found
- current usage is local/manual Streamlit execution

## Logs / Generated Artifacts

Potentially stale local artifacts:
- `streamlit_stdout.log`
- `streamlit_stderr.log`
- `__pycache__\`
- `~$result.xlsx`

These are not required to migrate functionality.

## Environment Variables

No required environment variables were found in the repo.

## Unresolved Questions

- `requirements_streamlit.txt` is incomplete relative to actual imports. It does not list `pandas` or `numpy`.
- There is no pinned Python version file.
- There is no formal test suite, so migration verification is manual.
- `render_report()` still exists although the `Отчет` page was removed from navigation.
- Some Russian strings inside source files still appear mojibake in raw console output, though the app itself has been functioning. A future cleanup pass may still be useful.
