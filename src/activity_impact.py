import pandas as pd
from .data_loader import find_column

def split_values(value):
    if pd.isna(value) or not str(value).strip():
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]

def parse_clock(value):
    """Convert HH:MM to minutes after midnight; return None if invalid."""
    try:
        hour, minute = str(value).strip()[:5].split(":")
        return int(hour) * 60 + int(minute)
    except (ValueError, TypeError, AttributeError):
        return None

def activity_impacts(tables, affected_service_ids, incident_time="10:00"):
    """
    Identify activities whose original room has an affected service that is
    required by normal room operation or by the activity's declared service types.

    This is a conservative impact screen, not a complete schedule feasibility solver.
    """
    activities = tables.get("activities", pd.DataFrame()).copy()
    room_services = tables.get("room_services", pd.DataFrame()).copy()
    services = tables.get("services", pd.DataFrame()).copy()
    rooms = tables.get("rooms", pd.DataFrame()).copy()

    required_activity_cols = {"activity_id", "activity_name", "original_room_id",
                              "original_start", "original_end", "required_service_types"}
    if activities.empty or not required_activity_cols.issubset(activities.columns):
        return pd.DataFrame(), ["activities.csv is missing required columns or has no rows."]
    if room_services.empty or not {"room_id", "service_id", "required_for_normal_operation", "service_type"}.issubset(room_services.columns):
        return pd.DataFrame(), ["room_services.csv is missing required columns or has no rows."]
    if services.empty or not {"service_id", "initial_state", "state_from"}.issubset(services.columns):
        return pd.DataFrame(), ["services.csv is missing required columns or has no rows."]

    affected = {str(x).strip() for x in affected_service_ids if str(x).strip()}
    incident_min = parse_clock(incident_time)
    if incident_min is None:
        return pd.DataFrame(), [f"Invalid incident time: {incident_time}"]

    # Normalize service state information. A state applies from state_from onwards.
    service_state = {}
    for _, row in services.iterrows():
        sid = str(row["service_id"]).strip()
        state_from = parse_clock(row["state_from"])
        state = str(row["initial_state"]).strip().lower()
        service_state[sid] = {"state": state, "state_from": state_from}

    # Use known room-service mappings; booleans in CSV may be parsed as bool or text.
    room_services["room_id"] = room_services["room_id"].astype(str).str.strip()
    room_services["service_id"] = room_services["service_id"].astype(str).str.strip()
    room_services["service_type_norm"] = room_services["service_type"].astype(str).str.strip().str.lower()
    room_services["required_norm"] = room_services["required_for_normal_operation"].astype(str).str.lower().isin(
        ["true", "1", "yes"]
    )

    room_name = {}
    if not rooms.empty and {"room_id", "room_name"}.issubset(rooms.columns):
        room_name = dict(zip(rooms["room_id"].astype(str), rooms["room_name"].astype(str)))

    results = []
    for _, activity in activities.iterrows():
        room_id = str(activity["original_room_id"]).strip()
        start = parse_clock(activity["original_start"])
        end = parse_clock(activity["original_end"])
        if start is None or end is None:
            continue
        # If the activity ends at/before the incident, this incident does not affect its original time slot.
        if end <= incident_min:
            continue

        activity_types = {x.lower() for x in split_values(activity["required_service_types"])}
        mappings = room_services[room_services["room_id"] == room_id]
        reasons = []
        implicated = []

        for _, mapping in mappings.iterrows():
            sid = str(mapping["service_id"]).strip()
            service_type = str(mapping["service_type_norm"]).strip()
            state_info = service_state.get(sid, {})
            state = state_info.get("state", "unknown")
            state_from = state_info.get("state_from")

            # A selected/downstream service is considered failed/degraded for this analysis.
            if sid not in affected:
                continue
            if state not in {"unavailable", "degraded", "failed", "down", "unknown"}:
                # A selected service may be an impact candidate even if its baseline state
                # is listed as available; don't silently classify it as failed.
                continue
            if state_from is not None and start < state_from and end <= state_from:
                continue

            room_requires = bool(mapping["required_norm"])
            activity_requires_type = service_type in activity_types
            if not (room_requires or activity_requires_type):
                continue

            why = []
            if room_requires:
                why.append("room marks this service as required for normal operation")
            if activity_requires_type:
                why.append(f"activity requires service type '{service_type}'")
            reasons.append(f"{sid} ({service_type}): " + " and ".join(why))
            implicated.append(sid)

        if reasons:
            results.append({
                "activity_id": str(activity["activity_id"]),
                "activity_name": str(activity["activity_name"]),
                "original_room_id": room_id,
                "room_name": room_name.get(room_id, room_id),
                "original_start": str(activity["original_start"]),
                "original_end": str(activity["original_end"]),
                "priority": str(activity.get("priority", "unknown")),
                "affected_services": ", ".join(sorted(set(implicated))),
                "impact_explanation": "; ".join(reasons),
                "status": "Potentially affected — requires recovery/constraint checks",
            })

    columns = ["activity_id", "activity_name", "original_room_id", "room_name",
               "original_start", "original_end", "priority", "affected_services",
               "impact_explanation", "status"]
    notes = [
        "Activities ending at or before the incident time are excluded.",
        "Only affected services required by room operation or activity service types are included.",
        "This screen does not yet validate alternate rooms, staff, mode-specific requirements, or repair restoration timelines."
    ]
    return pd.DataFrame(results, columns=columns), notes
