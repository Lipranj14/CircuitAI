import React from 'react';
import { useStore } from '../store/useStore';
import { Calculator } from 'lucide-react';

export const EquationViewer: React.FC = () => {
  const { analysisData, activeOverlays, setHighlightedElements } = useStore();

  if (!analysisData || !analysisData.equations || analysisData.equations.length === 0) return null;
  if (!activeOverlays.equations) return null;

  return (
    <div className="absolute right-4 bottom-4 w-96 bg-slate-900/95 backdrop-blur-md border border-emerald-500/30 rounded-xl shadow-2xl p-4 z-30">
      <h3 className="font-semibold text-emerald-400 mb-3 flex items-center gap-2">
        <Calculator size={18} /> Derived Equations
      </h3>
      <div className="space-y-4 max-h-80 overflow-y-auto pr-2">
        {analysisData.equations.map((eq: any) => (
          <div key={eq.id} className="bg-slate-950 rounded-lg p-3 border border-slate-800 transition-all hover:border-emerald-500/50 shadow-inner">
            <div className="text-[10px] text-slate-500 font-mono mb-2 uppercase tracking-wider flex justify-between">
              <span className="text-emerald-500/70">{eq.type} Law</span>
              <span>{eq.related_id}</span>
            </div>
            
            <div className="flex flex-wrap gap-1 font-mono text-sm items-center text-slate-200">
              {eq.ordered_terms?.map((term: string, idx: number) => {
                // Find associated components by checking if comp id is substring of term
                const relatedComps = eq.participating_components?.filter((c: string) => term.includes(c)) || [];
                
                return (
                  <span 
                    key={idx} 
                    className="px-1.5 py-0.5 rounded cursor-pointer transition-colors hover:bg-emerald-900/60 hover:text-emerald-300"
                    onMouseEnter={() => {
                        if (relatedComps.length > 0) {
                            setHighlightedElements(relatedComps.map((id: string) => ({ type: 'component', id })));
                        } else if (eq.type === 'KCL') {
                           // If it's a current term and we know the node, highlight the node
                           setHighlightedElements([{ type: 'node', id: eq.related_id }]);
                        }
                    }}
                    onMouseLeave={() => setHighlightedElements([])}
                  >
                    {term}
                  </span>
                );
              })}
              <span className="text-slate-400 px-1">= 0</span>
            </div>
            
          </div>
        ))}
      </div>
      <div className="mt-3 text-[10px] text-slate-500 text-center">
        Hover over terms to highlight elements
      </div>
    </div>
  );
};
