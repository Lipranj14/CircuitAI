import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
url = "/api/v1/pipeline/simulate"

# Build a simple RC circuit with a battery
# Node 1: Positive terminal of battery, and one side of Resistor
# Node 2: Other side of Resistor, and positive side of Capacitor
# Node GND (0): Negative terminal of battery, and negative side of Capacitor
circuit = {
    "components": [
        {
            "id": "V1",
            "type": "battery",
            "value": "5V",
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
        },
        {
            "id": "G1",
            "type": "ground",
            "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
            "pins": [{"name": "pin1", "x": 0, "y": 0}]
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
            "connected_pins": ["V1.pin2", "C1.pin2", "G1.pin1"],
            "label": "GND"
        }
    ],
    "labels": [],
    "image_width": 0,
    "image_height": 0
}


def test_dc():
    print("--- Running DC Analysis ---")
    payload = {
        "circuit": circuit,
        "analysis_type": "dc"
    }
    resp = client.post(url, json=payload)
    if resp.status_code == 200:
        data = resp.json()["data"]
        print("Status:", data["status"])
        print("Nodes Voltages:", json.dumps(data["nodes"], indent=2))
        print("Branch Currents:", json.dumps(data["branch_currents"], indent=2))
    else:
        print("Failed:", resp.text)


def test_transient():
    print("\n--- Running Transient Analysis ---")
    payload = {
        "circuit": circuit,
        "analysis_type": "transient",
        "time_step": 1e-4,  # 0.1ms
        "end_time": 5e-3    # 5ms (5 RC time constants)
    }
    resp = client.post(url, json=payload)
    if resp.status_code == 200:
        data = resp.json()["data"]
        print("Status:", data["status"])
        
        # We don't want to print the whole array, just check if it's there
        times = data["time"]
        nodes = data["nodes"]
        
        print(f"Time steps returned: {len(times)}")
        n2_key = 'n2' if 'n2' in nodes else 'N2'
        if n2_key in nodes:
            print(f"Final Voltage at {n2_key} (Capacitor): {nodes[n2_key][-1]:.3f} V")
            print(f"Initial Voltage at {n2_key} (Capacitor): {nodes[n2_key][0]:.3f} V")
        else:
            print(f"Available nodes: {list(nodes.keys())}")
    else:
        print("Failed:", resp.text)

if __name__ == "__main__":
    test_dc()
    test_transient()
