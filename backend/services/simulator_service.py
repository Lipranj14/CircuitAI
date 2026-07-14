"""
circuit_vision/simulator.py — SPICE Simulation Engine

Converts a CircuitGraph into a PySpice netlist and runs DC, AC,
and Transient analyses to compute electrical properties.
"""

import logging
import re
import math
from typing import Optional

import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

from schemas.domain import CircuitGraph, CircuitNode, DetectedComponent, SimulationRequest, SimulationResponse

# Setup standard logger for our app
app_logger = logging.getLogger(__name__)

def _configure_windows_ngspice():
    """Configures Ngspice environment variables to handle paths with spaces on Windows."""
    import os
    import pathlib
    import PySpice
    
    if os.name != 'nt':
        return
        
    try:
        pyspice_dir = pathlib.Path(PySpice.__file__).parent
        spice64_dir = pyspice_dir / "Spice" / "NgSpice" / "Spice64_dll"
        cm_dir = spice64_dir / "lib" / "ngspice"
        
        # 1. Verify DLLs exist
        dll_vs = spice64_dir / "dll-vs" / "ngspice.dll"
        dll_mingw = spice64_dir / "dll-mingw" / "libngspice-0.dll"
        
        if not dll_vs.exists() and not dll_mingw.exists():
            msg = f"ngspice DLL not found at {dll_vs} or {dll_mingw}. Please install ngspice or reinstall PySpice."
            app_logger.error(msg)
            print(msg)
            
        # 2. Verify .cm libraries exist
        if cm_dir.exists():
            required_cms = ['analog.cm', 'digital.cm', 'spice2poly.cm', 'xtradev.cm']
            for cm in required_cms:
                cm_path = cm_dir / cm
                if not cm_path.exists():
                    msg = f"Ngspice code model couldn't be loaded: {cm_path} does not exist."
                    app_logger.error(msg)
                    print(msg)
                    
            # 3. Quote paths correctly to handle spaces in project directory
            os.environ['SPICE_LIB_DIR'] = str(spice64_dir / "share" / "ngspice")
            os.environ['SPICE_SCRIPTS'] = str(spice64_dir / "share" / "ngspice" / "scripts")
            os.environ['NGSPICE_LIBRARY_PATH'] = str(dll_vs)
        else:
            msg = f"Ngspice lib directory not found: {cm_dir}"
            app_logger.error(msg)
            print(msg)
    except Exception as e:
        app_logger.error(f"Failed to configure Windows Ngspice path: {e}")

# Apply Windows path fix before any simulations run
_configure_windows_ngspice()

class CircuitValidationError(Exception):
    """Exception raised for electrical topology errors in the circuit."""
    def __init__(self, message: str, highlight_ids: list[str]):
        super().__init__(message)
        self.highlight_ids = highlight_ids

class NgSpiceSimulationError(Exception):
    """Exception raised for specific Ngspice simulation crashes."""
    def __init__(self, error: str, component: str, fix: str):
        super().__init__(error)
        self.error = error
        self.component = component
        self.fix = fix

import io
import contextlib
from PySpice.Spice.NgSpice.Shared import NgSpiceCommandError

@contextlib.contextmanager
def capture_ngspice_logs():
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    ngspice_logger = logging.getLogger('PySpice.Spice.NgSpice.Shared')
    pyspice_logger = logging.getLogger('PySpice')
    
    ngspice_logger.addHandler(handler)
    pyspice_logger.addHandler(handler)
    try:
        yield log_stream
    except NgSpiceCommandError as e:
        logs = log_stream.getvalue()
        
        error = "Solver convergence"
        component = "Circuit"
        fix = "Check for reasonable component values or simplify the circuit."
        
        m_short = re.search(r'singular matrix:\s*check nodes (v\w+)#branch', logs, re.IGNORECASE)
        if m_short:
            error = "Short circuit"
            component = m_short.group(1).upper()
            fix = f"Ensure voltage source {component} is not directly shorted to itself or another ideal voltage source."
            raise NgSpiceSimulationError(error, component, fix)
            
        m_float = re.search(r'singular matrix:\s*check nodes (\w+)', logs, re.IGNORECASE)
        if m_float:
            error = "Floating node"
            component = m_float.group(1).upper()
            fix = f"Node '{component}' might be floating. Ensure a complete path to Ground."
            raise NgSpiceSimulationError(error, component, fix)
            
        if "unable to find definition of model" in logs.lower():
            error = "Missing model"
            fix = "A component requires a SPICE model that is not loaded."
            raise NgSpiceSimulationError(error, component, fix)
            
        if "parameter value out of range" in logs.lower() or "unrecognized parameter" in logs.lower():
            error = "Invalid component parameter"
            fix = "Check component values for invalid syntax or extreme ranges."
            raise NgSpiceSimulationError(error, component, fix)
            
        if "no ground node" in logs.lower():
            error = "Missing ground"
            fix = "Circuit requires a Ground reference node (GND or 0)."
            raise NgSpiceSimulationError(error, component, fix)
            
        raise NgSpiceSimulationError(error, component, fix)
    finally:
        ngspice_logger.removeHandler(handler)
        pyspice_logger.removeHandler(handler)



def parse_value(value_str: str, default: float = 1.0) -> float:
    """
    Parse a component value string (e.g., '10k', '4.7uF', '9V') into a float.
    """
    if not value_str:
        return default
    
    value_str = value_str.strip()
    # Match number followed by optional multiplier and units
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


class ComponentBuilderRegistry:
    """Deterministic registry for mapping component types to PySpice netlist builders."""
    
    def __init__(self):
        self._builders = {}
        
    def register(self, comp_type: str, builder_func: callable):
        self._builders[comp_type] = builder_func
        
    def build_component(self, comp_type: str, circuit: Circuit, comp, node1: str, node2: str, val_str: str) -> bool:
        builder = self._builders.get(comp_type)
        if builder:
            builder(circuit, comp, node1, node2, val_str)
            return True
        return False

registry = ComponentBuilderRegistry()

def build_resistor(circuit, comp, node1, node2, val_str):
    val = parse_value(val_str, default=1000.0)
    circuit.R(comp.id, node1, node2, val@u_Ohm)

def build_voltage_source(circuit, comp, node1, node2, val_str):
    val = parse_value(val_str, default=9.0)
    circuit.V(comp.id, node1, node2, val@u_V)

def build_capacitor(circuit, comp, node1, node2, val_str):
    val = parse_value(val_str, default=1e-6)
    circuit.C(comp.id, node1, node2, val@u_F)

def build_inductor(circuit, comp, node1, node2, val_str):
    val = parse_value(val_str, default=1e-3)
    circuit.L(comp.id, node1, node2, val@u_H)

def build_diode(circuit, comp, node1, node2, val_str):
    # Register the model only once if it doesn't exist
    if 'MyDiode' not in circuit.models:
        circuit.model('MyDiode', 'D', IS=1e-14, N=1.5)
    circuit.D(comp.id, node1, node2, model='MyDiode')

def build_switch(circuit, comp, node1, node2, val_str):
    # Model closed switch as 1mOhm
    circuit.R(comp.id, node1, node2, 1e-3@u_Ohm)

registry.register('resistor', build_resistor)
registry.register('battery', build_voltage_source)
registry.register('voltage_source', build_voltage_source)
registry.register('capacitor', build_capacitor)
registry.register('inductor', build_inductor)
registry.register('led', build_diode)
registry.register('diode', build_diode)
registry.register('switch', build_switch)



class NetlistBuilder:
    """Converts a CircuitGraph into a PySpice Circuit."""
    
    def __init__(self, graph: CircuitGraph):
        self.graph = graph
        self.circuit = Circuit('AI Circuit Simulation')
        self.spice_nodes: dict[str, str] = {}  # Maps logical node ID to SPICE node name
        self.node_connections: dict[str, list[str]] = {} # Maps SPICE node to connected pins
        
    def build(self) -> Circuit:
        """Construct the PySpice netlist."""
        self._validate_circuit()
        self._map_nodes()
        self._add_components()
        return self.circuit

    def _validate_circuit(self):
        """Validate circuit topology before attempting simulation."""
        nodes = self.graph.nodes
        comps = self.graph.components
        
        if not comps:
            raise CircuitValidationError("Circuit graph has no components.", [])
            
        if not nodes:
            raise CircuitValidationError("Circuit graph has no wires or nodes connected.", [])
            
        # 1. Build bipartite graph
        adj_comp = {c.id: set() for c in comps}
        adj_node = {n.id: set() for n in nodes}
        
        # Check unique IDs and build ground/power sets
        comp_ids = set()
        ground_comp_ids = set()
        ground_node_ids = set()
        has_power = False
        
        for comp in comps:
            if comp.id in comp_ids:
                raise CircuitValidationError(f"Duplicate component ID found: {comp.id}", [comp.id])
            comp_ids.add(comp.id)
            
            ctype = comp.type.lower()
            if ctype in ['ground']:
                ground_comp_ids.add(comp.id)
            if ctype in ['battery', 'voltage_source', 'current_source']:
                has_power = True

        for node in nodes:
            if node.label and node.label.upper() in ['GND', 'GROUND']:
                ground_node_ids.add(node.id)
            for pin_ref in node.connected_pins:
                comp_id = pin_ref.split('.')[0]
                if comp_id in adj_comp:
                    adj_comp[comp_id].add(node.id)
                    adj_node[node.id].add(comp_id)

        # 2. Check for Ground and Power Source
        for g_comp in ground_comp_ids:
            ground_node_ids.update(adj_comp[g_comp])

        if not ground_node_ids and not ground_comp_ids:
            raise CircuitValidationError("No Ground node detected. Please connect a Ground component.", [])
            
        if not has_power:
            raise CircuitValidationError("Missing Power Source. Please connect a Battery or Voltage Source.", [])

        # 3. Detect floating components (degree < 2)
        for comp in comps:
            ctype = comp.type.lower()
            if ctype in ['ground', 'terminal', 'junction']:
                continue
            if len(adj_comp[comp.id]) < 2:
                raise CircuitValidationError(
                    f"Component {comp.label or comp.id} is floating (needs at least 2 connections).",
                    [comp.id]
                )

        # 4. Detect floating nodes (degree < 2)
        for node in nodes:
            connected_comps = adj_node[node.id]
            if len(connected_comps) == 1:
                comp_id = list(connected_comps)[0]
                comp = next((c for c in comps if c.id == comp_id), None)
                comp_name = comp.label or comp.id if comp else comp_id
                app_logger.warning(f"Component {comp_name} has an unconnected wire or terminal. Proceeding anyway.")
            elif len(connected_comps) == 0:
                raise CircuitValidationError(
                    "Found an isolated piece of wire. Please remove it or connect it to the circuit.",
                    []
                )

        # 5. Detect disconnected subgraphs (BFS from Ground)
        start_node = list(ground_node_ids)[0] if ground_node_ids else list(adj_comp[list(ground_comp_ids)[0]])[0]
        visited_nodes = set([start_node])
        visited_comps = set()
        
        queue = [start_node]
        while queue:
            curr_node = queue.pop(0)
            for comp_id in adj_node[curr_node]:
                if comp_id not in visited_comps:
                    visited_comps.add(comp_id)
                    for next_node in adj_comp[comp_id]:
                        if next_node not in visited_nodes:
                            visited_nodes.add(next_node)
                            queue.append(next_node)
                            
        # Check if any component is unvisited
        for comp in comps:
            if comp.id not in visited_comps:
                raise CircuitValidationError(
                    f"Component {comp.label or comp.id} is not connected to the main circuit (disconnected subgraph).",
                    [comp.id]
                )

    def _map_nodes(self):
        """Map CircuitNode IDs to SPICE node names. GND must be '0'."""
        has_ground = False
        
        # Identify ground nodes
        for node in self.graph.nodes:
            if node.label and node.label.upper() in ['GND', 'GROUND']:
                self.spice_nodes[node.id] = '0'
                has_ground = True
            else:
                # Check if any pin in this node belongs to a ground component
                for pin_ref in node.connected_pins:
                    comp_id = pin_ref.split('.')[0]
                    comp = next((c for c in self.graph.components if c.id == comp_id), None)
                    if comp and comp.type == 'ground':
                        self.spice_nodes[node.id] = '0'
                        has_ground = True
                        break

        # If no explicit ground, pick the first node connected to a battery's pin2 (negative terminal)
        if not has_ground and self.graph.nodes:
            batteries = self.graph.get_components_by_type('battery')
            if batteries:
                batt = batteries[0]
                neg_pin_ref = f"{batt.id}.pin2"
                for node in self.graph.nodes:
                    if neg_pin_ref in node.connected_pins:
                        self.spice_nodes[node.id] = '0'
                        has_ground = True
                        break
            
            # Absolute fallback: ground the very first node
            if not has_ground:
                self.spice_nodes[self.graph.nodes[0].id] = '0'

        # Map remaining nodes
        node_counter = 1
        for node in self.graph.nodes:
            if node.id not in self.spice_nodes:
                self.spice_nodes[node.id] = f"N{node_counter}"
                node_counter += 1
                
            # Build node_connections map for debugging/UI
            sp_name = self.spice_nodes[node.id]
            if sp_name not in self.node_connections:
                self.node_connections[sp_name] = []
            for pin_ref in node.connected_pins:
                self.node_connections[sp_name].append(pin_ref)

    def _get_spice_node(self, comp_id: str, pin_name: str) -> Optional[str]:
        """Find the SPICE node for a specific component pin."""
        pin_ref = f"{comp_id}.{pin_name}"
        # Fallback for implicit pin names
        alt_pin_ref = f"{comp_id}.pin{1 if '1' in pin_name else 2}"
        
        for node in self.graph.nodes:
            if pin_ref in node.connected_pins or alt_pin_ref in node.connected_pins:
                return self.spice_nodes[node.id]
        
        # If pin isn't connected anywhere, return None (floating)
        return None

    def _add_components(self):
        """Iterate through detected components and add them to the SPICE circuit."""
        added_count = 0
        
        for i, comp in enumerate(self.graph.components):
            comp_type = comp.type.lower()
            if comp_type in ['ground', 'terminal', 'junction']:
                continue
                
            # Determine SPICE nodes for pins
            # Assuming standard 2-pin components for now (pin1=pos, pin2=neg)
            pins = comp.pins
            if len(pins) < 2:
                # If pins weren't explicitly generated, assume pin1 and pin2
                node1 = self._get_spice_node(comp.id, 'pin1')
                node2 = self._get_spice_node(comp.id, 'pin2')
            else:
                node1 = self._get_spice_node(comp.id, pins[0].name)
                node2 = self._get_spice_node(comp.id, pins[1].name)
                
            if not node1 or not node2 or node1 == node2:
                # Skip disconnected or shorted components
                continue

            val_str = comp.value or comp.label or ''
            
            if registry.build_component(comp_type, self.circuit, comp, node1, node2, val_str):
                added_count += 1

        if added_count == 0:
            raise ValueError("No valid fully-connected components found. Ensure components are wired together.")


class CircuitSimulator:
    """Runs PySpice simulations on a built netlist."""
    
    def __init__(self, request: SimulationRequest):
        self.request = request
        self.builder = NetlistBuilder(request.circuit)
        
        try:
            self.circuit = self.builder.build()
            self.simulator = self.circuit.simulator(temperature=25, nominal_temperature=25)
        except Exception as e:
            err_str = str(e)
            if "couldn't be loaded" in err_str or "Library" in err_str:
                raise RuntimeError(
                    f"ngspice failed to load a library. "
                    f"Please verify ngspice is installed correctly. Error: {e}"
                )
            elif "ngspice" in err_str.lower() or "shared" in err_str.lower():
                raise RuntimeError(
                    f"ngspice initialization failed. Ensure ngspice is installed. Error: {e}"
                )
            raise e
        
    def run(self) -> SimulationResponse:
        """Execute the requested analysis type."""
        atype = self.request.analysis_type.lower()
        
        try:
            with capture_ngspice_logs():
                if atype == 'dc':
                    return self._run_dc()
                elif atype == 'transient':
                    return self._run_transient()
                elif atype == 'ac':
                    return self._run_ac()
                else:
                    raise ValueError(f"Unknown analysis type: {atype}")
        except NgSpiceSimulationError:
            raise
        except Exception as e:
            app_logger.error(f"Simulation failed: {e}", exc_info=True)
            return SimulationResponse(
                status="error",
                analysis_type=atype,
                error_message=str(e)
            )

    def _run_dc(self) -> SimulationResponse:
        """Operating Point Analysis (Steady State)."""
        analysis = self.simulator.operating_point()
        
        def safe_float(v):
            try:
                return float(v[0])
            except Exception:
                try:
                    return float(v)
                except Exception:
                    return 0.0
        
        nodes = {}
        for node in analysis.nodes.values():
            name = str(node.name)
            if name != '0':
                nodes[name] = [safe_float(node)]
                
        branch_currents = {}
        for branch in analysis.branches.values():
            name = str(branch.name)
            branch_currents[name] = [safe_float(branch)]
            
        return SimulationResponse(
            analysis_type="dc",
            time=[0.0],
            nodes=nodes,
            branch_currents=branch_currents,
            node_connections=self.builder.node_connections
        )

    def _run_transient(self) -> SimulationResponse:
        """Transient Analysis (Time Domain)."""
        step = self.request.time_step
        end = self.request.end_time
        
        analysis = self.simulator.transient(step_time=step, end_time=end)
        
        time_points = [float(t) for t in analysis.time]
        
        nodes = {}
        for node in analysis.nodes.values():
            name = str(node.name)
            if name != '0':
                nodes[name] = [float(v) for v in node.as_ndarray()]
                
        branch_currents = {}
        for branch in analysis.branches.values():
            name = str(branch.name)
            branch_currents[name] = [float(i) for i in branch.as_ndarray()]
            
        return SimulationResponse(
            analysis_type="transient",
            time=time_points,
            nodes=nodes,
            branch_currents=branch_currents,
            node_connections=self.builder.node_connections
        )

    def _run_ac(self) -> SimulationResponse:
        """AC Sweep Analysis (Frequency Domain)."""
        analysis = self.simulator.ac(
            start_frequency=self.request.start_freq@u_Hz,
            stop_frequency=self.request.stop_freq@u_Hz,
            number_of_points=self.request.points_per_decade,
            variation='dec'
        )
        
        freq_points = [float(f) for f in analysis.frequency]
        
        nodes = {}
        for node in analysis.nodes.values():
            name = str(node.name)
            if name != '0':
                # Convert complex numbers to magnitude (absolute value)
                nodes[name] = [float(abs(v)) for v in node.as_ndarray()]
                
        branch_currents = {}
        for branch in analysis.branches.values():
            name = str(branch.name)
            branch_currents[name] = [float(abs(i)) for i in branch.as_ndarray()]
            
        return SimulationResponse(
            analysis_type="ac",
            frequency=freq_points,
            nodes=nodes,
            branch_currents=branch_currents,
            node_connections=self.builder.node_connections
        )
