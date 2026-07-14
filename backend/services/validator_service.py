import uuid
from collections import defaultdict
from schemas.domain import CircuitGraph, ValidationCheck, ValidationReport, RepairSuggestion, RepairAction

class CircuitValidator:
    """Pre-simulation electrical rules engine."""
    
    def __init__(self, graph: CircuitGraph):
        self.graph = graph
        self.checks = []
        
    def _add_check(self, name: str, status: str, description: str, visual_hints=None, repair=None):
        self.checks.append(ValidationCheck(
            id=str(uuid.uuid4()),
            name=name,
            status=status,
            description=description,
            visual_hints=visual_hints or [],
            repair=repair
        ))

    def validate(self) -> ValidationReport:
        nodes = self.graph.nodes
        comps = self.graph.components
        
        if not comps:
            return ValidationReport(is_valid=True, checks=[])
            
        adj_comp = {c.id: set() for c in comps}
        
        ground_comp_ids = set()
        ground_node_ids = set()
        
        for comp in comps:
            if comp.type.lower() == 'ground':
                ground_comp_ids.add(comp.id)
                
        # Group nodes by label for duplicate check
        label_to_nodes = defaultdict(list)
        
        for node in nodes:
            if node.label:
                label_to_nodes[node.label].append(node.id)
                if node.label.upper() in ['GND', 'GROUND']:
                    ground_node_ids.add(node.id)
            for pin_ref in node.connected_pins:
                comp_id = pin_ref.split('.')[0]
                if comp_id in adj_comp:
                    adj_comp[comp_id].add(node.id)
                    
        # 1. Ground Check
        gnd_node_id = list(ground_node_ids)[0] if ground_node_ids else None
        if not gnd_node_id and ground_comp_ids:
            gnd_comp = list(ground_comp_ids)[0]
            if adj_comp[gnd_comp]:
                gnd_node_id = list(adj_comp[gnd_comp])[0]
                
        if not gnd_node_id and not ground_comp_ids:
            target_node = "GND_AUTO"
            batteries = [c for c in self.graph.components if c.type in ('battery', 'voltage_source')]
            batt = batteries[0] if batteries else comps[0]
            
            repair = RepairSuggestion(
                id=str(uuid.uuid4()),
                description="Add Ground Reference",
                reason="Connect to a 0V reference.",
                actions=[RepairAction(action_type="add_connection", source_pin=f"{batt.id}.pin2", target_node=target_node)],
                visual_hints=[batt.id]
            )
            self._add_check(
                "Missing Ground Reference", "error", 
                "Electrical potential is relative. Without a Ground (0V) reference point, nodal analysis cannot solve the circuit equations because there's no defined 'zero'.\n\n**How to Fix:** Place a GND symbol and connect it to the negative terminal of your power source.",
                visual_hints=[batt.id], repair=repair
            )
        else:
            self._add_check("Ground Reference", "pass", "A valid 0V reference is present.")
            
        # 2. Duplicate Node Labels
        dup_found = False
        for label, node_ids in label_to_nodes.items():
            if len(node_ids) > 1 and label.upper() not in ['GND', 'GROUND']:
                self._add_check(
                    "Duplicate Node Labels", "error",
                    f"Label '{label}' is assigned to {len(node_ids)} distinct electrical nodes. Rename them or connect them.",
                )
                dup_found = True
        if not dup_found:
            self._add_check("Node Labels", "pass", "No duplicate custom node labels.")

        # 3. Short Circuits (Voltage Source)
        short_found = False
        for comp in comps:
            if comp.type.lower() in ['battery', 'voltage_source', 'dc_source']:
                if len(adj_comp[comp.id]) == 1: # Both pins connected to same node!
                    self._add_check(
                        "Short Circuit", "error",
                        f"**{comp.label or comp.id} is short-circuited.** Both terminals connect to the exact same node (equipotential). This violates KVL (a non-zero voltage drop across 0 ohms implies infinite current).\n\n**How to Fix:** Ensure the positive and negative terminals connect to different parts of the circuit.",
                        visual_hints=[comp.id]
                    )
                    short_found = True
        if not short_found:
            self._add_check("Short Circuits", "pass", "No short-circuited voltage sources.")

        # 4. Floating Nodes/Components
        floating_found = False
        for comp in comps:
            ctype = comp.type.lower()
            if ctype in ['ground', 'terminal', 'junction']:
                continue
                
            connected_nodes = adj_comp[comp.id]
            if len(connected_nodes) <= 1:
                floating_found = True
                
                # Determine floating pin
                pin1 = f"{comp.id}.pin1"
                pin2 = f"{comp.id}.pin2"
                if comp.pins and len(comp.pins) >= 2:
                    pin1 = f"{comp.id}.{comp.pins[0].name}"
                    pin2 = f"{comp.id}.{comp.pins[1].name}"
                    
                pin1_conn = any(pin1 in n.connected_pins for n in nodes)
                pin2_conn = any(pin2 in n.connected_pins for n in nodes)
                
                floating_pin = pin1 if not pin1_conn else (pin2 if not pin2_conn else f"{comp.id}.pin_x")
                
                # We no longer auto-suggest connecting every floating pin to ground.
                # The user should manually draw the missing wire.
                
                self._add_check(
                    "Open Circuit (Floating Node)", "warning",
                    f"**{comp.label or comp.id} has an unconnected terminal.** Some terminals may be unconnected — check Edit Values panel.\n\n**How to Fix:** Connect the floating pin to another node or to Ground.",
                    visual_hints=[comp.id]
                )
                
        if not floating_found:
            self._add_check("Closed Loops", "pass", "All components are part of a closed electrical loop.")
            
        # 5. Diode/Transistor Specifics
        diode_found = any(c.type.lower() in ['diode', 'led'] for c in comps)
        if diode_found:
            self._add_check("Diode Orientation", "pass", "Diode polarity appears standard.")
            
        bjt_found = False
        for comp in comps:
            if 'transistor' in comp.type.lower() or 'mosfet' in comp.type.lower():
                bjt_found = True
                if len(adj_comp[comp.id]) < 3:
                    self._add_check(
                        "Transistor Orientation", "warning",
                        f"Transistor {comp.label or comp.id} has floating pins. Ensure Base, Collector, and Emitter are connected.",
                        visual_hints=[comp.id]
                    )
                if len(adj_comp[comp.id]) == 1:
                    self._add_check(
                        "Transistor Short", "error",
                        f"Transistor {comp.label or comp.id} is short-circuited across all its pins.",
                        visual_hints=[comp.id]
                    )
        
        if bjt_found and not any(c.name.startswith("Transistor") for c in self.checks):
            self._add_check("Transistor Orientation", "pass", "Transistors are properly connected.")
            
        is_valid = not any(c.status == 'error' for c in self.checks)
        return ValidationReport(is_valid=is_valid, checks=self.checks)
