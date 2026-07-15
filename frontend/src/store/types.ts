export type ViewMode = 'flow' | 'svg' | 'json' | 'image';

export interface ActiveOverlays {
  currentFlow: boolean;
  nodeVoltages: boolean;
  kvlLoops: boolean;
  kclNodes: boolean;
  equations: boolean;
}

export interface HighlightedElement {
  type: 'component' | 'node' | 'loop' | 'branch' | 'path';
  id: string;
}

export type PipelineStage = 'idle' | 'uploading' | 'detecting' | 'reconstructing' | 'validating' | 'simulating' | 'visualization' | 'error';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  quiz?: any;
}

export interface UIStore {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  activeOverlays: ActiveOverlays;
  toggleOverlay: (overlay: keyof ActiveOverlays) => void;
  setAllOverlays: (overlays: ActiveOverlays) => void;
  activeLoopId: string | null;
  setActiveLoopId: (id: string | null) => void;
  activeNodeId: string | null;
  setActiveNodeId: (id: string | null) => void;
  hoveredElementId: string | null;
  setHoveredElementId: (id: string | null) => void;
  pipelineStage: PipelineStage;
  setPipelineStage: (stage: PipelineStage) => void;
  selectedComponentId: string | null;
  setSelectedComponentId: (id: string | null) => void;
  highlightedElements: HighlightedElement[];
  setHighlightedElements: (elements: HighlightedElement[]) => void;
}

export interface CircuitDataStore {
  circuitJson: any | null;
  setCircuitJson: (json: any) => void;
  analysisData: any | null;
  setAnalysisData: (data: any) => void;
  svgContent: string | null;
  setSvgContent: (svg: string | null) => void;
  uploadedImage: string | null;
  setUploadedImage: (img: string | null) => void;
  simulationData: any | null;
  setSimulationData: (data: any) => void;
  isSimulating: boolean;
  setIsSimulating: (isSimulating: boolean) => void;
  updateComponentValue: (compId: string, newValue: string) => void;
  suggestedRepairs: any[];
  setSuggestedRepairs: (repairs: any[]) => void;
  applyRepair: (repairId: string) => void;
  validationReport: any | null;
  setValidationReport: (report: any | null) => void;
  // Wire management
  addWireBetween: (sourceCompId: string, targetCompId: string, sourceHandle?: string, targetHandle?: string) => void;
  removeWireBetween: (sourceCompId: string, targetCompId: string, sourceHandle?: string, targetHandle?: string) => void;
  circuitHistory: any[];
  undo: () => void;
  resetCircuit: () => void;
}

export interface TutorStore {
  chatHistory: ChatMessage[];
  addChatMessage: (msg: ChatMessage) => void;
  clearChat: () => void;
  isTutorTyping: boolean;
  setIsTutorTyping: (typing: boolean) => void;
  learningMode: boolean;
  setLearningMode: (mode: boolean) => void;
  suggestedQuestions: string[];
  setSuggestedQuestions: (qs: string[]) => void;
  componentMetadata: Record<string, any>;
  setComponentMetadata: (id: string, metadata: any) => void;
}

export interface GlobalStore {
  clearAll: () => void;
}

export type StoreState = UIStore & CircuitDataStore & TutorStore & GlobalStore;
