import re
import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

class UnionFind:
    def __init__(self):
        self.parent = {}
    
    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y

def parse_value(value_str, default=1.0):
    if not value_str:
        return default
    value_str = value_str.strip()
    # Match number followed by optional multiplier and units (e.g. 1k, 10uF, 9V, 220)
    match = re.match(r'^([\d\.]+)\s*([a-zA-ZΩμµ]*)$', value_str)
    if not match:
        match_num = re.search(r'[\d\.]+', value_str)
        if match_num:
            try:
                return float(match_num.group(0))
            except ValueError:
                return default
        return default
    
    try:
        val_num = float(match.group(1))
    except ValueError:
        return default
        
    suffix = match.group(2).lower()
    
    if 'p' in suffix:
        return val_num * 1e-12
    elif 'n' in suffix:
        return val_num * 1e-9
    elif 'u' in suffix or 'μ' in suffix or 'µ' in suffix:
        return val_num * 1e-6
    elif 'm' in suffix:
        if suffix.startswith('meg'):
            return val_num * 1e6
        return val_num * 1e-3
    elif 'k' in suffix:
        return val_num * 1e3
    elif 'g' in suffix:
        return val_num * 1e9
    elif 't' in suffix:
        return val_num * 1e12
        
    return val_num

def run_simulation(graph_data):
    """
    Converts React Flow nodes & edges into a PySpice Circuit using a DSU
    algorithm to group pins into SPICE nodes.
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    
    if not nodes:
        raise ValueError("Circuit must have at least one component.")
        
    circuit = Circuit('AI Sketch Circuit')
    uf = UnionFind()
    
    # 1. Map handles to pins and union connections
    # We define pin1 as Left/Top handles and pin2 as Right/Bottom handles.
    # Ground nodes have all their pins connected to reference 0.
    ground_ref = ('ground', 'gnd')
    
    for node in nodes:
        node_type = node.get('type', '').lower()
        if node_type == 'ground':
            uf.union((node['id'], 'pin1'), ground_ref)
            uf.union((node['id'], 'pin2'), ground_ref)
            
    # Count connections per pin to avoid floating nodes
    pin_connection_count = {}
    for node in nodes:
        pin_connection_count[(node['id'], 'pin1')] = 0
        pin_connection_count[(node['id'], 'pin2')] = 0

    for edge in edges:
        source_id = edge.get('source')
        target_id = edge.get('target')
        if not source_id or not target_id:
            continue
            
        src_handle = edge.get('sourceHandle') or 'pin2'
        src_pin = 'pin1' if 'pin1' in src_handle else 'pin2'
        
        tgt_handle = edge.get('targetHandle') or 'pin1'
        tgt_pin = 'pin1' if 'pin1' in tgt_handle else 'pin2'
        
        src_key = (source_id, src_pin)
        tgt_key = (target_id, tgt_pin)
        
        # Initialize in union-find if not present
        uf.union(src_key, tgt_key)
        
        if src_key in pin_connection_count:
            pin_connection_count[src_key] += 1
        if tgt_key in pin_connection_count:
            pin_connection_count[tgt_key] += 1

    # 2. Check for ground nodes, fallback to auto-ground if missing
    has_ground = any(node.get('type', '').lower() == 'ground' for node in nodes)
    if not has_ground:
        # Find first battery to ground its negative terminal (pin2)
        battery_nodes = [n for n in nodes if n.get('type', '').lower() == 'battery']
        if battery_nodes:
            uf.union((battery_nodes[0]['id'], 'pin2'), ground_ref)
        elif nodes:
            # Fallback to first non-ground node's pin2
            non_ground = [n for n in nodes if n.get('type', '').lower() != 'ground']
            if non_ground:
                uf.union((non_ground[0]['id'], 'pin2'), ground_ref)

    # 3. Create SPICE node names for each disjoint set
    root_to_spice_node = {}
    ground_root = uf.find(ground_ref)
    root_to_spice_node[ground_root] = '0'
    
    node_counter = 1
    for node in nodes:
        if node.get('type', '').lower() == 'ground':
            continue
        for pin in ['pin1', 'pin2']:
            pk = (node['id'], pin)
            root = uf.find(pk)
            if root not in root_to_spice_node:
                root_to_spice_node[root] = f"N{node_counter}"
                node_counter += 1

    # 4. Add components to the circuit
    added_components = 0
    for i, node in enumerate(nodes):
        node_id = node['id']
        node_type = node.get('type', '').lower()
        
        if node_type == 'ground':
            continue
            
        # Skip components that are not fully connected
        if pin_connection_count.get((node_id, 'pin1'), 0) == 0 or pin_connection_count.get((node_id, 'pin2'), 0) == 0:
            continue
            
        node1 = root_to_spice_node[uf.find((node_id, 'pin1'))]
        node2 = root_to_spice_node[uf.find((node_id, 'pin2'))]
        
        # Prevent short-circuited components
        if node1 == node2:
            continue
            
        label = node.get('data', {}).get('label', '')
        val_str = node.get('data', {}).get('value', '') or label
        
        if node_type == 'resistor':
            val = parse_value(val_str, default=1000.0)
            circuit.R(i, node1, node2, val@u_Ohm)
            added_components += 1
            
        elif node_type == 'battery':
            val = parse_value(val_str, default=9.0)
            circuit.V(i, node1, node2, val@u_V)
            added_components += 1
            
        elif node_type == 'capacitor':
            val = parse_value(val_str, default=1e-6)
            circuit.C(i, node1, node2, val@u_F)
            added_components += 1
            
        elif node_type == 'inductor':
            val = parse_value(val_str, default=1e-3)
            circuit.L(i, node1, node2, val@u_H)
            added_components += 1
            
        elif node_type == 'led':
            circuit.model('MyLED', 'D', IS=1e-14, N=1.5)
            circuit.D(i, node1, node2, model='MyLED')
            added_components += 1
            
        elif node_type == 'switch':
            state = node.get('data', {}).get('state', 'closed')
            # Model switch as a low or high resistor
            val = 1e-3 if state == 'closed' else 1e9
            circuit.R(i, node1, node2, val@u_Ohm)
            added_components += 1

    if added_components == 0:
        raise ValueError("No valid fully-connected components found to simulate. Please connect all component pins.")

    # 5. Run Operating Point or Transient Analysis
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    
    try:
        analysis = simulator.transient(step_time=1@u_us, end_time=1@u_ms)
        
        results = {
            "time": [float(t) for t in analysis.time],
            "nodes": {},
            "node_connections": {}
        }
        
        for name, node_voltages in analysis.nodes.items():
            if str(name) != '0':
                results["nodes"][str(name)] = [float(v) for v in node_voltages.as_ndarray()]
                
        # Generate pin connection description for each SPICE node
        connections = {}
        for node in nodes:
            if node.get('type', '').lower() == 'ground':
                continue
            for pin in ['pin1', 'pin2']:
                pk = (node['id'], pin)
                rt = uf.find(pk)
                sp_name = root_to_spice_node.get(rt)
                if sp_name and sp_name != '0':
                    if sp_name not in connections:
                        connections[sp_name] = []
                    lbl = node.get('data', {}).get('label') or f"{node_type.upper()} ({node_id})"
                    connections[sp_name].append(f"{lbl} ({'Pin 1' if pin == 'pin1' else 'Pin 2'})")
        results["node_connections"] = connections
        
        return {"status": "success", "data": results}
        
    except Exception as e:
        raise ValueError(f"SPICE Simulation failed: {str(e)}")
