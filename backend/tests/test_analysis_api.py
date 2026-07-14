import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_analysis_endpoint():
    payload = {
        "components": [
            {
                "id": "V1",
                "type": "battery",
                "bbox": {"x": 0, "y": 0, "w": 1, "h": 1},
                "pins": [
                    {"name": "pin1", "x": 0, "y": 0, "connected_node": "N1"},
                    {"name": "pin2", "x": 0, "y": 0, "connected_node": "0"}
                ]
            },
            {
                "id": "R1",
                "type": "resistor",
                "bbox": {"x": 0, "y": 0, "w": 1, "h": 1},
                "pins": [
                    {"name": "pin1", "x": 0, "y": 0, "connected_node": "N1"},
                    {"name": "pin2", "x": 0, "y": 0, "connected_node": "0"}
                ]
            }
        ],
        "nodes": [
            {"id": "N1", "connected_pins": ["V1.pin1", "R1.pin1"]},
            {"id": "0", "connected_pins": ["V1.pin2", "R1.pin2"], "label": "GND"}
        ]
    }
    
    response = client.post("/api/v1/analysis", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert "data" in data
    
    knowledge = data["data"]
    
    # Topology
    assert len(knowledge["topology"]["nodes"]) == 2
    
    # Equations (KCL and KVL)
    # KCL at N1
    assert len(knowledge["equations"]) >= 1
