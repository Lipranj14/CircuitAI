import React from 'react';
import { Wrench, CheckCircle, AlertTriangle } from 'lucide-react';
import { useStore } from '../store/useStore';

export const RepairPanel: React.FC = () => {
  const { suggestedRepairs, applyRepair, setHighlightedElements, validationReport } = useStore();

  // Merge repairs from suggestedRepairs (from pipeline) and validationReport checks
  const allRepairs = React.useMemo(() => {
    const repairs = [...(suggestedRepairs || [])];
    const existingIds = new Set(repairs.map(r => r.id));
    
    // Also pull repair suggestions from validation checks
    if (validationReport?.checks) {
      for (const check of validationReport.checks) {
        if (check.repair && !existingIds.has(check.repair.id)) {
          repairs.push({
            ...check.repair,
            // Use the check's description/reason if the repair doesn't have detailed ones
            description: check.repair.description || check.name,
            reason: check.repair.reason || check.description,
            visual_hints: check.repair.visual_hints || check.visual_hints || [],
          });
          existingIds.add(check.repair.id);
        }
      }
    }
    return repairs;
  }, [suggestedRepairs, validationReport]);

  if (!allRepairs || allRepairs.length === 0) return null;

  return (
    <div className="sidebar-section bg-[var(--nixt-card)] rounded-[24px] border border-[var(--nixt-border)] shadow-lg mt-5 p-6 relative overflow-hidden group">
      <div className="absolute top-0 left-0 bottom-0 w-1.5 bg-[var(--nixt-glow)] shadow-[0_0_15px_rgba(177,155,255,0.5)]"></div>
      
      <h3 className="section-title flex items-center gap-2 mb-5 text-[var(--nixt-glow)] font-bold relative z-10 tracking-wide text-[15px]">
        <Wrench size={18} />
        Validation Feedback
      </h3>
      
      <div className="space-y-4 relative z-10">
        {allRepairs.map((repair) => (
          <div 
            key={repair.id}
            className="bg-[#1C1A24] border border-[var(--nixt-border)] rounded-[16px] p-5 transition-all hover:bg-[#252230] hover:border-[var(--nixt-glow)]/50 group shadow-inner"
            onMouseEnter={() => setHighlightedElements((repair.visual_hints || []).map((id: string) => ({ type: 'component' as const, id })))}
            onMouseLeave={() => setHighlightedElements([])}
          >
            <div className="flex justify-between items-start mb-3">
              <strong className="text-[var(--nixt-glow)] text-[14px] font-bold flex items-center gap-2">
                <AlertTriangle size={18} className="text-[var(--nixt-glow)]" />
                {repair.description}
              </strong>
            </div>
            
            {/* Split reason by \n\n to separate the educational explanation from the 'How to Fix' */}
            <div className="text-[13px] text-slate-300 mb-4 leading-relaxed space-y-2">
              {(repair.reason || '').replace(/\\n/g, '\n').split('\n\n').map((paragraph: string, idx: number) => {
                if (paragraph.startsWith('**How to Fix:**')) {
                  return (
                    <div key={idx} className="bg-amber-500/10 p-3 rounded-lg border border-amber-500/20 text-amber-200/90 font-medium shadow-inner">
                      <span className="text-amber-400 font-bold block mb-1">How to Fix:</span>
                      {paragraph.replace('**How to Fix:**', '').trim()}
                    </div>
                  );
                }
                // Handle bolding in react securely
                const renderBold = (text: string) => {
                  const parts = text.split(/\*\*(.*?)\*\*/g);
                  return parts.map((part, i) => i % 2 === 1 ? <strong key={i} className="text-white font-semibold">{part}</strong> : part);
                };
                return <p key={idx}>{renderBold(paragraph)}</p>;
              })}
            </div>
            
            {repair.action && (
              <button 
                onClick={() => applyRepair(repair.id)}
                className="mt-5 w-full bg-[var(--nixt-glow)] hover:bg-white text-[var(--nixt-dark)] text-[13px] font-bold py-3.5 px-4 rounded-[12px] flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(177,155,255,0.2)] uppercase tracking-widest group-hover:scale-[1.01]"
              >
                <CheckCircle size={16} /> Auto-Fix Issue
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
