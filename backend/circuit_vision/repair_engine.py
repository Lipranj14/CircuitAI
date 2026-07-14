import uuid
from schemas.domain import CircuitGraph, RepairSuggestion, RepairAction

class AutoRepairEngine:
    """Analyzes a CircuitGraph and generates suggested repairs for incomplete topologies."""
    
    def __init__(self, graph: CircuitGraph):
        self.graph = graph
        self.repairs = []
        
    def analyze(self) -> list[RepairSuggestion]:
        nodes = self.graph.nodes
        comps = self.graph.components
        
        if not comps:
            return []
            
        adj_comp = {c.id: set() for c in comps}
        adj_node = {n.id: set() for n in nodes}
        
        ground_comp_ids = set()
        ground_node_ids = set()
        
        # Build adjacency
        for comp in comps:
            if comp.type.lower() == 'ground':
                ground_comp_ids.add(comp.id)
                
        for node in nodes:
            if node.label and node.label.upper() in ['GND', 'GROUND']:
                ground_node_ids.add(node.id)
            for pin_ref in node.connected_pins:
                comp_id = pin_ref.split('.')[0]
                if comp_id in adj_comp:
                    adj_comp[comp_id].add(node.id)
                    adj_node[node.id].add(comp_id)
                    
        # Resolve Ground Node ID
        gnd_node_id = list(ground_node_ids)[0] if ground_node_ids else None
        if not gnd_node_id and ground_comp_ids:
            gnd_comp = list(ground_comp_ids)[0]
            if adj_comp[gnd_comp]:
                gnd_node_id = list(adj_comp[gnd_comp])[0]
                
        # 1. Missing Ground
        if not gnd_node_id and not ground_comp_ids:
            target_node = "GND_AUTO"
            batteries = self.graph.get_components_by_type('battery') or self.graph.get_components_by_type('voltage_source')
            if batteries:
                batt = batteries[0]
                source_pin = f"{batt.id}.pin2"
                self.repairs.append(RepairSuggestion(
                    id=str(uuid.uuid4()),
                    description=f"Connect {batt.label or batt.id} to Ground",
                    reason="SPICE simulations require a ground reference node (0V) to calculate voltages.",
                    actions=[RepairAction(action_type="add_connection", source_pin=source_pin, target_node=target_node)],
                    visual_hints=[batt.id]
                ))
            else:
                comp = comps[0]
                source_pin = f"{comp.id}.pin2"
                self.repairs.append(RepairSuggestion(
                    id=str(uuid.uuid4()),
                    description="Add Ground Reference",
                    reason="The circuit needs a ground node to serve as a 0V reference.",
                    actions=[RepairAction(action_type="add_connection", source_pin=source_pin, target_node=target_node)],
                    visual_hints=[comp.id]
                ))
            
            # If no ground exists, return immediately so they fix it first, before we try linking things to ground.
            return self.repairs

        # Floating components are now handled purely as validation errors 
        # (user should draw the missing wires manually) instead of automatically
        # tying everything to ground.

        return self.repairs
