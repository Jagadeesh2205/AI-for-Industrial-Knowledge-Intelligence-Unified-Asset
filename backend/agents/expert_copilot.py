"""
Expert Copilot Agent — Primary Q&A agent for industrial knowledge.

Handles 80% of user interactions. Answers operational, maintenance,
and engineering queries with citations and follow-up suggestions.
"""

from backend.agents.base_agent import BaseAgent
from backend.retrieval.hybrid_retriever import HybridRetriever
from typing import AsyncGenerator


EXPERT_COPILOT_SYSTEM = """You are the Expert Industrial Knowledge Copilot for a facility's operations and maintenance team.

Your knowledge comes exclusively from the facility's own documents:
- Maintenance work orders and repair records
- Standard Operating Procedures (SOPs)
- Inspection reports and NDT findings
- OEM equipment manuals
- Regulatory compliance documents
- Incident and near-miss reports

ANSWERING RULES:
1. Every factual claim must cite its source document, type, page, and date.
   Format: [Source: {title} | {type} | Page {n}]
2. If documents conflict, explicitly flag the conflict and list both sources.
3. If the answer isn't in the documents, say: "This specific information isn't in the available documentation. I recommend consulting the appropriate expert or source."
4. For safety-critical questions, always prepend: ⚠️ SAFETY NOTE: Verify with current PTW and qualified personnel before proceeding.
5. End every response with 2-3 suggested follow-up questions prefixed with 💡

RESPONSE FORMAT:
- Field technician queries: Brief, numbered steps, no jargon
- Engineering queries: Detailed, technical, with referenced parameters
- Compliance queries: Gap/compliance status first, then supporting evidence

Keep responses well-structured with headers, bullet points, and clear sections."""


class ExpertCopilot(BaseAgent):
    """Primary Q&A agent for general industrial knowledge queries."""

    def __init__(self, retriever: HybridRetriever):
        super().__init__()
        self.retriever = retriever
        self.system_prompt = EXPERT_COPILOT_SYSTEM

    async def answer(self, query: str, chat_history: list = None,
                     field_mode: bool = False) -> AsyncGenerator[str, None]:
        """
        Answer a query with streaming response.
        
        Args:
            query: User's question
            chat_history: Previous messages in this session
            field_mode: If True, use simplified response format
        """
        # Retrieve context
        retrieval_result = self.retriever.retrieve(query, top_k=8)
        context = self.retriever.format_context_for_llm(retrieval_result["chunks"])
        
        # Adjust system prompt for field mode
        system_prompt = self.system_prompt
        if field_mode:
            system_prompt += "\n\nFIELD MODE ACTIVE: Keep answer under 200 words. Use numbered steps. No technical jargon. Prioritize actionable instructions."
        
        # Stream response
        async for token in self.stream_response(query, context, system_prompt, chat_history):
            yield token

    async def answer_complete(self, query: str, chat_history: list = None,
                               field_mode: bool = False) -> dict:
        """
        Get a complete response (non-streaming) with metadata.
        """
        retrieval_result = self.retriever.retrieve(query, top_k=8)
        context = self.retriever.format_context_for_llm(retrieval_result["chunks"])
        
        system_prompt = self.system_prompt
        if field_mode:
            system_prompt += "\n\nFIELD MODE: Concise, numbered steps, no jargon."
        
        response = await self.generate_response(query, context, system_prompt, chat_history)
        
        # Extract citations from response
        import re
        citations = re.findall(r'\[(?:Source|SOURCE):([^\]]+)\]', response)
        
        return {
            "answer": response,
            "citations": citations,
            "sources": [
                {
                    "doc_id": chunk.doc_id,
                    "doc_type": chunk.doc_type,
                    "page_num": chunk.page_num,
                    "relevance": chunk.relevance_score,
                    "source_label": chunk.source_label,
                }
                for chunk in retrieval_result["chunks"]
                if chunk.doc_id != "graph"
            ],
            "intent": {
                "type": retrieval_result["intent"].type,
                "entities": retrieval_result["intent"].entities,
            },
            "total_sources": retrieval_result["total_sources"],
        }
