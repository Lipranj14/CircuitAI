import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Sparkles, Lightbulb, BookOpen, Cpu, Activity, Code, ArrowRight } from 'lucide-react';
import { useStore } from '../store/useStore';
import { apiClient } from '../api';

export const TutorChatPanel: React.FC = () => {
  const { 
    chatHistory, 
    addChatMessage, 
    circuitJson, 
    simulationData, 
    isTutorTyping, 
    setIsTutorTyping,
    setHighlightedElements,
    analysisData,
    suggestedQuestions,
    setSuggestedQuestions
  } = useStore();
  
  const [query, setQuery] = useState('');
  const [expertise, setExpertise] = useState('intermediate');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, isTutorTyping, suggestedQuestions]);

  useEffect(() => {
    if (!analysisData || suggestedQuestions.length > 0) return;

    const fetchQuestions = async () => {
      try {
        const data = await apiClient.getSuggestedQuestions({ analysis: analysisData });
        if (data.success && data.data && data.data.questions) {
          setSuggestedQuestions(data.data.questions);
        }
      } catch (err) {
        console.error("Failed to fetch suggested questions:", err);
        // Provide fallback questions so the panel is never empty
        setSuggestedQuestions([
          'What type of circuit is this?',
          'Explain the role of each component.',
          'Which laws apply to this circuit?'
        ]);
      }
    };

    fetchQuestions();
  }, [analysisData, suggestedQuestions.length, setSuggestedQuestions]);

  const handleSubmit = async (e: React.FormEvent | string) => {
    if (typeof e !== 'string') e.preventDefault();
    const userMsg = typeof e === 'string' ? e : query;
    if (!userMsg.trim() || !circuitJson) return;

    setQuery('');
    addChatMessage({ role: 'user', content: userMsg });
    setIsTutorTyping(true);
    setSuggestedQuestions([]);

    try {
      const payload = {
        query: userMsg,
        chat_history: chatHistory,
        expertise_level: expertise,
        circuit: circuitJson,
        knowledge: analysisData,
        simulation_data: simulationData
      };
      
      const response = await apiClient.tutorChat(payload);
      const data = response.data || response;
      
      if (data.message) {
        const msg: any = { role: 'assistant', content: data.message };
        if (data.quiz) msg.quiz = data.quiz;
        addChatMessage(msg);
      }
      
      if (data.highlight_elements && data.highlight_elements.length > 0) {
        setHighlightedElements(data.highlight_elements);
      } else if (data.highlight_components && data.highlight_components.length > 0) {
        setHighlightedElements(data.highlight_components.map((id: string) => ({ type: 'component', id })));
      } else {
        setHighlightedElements([]);
      }

    } catch (err) {
      console.error(err);
      addChatMessage({ role: 'assistant', content: 'I couldn\'t connect to the server right now. Please check that the backend is running and try again.' });
    } finally {
      setIsTutorTyping(false);
    }
  };

  // Build a mini circuit summary for the tutor panel
  const circuitType = analysisData?.circuit_type;
  const componentCount = analysisData?.component_count ?? circuitJson?.components?.length;
  const nodeCount = analysisData?.node_count;
  const loopCount = analysisData?.loop_count;

  return (
    <div className="flex flex-col h-full bg-[var(--nixt-dark)]/80 backdrop-blur-3xl border-l border-[var(--nixt-border)] w-[360px] text-white shadow-2xl relative overflow-hidden z-20">
      {/* Premium Header */}
      <div className="px-6 py-5 border-b border-[var(--nixt-border)] flex justify-between items-center z-10">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-[14px] bg-[var(--nixt-card)] border border-[var(--nixt-border)] shadow-lg">
            <Sparkles className="text-[var(--nixt-glow)] w-5 h-5" />
          </div>
          <div>
            <h2 className="text-[16px] font-bold tracking-wide text-white mb-0.5">Circuit AI</h2>
            <div className="text-[10px] text-emerald-400 font-medium flex items-center gap-1 mt-0.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Online
            </div>
          </div>
        </div>
        <select 
          className="bg-white/5 hover:bg-white/10 text-xs px-2.5 py-1.5 rounded-lg text-slate-300 border border-white/5 transition-all outline-none cursor-pointer focus:ring-2 focus:ring-purple-500/50"
          value={expertise}
          onChange={(e) => setExpertise(e.target.value)}
        >
          <option value="beginner" className="bg-slate-900">Beginner</option>
          <option value="intermediate" className="bg-slate-900">Intermediate</option>
          <option value="advanced" className="bg-slate-900">Advanced</option>
        </select>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide z-10 relative">
        {/* Empty state: show circuit summary + suggested questions when available */}
        {chatHistory.length === 0 && (
          <div className="animate-fade-in-up">
            {analysisData ? (
              <div className="space-y-6">
                <div className="relative overflow-hidden bg-[var(--nixt-card)] border border-[var(--nixt-border)] rounded-[24px] p-6 shadow-xl group hover:border-[var(--nixt-glow)]/50 transition-all duration-500">
                  <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                    <Cpu size={64} />
                  </div>
                  <div className="flex items-center gap-2 mb-5 relative z-10">
                    <div className="p-2 bg-[var(--nixt-glow)]/10 rounded-[10px] border border-[var(--nixt-glow)]/20">
                      <BookOpen size={16} className="text-[var(--nixt-glow)]" />
                    </div>
                    <span className="text-[11px] font-bold text-[var(--nixt-text-dim)] uppercase tracking-widest">Context Loaded</span>
                  </div>
                  {circuitType && (
                    <p className="text-[15px] text-white font-bold mb-4 leading-relaxed relative z-10">{circuitType}</p>
                  )}
                  <div className="flex gap-4 text-[12px] font-bold text-[var(--nixt-text-dim)] relative z-10 uppercase tracking-widest">
                    {componentCount != null && (
                      <span className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-cyan-400"></div>{componentCount} components</span>
                    )}
                    {nodeCount != null && (
                      <span className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-purple-400"></div>{nodeCount} nodes</span>
                    )}
                  </div>
                </div>

                <p className="text-[13px] text-[var(--nixt-text-dim)] text-center font-bold tracking-wide">
                  Ask me anything about this circuit design.
                </p>

                {/* Centered Search Bar for Empty State */}
                <div className="w-full mt-6">
                  <form onSubmit={handleSubmit} className="relative group w-full shadow-2xl">
                    <input
                      type="text"
                      className="w-full bg-[#1C1A24] text-white px-5 py-4.5 pr-14 rounded-[20px] border border-[var(--nixt-border)] focus:outline-none focus:border-[var(--nixt-glow)] focus:ring-1 focus:ring-[var(--nixt-glow)] transition-all text-[14.5px] placeholder-[var(--nixt-text-dim)] shadow-inner"
                      placeholder={circuitJson ? "Ask Circuit AI..." : "Upload a circuit first..."}
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      disabled={!circuitJson || isTutorTyping}
                      autoFocus
                    />
                    <button 
                      type="submit" 
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 bg-[var(--nixt-glow)] text-[var(--nixt-dark)] hover:bg-white p-2.5 rounded-[14px] disabled:opacity-30 disabled:grayscale transition-all shadow-lg group-focus-within:scale-105"
                      disabled={!query.trim() || !circuitJson || isTutorTyping}
                    >
                      <Send size={18} className="ml-0.5 font-bold" />
                    </button>
                  </form>
                </div>
              </div>
            ) : (
              <div className="text-center text-[var(--nixt-text-dim)] mt-12 flex flex-col items-center">
                <div className="w-20 h-20 bg-[var(--nixt-card)] rounded-[24px] flex items-center justify-center mb-6 shadow-inner border border-[var(--nixt-border)]">
                  <Lightbulb size={32} className="text-[var(--nixt-glow)]/50" />
                </div>
                <p className="font-bold text-white text-[16px]">I'm your AI Assistant!</p>
                <p className="text-[13px] mt-2 text-[var(--nixt-text-dim)] max-w-[200px] font-medium leading-relaxed">Upload a circuit diagram or paste a netlist to begin.</p>
              </div>
            )}
          </div>
        )}
        
        {chatHistory.map((msg, index) => (
          <div key={index} className={`flex gap-3 animate-fade-in-up ${msg.role === 'user' ? 'flex-row-reverse' : ''}`} style={{ animationDelay: `${index * 50}ms` }}>
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-lg border border-[var(--nixt-border)] ${
              msg.role === 'user' 
                ? 'bg-[var(--nixt-glow)]/10 text-[var(--nixt-glow)]' 
                : 'bg-[var(--nixt-card)] text-white'
            }`}>
              {msg.role === 'user' ? <User size={16} /> : <Sparkles size={16} />}
            </div>
            <div className={`p-4 max-w-[80%] whitespace-pre-wrap text-[14px] leading-relaxed shadow-lg border ${
              msg.role === 'user' 
                ? 'bg-[#1C1A24] border-[var(--nixt-border)] text-white rounded-[20px] rounded-tr-[4px]' 
                : 'bg-[var(--nixt-card)] border-[var(--nixt-border)] text-white rounded-[20px] rounded-tl-[4px]'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        
        {isTutorTyping && (
          <div className="flex gap-3 animate-fade-in-up">
            <div className="w-9 h-9 rounded-xl bg-[var(--nixt-card)] flex items-center justify-center shrink-0 shadow-lg border border-[var(--nixt-border)]">
              <Sparkles size={16} className="text-[var(--nixt-glow)]" />
            </div>
            <div className="p-4 bg-[var(--nixt-card)] border border-[var(--nixt-border)] text-white text-sm rounded-[20px] rounded-tl-[4px] flex items-center gap-1.5 backdrop-blur-md">
              <div className="w-1.5 h-1.5 rounded-full bg-[var(--nixt-glow)] animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-1.5 h-1.5 rounded-full bg-[var(--nixt-glow)] animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-1.5 h-1.5 rounded-full bg-[var(--nixt-glow)] animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        )}
        
        {/* Suggested questions */}
        {!isTutorTyping && suggestedQuestions.length > 0 && chatHistory.length === 0 && (
          <div className="space-y-3 animate-fade-in-up delay-300">
            <p className="text-[11px] text-[var(--nixt-text-dim)] font-bold uppercase tracking-widest pl-1 mb-2">Suggested prompts</p>
            {suggestedQuestions.map((q, idx) => (
              <button 
                key={idx}
                onClick={() => handleSubmit(q)}
                className="w-full text-left p-4 bg-[#1C1A24] hover:bg-[#252230] border border-[var(--nixt-border)] hover:border-[var(--nixt-glow)]/50 rounded-[16px] text-[13.5px] text-white transition-all duration-300 hover:translate-x-1 shadow-md flex items-center justify-between group font-medium"
              >
                <span>{q}</span>
                <ArrowRight size={16} className="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all text-[var(--nixt-glow)]" />
              </button>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} className="h-4" />
      </div>

      {chatHistory.length > 0 && (
        <div className="p-6 border-t border-[var(--nixt-border)] bg-[var(--nixt-dark)]/90 backdrop-blur-xl z-10 animate-fade-in-up">
          <form onSubmit={handleSubmit} className="relative group">
            <input
              type="text"
              className="w-full bg-[#1C1A24] text-white px-5 py-4 pr-14 rounded-[20px] border border-[var(--nixt-border)] focus:outline-none focus:border-[var(--nixt-glow)] focus:ring-1 focus:ring-[var(--nixt-glow)] transition-all text-[14px] placeholder-[var(--nixt-text-dim)] shadow-inner"
              placeholder={circuitJson ? "Message Circuit AI..." : "Upload a circuit first..."}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={!circuitJson || isTutorTyping}
              autoFocus
            />
            <button 
              type="submit" 
              className="absolute right-2.5 top-1/2 -translate-y-1/2 bg-[var(--nixt-glow)] text-[var(--nixt-dark)] hover:bg-white p-2.5 rounded-[14px] disabled:opacity-30 disabled:grayscale transition-all shadow-lg group-focus-within:scale-105"
              disabled={!query.trim() || !circuitJson || isTutorTyping}
            >
              <Send size={18} className="ml-0.5 font-bold" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
