import type { StateCreator } from 'zustand';
import type { StoreState, TutorStore } from './types';

export const createTutorSlice: StateCreator<StoreState, [], [], TutorStore> = (set) => ({
  chatHistory: [],
  addChatMessage: (msg) => set((state) => ({ chatHistory: [...state.chatHistory, msg] })),
  clearChat: () => set({ chatHistory: [], highlightedElements: [] }),
  
  isTutorTyping: false,
  setIsTutorTyping: (typing) => set({ isTutorTyping: typing }),
  
  learningMode: true,
  setLearningMode: (mode) => set({ learningMode: mode }),
  
  suggestedQuestions: [],
  setSuggestedQuestions: (qs) => set({ suggestedQuestions: qs }),
  
  componentMetadata: {},
  setComponentMetadata: (id, metadata) => set((state) => ({
      componentMetadata: { ...state.componentMetadata, [id]: metadata }
  })),
});
