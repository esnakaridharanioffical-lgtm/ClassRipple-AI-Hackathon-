import pandas as pd
from .data_loader import find_column

def data_quality_report(tables):
    rows = []
    for name, df in tables.items():
        rows.append({
            "Table": name,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Missing cells": int(df.isna().sum().sum()),
            "Duplicate rows": int(df.duplicated().sum()),
        })
    return pd.DataFrame(rows)

def find_service_column(tables):
    services = tables.get("services", pd.DataFrame())
    if services.empty:
        return None
    return find_column(services, ["service_id", "id", "service"])

def service_lookup(tables):
    services = tables.get("services", pd.DataFrame())
    col = find_service_column(tables)
    if col is None:
        return set()
    return set(services[col].dropna().astype(str).str.strip())

def validate_initial_services(initial_services, tables):
    known = service_lookup(tables)
    return [{
        "Service ID": str(s),
        "Validation": "Found in services.csv" if str(s) in known else "Not matched in services.csv — inspect incident/schema",
    } for s in initial_services]
