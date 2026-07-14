import { create } from 'zustand';
import type { StoreState } from './types';
import { createUISlice } from './uiSlice';
import { createCircuitSlice } from './circuitSlice';
import { createTutorSlice } from './tutorSlice';

// Re-export types so existing imports don't break
export * from './types';

export const useStore = create<StoreState>()((...a) => ({
  ...createUISlice(...a),
  ...createCircuitSlice(...a),
  ...createTutorSlice(...a),
  
  clearAll: () => a[0]({
    circuitJson: null,
    analysisData: null,
    svgContent: null,
    uploadedImage: null,
    simulationData: null,
    chatHistory: [],
    highlightedElements: [],
    suggestedRepairs: [],
    suggestedQuestions: [],
    componentMetadata: {},
    validationReport: null,
    viewMode: 'flow',
    activeOverlays: {
      currentFlow: false,
      nodeVoltages: false,
      kvlLoops: false,
      kclNodes: false,
      equations: false
    },
    activeLoopId: null,
    activeNodeId: null,
    hoveredElementId: null,
    pipelineStage: 'idle',
    selectedComponentId: null
  })
}));
