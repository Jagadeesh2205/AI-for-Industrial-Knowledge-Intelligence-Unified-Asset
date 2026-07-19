"""
Compliance Agent — Regulatory gap detection and compliance analysis.

Supports:
- OISD (Oil Industry Safety Directorate)
- PESO (Petroleum and Explosives Safety Organisation)
- Factory Act 1948
- IS standards (Bureau of Indian Standards)
- Environmental regulations (CPCB)
"""

from backend.agents.base_agent import BaseAgent
from backend.agents.expert_copilot import ExpertCopilot
from backend.retrieval.hybrid_retriever import HybridRetriever
from typing import AsyncGenerator


COMPLIANCE_AGENT_SYSTEM = """You are a Regulatory Compliance Specialist for industrial facilities.

Your role is to analyze compliance against Indian and international safety standards:
- OISD (Oil Industry Safety Directorate) standards
- PESO (Petroleum and Explosives Safety Organisation) regulations
- Factory Act 1948 requirements
- IS (Indian Standards) from Bureau of Indian Standards
- ASME/API international standards
- Environmental regulations (CPCB norms)

COMPLIANCE ANALYSIS FRAMEWORK:

1. REQUIREMENT MAPPING: Identify all applicable regulatory requirements
2. EVIDENCE GATHERING: Find current procedures, inspection records, certifications
3. GAP ANALYSIS: Compare requirements vs. actual compliance evidence
4. STATUS ASSESSMENT: Rate each requirement as:
   - 🟢 GREEN: Fully compliant with documented evidence
   - 🟡 AMBER: Partially compliant or evidence is outdated
   - 🔴 RED: Non-compliant or no evidence found
5. REMEDIATION: Specific actions to close each gap

Output format:
| Requirement | Status | Evidence | Gap | Action Required |
|-------------|--------|----------|-----|-----------------|

Always cite the specific regulation clause and the evidence document.
Highlight any CRITICAL safety gaps with ⚠️ warnings.
End with a compliance summary score and 2-3 recommended next steps."""


class ComplianceAgent(BaseAgent):
    """Regulatory compliance gap detection agent."""

    def __init__(self, retriever: HybridRetriever):
        super().__init__()
        self.retriever = retriever
        self.system_prompt = COMPLIANCE_AGENT_SYSTEM

    async def check_compliance(self, regulation: str = "", scope: str = "",
                                query: str = "",
                                chat_history: list = None,
                                meta_out: dict = None) -> AsyncGenerator[str, None]:
        """
        Run compliance analysis.
        """
        if regulation and scope:
            full_query = (f"Check compliance with {regulation} for {scope}. "
                        f"Identify all gaps and required actions. {query}")
        else:
            full_query = query or "Provide a general compliance overview for the facility."

        retrieval_result = self.retriever.retrieve(full_query, top_k=10, agent_type="compliance")
        context = self.retriever.format_context_for_llm(retrieval_result["chunks"])

        if meta_out is not None:
            meta_out["sources"] = ExpertCopilot._chunks_to_sources(retrieval_result["chunks"])
            meta_out["intent_type"] = retrieval_result["intent"].type
            meta_out["total_sources"] = retrieval_result["total_sources"]

        async for token in self.stream_response(full_query, context, self.system_prompt, chat_history):
            yield token

    async def check_compliance_complete(self, regulation: str = "",
                                         scope: str = "", query: str = "") -> dict:
        """Get complete compliance analysis with metadata."""
        if regulation:
            full_query = f"Compliance check: {regulation} for {scope}."
        else:
            full_query = query or "General compliance overview."
        
        retrieval_result = self.retriever.retrieve(full_query, top_k=10)
        context = self.retriever.format_context_for_llm(retrieval_result["chunks"])
        
        response = await self.generate_response(full_query, context, self.system_prompt)
        
        # Get compliance gaps from graph
        gaps = []
        if regulation:
            gaps = self.retriever.graph.get_compliance_gaps(regulation)
        
        return {
            "answer": response,
            "regulation": regulation,
            "scope": scope,
            "sources": ExpertCopilot._chunks_to_sources(retrieval_result["chunks"]),
            "intent": {
                "type": retrieval_result["intent"].type,
                "entities": retrieval_result["intent"].entities,
            },
            "total_sources": retrieval_result.get("total_sources", 0),
            "compliance_gaps": [
                {
                    "equipment": gap.get("equipment", {}).get("tag", ""),
                    "status": gap.get("status", "UNKNOWN"),
                    "details": gap.get("details", {}),
                }
                for gap in gaps
            ],
        }
