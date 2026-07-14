const API_BASE_URL = 'http://localhost:8001/api';

export const apiClient = {
  analyzeCircuitV2: async (formData: FormData) => {
    const response = await fetch(`${API_BASE_URL}/v1/pipeline/analyze`, {
      method: 'POST',
      body: formData,
    });
    const res = await response.json();
    return { status: res.success ? 'success' : 'error', error: res.error || res.message, ...res.data };
  },

  analyzeNetlist: async (netlist: string) => {
    const response = await fetch(`${API_BASE_URL}/v1/pipeline/analyze-netlist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ netlist }),
    });
    const res = await response.json();
    return { status: res.success ? 'success' : 'error', ...res.data };
  },

  validateCircuit: async (circuitJson: any) => {
    const response = await fetch(`${API_BASE_URL}/v1/pipeline/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(circuitJson),
    });
    const res = await response.json();
    return res.data;
  },

  simulateV2: async (payload: any) => {
    const response = await fetch(`${API_BASE_URL}/v1/pipeline/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const res = await response.json();
    return res.success ? { success: true, data: res.data } : { success: false, ...res };
  },

  tutorChat: async (payload: any) => {
    const response = await fetch(`${API_BASE_URL}/v1/tutor/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const res = await response.json();
    return res;
  },

  getSuggestedQuestions: async (payload: any) => {
    const response = await fetch(`${API_BASE_URL}/v1/tutor/suggested-questions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return response.json();
  },

  getComponentMetadata: async (payload: any) => {
    const response = await fetch(`${API_BASE_URL}/v1/tutor/component-metadata`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return response.json();
  }
};
