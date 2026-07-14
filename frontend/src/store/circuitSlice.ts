import type { StateCreator } from 'zustand';
import type { StoreState, CircuitDataStore } from './types';

export const createCircuitSlice: StateCreator<StoreState, [], [], CircuitDataStore> = (set) => ({
  circuitJson: null,
  setCircuitJson: (json) => set({ circuitJson: json }),
  
  analysisData: null,
  setAnalysisData: (data) => set({ analysisData: data }),
  
  svgContent: null,
  setSvgContent: (svg) => set({ svgContent: svg }),
  
  uploadedImage: null,
  setUploadedImage: (img) => set({ uploadedImage: img }),
  
  simulationData: null,
  setSimulationData: (data) => set({ simulationData: data }),
  
  isSimulating: false,
  setIsSimulating: (isSimulating) => set({ isSimulating }),
  
  updateComponentValue: (compId, newValue) => set((state) => {
    if (!state.circuitJson) return state;
    const newCircuit = { ...state.circuitJson };
    newCircuit.components = newCircuit.components.map((c: any) => {
      if (c.id === compId) {
        return { ...c, value: newValue };
      }
      return c;
    });
    return { circuitJson: newCircuit };
  }),
  
  suggestedRepairs: [],
  setSuggestedRepairs: (repairs) => set({ suggestedRepairs: repairs }),
  
  validationReport: null,
  setValidationReport: (report) => set({ validationReport: report }),
  
  applyRepair: (repairId) => set((state) => {
    if (!state.circuitJson) return state;
    
    // Search in suggestedRepairs first
    let repair = state.suggestedRepairs.find(r => r.id === repairId);
    
    // If not found, search inside validationReport.checks[].repair
    if (!repair && state.validationReport?.checks) {
      for (const check of state.validationReport.checks) {
        if (check.repair?.id === repairId) {
          repair = check.repair;
          break;
        }
      }
    }
    
    if (!repair) return state;
    
    const newCircuit = JSON.parse(JSON.stringify(state.circuitJson));
    
    repair.actions.forEach((action: any) => {
      if (action.action_type === 'add_connection') {
        const { source_pin, target_node } = action;
        
        let target = newCircuit.nodes.find((n: any) => n.id === target_node);
        if (!target) {
            target = {
                id: target_node,
                connected_pins: [],
                label: target_node === 'GND_AUTO' ? 'GND' : undefined
            };
            newCircuit.nodes.push(target);
        }
        
        newCircuit.nodes.forEach((n: any) => {
            n.connected_pins = n.connected_pins.filter((pin: string) => pin !== source_pin);
        });
        
        if (!target.connected_pins.includes(source_pin)) {
            target.connected_pins.push(source_pin);
        }
      }
    });
    
    return {
      circuitJson: newCircuit,
      suggestedRepairs: state.suggestedRepairs.filter(r => r.id !== repairId),
      highlightedElements: []
    };
  }),

  addWireBetween: (sourceCompId, targetCompId, _sourceHandle, _targetHandle) => set((state) => {
    if (!state.circuitJson) return state;
    const newCircuit = JSON.parse(JSON.stringify(state.circuitJson));
    
    const sourceComp = newCircuit.components.find((c: any) => c.id === sourceCompId);
    const targetComp = newCircuit.components.find((c: any) => c.id === targetCompId);
    if (!sourceComp || !targetComp) return state;

    // Check if these two components are already connected at ANY node
    const alreadyConnected = newCircuit.nodes.some((n: any) => {
      const hasSource = n.connected_pins.some((p: string) => p.startsWith(sourceCompId + '.'));
      const hasTarget = n.connected_pins.some((p: string) => p.startsWith(targetCompId + '.'));
      return hasSource && hasTarget;
    });
    if (alreadyConnected) return state;

    // Find pins that are NOT yet in any node — prefer free pins
    const allConnectedPins = new Set<string>();
    for (const n of newCircuit.nodes) {
      for (const p of n.connected_pins) allConnectedPins.add(p);
    }
    
    const sourcePins = (sourceComp.pins || []).map((p: any) => `${sourceCompId}.${p.name}`);
    const targetPins = (targetComp.pins || []).map((p: any) => `${targetCompId}.${p.name}`);
    
    const sourcePin = sourcePins.find((p: string) => !allConnectedPins.has(p)) || sourcePins[sourcePins.length - 1] || `${sourceCompId}.pin2`;
    const targetPin = targetPins.find((p: string) => !allConnectedPins.has(p)) || targetPins[0] || `${targetCompId}.pin1`;

    // Always create a NEW independent node — never merge into existing nodes
    const newNodeId = `N_user_${Date.now()}`;
    newCircuit.nodes.push({
      id: newNodeId,
      connected_pins: [sourcePin, targetPin],
      label: null
    });
    
    newCircuit.nodes = newCircuit.nodes.filter((n: any) => n.connected_pins.length > 0);
    return { circuitJson: newCircuit };
  }),

  removeWireBetween: (sourceCompId, targetCompId, _sourceHandle, _targetHandle) => set((state) => {
    if (!state.circuitJson) return state;
    const newCircuit = JSON.parse(JSON.stringify(state.circuitJson));
    
    for (const node of newCircuit.nodes) {
      const sourcePins = node.connected_pins.filter((p: string) => p.startsWith(sourceCompId + '.'));
      const targetPins = node.connected_pins.filter((p: string) => p.startsWith(targetCompId + '.'));
      
      if (sourcePins.length > 0 && targetPins.length > 0) {
        // Split: keep source pins in this node, move target pins to an isolated node
        node.connected_pins = node.connected_pins.filter((p: string) => !p.startsWith(targetCompId + '.'));
        
        const newNodeId = `N_split_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
        newCircuit.nodes.push({
          id: newNodeId,
          connected_pins: targetPins,
          label: null
        });
        break; // only split the first shared node
      }
    }
    
    newCircuit.nodes = newCircuit.nodes.filter((n: any) => n.connected_pins.length > 0);
    return { circuitJson: newCircuit };
  }),
});
