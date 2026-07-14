import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
url = "/api/v1/tutor/chat"

# Simulated CircuitGraph
circuit = {
    "components": [
        {
            "id": "V1",
            "type": "battery",
            "value": "9V",
            "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
            "pins": [{"name": "pin1", "x": 0, "y": 0}, {"name": "pin2", "x": 0, "y": 0}]
        },
        {
            "id": "R1",
            "type": "resistor",
            "value": "1k",
            "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
            "pins": [{"name": "pin1", "x": 0, "y": 0}, {"name": "pin2", "x": 0, "y": 0}]
        },
        {
            "id": "C1",
            "type": "capacitor",
            "value": "1uF",
            "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
            "pins": [{"name": "pin1", "x": 0, "y": 0}, {"name": "pin2", "x": 0, "y": 0}]
        }
    ],
    "wires": [],
    "junctions": [],
    "nodes": [
        {
            "id": "N1",
            "connected_pins": ["V1.pin1", "R1.pin1"]
        },
        {
            "id": "N2",
            "connected_pins": ["R1.pin2", "C1.pin1"]
        },
        {
            "id": "GND",
            "connected_pins": ["V1.pin2", "C1.pin2"],
            "label": "GND"
        }
    ],
    "labels": [],
    "image_width": 0,
    "image_height": 0
}

# Simulated DC Analysis
simulation_data = {
    "status": "success",
    "analysis_type": "dc",
    "time": [0.0],
    "frequency": [],
    "nodes": {
        "N1": [9.0],
        "N2": [9.0]
    },
    "branch_currents": {
        "V1": [0.0]
    },
    "node_connections": {}
}


def test_tutor():
    print("--- Testing AI Circuit Tutor ---")
    payload = {
        "query": "Why is the voltage at node N2 9V, but the current is 0A?",
        "expertise_level": "intermediate",
        "chat_history": [],
        "circuit": circuit,
        "simulation_data": simulation_data
    }
    
    resp = client.post(url, json=payload)
    if resp.status_code == 200:
        data = resp.json()["data"]
        print("\n=== AI Tutor Response ===")
        print(data["message"])
        print("\n=== Highlights ===")
        print(data.get("highlight_components", []))
        
        if data.get("quiz"):
            print("\n=== Quiz ===")
            q = data["quiz"]
            print("Q:", q["question"])
            for i, opt in enumerate(q["options"]):
                prefix = "[*]" if i == q["correct_option_index"] else "[ ]"
                print(f"{prefix} {opt}")
            print("Explanation:", q["explanation"])
    else:
        print("Failed:", resp.text)


if __name__ == "__main__":
    test_tutor()
