import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { GraduationCap, ArrowRight, Check, X } from 'lucide-react';

export const GuidedLearningWidget: React.FC = () => {
  const { analysisData, setAllOverlays, setActiveLoopId, setActiveNodeId, setHighlightedElements, addChatMessage, setLearningMode } = useStore();
  const [step, setStep] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  if (!analysisData) return null;

  const steps = [
    {
      title: "Identify Components",
      desc: "First, let's look at what makes up this circuit. Notice the components that have been highlighted.",
      action: () => {
        setAllOverlays({ currentFlow: false, nodeVoltages: false, kvlLoops: false, kclNodes: false, equations: false });
        if (analysisData.components) {
            setHighlightedElements(analysisData.components.map((c: any) => ({ type: 'component', id: c.id })));
        } else {
            setHighlightedElements([]);
        }
      }
    },
    {
      title: "Identify Nodes",
      desc: "Nodes are the junctions where components connect. A node shares the same voltage everywhere.",
      action: () => {
        setAllOverlays({ currentFlow: false, nodeVoltages: false, kvlLoops: false, kclNodes: true, equations: false });
        if (analysisData.topology?.nodes?.[0]) {
           setActiveNodeId(analysisData.topology.nodes[0].id);
        }
      }
    },
    {
      title: "Identify Loops",
      desc: "Loops are closed paths in the circuit. KVL states the sum of voltages around any loop is zero.",
      action: () => {
        setAllOverlays({ currentFlow: false, nodeVoltages: false, kvlLoops: true, kclNodes: false, equations: false });
        if (analysisData.topology?.loops?.[0]) {
           setActiveLoopId(analysisData.topology.loops[0].id);
        }
      }
    },
    {
      title: "Electrical Laws & Equations",
      desc: "Based on the loops and nodes, we can construct the KVL and KCL equations (see bottom right).",
      action: () => {
        setAllOverlays({ currentFlow: false, nodeVoltages: false, kvlLoops: true, kclNodes: false, equations: true });
      }
    },
    {
      title: "Explain Solution",
      desc: "Let's ask the AI Tutor to explain the behavior of this specific circuit in detail.",
      action: () => {
        setAllOverlays({ currentFlow: true, nodeVoltages: true, kvlLoops: false, kclNodes: false, equations: false });
        addChatMessage({ role: 'user', content: 'Can you walk me through the solution for this circuit?' });
      }
    }
  ];

  const handleNext = () => {
    if (step < steps.length - 1) {
      const nextStep = step + 1;
      setStep(nextStep);
      steps[nextStep].action();
    }
  };
  
  const startWizard = () => {
     setIsOpen(true);
     setLearningMode(true);
     setStep(0);
     steps[0].action();
  };

  const closeWizard = () => {
    setIsOpen(false);
    setLearningMode(false);
    setHighlightedElements([]);
    setAllOverlays({ currentFlow: false, nodeVoltages: false, kvlLoops: false, kclNodes: false, equations: false });
  };

  // Hidden trigger button — clicked from the sidebar NextStepCard
  // This is the SINGLE entry point for the guided lesson
  if (!isOpen) {
    return (
      <button 
        id="guided-lesson-trigger"
        onClick={startWizard}
        className="hidden"
        aria-hidden="true"
      />
    );
  }

  return (
    <div className="absolute left-4 bottom-4 w-80 bg-slate-900/95 backdrop-blur-md border border-indigo-500/30 rounded-xl shadow-2xl p-5 z-30">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-bold text-indigo-400 flex items-center gap-2">
          <GraduationCap size={20} /> Guided Lesson
        </h3>
        <button onClick={closeWizard} className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors">
          <X size={16} />
        </button>
      </div>
      
      {/* Progress Dots */}
      <div className="flex gap-1 mb-4">
        {steps.map((_, i) => (
          <div key={i} className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${i <= step ? 'bg-indigo-500' : 'bg-slate-700'}`} />
        ))}
      </div>

      <div className="mb-6">
        <p className="text-[10px] text-indigo-400/60 uppercase tracking-wider font-semibold mb-1">Step {step + 1} of {steps.length}</p>
        <h4 className="text-white font-semibold text-sm mb-1.5">{steps[step].title}</h4>
        <p className="text-slate-400 text-xs leading-relaxed">{steps[step].desc}</p>
      </div>

      <div className="flex justify-between items-center">
        <button 
          onClick={() => {
              if (step > 0) {
                  const prev = step - 1;
                  setStep(prev);
                  steps[prev].action();
              }
          }} 
          disabled={step === 0}
          className="text-xs text-slate-400 disabled:opacity-30 hover:text-white px-3 py-1.5 rounded-md hover:bg-slate-800 transition-colors"
        >
          Previous
        </button>
        <button 
          onClick={step === steps.length - 1 ? closeWizard : handleNext}
          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4 py-2 rounded-lg font-semibold flex items-center gap-1.5 transition-colors shadow-md"
        >
          {step === steps.length - 1 ? <><Check size={14}/> Finish</> : <>Next <ArrowRight size={14}/></>}
        </button>
      </div>
    </div>
  );
};
