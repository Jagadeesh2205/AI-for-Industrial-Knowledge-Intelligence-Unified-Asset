"""
Base Agent — Shared LLM client infrastructure for all AI agents.

Supports multiple LLM providers: Gemini, OpenAI, Anthropic, Mock.
Provides streaming response generation and citation formatting.
"""

import json
import os
from typing import AsyncGenerator, Optional
from backend.config import (
    LLM_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY,
    AZURE_FOUNDRY_ENDPOINT, AZURE_FOUNDRY_KEY, AZURE_FOUNDRY_MODEL, LLM_MODELS
)


class BaseAgent:
    """
    Base class for all AI agents.
    Handles LLM provider selection, streaming, and response formatting.
    """

    BASE_CITATION_INSTRUCTION = """
    For every factual claim in your answer, append a citation in this format:
    [SOURCE: Document Title | Type | Page X]
    
    Never make claims that aren't supported by the provided context.
    If the context doesn't contain the answer, say so explicitly.
    Always end with 2-3 follow-up questions the user might want to ask next.
    """

    def __init__(self):
        self.provider = LLM_PROVIDER
        self._client = None

    def _get_client(self):
        """Lazy-initialize LLM client based on provider."""
        if self._client is not None:
            return self._client

        if self.provider == "gemini":
            try:
                from google import genai
                api_key = os.getenv("GEMINI_API_KEY", "")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY environment variable is not set")
                # New google-genai SDK — client created per-request in _stream_gemini
                self._client = True  # marker that gemini is available
                print(f"[Agent] Gemini provider ready (model={LLM_MODELS['gemini']})")
            except Exception as e:
                print(f"[Agent] Gemini init error: {e}. Falling back to mock.")
                self.provider = "mock"
                
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"OpenAI init error: {e}. Falling back to mock.")
                self.provider = "mock"
                
        elif self.provider == "anthropic":
            try:
                # pyrefly: ignore [missing-import]
                from anthropic import Anthropic
                self._client = Anthropic(api_key=ANTHROPIC_API_KEY)
            except Exception as e:
                print(f"Anthropic init error: {e}. Falling back to mock.")
                self.provider = "mock"
                
        elif self.provider == "openrouter":
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY
                )
            except Exception as e:
                print(f"OpenRouter init error: {e}. Falling back to mock.")
                self.provider = "mock"

        elif self.provider == "azure_foundry":
            try:
                from openai import OpenAI
                endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT", AZURE_FOUNDRY_ENDPOINT) or "https://inteligentapi.services.ai.azure.com/api/projects/proj-default/openai/v1"
                if endpoint.endswith("/responses"):
                    endpoint = endpoint[:-len("/responses")]
                api_key = os.getenv("AZURE_FOUNDRY_KEY", AZURE_FOUNDRY_KEY)
                if not api_key:
                    print("[Agent] AZURE_FOUNDRY_KEY is missing.")
                    return None
                self._client = OpenAI(
                    base_url=endpoint,
                    api_key=api_key
                )
                print(f"[Agent] Azure Foundry ready (model={LLM_MODELS['azure_foundry']})")
            except Exception as e:
                print(f"Azure Foundry init error: {e}.")
                return None

        return self._client

    async def generate_response(self, query: str, context: str, 
                                 system_prompt: str, chat_history: list = None) -> str:
        """
        Generate a complete (non-streaming) response.
        """
        full_response = ""
        async for token in self.stream_response(query, context, system_prompt, chat_history):
            full_response += token
        return full_response

    async def stream_response(self, query: str, context: str,
                               system_prompt: str, 
                               chat_history: list = None) -> AsyncGenerator[str, None]:
        """
        Async generator for streaming LLM responses.
        Yields tokens as they arrive.
        """
        messages = self._build_messages(query, context, system_prompt, chat_history)

        if self.provider == "gemini":
            async for token in self._stream_gemini(messages, system_prompt):
                yield token
        elif self.provider == "openai":
            async for token in self._stream_openai(messages, system_prompt):
                yield token
        elif self.provider == "anthropic":
            async for token in self._stream_anthropic(messages, system_prompt):
                yield token
        elif self.provider == "openrouter":
            async for token in self._stream_openrouter(messages, system_prompt):
                yield token
        elif self.provider == "azure_foundry":
            async for token in self._stream_azure_foundry(messages, system_prompt):
                yield token
        else:
            # Mock provider — generate a helpful demo response
            async for token in self._stream_mock(query, context):
                yield token

    def _build_messages(self, query: str, context: str, 
                        system_prompt: str, chat_history: list = None) -> list[dict]:
        """Build message list for LLM."""
        messages = []
        
        # Add chat history if available
        if chat_history:
            for msg in chat_history[-6:]:  # Last 6 messages
                messages.append(msg)
        
        # Build the user message with context
        user_message = f"""Based on the following knowledge base context, answer the user's question.

CONTEXT:
{context}

USER QUESTION:
{query}

Remember to cite sources for every factual claim using the format shown in the context labels."""

        messages.append({"role": "user", "content": user_message})
        return messages

    async def _stream_gemini(self, messages: list, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Gemini using new google-genai SDK."""
        import asyncio
        import queue
        import threading
        try:
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                yield ("⚠️ **Gemini API key not configured.**\n\n"
                       "Please set `GEMINI_API_KEY` in your Render environment variables "
                       "and redeploy the backend.")
                return

            from google import genai
            from google.genai import types

            # Build history (all but last message)
            history = []
            for msg in messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

            last_msg = messages[-1]["content"]

            # Use a queue to bridge sync iteration → async yield
            token_queue: queue.Queue = queue.Queue()
            SENTINEL = object()

            def run_stream():
                import time
                # Primary model first; fall back when it's overloaded
                models_to_try = [LLM_MODELS["gemini"], "gemini-1.5-flash-latest", "gemini-1.5-pro"]
                MAX_ATTEMPTS = 4
                attempt = 0
                model_idx = 0
                while attempt < MAX_ATTEMPTS:
                    model = models_to_try[min(model_idx, len(models_to_try) - 1)]
                    emitted = False
                    try:
                        client = genai.Client(api_key=api_key)
                        chat = client.chats.create(
                            model=model,
                            history=history,
                            config=types.GenerateContentConfig(
                                system_instruction=system_prompt,
                                max_output_tokens=8192,
                                temperature=0.3,
                            ),
                        )
                        stream = chat.send_message_stream(last_msg)
                        for chunk in stream:
                            if chunk.text:
                                emitted = True
                                token_queue.put(chunk.text)
                        break
                    except Exception as exc:
                        msg = str(exc)
                        retryable = any(s in msg for s in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "DEADLINE", "404", "NOT_FOUND"))
                        # Only retry if nothing was streamed yet — otherwise the
                        # user would see the answer restart mid-response
                        if retryable and not emitted and attempt < MAX_ATTEMPTS - 1:
                            print(f"[Agent] {model} attempt {attempt + 1}/{MAX_ATTEMPTS} failed ({msg[:100]})")
                            model_idx += 1  # next attempt uses the fallback model
                            attempt += 1
                            time.sleep(2)
                            continue
                        token_queue.put(f"\n\n⚠️ LLM Error: {exc}\n\nPlease try again in a moment.")
                        break
                token_queue.put(SENTINEL)

            thread = threading.Thread(target=run_stream, daemon=True)
            thread.start()

            loop = asyncio.get_event_loop()
            while True:
                token = await loop.run_in_executor(None, token_queue.get)
                if token is SENTINEL:
                    break
                yield token

        except Exception as e:
            yield f"\n\n⚠️ LLM Error: {str(e)}\n\nPlease check your API key configuration."


    async def _stream_openai(self, messages: list, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI."""
        try:
            client = self._get_client()
            if not client:
                async for token in self._stream_mock(messages[-1]["content"], ""):
                    yield token
                return

            all_messages = [{"role": "system", "content": system_prompt}] + messages
            
            stream = client.chat.completions.create(
                model=LLM_MODELS["openai"],
                messages=all_messages,
                stream=True,
                max_completion_tokens=2048,
                temperature=0.3,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n⚠️ LLM Error: {str(e)}"

    async def _stream_anthropic(self, messages: list, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Anthropic."""
        try:
            client = self._get_client()
            if not client:
                async for token in self._stream_mock(messages[-1]["content"], ""):
                    yield token
                return

            with client.messages.stream(
                model=LLM_MODELS["anthropic"],
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            yield f"\n\n⚠️ LLM Error: {str(e)}"

    async def _stream_mock(self, query: str, context: str) -> AsyncGenerator[str, None]:
        """
        Mock response generator for demo without API keys.
        Generates intelligent responses based on context and query.
        """
        import asyncio
        
        # Parse the context to extract useful info
        has_context = bool(context and len(context) > 50)
        
        if has_context:
            # Generate a response that references the context
            response = self._generate_mock_from_context(query, context)
        else:
            response = (
                "📋 **No documents have been indexed yet.**\n\n"
                "To get started:\n"
                "1. Upload industrial documents through the Documents page\n"
                "2. Wait for the ingestion pipeline to process them\n"
                "3. Then ask me questions about your facility's equipment, "
                "maintenance history, and procedures.\n\n"
                "**Example questions I can answer:**\n"
                "- \"What maintenance was done on P-101?\"\n"
                "- \"What are the failure modes for centrifugal pumps?\"\n"
                "- \"Are we compliant with OISD-116?\"\n\n"
                "💡 *Suggested follow-up:*\n"
                "1. What documents should I upload first?\n"
                "2. How does the knowledge graph work?\n"
                "3. What types of queries can you answer?"
            )
        
        # Stream token by token with realistic delay
        words = response.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.02)  # 20ms per word ≈ natural reading speed

    def _generate_mock_from_context(self, query: str, context: str) -> str:
        """Generate a mock response that references actual context."""
        import re
        
        # Extract source labels from context
        sources = re.findall(r'\[SOURCE:([^\]]+)\]', context)
        source_citations = [f"[SOURCE:{s}]" for s in sources[:3]]
        
        # Extract equipment tags
        equipment_tags = re.findall(r'\b[A-Z]{1,4}-\d{3,4}[A-Z]?\b', context)
        unique_tags = list(set(equipment_tags))[:3]
        
        # Extract first few meaningful sentences from context
        sentences = [s.strip() for s in context.split('.') if len(s.strip()) > 30][:5]
        
        response_parts = [
            f"Based on the available documentation, here is what I found:\n\n"
        ]
        
        if unique_tags:
            response_parts.append(f"**Equipment Referenced:** {', '.join(unique_tags)}\n\n")
        
        if sentences:
            response_parts.append("**Key Findings:**\n")
            for i, sent in enumerate(sentences[:3], 1):
                citation = source_citations[i-1] if i <= len(source_citations) else ""
                response_parts.append(f"{i}. {sent.strip()}. {citation}\n")
            response_parts.append("\n")
        
        if source_citations:
            response_parts.append(f"**Sources Consulted:** {len(sources)} document(s)\n\n")
        
        response_parts.append(
            "💡 *Suggested follow-up questions:*\n"
            "1. Can you provide more details about the maintenance history?\n"
            "2. What are the recommended corrective actions?\n"
            "3. Are there similar incidents documented for other equipment?"
        )
        
        return "".join(response_parts)

    async def _stream_openrouter(self, messages: list, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from OpenRouter."""
        try:
            client = self._get_client()
            if not client:
                async for token in self._stream_mock(messages[-1]["content"], ""):
                    yield token
                return

            all_messages = [{"role": "system", "content": system_prompt}] + messages
            
            stream = client.chat.completions.create(
                model=LLM_MODELS["openrouter"],
                messages=all_messages,
                stream=True,
                max_completion_tokens=2048,
                temperature=0.3,
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n⚠️ LLM Error: {str(e)}"

    async def _stream_azure_foundry(self, messages: list, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Azure AI Foundry."""
        try:
            api_key = os.getenv("AZURE_FOUNDRY_KEY", AZURE_FOUNDRY_KEY)
            if not api_key:
                yield ("⚠️ **Azure Foundry API key not configured.**\n\n"
                       "Please add `AZURE_FOUNDRY_KEY` to your Azure App Service environment variables and restart.")
                return

            client = self._get_client()
            if not client:
                yield ("⚠️ **Azure Foundry connection failed.**\n\n"
                       "Please check `AZURE_FOUNDRY_ENDPOINT` and `AZURE_FOUNDRY_KEY` in Azure portal.")
                return

            all_messages = [{"role": "system", "content": system_prompt}] + messages
            
            stream = client.chat.completions.create(
                model=LLM_MODELS["azure_foundry"],
                messages=all_messages,
                stream=True,
                max_completion_tokens=2048,
                temperature=0.3,
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n⚠️ LLM Error: {str(e)}"
