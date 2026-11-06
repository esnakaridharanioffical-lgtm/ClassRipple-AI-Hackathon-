from src.impact_engine import trace_service_impacts

def test_traces_two_downstream_levels():
    graph = {"A": {"B"}, "B": {"C"}, "C": set()}
    impacts = trace_service_impacts(["A"], graph, max_depth=3)
    assert set(impacts["service_id"]) == {"B", "C"}
    assert dict(zip(impacts["service_id"], impacts["impact_level"])) == {"B": 1, "C": 2}

def test_avoids_cycles():
    graph = {"A": {"B"}, "B": {"A", "C"}, "C": set()}
    impacts = trace_service_impacts(["A"], graph, max_depth=5)
    assert len(impacts) == 2


def test_dataset_service_link_schema_is_supported():
    from src.impact_engine import build_service_graph
    import pandas as pd
    tables = {"service_links": pd.DataFrame([
        {"source_service": "NET-CORE", "target_service": "NET-CAB"},
        {"source_service": "NET-CAB", "target_service": "NET-LAB"},
    ])}
    graph, mapping = build_service_graph(tables)
    impacts = trace_service_impacts(["NET-CORE"], graph, max_depth=3)
    assert mapping["source"] == "source_service"
    assert mapping["target"] == "target_service"
    assert list(impacts["service_id"]) == ["NET-CAB", "NET-LAB"]


def test_incident_ids_excludes_rule_descriptions():
    from src.impact_engine import incident_service_ids
    incident = {
        "affected_service_ids": ["PWR-CAB", "NET-CORE"],
        "rules": {"unknown_service_state": "unknown_not_usable_for_certified_plan"}
    }
    assert incident_service_ids(incident) == ["PWR-CAB", "NET-CORE"]
