import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { Calculator, Zap, RefreshCw, ChevronDown, ChevronRight, SlidersHorizontal } from 'lucide-react';
import { apiClient } from '../api';
import { ValidationModal } from './ValidationModal';

export const SimulationControls: React.FC = () => {
    const { 
    circuitJson, 
    updateComponentValue, 
    isSimulating, 
    setIsSimulating,
    setSimulationData,
    setAllOverlays,
    setHighlightedElements,
    setValidationReport,
    setPipelineStage
  } = useStore();

  const [analysisType, setAnalysisType] = useState('dc');
  const [simulationError, setSimulationError] = useState<{error: string, component?: string, fix?: string} | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [showParams, setShowParams] = useState(true);

  const handleValidateAndSimulate = async () => {
    if (!circuitJson) return;

    const missingComp = circuitJson.components.find((c: any) => c.value_missing && (!c.value || c.value.trim() === ''));
    if (missingComp) {
      setSimulationError({
        error: `Please enter a value for ${missingComp.id} before solving`,
        component: missingComp.id,
        fix: 'Use the Edit Values panel above to enter the missing value.'
      });
      setPipelineStage('error');
      return;
    }

    setIsSimulating(true);
    setHighlightedElements([]);
    setSimulationError(null);
    setPipelineStage('validating');

    try {
      const data = await apiClient.validateCircuit(circuitJson);
      
      if (!data) throw new Error('Validation failed');

      if (!data.is_valid || data.checks.some((c: any) => c.status === 'warning' || c.status === 'error')) {
        setValidationReport(data);
        setIsSimulating(false);
        setPipelineStage('error');
        return;
      }
      
      setPipelineStage('simulating');
      await executeSimulation();
    } catch (err: any) {
      console.error(err);
      setSimulationError({ error: 'System Error', fix: err.message });
      setPipelineStage('error');
      setIsSimulating(false);
    }
  };

  const executeSimulation = async () => {
    if (!circuitJson) return;
    setIsSimulating(true);
    setHighlightedElements([]);
    setSimulationError(null);

    try {
      const simData = await apiClient.simulateV2({
        circuit: circuitJson,
        analysis_type: analysisType
      });
      
      if (simData.success === false) {
        if (simData.highlight_ids) {
          setHighlightedElements(simData.highlight_ids.map((id: string) => ({ type: 'component', id })));
        }
        
        if (simData.error && simData.fix) {
            setSimulationError({
                error: simData.error,
                component: simData.component,
                fix: simData.fix
            });
            return;
        }
        
        const errorMsg = simData.reason || simData.error || simData.detail || 'Simulation failed';
        throw new Error(errorMsg);
      }

      setSimulationData(simData.data || simData);
      if (analysisType === 'dc') {
        setAllOverlays({ currentFlow: false, nodeVoltages: true, kvlLoops: false, kclNodes: false, equations: false });
      } else {
        setAllOverlays({ currentFlow: false, nodeVoltages: false, kvlLoops: false, kclNodes: false, equations: false });
      }
      setPipelineStage('visualization');
    } catch (err: any) {
      console.error(err);
      setSimulationError({
        error: err.error || err.message || 'Simulation Failed',
        component: err.component,
        fix: err.fix
      });
      setPipelineStage('error');
    } finally {
      setIsSimulating(false);
    }
  };

  if (!circuitJson) return null;

  return (
    <div className="sidebar-section bg-[var(--nixt-card)] rounded-[24px] border border-[var(--nixt-border)] shadow-lg mt-5 overflow-hidden group">
      <ValidationModal onProceed={executeSimulation} />
      
      {/* Collapsible Header */}
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-5 hover:bg-[#252230] transition-colors"
      >
        <h3 className="flex items-center gap-2 text-[var(--nixt-glow)] font-bold text-[15px]">
          <Calculator size={18} />
          Solve the Circuit
        </h3>
        {isExpanded ? <ChevronDown size={16} className="text-[var(--nixt-text-dim)]" /> : <ChevronRight size={16} className="text-[var(--nixt-text-dim)]" />}
      </button>
      
      {isExpanded && (
        <div className="px-5 pb-5 space-y-5">
          {simulationError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3.5 text-red-200 text-sm">
                <strong className="block text-red-400 mb-1.5 font-semibold">{simulationError.error} {simulationError.component ? `[${simulationError.component}]` : ''}</strong>
                <p className="text-[13px]">{simulationError.fix}</p>
            </div>
          )}
          
          <div>
            <label className="block text-[11px] text-[var(--nixt-text-dim)] mb-2 uppercase tracking-widest font-bold">Analysis Type</label>
            <select 
              className="w-full bg-[#0a0a0e] text-[13px] p-3.5 rounded-[16px] border border-[var(--nixt-border)] text-white focus:outline-none focus:border-[var(--nixt-glow)] focus:ring-1 focus:ring-[var(--nixt-glow)] shadow-inner"
              value={analysisType}
              onChange={(e) => setAnalysisType(e.target.value)}
            >
              <option value="dc" className="bg-[var(--nixt-dark)]">DC Operating Point</option>
              <option value="transient" className="bg-[var(--nixt-dark)]">Transient Analysis</option>
              <option value="ac" className="bg-[var(--nixt-dark)]">AC Sweep Analysis</option>
            </select>
          </div>

          {/* Collapsible component parameters */}
          <div>
            <button 
              onClick={() => setShowParams(!showParams)}
              className="flex items-center gap-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors mb-3"
            >
              <SlidersHorizontal size={12} />
              <span className="uppercase tracking-widest font-semibold">Edit Values</span>
              {showParams ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </button>

            {showParams && (
              <>
                <div className="max-h-48 overflow-y-auto space-y-3 pr-2 scrollbar-hide">
                  {circuitJson.components.filter((comp: any) => !['ground', 'junction', 'terminal'].includes(comp.type?.toLowerCase())).map((comp: any) => (
                    <div key={comp.id} className="flex items-center justify-between gap-3 bg-[#0a0a0e] p-3 rounded-[16px] border border-[var(--nixt-border)] hover:border-[var(--nixt-glow)]/50 transition-colors shadow-inner">
                      <div className="flex flex-col min-w-0">
                        <span className="text-[13px] font-mono text-white font-bold">{comp.id}</span>
                        <span className="text-[10px] text-[var(--nixt-text-dim)] capitalize font-bold">{comp.type}</span>
                      </div>
                      <input
                        type="text"
                        value={comp.value || ''}
                        onChange={(e) => updateComponentValue(comp.id, e.target.value)}
                        title={comp.value_missing ? "Value not detected from image — please enter manually" : ""}
                        className={`w-24 text-[13px] p-2 rounded-[12px] border text-white text-right font-mono focus:outline-none transition-all ${
                          comp.value_missing 
                            ? 'bg-yellow-900/40 border-yellow-500/80 focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400 placeholder-yellow-700/70' 
                            : 'bg-[#1C1A24] border-[var(--nixt-border)] focus:border-[var(--nixt-glow)] focus:ring-1 focus:ring-[var(--nixt-glow)]'
                        }`}
                        placeholder={comp.value_missing ? "Enter value (e.g. 5V, 1kΩ)" : "e.g. 1k, 5V"}
                      />
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-[var(--nixt-text-dim)] mt-3 italic text-center">Tip: Enter component values above to enable circuit solving.</p>
              </>
            )}
          </div>

          <button
            onClick={handleValidateAndSimulate}
            disabled={isSimulating}
            className="w-full bg-[var(--nixt-glow)] hover:bg-white disabled:bg-[var(--nixt-dark)] disabled:text-[var(--nixt-text-dim)] text-[var(--nixt-dark)] font-bold py-4 px-4 rounded-[16px] shadow-[0_0_20px_rgba(177,155,255,0.2)] flex justify-center items-center gap-2 disabled:opacity-50 transition-all uppercase tracking-widest text-[13px]"
          >
            {isSimulating ? (
              <><RefreshCw size={18} className="animate-spin" /> Computing...</>
            ) : (
              <><Zap size={18} /> Solve & Analyze</>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
