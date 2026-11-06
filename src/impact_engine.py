from collections import deque
import pandas as pd
from .data_loader import find_column

def _as_text(value):
    return "" if pd.isna(value) else str(value).strip()

def build_service_graph(tables):
    """
    Build a directed service graph from service_links.csv.
    Direction is interpreted as source -> dependent service when the column names
    support that interpretation. The UI reports the selected column mapping.
    """
    df = tables.get("service_links", pd.DataFrame())
    if df.empty:
        return {}, {"source": None, "target": None}
    source = find_column(df, ["source_service", "source_service_id", "upstream_service_id", "from_service_id", "source_id", "service_id"])
    target = find_column(df, ["target_service", "dependent_service_id", "downstream_service_id", "to_service_id", "target_service_id", "linked_service_id"])
    if source is None or target is None:
        # Do not guess an edge direction when schema is unknown.
        return {}, {"source": source, "target": target}
    graph = {}
    for _, row in df.iterrows():
        a, b = _as_text(row[source]), _as_text(row[target])
        if a and b:
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set())
    return graph, {"source": source, "target": target}

def trace_service_impacts(initial_services, graph, max_depth=8):
    """Breadth-first traversal; levels count edges from initial failed services."""
    results, visited = [], set()
    queue = deque((str(s), 0, str(s)) for s in initial_services if str(s).strip())
    for s in initial_services:
        visited.add(str(s))
    while queue:
        service, depth, root = queue.popleft()
        if depth >= max_depth:
            continue
        for dependent in sorted(graph.get(service, set())):
            if dependent in visited:
                continue
            visited.add(dependent)
            results.append({
                "root_service": root,
                "parent_service": service,
                "service_id": dependent,
                "impact_level": depth + 1,
                "cause": f"{dependent} depends on {service} according to service_links.csv",
                "status": "Derived — verify direction and service state",
            })
            queue.append((dependent, depth + 1, root))
    return pd.DataFrame(results, columns=[
        "root_service", "parent_service", "service_id", "impact_level", "cause", "status"
    ])

def incident_service_ids(incident):
    """Return explicitly listed affected service IDs; do not treat rule text as IDs."""
    if not isinstance(incident, dict):
        return []
    candidates = incident.get("affected_service_ids", [])
    if isinstance(candidates, list):
        return list(dict.fromkeys(
            str(value).strip() for value in candidates
            if isinstance(value, (str, int, float)) and str(value).strip()
        ))
    return []
