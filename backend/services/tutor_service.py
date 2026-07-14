"""
circuit_vision/tutor.py — AI Circuit Tutor Agent

Provides pedagogical explanations to ECE students based on the
circuit topology and simulation data using Gemini structured outputs.
"""

import json
import logging
import httpx
import os
from google import genai
from google.genai import types
from circuit_vision.config import OLLAMA_BASE_URL, OLLAMA_TEXT_MODEL, OLLAMA_TUTOR_SYSTEM_PROMPT

from schemas.domain import TutorRequest, TutorResponse, CircuitGraph, SimulationResponse, ComponentEducationalDetails, SuggestedQuestionsResponse, CircuitAnalysis

logger = logging.getLogger(__name__)

class CircuitTutor:
    """Agentic orchestrator for the Circuit Tutor."""
    
    def __init__(self, request: TutorRequest):
        self.request = request
        self.ollama_url = f"{OLLAMA_BASE_URL}/api/chat"
        self.model_name = OLLAMA_TEXT_MODEL
        
    def _build_circuit_context(self) -> str:
        """Compress the CircuitGraph into a textual description."""
        cg = self.request.circuit
        knowledge = self.request.knowledge
        
        context = []
        context.append(f"Circuit Diagram contains {cg.component_count} components and {len(cg.nodes)} electrical nodes.")
        
        # List components
        context.append("Components:")
        for comp in cg.components:
            val = f" ({comp.value})" if comp.value else ""
            lbl = f" [{comp.label}]" if comp.label else ""
            context.append(f"- ID: {comp.id} | Type: {comp.type}{lbl}{val}")
            
        # List electrical nodes and their connections
        context.append("\nElectrical Nodes (Connections):")
        for node in cg.nodes:
            lbl = f" ({node.label})" if node.label else ""
            pins = ", ".join(node.connected_pins)
            context.append(f"- Node {node.id}{lbl} connects: {pins}")
            
        if knowledge:
            # Check if it's a dict (from API payload) or object
            if isinstance(knowledge, dict):
                eqs = knowledge.get('equations', [])
                groupings = knowledge.get('grouping', {})
            else:
                eqs = getattr(knowledge, 'equations', [])
                groupings = getattr(knowledge, 'grouping', None)
                if groupings:
                    groupings = {"series_groups": groupings.series_groups, "parallel_groups": groupings.parallel_groups}
            
            context.append("\n=== DETERMINISTIC CIRCUIT KNOWLEDGE ===")
            if groupings:
                series = groupings.get('series_groups', [])
                parallel = groupings.get('parallel_groups', [])
                if series:
                    context.append(f"Series Groups: {series}")
                if parallel:
                    context.append(f"Parallel Groups: {parallel}")
            
            context.append("Algebraic Equations (KVL & KCL):")
            for eq in eqs:
                # Handle dict or object
                if isinstance(eq, dict):
                    context.append(f"- {eq.get('type')} at {eq.get('related_id')}: {eq.get('rendered_string')}")
                else:
                    context.append(f"- {eq.type} at {eq.related_id}: {eq.rendered_string}")
        
        return "\n".join(context)
        
    def _build_simulation_context(self) -> str:
        """Summarize simulation results for the prompt."""
        sim = self.request.simulation_data
        if not sim:
            return "No simulation data provided. The user has not run a simulation yet."
            
        context = []
        context.append(f"Simulation Analysis Type: {sim.analysis_type.upper()}")
        
        if sim.analysis_type == 'dc':
            context.append("DC Steady-State Voltages:")
            for node, vals in sim.nodes.items():
                if vals:
                    context.append(f"- Node {node}: {vals[0]:.3f} V")
            context.append("DC Branch Currents:")
            for branch, currents in sim.branch_currents.items():
                if currents:
                    context.append(f"- Branch {branch}: {currents[0]:.3e} A")
                    
        elif sim.analysis_type == 'transient':
            if not sim.time:
                return "Simulation failed to produce time steps."
            t_max = sim.time[-1]
            context.append(f"Transient Analysis (from 0 to {t_max:.3e} s):")
            for node, vals in sim.nodes.items():
                if vals:
                    v_start = vals[0]
                    v_end = vals[-1]
                    v_min = min(vals)
                    v_max = max(vals)
                    context.append(f"- Node {node}: Starts at {v_start:.3f}V, Ends at {v_end:.3f}V (Min: {v_min:.3f}V, Max: {v_max:.3f}V)")
                    
        elif sim.analysis_type == 'ac':
            context.append("AC Sweep Analysis:")
            for node, vals in sim.nodes.items():
                if vals:
                    v_min = min(vals)
                    v_max = max(vals)
                    context.append(f"- Node {node} Magnitude: Min {v_min:.3f}, Max {v_max:.3f}")
                    
        return "\n".join(context)
        
    async def generate_response(self) -> TutorResponse:
        """Call Ollama to generate the pedagogical response."""
        
        circuit_context = self._build_circuit_context()
        sim_context = self._build_simulation_context()
        expertise = self.request.expertise_level
        
        system_prompt = OLLAMA_TUTOR_SYSTEM_PROMPT + f"\n\n=== CIRCUIT TOPOLOGY ===\n{circuit_context}\n\n=== SIMULATION DATA ===\n{sim_context}"

        # Build prompt for Gemini API
        prompt = system_prompt + "\n\n=== CHAT HISTORY ===\n"
        for msg in self.request.chat_history:
            role = 'Tutor' if msg.role == 'assistant' else 'Student'
            prompt += f"{role}: {msg.content}\n"
            
        prompt += f"\nStudent: {self.request.query}\nTutor:"
        
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json"
                )
            )
            text = response.text.strip()
            
            if text.startswith('```json'):
                text = text.strip()[7:-3].strip()
            elif text.startswith('```'):
                text = text.strip()[3:-3].strip()
                
            resp_data = json.loads(text, strict=False)
            
            # Map the new prompt's schema to the existing TutorResponse
            message = resp_data.get("message", "No message provided.")
            
            # Handle both formats in case the model returns the old or new one
            highlight_raw = resp_data.get("highlight", [])
            highlight_elements = resp_data.get("highlight_elements", [])
            
            for h in highlight_raw:
                if isinstance(h, str):
                    if h.startswith("node_"):
                        highlight_elements.append({"type": "node", "id": h})
                    else:
                        highlight_elements.append({"type": "component", "id": h})
            
            # Add equation to message if provided
            eq = resp_data.get("equation", "")
            if eq:
                message += f"\n\n**Equation:** $${eq}$$"
                
            return TutorResponse(
                message=message,
                highlight_elements=highlight_elements,
                highlight_components=[],
                quiz=None
            )
            
        except Exception as e:
            logger.error(f"Tutor generation failed: {e}", exc_info=True)
            # Fallback error response
            return TutorResponse(
                message=f"I encountered an error trying to analyze that: {str(e)}\n\nPlease try asking again.",
                highlight_components=[],
                highlight_elements=[],
                quiz=None
            )

    async def get_component_metadata(self, comp_id: str, comp_type: str, analysis: CircuitAnalysis) -> ComponentEducationalDetails:
        """Fetch educational metadata for a specific component in the context of the circuit."""
        system_prompt = f"""
You are an Electrical Engineering Tutor.
The student clicked on component `{comp_id}` (Type: `{comp_type}`).
The circuit is a {analysis.difficulty} {analysis.circuit_type}.

Provide educational details about this component. Keep descriptions concise.
Return strictly as JSON matching this schema:
{{
    "name": "Component Name",
    "purpose": "General purpose of this component type",
    "function_in_circuit": "Specific role in this {analysis.circuit_type}",
    "related_equations": ["Eq 1", "Eq 2"],
    "common_mistakes": ["Mistake 1", "Mistake 2"]
}}
"""
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=[system_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            text = response.text.strip()

            if text.startswith('```json'): text = text[7:-3].strip()
            elif text.startswith('```'): text = text[3:-3].strip()
            
            return ComponentEducationalDetails(**json.loads(text, strict=False))
        except Exception as e:
            logger.error(f"Failed to generate component metadata: {e}")
            return ComponentEducationalDetails(
                name=comp_type.capitalize(),
                purpose="An electrical component.",
                function_in_circuit="Part of the circuit topology.",
                related_equations=[],
                common_mistakes=["Ensure connections are correct."]
            )

    async def generate_suggested_questions(self, analysis: CircuitAnalysis) -> SuggestedQuestionsResponse:
        """Generate leading questions based on the deterministic circuit analysis."""
        system_prompt = f"""
You are an Electrical Engineering Tutor. 
The student has just uploaded a {analysis.difficulty} {analysis.circuit_type}.
It has {analysis.component_count} components, {analysis.loop_count} loops, and {analysis.node_count} nodes.
Applicable laws: {', '.join(analysis.applicable_laws)}.

Generate 3 to 4 insightful questions the student might want to ask you to explore and understand this specific circuit better.
The questions should guide them to learn concepts rather than just giving answers.
Return strictly as JSON matching this schema:
{{
    "questions": ["Question 1?", "Question 2?", "Question 3?"]
}}
"""
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=[system_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            text = response.text.strip()

            if text.startswith('```json'): text = text[7:-3].strip()
            elif text.startswith('```'): text = text[3:-3].strip()
            
            return SuggestedQuestionsResponse(**json.loads(text, strict=False))
        except Exception as e:
            logger.error(f"Failed to generate suggested questions: {e}")
            return SuggestedQuestionsResponse(questions=["What does this circuit do?", "Can you explain the current flow?"])
