# Migration Checklist

## Goal
Move this repository to a new Windows machine and restore a working local Streamlit dashboard plus analysis workflow.

Repo root expected after copy:
- `C:\Users\<username>\Documents\Scripts\Segmentation data for analysis`

## 1. Copy Files

Copy the entire folder, especially:
- `df_all.csv`
- `analyze_resegmentation.py`
- `streamlit_app.py`
- `requirements_streamlit.txt`
- `project_notes.md`
- `resegmentation_analysis_report.md`
- `Segmentation.ipynb`

Optional to copy:
- `credits.xlsx`
- `result.xlsx`

Safe to ignore/regenerate:
- `__pycache__\`
- `streamlit_stdout.log`
- `streamlit_stderr.log`
- `~$result.xlsx`

## 2. Install Python

Verified working interpreter on old machine:
- Python `3.14.3`

Recommended:
- install a recent 64-bit Python on Windows

Verify:
```powershell
python --version
```

## 3. Create Virtual Environment

From repo root:
```powershell
Set-Location "C:\Users\<username>\Documents\Scripts\Segmentation data for analysis"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

## 4. Install Dependencies

Install using:
```powershell
pip install -r .\requirements_streamlit.txt
```

Optional check:
```powershell
pip list
```

## 5. Verify Input Data

Check that `df_all.csv` exists:
```powershell
Test-Path ".\df_all.csv"
```

Check columns:
```powershell
@'
import pandas as pd
df = pd.read_csv("df_all.csv", nrows=2)
print(df.columns.tolist())
'@ | python -
```

Current expected columns:
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

Backward compatibility currently supported:
- older `overdue_debt_bn` will be mapped to `debt`
- older `loan_amount_bn` will be mapped to `loan`
- segment labels and transfer labels are normalized to `КОРП`, `МСБ`, `КОРП->МСБ`, `МСБ->КОРП`

## 6. Syntax Check

```powershell
python -m py_compile .\analyze_resegmentation.py .\streamlit_app.py
```

If this fails, do not continue to run the dashboard until fixed.

## 7. Smoke Test Data Loading

```powershell
@'
import sys
sys.path.insert(0, r".")
from analyze_resegmentation import load_data
df = load_data()
print(df.head(2).to_string())
print(df.columns.tolist())
'@ | python -
```

Expected:
- no exception
- dataframe contains internal `debt`
- dataframe contains internal `loan`

## 8. Run Analysis Script

```powershell
python .\analyze_resegmentation.py
```

Expected output:
- writes or refreshes `resegmentation_analysis_report.md`

## 9. Run Streamlit Dashboard

Use the repo root:
```powershell
python -m streamlit run .\streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
```

Open locally:
- `http://127.0.0.1:8501`

Open from another machine on the same network:
- `http://<new-machine-ip>:8501`

To find the new machine IP:
```powershell
ipconfig
```

## 10. HTTP Check

In another PowerShell:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8501" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

Expected:
- `200`

## 11. Manual Functional Checks

Check these pages:
- `Обзор`
- `Гипотеза 1`
- `Гипотеза 2`
- `Гипотеза 3`
- `Клиенты`

Specifically verify:
- app loads without `KeyError` on missing columns
- charts render with Russian labels
- `debt` is shown as `Долг`
- `loan` is shown as `Сумма кредита`
- `loan_rest_bn` does not appear in UI
- Hypothesis 1 debt boxplot renders with split cohorts and no-zero logic

## 12. Common Failure Modes

### Missing Python packages
Symptom:
- `ModuleNotFoundError`

Fix:
```powershell
pip install pandas numpy streamlit plotly
```

### Streamlit not recognized
Fix:
```powershell
python -m streamlit run .\streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
```

### pandas import breaks because of NumPy alias compatibility
Status:
- repo already includes a NumPy alias shim in `analyze_resegmentation.py`

### Port 8501 already occupied
Find process:
```powershell
netstat -ano | Select-String ":8501"
```

Stop process:
```powershell
Stop-Process -Id <PID> -Force
```

Or run temporarily on another port:
```powershell
python -m streamlit run .\streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port 8502
```

## 13. Things Not Currently Defined

There is currently no:
- lint command
- unit/integration test command
- build command
- deploy command
- `.env` file
- CI pipeline

If migration is successful, consider adding:
- full `requirements.txt`
- a `README.md`
- a small smoke-test script
