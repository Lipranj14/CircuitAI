import React from 'react';
import { BookOpen, Activity, Cpu, Code, Lightbulb, Clock, Loader2, Zap } from 'lucide-react';
import { useStore } from '../store/useStore';

// Skeleton placeholder for loading state
const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`animate-pulse bg-slate-700/50 rounded ${className}`} />
);

export const CircuitSummaryCard: React.FC = () => {
  const { analysisData, circuitJson, pipelineStage } = useStore();

  const isLoading = pipelineStage === 'uploading' || pipelineStage === 'detecting' || pipelineStage === 'reconstructing';

  // Show loading skeleton when processing
  if (isLoading) {
    return (
      <div className="sidebar-section bg-[var(--nixt-card)] border border-[var(--nixt-border)] rounded-[24px] p-6 shadow-lg relative overflow-hidden group">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
        <div className="flex items-center gap-2 mb-4 border-b border-white/5 pb-3">
          <Loader2 size={18} className="text-indigo-400 animate-spin" />
          <h3 className="font-semibold text-sm text-indigo-200">Analyzing Circuit...</h3>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-[#1C1A24] rounded-xl p-3 border border-[var(--nixt-border)]">
            <Skeleton className="h-2 w-8 mb-2.5 mx-auto bg-white/10" />
            <Skeleton className="h-3 w-16 mx-auto bg-white/10" />
          </div>
          <div className="bg-[#1C1A24] rounded-xl p-3 border border-[var(--nixt-border)]">
            <Skeleton className="h-2 w-12 mb-2.5 mx-auto bg-white/10" />
            <Skeleton className="h-3 w-14 mx-auto bg-white/10" />
          </div>
        </div>
        <div className="flex justify-between items-center bg-[#1C1A24] p-3 rounded-xl border border-[var(--nixt-border)]">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-14" />
          <Skeleton className="h-3 w-14" />
        </div>
      </div>
    );
  }

  if (!analysisData || !circuitJson) return null;

  const circuitType = analysisData.circuit_type || 'Unknown';
  const difficulty = analysisData.difficulty || 'Unknown';
  const componentCount = analysisData.component_count ?? circuitJson.components?.length ?? 0;
  const nodeCount = analysisData.node_count ?? circuitJson.nodes?.length ?? 0;
  const loopCount = analysisData.loop_count ?? 0;
  const laws = analysisData.applicable_laws || [];

  const learningTime = difficulty === 'Beginner' ? '5 – 10 min' : difficulty === 'Intermediate' ? '15 – 20 min' : '30+ min';

  return (
    <div className="sidebar-section bg-[var(--nixt-card)] border border-[var(--nixt-border)] rounded-[24px] p-5 shadow-lg relative overflow-hidden group hover:border-[var(--nixt-glow)]/50 transition-all duration-500 flex flex-col gap-4">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
      
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-[var(--nixt-border)] pb-4 relative z-10">
        <div className="bg-[var(--nixt-glow)]/15 p-2 rounded-xl border border-[var(--nixt-glow)]/30 shadow-[0_0_15px_rgba(168,85,247,0.2)]">
          <BookOpen size={18} className="text-[var(--nixt-glow)]" />
        </div>
        <h3 className="font-semibold text-base text-white tracking-wide">Circuit Overview</h3>
      </div>
      
      {/* Type & Difficulty */}
      <div className="grid grid-cols-2 gap-3 relative z-10">
        <div className="bg-black/30 rounded-[16px] p-4 border border-[var(--nixt-border)] flex flex-col items-center justify-center shadow-inner hover:border-[var(--nixt-glow)]/30 transition-colors">
          <p className="text-[10px] text-[var(--nixt-text-dim)] uppercase tracking-widest mb-1.5 font-bold">Type</p>
          <p className="text-[14px] font-bold text-indigo-100">{circuitType}</p>
        </div>
        <div className="bg-black/30 rounded-[16px] p-4 border border-[var(--nixt-border)] flex flex-col items-center justify-center shadow-inner hover:border-[var(--nixt-glow)]/30 transition-colors">
          <p className="text-[10px] text-[var(--nixt-text-dim)] uppercase tracking-widest mb-1.5 font-bold">Difficulty</p>
          <p className={`text-[14px] font-bold ${difficulty === 'Beginner' ? 'text-emerald-400' : difficulty === 'Intermediate' ? 'text-amber-400' : 'text-red-400'}`}>{difficulty}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="flex justify-between items-center text-[12px] font-bold text-[var(--nixt-text-dim)] bg-black/30 p-4 rounded-[16px] border border-[var(--nixt-border)] relative z-10 shadow-inner">
        <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.5)]"></div> {componentCount} Comps</span>
        <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(192,132,252,0.5)]"></div> {nodeCount} Nodes</span>
        <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]"></div> {loopCount} Loops</span>
      </div>

      {/* What this circuit does */}
      {analysisData.overview && (
        <div className="relative z-10 bg-gradient-to-br from-[#1C1A24] to-[#151419] p-5 rounded-[16px] border border-[var(--nixt-border)] shadow-inner hover:border-[var(--nixt-glow)]/30 transition-colors">
          <p className="text-[11px] text-[var(--nixt-text-dim)] uppercase tracking-widest mb-2.5 font-bold flex items-center gap-2">
            <Zap size={14} className="text-amber-400" /> What this circuit does
          </p>
          <p className="text-[13.5px] text-slate-300 leading-relaxed font-medium">
            {analysisData.overview}
          </p>
        </div>
      )}

      {/* Applicable Laws */}
      {laws.length > 0 && (
        <div className="relative z-10 bg-black/20 p-4 rounded-[16px] border border-[var(--nixt-border)] hover:border-[var(--nixt-glow)]/30 transition-colors">
          <p className="text-[11px] text-[var(--nixt-text-dim)] uppercase tracking-widest mb-3 flex items-center gap-2 font-bold">
            <Lightbulb size={14} className="text-yellow-400" /> Applicable Laws
          </p>
          <div className="flex flex-wrap gap-2">
            {laws.map((law: string, idx: number) => (
              <span key={idx} className="bg-[var(--nixt-glow)]/10 text-[var(--nixt-glow)] border border-[var(--nixt-glow)]/30 text-[11px] px-3.5 py-1.5 rounded-full font-bold tracking-wide shadow-sm">
                {law}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Learning Time */}
      <div className="bg-[var(--nixt-glow)]/10 rounded-[16px] p-4 border border-[var(--nixt-glow)]/20 flex items-center justify-between relative z-10 shadow-[inset_0_0_20px_rgba(168,85,247,0.05)]">
        <p className="text-[11px] text-[var(--nixt-glow)] uppercase tracking-widest font-bold flex items-center gap-2">
          <Clock size={16} /> Est. Learning Time
        </p>
        <p className="text-[14px] text-white font-bold">{learningTime}</p>
      </div>
    </div>
  );
};
