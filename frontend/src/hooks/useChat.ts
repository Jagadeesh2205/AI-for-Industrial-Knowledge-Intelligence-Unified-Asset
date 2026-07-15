import { useState, useCallback, useRef, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace('http', 'ws');
const HISTORY_KEY = 'plant_brain_chat_history';
const MAX_SESSIONS = 50;

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: any[];
  responseTimeMs?: number;
}

export interface ChatSession {
  id: string;
  title: string;         // first user message (truncated)
  agent: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}

function serializeSessions(sessions: ChatSession[]): string {
  return JSON.stringify(sessions.map(s => ({
    ...s,
    messages: s.messages.map(m => ({
      ...m,
      timestamp: m.timestamp.toISOString(),
    })),
    createdAt: s.createdAt.toISOString(),
    updatedAt: s.updatedAt.toISOString(),
  })));
}

function deserializeSessions(raw: string): ChatSession[] {
  try {
    const parsed = JSON.parse(raw);
    return parsed.map((s: any) => ({
      ...s,
      messages: s.messages.map((m: any) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      })),
      createdAt: new Date(s.createdAt),
      updatedAt: new Date(s.updatedAt),
    }));
  } catch {
    return [];
  }
}

function loadSessionsFromStorage(): ChatSession[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? deserializeSessions(raw) : [];
  } catch {
    return [];
  }
}

function saveSessionsToStorage(sessions: ChatSession[]) {
  try {
    localStorage.setItem(HISTORY_KEY, serializeSessions(sessions));
  } catch {
    // Storage full or unavailable
  }
}

export function useChat(externalSessionId?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStream, setCurrentStream] = useState('');
  const [responseTime, setResponseTime] = useState(0);
  const [sessions, setSessions] = useState<ChatSession[]>(loadSessionsFromStorage);
  const [currentAgent, setCurrentAgent] = useState('copilot');
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef('');
  const sessionIdRef = useRef(externalSessionId || crypto.randomUUID());
  const messagesRef = useRef<ChatMessage[]>([]);

  // Keep messagesRef in sync with state
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const connectWs = useCallback(() => {
    const sid = sessionIdRef.current;
    const ws = new WebSocket(`${WS_BASE}/ws/chat/${sid}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'token') {
        streamRef.current += data.content;
        setCurrentStream(streamRef.current);
      } else if (data.type === 'done') {
        const finalContent = streamRef.current;
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: finalContent,
          timestamp: new Date(),
          responseTimeMs: data.response_time_ms,
        };
        setMessages((prev) => {
          const updated = [...prev, assistantMsg];
          // Persist session after AI responds
          persistSession(updated);
          return updated;
        });
        setResponseTime(data.response_time_ms || 0);
        setCurrentStream('');
        streamRef.current = '';
        setIsStreaming(false);
      } else if (data.type === 'error') {
        const errMsg: ChatMessage = {
          role: 'assistant',
          content: `⚠️ ${data.content}`,
          timestamp: new Date(),
        };
        setMessages((prev) => {
          const updated = [...prev, errMsg];
          persistSession(updated);
          return updated;
        });
        setCurrentStream('');
        streamRef.current = '';
        setIsStreaming(false);
      }
    };

    ws.onerror = () => {
      console.log('WebSocket error — falling back to REST API');
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    wsRef.current = ws;
    return ws;
  }, []);

  const persistSession = useCallback((msgs: ChatMessage[]) => {
    if (msgs.length === 0) return;
    const firstUserMsg = msgs.find(m => m.role === 'user');
    if (!firstUserMsg) return;

    const title = firstUserMsg.content.length > 60
      ? firstUserMsg.content.substring(0, 60) + '…'
      : firstUserMsg.content;

    const now = new Date();
    const sessionId = sessionIdRef.current;

    setSessions(prev => {
      const existingIdx = prev.findIndex(s => s.id === sessionId);
      const session: ChatSession = {
        id: sessionId,
        title,
        agent: currentAgent,
        messages: msgs,
        createdAt: existingIdx >= 0 ? prev[existingIdx].createdAt : now,
        updatedAt: now,
      };

      let updated: ChatSession[];
      if (existingIdx >= 0) {
        updated = [...prev];
        updated[existingIdx] = session;
      } else {
        updated = [session, ...prev];
      }

      // Trim to max sessions
      if (updated.length > MAX_SESSIONS) {
        updated = updated.slice(0, MAX_SESSIONS);
      }

      saveSessionsToStorage(updated);
      return updated;
    });
  }, [currentAgent]);

  const sendMessage = useCallback(
    async (query: string, agent: string = 'copilot', fieldMode: boolean = false) => {
      setCurrentAgent(agent);

      const userMsg: ChatMessage = { role: 'user', content: query, timestamp: new Date() };
      setMessages((prev) => [...prev, userMsg]);

      setIsStreaming(true);
      streamRef.current = '';
      setCurrentStream('');

      // Try WebSocket first
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({ query, agent, field_mode: fieldMode })
        );
        return;
      }

      // Try to connect WebSocket
      try {
        const ws = connectWs();
        await new Promise<void>((resolve, reject) => {
          ws.onopen = () => {
            ws.send(JSON.stringify({ query, agent, field_mode: fieldMode }));
            resolve();
          };
          ws.onerror = () => reject();
          setTimeout(reject, 3000);
        });
      } catch {
        // Fallback to REST
        try {
          const resp = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, agent, field_mode: fieldMode }),
          });
          const data = await resp.json();
          const assistantMsg: ChatMessage = {
            role: 'assistant',
            content: data.answer,
            timestamp: new Date(),
            sources: data.sources,
            responseTimeMs: data.response_time_ms,
          };
          setMessages((prev) => {
            const updated = [...prev, assistantMsg];
            persistSession(updated);
            return updated;
          });
          setResponseTime(data.response_time_ms || 0);
        } catch (err) {
          const errMsg: ChatMessage = {
            role: 'assistant',
            content: '⚠️ Unable to connect to the server. Make sure the backend is running on port 8000.',
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errMsg]);
        }
        setIsStreaming(false);
      }
    },
    [connectWs, persistSession]
  );

  const startNewChat = useCallback(() => {
    // Save current session if it has messages
    if (messagesRef.current.length > 0) {
      persistSession(messagesRef.current);
    }
    // Reset to new session
    sessionIdRef.current = crypto.randomUUID();
    setMessages([]);
    setCurrentStream('');
    streamRef.current = '';
    setIsStreaming(false);
    wsRef.current?.close();
    wsRef.current = null;
  }, [persistSession]);

  const loadSession = useCallback((session: ChatSession) => {
    // Save current session first
    if (messagesRef.current.length > 0) {
      persistSession(messagesRef.current);
    }
    sessionIdRef.current = session.id;
    setMessages(session.messages);
    setCurrentAgent(session.agent);
    wsRef.current?.close();
    wsRef.current = null;
  }, [persistSession]);

  const clearHistory = useCallback(() => {
    setSessions([]);
    localStorage.removeItem(HISTORY_KEY);
  }, []);

  const deleteSession = useCallback((sessionId: string) => {
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== sessionId);
      saveSessionsToStorage(updated);
      return updated;
    });
  }, []);

  // Cleanup
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return {
    messages,
    currentStream,
    isStreaming,
    responseTime,
    sessions,
    sendMessage,
    startNewChat,
    loadSession,
    clearHistory,
    deleteSession,
    clearMessages: startNewChat,
  };
}
