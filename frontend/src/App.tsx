import React, { useRef, useCallback } from 'react';
import { Upload, Zap, Activity, Trash2, GraduationCap, ArrowRight, Calculator, Sparkles, RefreshCw, FileImage, X, AlertTriangle } from 'lucide-react';
import { useStore } from './store/useStore';
import { TutorChatPanel } from './components/TutorChatPanel';
import { SimulationControls } from './components/SimulationControls';
import { RepairPanel } from './components/RepairPanel';
import { apiClient } from './api';
import { CircuitViewer } from './components/CircuitViewer';
import { PipelineProgress } from './components/PipelineProgress';
import { PropertiesPanel } from './components/PropertiesPanel';
import { CircuitSummaryCard } from './components/CircuitSummaryCard';
import { EquationViewer } from './components/EquationViewer';
import { GuidedLearningWidget } from './components/GuidedLearningWidget';
import { layoutCircuit } from './utils/circuitLayout';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { applyNodeChanges } from 'reactflow';
import type { NodeChange } from 'reactflow';

function App() {
  const {
    viewMode, setViewMode,
    circuitJson, setCircuitJson,
    svgContent, setSvgContent,
    setUploadedImage,
    simulationData, setSimulationData,
    setSuggestedRepairs,
    setPipelineStage,
    selectedComponentId,
    setAnalysisData,
    clearAll
  } = useStore();

  const [isUploading, setIsUploading] = React.useState(false);
  const [isLayingOut, setIsLayingOut] = React.useState(false);
  const [dragActive, setDragActive] = React.useState(false);
  const [uploadedFileName, setUploadedFileName] = React.useState<string | null>(null);
  const [uploadError, setUploadError] = React.useState<{ message: string; hint: string } | null>(null);
  const [fallbackActive, setFallbackActive] = React.useState(false);
  const [uploadTab, setUploadTab] = React.useState<'image' | 'netlist'>('image');
  const [netlistInput, setNetlistInput] = React.useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const friendlyError = (err: any): { message: string; hint: string } => {
    const msg = err?.message || String(err);
    if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('fetch')) {
      return { message: 'Could not reach the analysis server.', hint: 'Make sure the backend is running on port 8001 and try again.' };
    }
    if (msg.includes('timeout') || msg.includes('Timeout')) {
      return { message: 'The analysis took too long.', hint: 'Try uploading a simpler or higher-contrast circuit image.' };
    }
    if (msg.includes('image') || msg.includes('Image')) {
      return { message: 'The image could not be processed.', hint: 'Use a clear PNG or JPG photo of a circuit schematic.' };
    }
    return { message: 'Something went wrong during analysis.', hint: msg };
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setUploadError(null);
    clearAll();
    setUploadedFileName(file.name);
    setPipelineStage('uploading');
    
    setTimeout(() => { if (useStore.getState().pipelineStage === 'uploading') setPipelineStage('detecting') }, 800);
    setTimeout(() => { if (useStore.getState().pipelineStage === 'detecting') setPipelineStage('reconstructing') }, 2000);
    
    const reader = new FileReader();
    reader.onload = (e) => setUploadedImage(e.target?.result as string);
    reader.readAsDataURL(file);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const data = await apiClient.analyzeCircuitV2(formData);

      // Capture fallback flag if present
      if (data.fallback) {
        setFallbackActive(true);
      } else {
        setFallbackActive(false);
      }

      if (data.status !== 'success') {
        throw new Error(data.error || 'Analysis did not return a valid circuit.');
      }

      setSvgContent(data.svg || null);
      if (data.circuit) setCircuitJson(data.circuit);
      if (data.analysis) {
        setAnalysisData({ ...data.analysis, overview: data.overview });
      }
      if (data.repairs) setSuggestedRepairs(data.repairs);
      setViewMode('flow');
      setPipelineStage('idle');
    } catch (error: any) {
      console.error(error);
      setUploadError(friendlyError(error));
      setPipelineStage('error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleNetlistSubmit = async () => {
    if (!netlistInput.trim()) return;
    setIsUploading(true);
    setUploadError(null);
    clearAll();
    setUploadedFileName('SPICE Netlist');
    setPipelineStage('detecting');
    
    setTimeout(() => { if (useStore.getState().pipelineStage === 'detecting') setPipelineStage('reconstructing') }, 800);

    try {
      const data = await apiClient.analyzeNetlist(netlistInput);

      if (data.fallback) {
        setFallbackActive(true);
      } else {
        setFallbackActive(false);
      }

      if (data.status !== 'success') {
        throw new Error(data.error || 'Analysis did not return a valid circuit.');
      }

      setSvgContent(data.svg || null);
      if (data.circuit) setCircuitJson(data.circuit);
      if (data.analysis) setAnalysisData(data.analysis);
      if (data.repairs) setSuggestedRepairs(data.repairs);
      setViewMode('flow');
      setPipelineStage('idle');
    } catch (error: any) {
      console.error(error);
      setUploadError(friendlyError(error));
      setPipelineStage('error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleReplace = () => {
    setUploadError(null);
    fileInputRef.current?.click();
  };

  const handleRemove = () => {
    setUploadError(null);
    setUploadedFileName(null);
    clearAll();
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
  };

  // --- Layout: place components at their actual image positions ---
  const [rfNodes, setRfNodes] = React.useState<any[]>([]);
  const lastComponentIds = React.useRef<string>('');

  React.useEffect(() => {
    if (!circuitJson?.components) {
      setRfNodes([]);
      lastComponentIds.current = '';
      return;
    }
    const comps = circuitJson.components as any[];
    
    // Only re-run full layout if the component list itself changed
    // (not when wires/nodes change due to user edits)
    const currentIds = comps.map((c: any) => c.id).sort().join(',');
    if (currentIds === lastComponentIds.current) {
      // Components haven't changed — just update data (values, labels) without resetting positions
      setRfNodes(prev => {
        const updated = prev.map(node => {
          const comp = comps.find((c: any) => c.id === node.id);
          if (comp) {
            return {
              ...node,
              data: {
                ...node.data,
                label: comp.label || comp.id,
                value: comp.value,
                componentType: comp.type || 'resistor'
              }
            };
          }
          return node;
        });
        return updated;
      });
      return;
    }
    lastComponentIds.current = currentIds;

    // Generate connections for layout
    const connections: any[] = [];
    if (circuitJson.nodes) {
      for (const node of circuitJson.nodes) {
        const pins: string[] = node.connected_pins || [];
        for (let i = 0; i < pins.length; i++) {
          for (let j = i + 1; j < pins.length; j++) {
            const from = pins[i].split('.')[0];
            const to = pins[j].split('.')[0];
            if (from !== to) {
              connections.push({ from, to });
            }
          }
        }
      }
    }

    const generateLayout = async () => {
      setIsLayingOut(true);
      try {
        const positions = await layoutCircuit(comps, connections);
        const rfComps = comps.map((c: any) => ({
          id: c.id,
          type: 'component',
          position: positions[c.id] ?? { x: 100, y: 100 },
          data: { 
            label: c.label || c.id, 
            value: c.value, 
            componentType: c.type || 'resistor' 
          },
          zIndex: 10
        }));

        setRfNodes(rfComps);
      } catch (err) {
        console.error('Layout error:', err);
      } finally {
        setIsLayingOut(false);
      }
    };
    generateLayout();
  }, [circuitJson]);

  // Handle node drag to persist position changes
  const handleNodesChange = useCallback((changes: NodeChange[]) => {
    setRfNodes((nds: any[]) => applyNodeChanges(changes, nds));
  }, []);

  // --- Pairwise edge generation with smart handle selection ---
  const rfEdges = React.useMemo(() => {
    if (!circuitJson?.nodes || !circuitJson?.components) return [];

    // Build a position lookup from rfNodes (we can't depend on rfNodes directly, so recalculate)
    const posMap: Record<string, { x: number; y: number }> = {};
    for (const n of rfNodes) {
      posMap[n.id] = n.position;
    }

    // Choose the best handle (top/right/bottom/left) based on the relative position of the two components
    const pickHandles = (srcId: string, tgtId: string): [string, string] => {
      const s = posMap[srcId] || { x: 0, y: 0 };
      const t = posMap[tgtId] || { x: 0, y: 0 };
      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const angle = Math.atan2(dy, dx) * (180 / Math.PI); // -180 to 180

      if (angle >= -45 && angle < 45) {
        // Target is to the RIGHT
        return ['right', 'left'];
      } else if (angle >= 45 && angle < 135) {
        // Target is BELOW
        return ['bottom', 'top'];
      } else if (angle >= -135 && angle < -45) {
        // Target is ABOVE
        return ['top', 'bottom'];
      } else {
        // Target is to the LEFT
        return ['left', 'right'];
      }
    };

    const edges: any[] = [];
    let edgeCounter = 0;
    const seenEdges = new Set<string>();

    for (const node of circuitJson.nodes) {
      const pins: string[] = node.connected_pins || [];
      // Create pairwise edges between all components at this node (not just consecutive)
      for (let i = 0; i < pins.length; i++) {
        for (let j = i + 1; j < pins.length; j++) {
          const compI = pins[i].split('.')[0];
          const compJ = pins[j].split('.')[0];
          if (compI === compJ) continue; // skip self-loops

          const edgeKey = [compI, compJ].sort().join('--');
          if (seenEdges.has(edgeKey)) continue; // deduplicate
          seenEdges.add(edgeKey);

          const [srcHandle, tgtHandle] = pickHandles(compI, compJ);

          edges.push({
            id: `e-${compI}-${compJ}-${edgeCounter++}`,
            source: compI,
            target: compJ,
            sourceHandle: srcHandle,
            targetHandle: tgtHandle,
            type: 'step',
          });
        }
      }
    }
    return edges;
  }, [circuitJson, rfNodes]);

  // Inject Simulation Results into React Flow Nodes
  const nodesWithSim = React.useMemo(() => {
    if (!simulationData || simulationData.analysis_type !== 'dc') return rfNodes;
    return rfNodes.map((n: any) => {
      let voltage = undefined;
      const connections = simulationData.node_connections || {};
      for (const [spiceNode, pins] of Object.entries(connections) as any) {
        if (pins.some((p: string) => p.startsWith(n.id + '.'))) {
          voltage = simulationData.nodes[spiceNode]?.[0];
          break;
        }
      }
      return { ...n, data: { ...n.data, voltage } };
    });
  }, [rfNodes, simulationData]);

  // Format transient data for charts
  const transientChartData = React.useMemo(() => {
    if (!simulationData || simulationData.analysis_type !== 'transient') return null;
    return simulationData.time.map((t: number, i: number) => {
      const point: any = { time: (t * 1e6).toFixed(1) };
      Object.keys(simulationData.nodes).forEach(node => {
        point[node] = simulationData.nodes[node][i];
      });
      return point;
    });
  }, [simulationData]);

  // Whether upload area should be compact (file already loaded)
  const hasFile = !!circuitJson && !!uploadedFileName;

  return (
    <div className="flex h-screen w-screen bg-[var(--nixt-dark)] overflow-hidden font-sans relative nixt-gradient-bg">
        <div className="nixt-curves !rounded-none" />
        
        {/* Fallback warning banner */}
        {fallbackActive && (
          <div className="absolute top-6 left-1/2 transform -translate-x-1/2 bg-amber-500/90 border border-amber-400 text-white px-5 py-2.5 rounded-full shadow-lg z-30 flex items-center gap-2 backdrop-blur-md">
            <AlertTriangle size={18} />
            <span className="text-sm font-semibold tracking-wide">Running in fallback mode – using mock data due to API limits.</span>
          </div>
        )}
        
      {/* LEFT SIDEBAR — Circuit Overview */}
      <aside className="w-[340px] h-full bg-[var(--nixt-dark)]/80 backdrop-blur-3xl border-r border-[var(--nixt-border)] flex flex-col z-20 animate-fade-in-up relative">
        <div className="px-8 py-6 border-b border-[var(--nixt-border)] flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--nixt-card)] border border-[var(--nixt-border)] shadow-[0_0_20px_rgba(177,155,255,0.2)]">
              <Zap className="text-[var(--nixt-glow)] w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-2xl tracking-tight text-white leading-none mb-1">CircuitAI</h1>
              <p className="text-[10px] text-[var(--nixt-glow)] font-bold tracking-widest uppercase">Learning Platform</p>
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* UPLOAD ZONE — Full or Compact */}
          {hasFile ? (
            /* Compact file card after successful upload */
            <div className="bg-[var(--nixt-card)] border border-[var(--nixt-border)] rounded-2xl p-4 flex items-center gap-4 hover:border-[var(--nixt-glow)]/50 transition-all shadow-xl relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-r from-[var(--nixt-glow)]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="bg-[#1C1A24] p-3 rounded-xl text-[var(--nixt-glow)] shrink-0 border border-[var(--nixt-border)] relative z-10">
                <FileImage size={22} />
              </div>
              <div className="flex-1 min-w-0 relative z-10">
                <p className="text-[15px] font-semibold text-white truncate">{uploadedFileName}</p>
                <p className="text-[11px] font-medium text-[var(--nixt-text-dim)] mt-1 tracking-wide uppercase">{circuitJson?.components?.length || 0} components</p>
              </div>
              <div className="flex gap-2 shrink-0 relative z-10">
                <button onClick={handleReplace} title="Replace" className="p-2 text-[var(--nixt-text-dim)] hover:text-[var(--nixt-glow)] hover:bg-white/5 rounded-xl transition-colors">
                  <RefreshCw size={18} />
                </button>
                <button onClick={handleRemove} title="Remove" className="p-2 text-[var(--nixt-text-dim)] hover:text-red-400 hover:bg-white/5 rounded-xl transition-colors">
                  <X size={18} />
                </button>
              </div>
            </div>
          ) : (
            /* Full upload drop zone */
            <div className="sidebar-section">
              <div className="flex gap-2 mb-6 bg-[#0a0a0e] p-1.5 rounded-[16px] border border-[var(--nixt-border)] shadow-inner">
                <button 
                  onClick={() => setUploadTab('image')} 
                  className={`flex-1 py-2.5 text-[13px] font-bold tracking-wide rounded-xl transition-all ${uploadTab === 'image' ? 'bg-[var(--nixt-card)] text-white shadow-lg border border-[var(--nixt-border)]' : 'text-[var(--nixt-text-dim)] hover:text-white hover:bg-white/5'}`}
                >
                  UPLOAD IMAGE
                </button>
                <button 
                  onClick={() => setUploadTab('netlist')} 
                  className={`flex-1 py-2.5 text-[13px] font-bold tracking-wide rounded-xl transition-all ${uploadTab === 'netlist' ? 'bg-[var(--nixt-card)] text-white shadow-lg border border-[var(--nixt-border)]' : 'text-[var(--nixt-text-dim)] hover:text-white hover:bg-white/5'}`}
                >
                  PASTE NETLIST
                </button>
              </div>

              {uploadTab === 'image' ? (
                <div
                  className={`border-2 border-dashed rounded-[24px] p-10 text-center cursor-pointer transition-all duration-500 group ${
                    dragActive ? 'border-[var(--nixt-glow)] bg-[var(--nixt-glow)]/10 scale-[1.02] shadow-[0_0_30px_rgba(177,155,255,0.2)]' : 'border-[var(--nixt-border)] bg-[var(--nixt-card)] hover:bg-[#1C1A24] hover:border-[var(--nixt-glow)]/40 hover:shadow-[0_0_20px_rgba(177,155,255,0.1)]'
                  }`}
                  onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {isUploading ? (
                    <div className="animate-pulse">
                      <div className="w-16 h-16 mx-auto mb-5 rounded-[20px] bg-[var(--nixt-glow)]/20 flex items-center justify-center border border-[var(--nixt-glow)]/40 shadow-[0_0_25px_rgba(177,155,255,0.4)]">
                        <Activity size={32} className="text-[var(--nixt-glow)]" />
                      </div>
                      <p className="text-[15px] font-bold text-white tracking-wide">Analyzing circuit...</p>
                      <p className="text-[12px] text-[var(--nixt-text-dim)] mt-2 font-medium">This may take a moment</p>
                    </div>
                  ) : (
                    <div>
                      <div className="w-16 h-16 mx-auto mb-5 rounded-[20px] bg-[#22202D] border border-[var(--nixt-border)] flex items-center justify-center group-hover:bg-[#2A2736] group-hover:border-[var(--nixt-glow)]/30 transition-all shadow-inner group-hover:shadow-[0_0_15px_rgba(177,155,255,0.2)]">
                        <Upload size={32} className="text-[var(--nixt-glow)] group-hover:scale-110 transition-transform duration-500" />
                      </div>
                      <p className="text-[15px] font-bold text-white tracking-wide">Drop image here</p>
                      <p className="text-[11px] font-bold text-[var(--nixt-text-dim)] mt-2 uppercase tracking-widest group-hover:text-[var(--nixt-glow)] transition-colors">PNG, JPG, PDF</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  <textarea 
                    value={netlistInput}
                    onChange={(e) => setNetlistInput(e.target.value)}
                    placeholder="V1 node_1 0 5V&#10;R1 node_1 node_2 1k&#10;D1 node_2 0"
                    className="w-full h-40 bg-[#0a0a0e] border border-[var(--nixt-border)] rounded-[20px] p-5 text-[14px] font-mono text-white focus:border-[var(--nixt-glow)] focus:ring-1 focus:ring-[var(--nixt-glow)] outline-none resize-none placeholder-[var(--nixt-text-dim)] shadow-inner"
                  />
                  <button 
                    onClick={handleNetlistSubmit}
                    disabled={isUploading || !netlistInput.trim()}
                    className="w-full bg-[var(--nixt-card)] hover:bg-[#1A1822] disabled:bg-[#0a0a0e] disabled:text-[var(--nixt-text-dim)] text-white text-[13px] font-bold tracking-widest uppercase py-4 rounded-[16px] transition-all shadow-xl border border-[var(--nixt-border)] hover:border-[var(--nixt-glow)]/50 flex items-center justify-center gap-3 group"
                  >
                    {isUploading ? <><Activity size={18} className="animate-spin" /> Processing...</> : <><ArrowRight size={18} className="text-[var(--nixt-glow)] group-hover:translate-x-1 transition-transform" /> Process Netlist</>}
                  </button>
                </div>
              )}
            </div>
          )}

          <input ref={fileInputRef} type="file" accept="image/*,.pdf" onChange={(e) => { if (e.target.files) handleUpload(e.target.files[0]) }} className="hidden" />

          {/* ERROR CARD */}
          {uploadError && (
            <div className="bg-red-950/30 border border-red-500/40 rounded-xl p-4 space-y-3">
              <div className="flex items-start gap-2.5">
                <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-300">{uploadError.message}</p>
                  <p className="text-xs text-red-400/80 mt-1 leading-relaxed">{uploadError.hint}</p>
                </div>
              </div>
              <button
                onClick={handleReplace}
                className="w-full bg-red-500/10 hover:bg-red-500/20 text-red-300 text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-1.5 transition-colors border border-red-500/20"
              >
                <RefreshCw size={14} /> Try Again
              </button>
            </div>
          )}
          
          {/* CIRCUIT OVERVIEW */}
          <CircuitSummaryCard />

          {/* WHAT TO DO NEXT — Guidance Card */}
          {circuitJson && <NextStepCard onStartLesson={() => {
            // This function is passed to the GuidedLearningWidget via store
            // We trigger the guided lesson from here
            const widget = document.getElementById('guided-lesson-trigger');
            if (widget) widget.click();
          }} />}

          {/* VALIDATION FEEDBACK */}
          <RepairPanel />

          {/* SOLVE THE CIRCUIT (collapsible) */}
          <SimulationControls />
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 relative flex flex-col h-full bg-transparent z-10">
        
        {/* LEARNING STEPPER */}
        <PipelineProgress />

        {/* VIEW SELECTOR */}
        {circuitJson && (
          <div className="absolute top-20 right-4 z-20 bg-slate-900/80 backdrop-blur border border-slate-700 rounded-lg p-1 flex gap-1 shadow-lg">
            <button onClick={() => setViewMode('flow')} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${viewMode === 'flow' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'}`}>Circuit Diagram</button>
            <button onClick={() => setViewMode('svg')} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${viewMode === 'svg' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'}`}>Schematic View</button>
          </div>
        )}

        <div className="flex-1 relative">
          {/* WELCOME STATE */}
          {!circuitJson && !isUploading && !uploadError && (
             <div className="absolute inset-0 flex flex-col items-center justify-center text-[var(--nixt-text-dim)]">
               <div className="relative mb-8">
                 <div className="absolute inset-0 bg-[var(--nixt-glow)]/20 blur-3xl rounded-full" />
                 <GraduationCap size={96} className="relative text-[var(--nixt-glow)]/80" />
               </div>
               <h2 className="text-4xl font-bold text-white mb-4 tracking-tight">Welcome to CircuitAI</h2>
               <p className="text-[15px] text-[var(--nixt-text-dim)] mb-8 max-w-md text-center leading-relaxed">
                 Upload a circuit diagram to start learning.<br/>
                 We'll identify components, build equations, and teach you step by step.
               </p>
               <button 
                 onClick={() => fileInputRef.current?.click()}
                 className="bg-white hover:bg-[var(--nixt-glow)] text-[var(--nixt-dark)] hover:text-white font-bold tracking-widest uppercase py-4 px-10 rounded-full shadow-[0_0_30px_rgba(177,155,255,0.3)] inline-flex items-center justify-center gap-3 transition-all duration-300 transform hover:scale-105 whitespace-nowrap"
               >
                 <Upload size={22} className="shrink-0" />
                 <span>Upload Circuit</span>
               </button>
             </div>
          )}

          {/* Processing state on canvas */}
          {(isUploading || isLayingOut) && !circuitJson && (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-slate-300 font-medium">{isLayingOut ? 'Laying out circuit...' : 'Analyzing your circuit...'}</p>
              <p className="text-xs text-slate-500 mt-1">{isLayingOut ? 'Computing optimal component placement' : 'Detecting components, wires, and connections'}</p>
            </div>
          )}

          {isLayingOut && circuitJson && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0f172a]/50 backdrop-blur-sm z-10">
              <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-slate-300 font-medium">Laying out circuit...</p>
              <p className="text-xs text-slate-500 mt-1">Computing optimal component placement</p>
            </div>
          )}

          {viewMode === 'flow' && circuitJson && !isLayingOut && (
            <CircuitViewer nodes={nodesWithSim} edges={rfEdges} onNodesChange={handleNodesChange} />
          )}

          {viewMode === 'svg' && svgContent && (
             <div className="w-full h-full p-8 flex items-center justify-center overflow-auto" dangerouslySetInnerHTML={{ __html: svgContent }} />
          )}
          
          <EquationViewer />
          <GuidedLearningWidget />
        </div>

        {/* TRANSIENT CHART POPUP */}
        {transientChartData && (
          <div className="absolute bottom-4 left-4 right-4 h-64 bg-slate-900/90 backdrop-blur-xl border border-slate-700 rounded-xl shadow-2xl p-4 flex flex-col z-30">
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-semibold text-cyan-400 flex items-center gap-2"><Activity size={18}/> Transient Waveforms</h4>
              <button onClick={() => setSimulationData(null)} className="text-slate-400 hover:text-white"><Trash2 size={16}/></button>
            </div>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={transientChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc' }} />
                  <Legend />
                  {Object.keys(transientChartData[0]).filter(k => k !== 'time').map((key, idx) => {
                    const colors = ["#22d3ee", "#a855f7", "#f59e0b", "#10b981", "#ef4444"];
                    return <Line key={key} type="monotone" dataKey={key} stroke={colors[idx % colors.length]} strokeWidth={2} dot={false} />;
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </main>

      {/* RIGHT SIDEBAR - CONTEXT AWARE */}
      {selectedComponentId ? <PropertiesPanel /> : <TutorChatPanel />}
    </div>
  );
}

// ——— Next Step Guidance Card ———
const NextStepCard: React.FC<{ onStartLesson: () => void }> = ({ onStartLesson }) => {
  const { analysisData, simulationData, chatHistory } = useStore();

  if (!analysisData) return null;

  let title = '';
  let description = '';
  let Icon = ArrowRight;
  let colorClass = 'border-cyan-500/30 from-cyan-950/30 to-blue-950/20';
  let iconColor = 'text-cyan-400';
  let actionLabel = '';
  let onAction: (() => void) | null = null;

  if (!simulationData && chatHistory.length === 0) {
    title = 'Start Learning';
    description = 'Walk through this circuit step by step — identify components, nodes, loops, and equations.';
    Icon = GraduationCap;
    colorClass = 'border-indigo-500/30 from-indigo-950/30 to-purple-950/20';
    iconColor = 'text-indigo-400';
    actionLabel = 'Start Guided Lesson';
    onAction = onStartLesson;
  } else if (!simulationData) {
    title = 'Ready to Solve';
    description = 'Expand "Solve the Circuit" below to run a simulation and calculate voltages and currents.';
    Icon = Calculator;
    colorClass = 'border-emerald-500/30 from-emerald-950/30 to-cyan-950/20';
    iconColor = 'text-emerald-400';
  } else {
    title = 'Ask Questions';
    description = 'Use the AI Tutor on the right to ask about any component, equation, or concept.';
    Icon = Sparkles;
    colorClass = 'border-purple-500/30 from-purple-950/30 to-pink-950/20';
    iconColor = 'text-purple-400';
  }

  return (
    <div className={`bg-gradient-to-br ${colorClass} border rounded-xl p-4 shadow-sm`}>
      <div className="flex items-start gap-3">
        <div className={`${iconColor} mt-0.5 shrink-0`}>
          <Icon size={20} />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-white mb-1">{title}</h4>
          <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
          {actionLabel && onAction && (
            <button
              onClick={onAction}
              className="mt-3 w-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-colors shadow-md shadow-indigo-500/20"
            >
              <GraduationCap size={14} /> {actionLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
