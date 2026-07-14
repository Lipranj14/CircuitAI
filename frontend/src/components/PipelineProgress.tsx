import React from 'react';
import { useStore } from '../store/useStore';
import { Upload, BookOpen, GraduationCap, Calculator, MessageCircle, CheckCircle } from 'lucide-react';

export const PipelineProgress: React.FC = () => {
  const { pipelineStage, analysisData, chatHistory, simulationData, learningMode } = useStore();

  const steps = [
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'overview', label: 'Overview', icon: BookOpen },
    { id: 'learn', label: 'Learn', icon: GraduationCap },
    { id: 'solve', label: 'Solve', icon: Calculator },
    { id: 'ask', label: 'Ask', icon: MessageCircle },
  ];

  // Auto-advance: map app state → highest reached step
  const getActiveIndex = (): number => {
    // Nothing uploaded yet
    if (!analysisData && pipelineStage === 'idle') return -1;

    // Currently processing upload
    if (pipelineStage === 'uploading' || pipelineStage === 'detecting' || pipelineStage === 'reconstructing') return 0;
    if (pipelineStage === 'error') return -1;

    // Currently running simulation
    if (pipelineStage === 'validating' || pipelineStage === 'simulating') return 3;

    // Determine highest step based on accumulated state
    if (chatHistory.length > 0) return 4;          // Student asked questions
    if (simulationData) return 3;                    // Simulation results exist
    if (pipelineStage === 'visualization') return 3; // Just finished simulating
    if (learningMode) return 2;                      // Guided lesson active
    if (analysisData) return 1;                      // Analysis available → Overview

    return -1;
  };

  const activeIndex = getActiveIndex();
  const isProcessing = pipelineStage === 'uploading' || pipelineStage === 'detecting' || pipelineStage === 'reconstructing';

  // Hide entirely when nothing has happened yet
  if (activeIndex === -1 && !isProcessing && pipelineStage !== 'error') return null;

  return (
    <div className="w-full bg-[var(--nixt-dark)] border-b border-[var(--nixt-border)] px-8 py-5 flex items-center justify-center gap-3 relative overflow-hidden z-20 shadow-md">
      {steps.map((step, i) => {
        const Icon = step.icon;
        const isActive = i === activeIndex;
        const isDone = i < activeIndex;

        let dotClass = 'bg-[#1C1A24] text-[var(--nixt-text-dim)] border-[var(--nixt-border)]';
        let labelClass = 'text-[var(--nixt-text-dim)] font-medium';

        if (isDone) {
          dotClass = 'bg-[var(--nixt-glow)]/10 text-[var(--nixt-glow)] border-[var(--nixt-glow)]/30';
          labelClass = 'text-[var(--nixt-glow)] font-bold';
        }
        if (isActive) {
          dotClass = 'bg-[var(--nixt-glow)] text-[var(--nixt-dark)] border-transparent shadow-[0_0_15px_rgba(177,155,255,0.4)] ring-4 ring-[var(--nixt-glow)]/20';
          labelClass = 'text-[var(--nixt-glow)] font-bold tracking-wide';
        }
        if (pipelineStage === 'error') {
          // On error, highlight upload step as error
          if (i === 0) {
            dotClass = 'bg-gradient-to-br from-red-500 to-rose-600 text-white border-transparent shadow-[0_0_15px_rgba(239,68,68,0.4)]';
            labelClass = 'text-red-400 font-bold';
          }
        }

        return (
          <React.Fragment key={step.id}>
            {i > 0 && (
              <div className={`h-[2px] w-14 transition-colors duration-500 ${isDone || isActive ? 'bg-gradient-to-r from-cyan-500/50 to-blue-500/50' : 'bg-white/5'}`} />
            )}

            <div className="flex flex-col items-center gap-2 min-w-[64px]">
              <div className={`relative flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-500 ${dotClass}`}>
                {isActive && isProcessing ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : isDone ? (
                  <CheckCircle size={18} strokeWidth={2.5} />
                ) : (
                  <Icon size={18} strokeWidth={2.5} />
                )}
              </div>
              <span className={`text-[12px] transition-all duration-300 uppercase tracking-widest ${labelClass}`}>{step.label}</span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};
