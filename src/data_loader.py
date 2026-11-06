from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

TABLES = [
    "activities", "activity_modes", "buildings", "constraints", "dependencies",
    "engineering_personnel", "facility_contacts", "parts", "room_availability",
    "room_features", "room_services", "rooms", "service_links",
    "service_repair_map", "services", "staff_assignments", "staff_directory",
    "staff_roles", "work_requests",
]

def load_dataset(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    tables, errors, warnings = {}, [], []
    for name in TABLES:
        path = data_dir / f"{name}.csv"
        if not path.exists():
            errors.append(f"Missing required file: {path.name}")
            continue
        try:
            tables[name] = pd.read_csv(path)
        except Exception as exc:
            errors.append(f"Could not read {path.name}: {exc}")
    incident_path = data_dir / "incident.json"
    incident = {}
    if incident_path.exists():
        try:
            incident = json.loads(incident_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Could not read incident.json: {exc}")
    else:
        errors.append("Missing required file: incident.json")

    for name, df in tables.items():
        if df.empty:
            warnings.append(f"{name}.csv has no rows")
        if df.columns.duplicated().any():
            errors.append(f"{name}.csv contains duplicate column names")

    return {"tables": tables, "incident": incident, "errors": errors, "warnings": warnings}

def find_column(df, candidates):
    """Return first matching column using case-insensitive normalized names."""
    normalized = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower().replace(" ", "_")
        if key in normalized:
            return normalized[key]
    return None
