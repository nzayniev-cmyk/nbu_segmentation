# Session Summary

Repo:
- `C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis`

Main files:
- `analyze_resegmentation.py`
- `streamlit_app.py`
- `df_all.csv`

Current app:
- local Streamlit dashboard for resegmentation analysis between `КОРП` and `МСБ`
- active pages: `Обзор`, `Гипотеза 1`, `Гипотеза 2`, `Гипотеза 3`, `Клиенты`
- `Отчет` removed from sidebar navigation

Current data contract:
- source CSV currently has `loan` and `debt`
- source CSV uses native statuses `entry`, `re_entry`, `exit_ahd`, `re_exit_ahd` plus `is_closed`
- dashboard/business wording:
  - `debt` => `Долг`
  - `loan` => `Сумма кредита`
- `loan_rest_bn` removed from UI

Compatibility:
- `analyze_resegmentation.py` maps old `overdue_debt_bn` to `debt` if needed
- `analyze_resegmentation.py` maps old `loan_amount_bn` to `loan` if needed
- segment labels and transfer labels are normalized to `КОРП`, `МСБ`, `КОРП->МСБ`, `МСБ->КОРП`

Important behavior:
- active client logic = positive `turnover_bn` in current or prior 2 months present in data
- Hypothesis 1:
  - credit class dynamics `t-5..t+5`
  - hover shows share + client count
  - yearly turnover boxplot excludes zeros and splits cohorts
  - debt boxplot excludes zeros and splits cohorts

Run:
```powershell
Set-Location "C:\Users\nzayniyev\Documents\Scripts\Segmentation data for analysis"
python -m streamlit run .\streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
```

Analysis:
```powershell
python .\analyze_resegmentation.py
```

Validation:
```powershell
python -m py_compile .\analyze_resegmentation.py .\streamlit_app.py
Invoke-WebRequest -Uri "http://127.0.0.1:8501" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

Known gaps:
- `requirements_streamlit.txt` does not list `pandas` or `numpy`
- no formal tests/lint/build/deploy
- `render_report()` still exists in code but is unused in navigation
