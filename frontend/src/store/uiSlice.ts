import type { StateCreator } from 'zustand';
import type { StoreState, UIStore } from './types';

export const createUISlice: StateCreator<StoreState, [], [], UIStore> = (set) => ({
  viewMode: 'svg',
  setViewMode: (mode) => set({ viewMode: mode }),
  
  activeOverlays: {
    currentFlow: false,
    nodeVoltages: false,
    kvlLoops: false,
    kclNodes: false,
    equations: false
  },
  toggleOverlay: (overlay) => set((state) => ({ 
    activeOverlays: { ...state.activeOverlays, [overlay]: !state.activeOverlays[overlay] } 
  })),
  setAllOverlays: (overlays) => set({ activeOverlays: overlays }),
  
  activeLoopId: null,
  setActiveLoopId: (id) => set({ activeLoopId: id }),
  
  activeNodeId: null,
  setActiveNodeId: (id) => set({ activeNodeId: id }),
  
  hoveredElementId: null,
  setHoveredElementId: (id) => set({ hoveredElementId: id }),
  
  pipelineStage: 'idle',
  setPipelineStage: (stage) => set({ pipelineStage: stage }),
  
  selectedComponentId: null,
  setSelectedComponentId: (id) => set({ selectedComponentId: id }),
  
  highlightedElements: [],
  setHighlightedElements: (elements) => set({ highlightedElements: elements }),
});
