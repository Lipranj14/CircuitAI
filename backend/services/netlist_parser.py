from schemas.domain import DetectedComponent, BoundingBox, Pin

def parse_spice_netlist(netlist_text: str) -> dict:
    components = []
    nodes_dict = {}
    connections = []

    component_type_map = {
        'V': 'voltage_source',
        'R': 'resistor',
        'C': 'capacitor',
        'L': 'inductor',
        'D': 'diode',
        'Q': 'transistor_bjt',
        'M': 'transistor_mosfet',
        'U': 'op_amp',
        'I': 'current_source'
    }

    for line in netlist_text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('*') or line.startswith('.'):
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        comp_id = parts[0]           # V1, R1, D1
        node_a = parts[1]            # node1
        node_b = parts[2]            # node2 or GND
        value = parts[3] if len(parts) > 3 else ""

        # Infer type from first letter of component ID
        prefix = comp_id[0].upper()
        comp_type = component_type_map.get(prefix, 'unknown')

        components.append({
            "id": comp_id,
            "type": comp_type,
            "value": value
        })

        # Build nodes
        for node_id in [node_a, node_b]:
            if node_id not in nodes_dict:
                nodes_dict[node_id] = []
            nodes_dict[node_id].append(comp_id)

        # Build connections
        connections.append({"from": f"{comp_id}.pin1", "to": node_a})
        connections.append({"from": f"{comp_id}.pin2", "to": node_b})

        # Handle GND component explicitly
        if node_a == 'GND' or node_b == 'GND':
            if not any(c['id'] == 'GND' for c in components):
                components.append({
                    "id": "GND",
                    "type": "ground",
                    "value": ""
                })

    nodes = [
        {"id": node_id, "connected_components": comp_list}
        for node_id, comp_list in nodes_dict.items()
    ]

    return {
        "components": components,
        "nodes": nodes,
        "connections": connections
    }

class NetlistParserService:
    def __init__(self):
        pass

    async def parse_netlist(self, netlist_text: str) -> dict:
        parsed = parse_spice_netlist(netlist_text)

        # Use same layout logic as detector
        from circuit_vision.component_detector import ComponentDetector
        detector = ComponentDetector()
        
        translated_components = []
        positions = detector.connection_aware_layout(
            parsed.get("components", []),
            parsed.get("connections", [])
        )

        for comp in parsed.get("components", []):
            coords = {
                "x": positions.get(comp["id"], {}).get("x", 100),
                "y": positions.get(comp["id"], {}).get("y", 100),
                "width": 100,
                "height": 80
            }
            translated_components.append(DetectedComponent(
                id=comp["id"],
                type=comp["type"],
                value=comp.get("value", ""),
                bbox=BoundingBox(x=coords["x"], y=coords["y"], w=coords["width"], h=coords["height"]),
                pins=detector._generate_default_pins(comp["type"], BoundingBox(x=coords["x"], y=coords["y"], w=coords["width"], h=coords["height"])),
                confidence=1.0,
                source="netlist"
            ))

        pin_usage = {}
        translated_nodes = []
        for node in parsed.get("nodes", []):
            node_pins = []
            for comp_id in node.get("connected_components", []):
                pin = detector.assign_next_available_pin(comp_id, pin_usage)
                node_pins.append(f"{comp_id}.{pin}")
            translated_nodes.append({
                "id": node["id"],
                "pins": node_pins
            })

        return {
            "success": True,
            "components": translated_components,
            "nodes": translated_nodes,
            "connections": parsed.get("connections", [])
        }
