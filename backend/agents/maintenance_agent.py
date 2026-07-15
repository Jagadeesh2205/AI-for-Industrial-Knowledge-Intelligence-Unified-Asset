"""
Maintenance RCA Agent — Root Cause Analysis for equipment failures.

Specialized in:
- 5-Why method analysis
- Ishikawa (fishbone) framework
- Cross-equipment failure pattern detection
- OEM manual failure mode cross-referencing
"""

from backend.agents.base_agent import BaseAgent
from backend.retrieval.hybrid_retriever import HybridRetriever
from typing import AsyncGenerator


MAINTENANCE_AGENT_SYSTEM = """You are a Root Cause Analysis (RCA) specialist for industrial equipment maintenance.

Your role is to analyze equipment failures systematically using proven methodologies:
- 5-Why Method: Drill down to the root cause through 5 levels of "why"
- Ishikawa Framework: Consider Man, Machine, Material, Method, Measurement, Environment

When analyzing equipment issues:

1. HISTORY REVIEW: Review the complete maintenance history for the equipment
2. PATTERN IDENTIFICATION: Identify patterns in previous failures
   - What failed? When? Under what conditions?
   - Is the interval between failures decreasing? (degradation trend)
3. OEM CROSS-REFERENCE: Compare reported symptoms against OEM manual failure modes
4. SYSTEMATIC ELIMINATION: List all possible causes, then eliminate with evidence
5. RECOMMENDATIONS: Provide specific, actionable recommendations

Your output must include:
- ⚠️ IMMEDIATE ACTIONS: What to do right now
- 🔍 PROBABLE ROOT CAUSES: Probability-ranked list with evidence citations
- 📊 SUPPORTING DATA: Referenced maintenance history, OEM specs, past incidents
- 🛡️ PREVENTIVE MEASURES: Long-term corrective actions
- 🔗 SIMILAR INCIDENTS: Related failures on other equipment

Always cite source documents for every finding.
End with 2-3 follow-up investigation questions."""


class MaintenanceAgent(BaseAgent):
    """Root Cause Analysis agent for equipment maintenance."""

    def __init__(self, retriever: HybridRetriever):
        super().__init__()
        self.retriever = retriever
        self.system_prompt = MAINTENANCE_AGENT_SYSTEM

    async def analyze(self, equipment_tag: str = "", symptoms: str = "",
                      query: str = "", chat_history: list = None) -> AsyncGenerator[str, None]:
        """
        Perform RCA analysis for equipment issues.
        """
        # Build a comprehensive query
        if equipment_tag and symptoms:
            full_query = (f"Equipment {equipment_tag} is showing: {symptoms}. "
                        f"Perform a root cause analysis. {query}")
        else:
            full_query = query or "Provide a general maintenance analysis."
        
        # Retrieve context with focus on maintenance data
        retrieval_result = self.retriever.retrieve(full_query, top_k=10, agent_type="maintenance")
        context = self.retriever.format_context_for_llm(retrieval_result["chunks"])
        
        # Stream response
        async for token in self.stream_response(full_query, context, self.system_prompt, chat_history):
            yield token

    async def analyze_complete(self, equipment_tag: str = "", symptoms: str = "",
                                query: str = "") -> dict:
        """Get complete RCA analysis with metadata."""
        if equipment_tag and symptoms:
            full_query = f"Equipment {equipment_tag}: {symptoms}. Root cause analysis."
        else:
            full_query = query
        
        retrieval_result = self.retriever.retrieve(full_query, top_k=10)
        context = self.retriever.format_context_for_llm(retrieval_result["chunks"])
        
        response = await self.generate_response(full_query, context, self.system_prompt)
        
        import re
        citations = re.findall(r'\[(?:Source|SOURCE):([^\]]+)\]', response)
        
        return {
            "answer": response,
            "equipment_tag": equipment_tag,
            "symptoms": symptoms,
            "citations": citations,
            "sources": [
                {
                    "doc_id": chunk.doc_id,
                    "doc_type": chunk.doc_type,
                    "relevance": chunk.relevance_score,
                }
                for chunk in retrieval_result["chunks"]
            ],
        }
