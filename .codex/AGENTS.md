# Repo Guidance For Codex

## Scope
This repo is a local Python analysis + Streamlit dashboard. Treat it as a small script-first project, not a packaged Python app.

## Highest Priority Files
- `analyze_resegmentation.py`
- `streamlit_app.py`
- `df_all.csv`

## Local Working Rules
- Prefer changing business logic in `analyze_resegmentation.py` first if the dashboard depends on derived fields.
- Prefer changing presentation/layout in `streamlit_app.py`.
- Keep commands Windows/PowerShell friendly.
- Default dashboard port is `8501`.
- Keep Russian UI text unless the task explicitly asks otherwise.
- Preserve current business wording:
  - `debt` => `Долг`
  - `loan` => `Сумма кредита`
- Current source CSV format uses native statuses `entry`, `re_entry`, `exit_ahd`, `re_exit_ahd` plus `is_closed`.

## Validation Standard
Minimum before finishing a change:
```powershell
python -m py_compile .\analyze_resegmentation.py .\streamlit_app.py
```

If the change affects runtime behavior, also do:
```powershell
python .\analyze_resegmentation.py
python -m streamlit run .\streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
Invoke-WebRequest -Uri "http://127.0.0.1:8501" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

## Known Project Gaps
- no tests
- no lint config
- no build/deploy pipeline

Document any new assumptions directly in repo docs, not only in chat.
