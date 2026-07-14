import React from 'react';
import { useStore } from '../store/useStore';
import { X, CheckCircle, AlertTriangle, ShieldAlert, Wrench } from 'lucide-react';

export const ValidationModal: React.FC<{ onProceed: () => void }> = ({ onProceed }) => {
  const { validationReport, setValidationReport, setHighlightedElements, applyRepair } = useStore();

  if (!validationReport) return null;

  const handleApplyRepair = (repairId: string) => {
    applyRepair(repairId);
    setValidationReport(null);
  };

  const hasErrors = validationReport.checks.some((c: any) => c.status === 'error');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
          <h2 className="text-lg font-bold flex items-center gap-2 text-white">
            <ShieldAlert className={hasErrors ? "text-red-500" : "text-amber-500"} />
            Circuit Validation Report
          </h2>
          <button onClick={() => setValidationReport(null)} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
        
        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {validationReport.checks.map((check: any) => (
            <div 
              key={check.id}
              className={`p-3 rounded-lg border flex gap-3 transition-colors ${
                check.status === 'error' ? 'bg-red-950/20 border-red-900/50 hover:border-red-500/50' : 
                check.status === 'warning' ? 'bg-amber-950/20 border-amber-900/50 hover:border-amber-500/50' :
                'bg-green-950/10 border-green-900/30 hover:border-green-500/30'
              }`}
              onMouseEnter={() => {
                if (check.visual_hints) {
                  setHighlightedElements(check.visual_hints.map((id: string) => ({ type: 'component', id })));
                }
              }}
              onMouseLeave={() => setHighlightedElements([])}
            >
              <div className="mt-0.5">
                {check.status === 'error' && <AlertTriangle size={18} className="text-red-500" />}
                {check.status === 'warning' && <AlertTriangle size={18} className="text-amber-500" />}
                {check.status === 'pass' && <CheckCircle size={18} className="text-green-500" />}
              </div>
              
              <div className="flex-1">
                <h4 className={`text-sm font-semibold mb-1 ${
                  check.status === 'error' ? 'text-red-400' :
                  check.status === 'warning' ? 'text-amber-400' : 'text-green-400'
                }`}>
                  {check.name}
                </h4>
                <p className="text-xs text-slate-300 leading-relaxed mb-2">
                  {check.description}
                </p>
                
                {check.repair && (
                  <div className="mt-3 bg-slate-950 rounded p-2 border border-slate-800 flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Suggested Fix: {check.repair.description}</span>
                    <button
                      onClick={() => handleApplyRepair(check.repair.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-cyan-500/10 text-cyan-400 rounded hover:bg-cyan-500/20 transition-colors"
                    >
                      <Wrench size={14} /> Apply Repair
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3">
          <button 
            onClick={() => setValidationReport(null)}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          
          <button 
            onClick={() => {
                setValidationReport(null);
                onProceed();
            }}
            disabled={hasErrors}
            className={`px-4 py-2 text-sm font-semibold rounded-lg flex items-center gap-2 transition-all ${
                hasErrors 
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed' 
                : 'bg-cyan-600 text-white hover:bg-cyan-500 shadow-lg shadow-cyan-500/20'
            }`}
          >
            {hasErrors ? "Fix errors to proceed" : "Run Simulation"}
          </button>
        </div>
        
      </div>
    </div>
  );
};
