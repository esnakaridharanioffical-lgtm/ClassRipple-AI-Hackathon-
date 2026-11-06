import pandas as pd
from src.activity_impact import activity_impacts

def test_activity_impact_requires_service_and_time_overlap():
    tables = {
        "activities": pd.DataFrame([
            {"activity_id":"A1","activity_name":"Exam","original_room_id":"R1","original_start":"10:00","original_end":"11:00","required_service_types":"power","priority":"critical"},
            {"activity_id":"A2","activity_name":"Morning meeting","original_room_id":"R1","original_start":"09:00","original_end":"09:45","required_service_types":"power","priority":"normal"},
        ]),
        "room_services": pd.DataFrame([
            {"room_id":"R1","service_id":"PWR-1","required_for_normal_operation":True,"service_type":"power","notes":""},
            {"room_id":"R1","service_id":"WAT-1","required_for_normal_operation":False,"service_type":"water","notes":""},
        ]),
        "services": pd.DataFrame([
            {"service_id":"PWR-1","initial_state":"unavailable","state_from":"10:00"},
            {"service_id":"WAT-1","initial_state":"available","state_from":"09:00"},
        ]),
        "rooms": pd.DataFrame([{"room_id":"R1","room_name":"Room 1"}])
    }
    result, _ = activity_impacts(tables, ["PWR-1"], "10:00")
    assert list(result["activity_id"]) == ["A1"]
