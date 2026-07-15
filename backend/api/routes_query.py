"""
Query Routes — REST endpoint for queries + WebSocket for streaming chat.
"""

import json
import uuid
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    agent: str = "copilot"          # copilot | maintenance | compliance
    session_id: Optional[str] = None
    field_mode: bool = False
    equipment_tag: Optional[str] = None
    symptoms: Optional[str] = None
    regulation: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    citations: list = []
    sources: list = []
    intent_type: str = ""
    entities: list = []
    total_sources: int = 0
    response_time_ms: int = 0
    session_id: str = ""


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Single-shot query endpoint (non-streaming)."""
    from backend.main import get_agents
    
    start_time = time.time()
    agents = get_agents()
    session_id = request.session_id or str(uuid.uuid4())

    try:
        if request.agent == "maintenance":
            result = await agents["maintenance"].analyze_complete(
                equipment_tag=request.equipment_tag or "",
                symptoms=request.symptoms or "",
                query=request.query,
            )
        elif request.agent == "compliance":
            result = await agents["compliance"].check_compliance_complete(
                regulation=request.regulation or "",
                query=request.query,
            )
        else:
            result = await agents["copilot"].answer_complete(
                query=request.query,
                field_mode=request.field_mode,
            )

        elapsed_ms = int((time.time() - start_time) * 1000)

        return QueryResponse(
            answer=result.get("answer", ""),
            citations=result.get("citations", []),
            sources=result.get("sources", []),
            intent_type=result.get("intent", {}).get("type", ""),
            entities=result.get("intent", {}).get("entities", []),
            total_sources=result.get("total_sources", 0),
            response_time_ms=elapsed_ms,
            session_id=session_id,
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return QueryResponse(
            answer=f"⚠️ Error processing query: {str(e)}",
            response_time_ms=elapsed_ms,
            session_id=session_id,
        )


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for streaming chat.
    
    Client sends: {"query": "...", "agent": "...", "field_mode": false}
    Server streams: {"type": "token|done|error", "content": "..."}
    """
    await websocket.accept()

    chat_history = []

    try:
        while True:
            # Receive query
            data = await websocket.receive_text()
            message = json.loads(data)
            
            query = message.get("query", "")
            agent_type = message.get("agent", "copilot")
            field_mode = message.get("field_mode", False)
            
            if not query:
                await websocket.send_json({"type": "error", "content": "Empty query"})
                continue

            from backend.main import get_agents
            agents = get_agents()

            # Stream response
            start_time = time.time()
            full_response = ""

            try:
                if agent_type == "maintenance":
                    stream = agents["maintenance"].analyze(
                        equipment_tag=message.get("equipment_tag", ""),
                        symptoms=message.get("symptoms", ""),
                        query=query,
                        chat_history=chat_history,
                    )
                elif agent_type == "compliance":
                    stream = agents["compliance"].check_compliance(
                        regulation=message.get("regulation", ""),
                        query=query,
                        chat_history=chat_history,
                    )
                else:
                    stream = agents["copilot"].answer(
                        query=query,
                        chat_history=chat_history,
                        field_mode=field_mode,
                    )

                async for token in stream:
                    full_response += token
                    await websocket.send_json({
                        "type": "token",
                        "content": token,
                    })

                elapsed_ms = int((time.time() - start_time) * 1000)
                
                await websocket.send_json({
                    "type": "done",
                    "content": "",
                    "response_time_ms": elapsed_ms,
                })

                # Update chat history
                chat_history.append({"role": "user", "content": query})
                chat_history.append({"role": "assistant", "content": full_response})

                # Keep only last 10 messages
                if len(chat_history) > 10:
                    chat_history = chat_history[-10:]

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Error: {str(e)}",
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
