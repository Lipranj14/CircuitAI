import React, { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { apiClient } from '../api';
import { Settings, Zap, BookOpen, AlertCircle, Info, Loader2, Edit2 } from 'lucide-react';

export const PropertiesPanel: React.FC = () => {
  const { 
      circuitJson, 
      selectedComponentId, 
      simulationData, 
      setCircuitJson, 
      setSelectedComponentId,
      learningMode,
      componentMetadata,
      setComponentMetadata,
      analysisData,
      addChatMessage
  } = useStore();

  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!selectedComponentId || !analysisData || !learningMode) return;
    
    // Check if we already have the metadata
    if (componentMetadata[selectedComponentId]) return;

    const fetchMetadata = async () => {
      setIsLoading(true);
      try {
        const comp = circuitJson.components.find((c: any) => c.id === selectedComponentId);
        const data = await apiClient.getComponentMetadata({
            comp_id: selectedComponentId,
            comp_type: comp?.type || 'unknown',
            analysis: analysisData
        });
        
        if (data.success && data.data) {
          setComponentMetadata(selectedComponentId, data.data);
        }
      } catch (err) {
        console.error("Failed to fetch component metadata:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMetadata();
  }, [selectedComponentId, analysisData, learningMode, circuitJson, componentMetadata, setComponentMetadata]);

  if (!selectedComponentId || !circuitJson) return null;

  const component = circuitJson.components.find((c: any) => c.id === selectedComponentId);
  if (!component) return null;

  const metadata = componentMetadata[selectedComponentId];

  // Extract sim data
  let voltage = undefined;
  let current = undefined;
  if (simulationData && simulationData.analysis_type === 'dc') {
      const connections = simulationData.node_connections || {};
      for (const [spiceNode, pins] of Object.entries(connections) as any) {
        if (pins.some((p: string) => p.startsWith(component.id + '.'))) {
          voltage = simulationData.nodes[spiceNode]?.[0];
          break;
        }
      }
      
      const currentKey = Object.keys(simulationData.branch_currents || {}).find(k => k.toLowerCase() === component.id.toLowerCase());
      if (currentKey) {
          current = simulationData.branch_currents[currentKey][0];
      }
  }

  const updateComponentValue = (id: string, value: string) => {
      const newCircuit = JSON.parse(JSON.stringify(circuitJson));
      const comp = newCircuit.components.find((c: any) => c.id === id);
      if (comp) {
          comp.value = value;
          setCircuitJson(newCircuit);
      }
  };

  const handleExplain = () => {
      setSelectedComponentId(null);
      addChatMessage({ 
          role: 'user', 
          content: `Can you explain the purpose of ${component.id} (${metadata?.name || component.type}) in this circuit?` 
      });
  };

  return (
    <div className="w-80 h-full bg-slate-900 border-l border-slate-800 flex flex-col shadow-2xl z-20">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <h2 className="font-bold text-lg text-white flex items-center gap-2">
          {learningMode ? <BookOpen size={18} className="text-indigo-400" /> : <Settings size={18} className="text-cyan-400" />}
          {learningMode ? 'Learning Profile' : 'Properties'}
        </h2>
        <button onClick={() => setSelectedComponentId(null)} className="text-slate-400 hover:text-white text-xs font-medium bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded transition-colors">Close</button>
      </div>

      <div className="p-4 space-y-6 overflow-y-auto">
        
        {/* Component Header */}
        <div className="flex items-center gap-3 bg-slate-950/50 p-3 rounded-xl border border-slate-800">
            <div className="w-10 h-10 bg-indigo-900/40 rounded-lg flex items-center justify-center border border-indigo-500/30 text-indigo-300 font-bold">
                {component.id.substring(0, 2).toUpperCase()}
            </div>
            <div>
                <h3 className="text-white font-semibold text-sm">{metadata?.name || component.type.replace('_', ' ')}</h3>
                <p className="text-slate-400 text-xs font-mono">{component.id}</p>
            </div>
            {learningMode && (
                <button 
                    onClick={handleExplain}
                    className="ml-auto bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white p-1.5 rounded-lg transition-colors border border-indigo-500/30 text-[10px] font-semibold flex items-center gap-1"
                >
                    <Info size={12}/> Explain
                </button>
            )}
        </div>

        {/* Learning Mode vs Sandbox Mode */}
        {learningMode ? (
            <div className="space-y-4">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center p-8 text-slate-500">
                        <Loader2 className="animate-spin mb-2" size={24} />
                        <span className="text-xs">Analyzing component...</span>
                    </div>
                ) : metadata ? (
                    <>
                        <div className="space-y-2">
                            <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center gap-1.5"><Info size={12}/> Purpose</h4>
                            <p className="text-xs text-slate-300 leading-relaxed bg-slate-800/30 p-3 rounded-lg border border-slate-800/50">{metadata.purpose}</p>
                        </div>

                        <div className="space-y-2">
                            <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center gap-1.5"><Zap size={12}/> Function Here</h4>
                            <p className="text-xs text-slate-300 leading-relaxed bg-indigo-900/20 p-3 rounded-lg border border-indigo-500/20">{metadata.function_in_circuit}</p>
                        </div>

                        {metadata.related_equations?.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center gap-1.5"><Settings size={12}/> Equations</h4>
                                <div className="flex flex-col gap-1.5">
                                    {metadata.related_equations.map((eq: string, idx: number) => (
                                        <div key={idx} className="bg-slate-950 px-3 py-2 rounded border border-slate-800 font-mono text-cyan-300 text-xs text-center">
                                            {eq}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {metadata.common_mistakes?.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="text-[10px] font-bold uppercase tracking-widest text-amber-500 flex items-center gap-1.5"><AlertCircle size={12}/> Common Mistakes</h4>
                                <ul className="list-disc list-inside text-xs text-amber-200/80 bg-amber-950/20 p-3 rounded-lg border border-amber-900/30 space-y-1">
                                    {metadata.common_mistakes.map((mistake: string, idx: number) => (
                                        <li key={idx} className="leading-snug">{mistake}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="text-xs text-slate-500 text-center italic">Failed to load educational data.</div>
                )}
            </div>
        ) : (
            /* SANDBOX MODE (Editing) */
            <div>
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-3 flex items-center gap-2">
                    <Edit2 size={14} /> Parameters
                </h3>
                <div className="bg-slate-950/50 rounded-xl p-3 border border-slate-800/50 shadow-inner">
                    <label className="block text-xs font-medium text-slate-400 mb-2">Value (e.g. 1k, 5V)</label>
                    <input 
                        type="text" 
                        value={component.value || ''}
                        onChange={(e) => updateComponentValue(component.id, e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white font-mono text-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none transition-all shadow-inner"
                        placeholder="Unspecified"
                    />
                </div>
            </div>
        )}

        {/* Simulation Results (Shared) */}
        {simulationData && (
          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-3 flex items-center gap-2">
              <Zap size={14} /> Real-Time Data
            </h3>
            <div className="bg-gradient-to-br from-cyan-950/40 to-blue-950/40 rounded-xl p-4 border border-cyan-900/50 space-y-3 shadow-inner">
              {voltage !== undefined ? (
                <div className="flex justify-between items-center">
                  <span className="text-cyan-400/80 text-xs font-medium">Nodal Voltage</span>
                  <span className="text-cyan-300 font-mono text-sm font-bold bg-cyan-950/50 px-2 py-0.5 rounded">{voltage.toFixed(3)} V</span>
                </div>
              ) : (
                <span className="text-slate-500 text-xs italic">Voltage N/A</span>
              )}
              
              {current !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-cyan-400/80 text-xs font-medium">Branch Current</span>
                  <span className="text-cyan-300 font-mono text-sm font-bold bg-cyan-950/50 px-2 py-0.5 rounded">{(current * 1000).toFixed(2)} mA</span>
                </div>
              )}
              
              {voltage !== undefined && current !== undefined && (
                <div className="flex justify-between items-center pt-3 mt-3 border-t border-cyan-900/30">
                  <span className="text-orange-400/80 text-xs font-medium">Power Dissip.</span>
                  <span className="text-orange-400 font-mono text-sm font-bold bg-orange-950/30 px-2 py-0.5 rounded border border-orange-900/30">
                    {Math.abs(voltage * current * 1000).toFixed(2)} mW
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
