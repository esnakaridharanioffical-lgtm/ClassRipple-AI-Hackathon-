# ClassRipple AI — Fresh Hackathon Project

A clean, separate Streamlit project for **THE RIPPLE: Campus in Crisis**. This first version focuses on reliable data loading, dependency-based ripple tracing, impact explanations, and transparent validation. It uses the supplied dataset and works offline.

## 1. Setup (Windows / VS Code)

Open this folder in VS Code, then in its terminal run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502
```

If PowerShell blocks activation, run without activation:
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502
```

## 2. What's included

- The original dataset files in `data/`
- Data loader with schema checks
- Service-dependency graph and multi-level traversal
- Incident-aware impact explorer
- Cause-and-effect explanations
- Basic data-quality and feasibility checks
- Streamlit dashboard and test starter

## 3. Important limitation

This is an initial working MVP, not a certified campus scheduling optimizer. It traces impacts from relationships present in the supplied files and flags data uncertainty. It does **not** claim that a recovery timetable or repair allocation is feasible until a complete constraint solver and independent validator are implemented.

## 4. Folder layout

```text
ClassRippleAI_Fresh/
├── app.py
├── requirements.txt
├── README.md
├── data/                  # supplied dataset + docs
├── src/
│   ├── data_loader.py
│   ├── impact_engine.py
│   └── validation.py
└── tests/
    └── test_core.py
```
