import { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import type { ChatSession } from '../hooks/useChat';
import { useSearchParams } from 'react-router-dom';

const AGENTS = [
  { id: 'copilot', label: '🤖 Expert Copilot', desc: 'General Q&A' },
  { id: 'maintenance', label: '🔧 Maintenance RCA', desc: 'Root cause analysis' },
  { id: 'compliance', label: '📋 Compliance', desc: 'Regulatory gaps' },
];

const SUGGESTIONS = [
  'What maintenance was done on P-101?',
  'P-101 is vibrating and bearing temp is 78°C. What should I check?',
  'What does the OEM manual say about bearing replacement intervals?',
  'Are we compliant with OISD-116 Section 4.2?',
  'Show me similar failures across other equipment',
  'What is the LOTO procedure for P-101?',
];

const AGENT_COLORS: Record<string, string> = {
  copilot: '#3B82F6',
  maintenance: '#F59E0B',
  compliance: '#22C55E',
};

function formatDate(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function groupSessionsByDate(sessions: ChatSession[]) {
  const groups: { label: string; sessions: ChatSession[] }[] = [];
  const seen = new Set<string>();

  for (const session of sessions) {
    const label = formatDate(session.updatedAt);
    if (!seen.has(label)) {
      seen.add(label);
      groups.push({ label, sessions: [] });
    }
    groups[groups.length - 1].sessions.push(session);
  }
  return groups;
}

export default function Copilot() {
  const [agent, setAgent] = useState('copilot');
  const [input, setInput] = useState('');
  const [fieldMode, setFieldMode] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const {
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
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [searchParams] = useSearchParams();

  // Auto-submit query from URL
  useEffect(() => {
    const q = searchParams.get('q');
    if (q && messages.length === 0) {
      sendMessage(q, agent, fieldMode);
    }
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStream]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    setActiveSessionId(null); // we're in the current live session
    sendMessage(input.trim(), agent, fieldMode);
    setInput('');
  };

  const handleSuggestion = (q: string) => {
    setActiveSessionId(null);
    sendMessage(q, agent, fieldMode);
  };

  const handleNewChat = () => {
    startNewChat();
    setActiveSessionId(null);
    setInput('');
    inputRef.current?.focus();
  };

  const handleLoadSession = (session: ChatSession) => {
    loadSession(session);
    setActiveSessionId(session.id);
    setAgent(session.agent);
  };

  const groups = groupSessionsByDate(sessions);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Top bar */}
      <div className="agent-selector">
        {AGENTS.map((a) => (
          <button
            key={a.id}
            className={`agent-btn ${agent === a.id ? 'active' : ''}`}
            onClick={() => setAgent(a.id)}
            disabled={!!activeSessionId}
          >
            {a.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button
          className={`agent-btn ${fieldMode ? 'active' : ''}`}
          onClick={() => setFieldMode(!fieldMode)}
          title="Field Mode: Concise answers for technicians"
          disabled={!!activeSessionId}
        >
          📱 Field Mode
        </button>
        <button
          className="agent-btn"
          onClick={handleNewChat}
          title="Start a new conversation"
          style={{ borderColor: 'var(--accent-teal)', color: 'var(--accent-teal)' }}
        >
          ✦ New Chat
        </button>
        <button
          className={`agent-btn ${historyOpen ? 'active' : ''}`}
          onClick={() => setHistoryOpen(!historyOpen)}
          title="Toggle chat history"
        >
          🕘 History {sessions.length > 0 && `(${sessions.length})`}
        </button>
      </div>

      {/* Main layout with optional history sidebar */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Chat area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div className="chat-messages" style={{ flex: 1 }}>

            {/* View-only banner when browsing history */}
            {activeSessionId && (
              <div className="history-view-banner">
                <span>📖 Viewing past conversation</span>
                <button className="history-banner-btn" onClick={handleNewChat}>
                  ✦ Start New Chat
                </button>
              </div>
            )}

            {messages.length === 0 && !currentStream && !activeSessionId && (
              <div style={{ margin: 'auto', maxWidth: '600px', textAlign: 'center' }}>
                <div style={{ fontSize: '64px', marginBottom: '16px' }}>🧠</div>
                <h2 style={{
                  fontSize: '24px',
                  fontWeight: 700,
                  background: 'var(--gradient-primary)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  marginBottom: '8px',
                }}>
                  Plant Brain AI Copilot
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
                  Ask me about equipment maintenance, safety procedures,
                  inspection reports, or regulatory compliance.
                </p>
                <div className="suggestions" style={{ justifyContent: 'center' }}>
                  {SUGGESTIONS.map((q, i) => (
                    <button
                      key={i}
                      className="suggestion-chip"
                      onClick={() => handleSuggestion(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.role}`}>
                <div className={`message-avatar ${msg.role === 'assistant' ? 'ai' : 'user-avatar'}`}>
                  {msg.role === 'assistant' ? '🧠' : '👤'}
                </div>
                <div>
                  <div className={`message-content ${msg.role === 'user' ? 'user-msg' : ''}`}
                    dangerouslySetInnerHTML={{
                      __html: msg.role === 'assistant'
                        ? formatMessage(msg.content)
                        : escapeHtml(msg.content),
                    }}
                  />
                  {msg.responseTimeMs && (
                    <div style={{
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                      marginTop: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}>
                      ⚡ {(msg.responseTimeMs / 1000).toFixed(1)}s
                      <span style={{ color: 'var(--accent-secondary)' }}>
                        (manual search avg: 23 min)
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Streaming indicator */}
            {currentStream && (
              <div className="chat-message">
                <div className="message-avatar ai">🧠</div>
                <div className="message-content"
                  dangerouslySetInnerHTML={{ __html: formatMessage(currentStream) }}
                />
              </div>
            )}

            {isStreaming && !currentStream && (
              <div className="chat-message">
                <div className="message-avatar ai">🧠</div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area — disabled when viewing history */}
          {!activeSessionId && (
            <div className="chat-input-area">
              <div className="chat-input-wrapper">
                <input
                  ref={inputRef}
                  type="text"
                  className="chat-input"
                  placeholder={fieldMode
                    ? 'Ask a quick question (Field Mode)...'
                    : 'Ask about equipment, maintenance, procedures, or compliance...'}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  disabled={isStreaming}
                />
                <button
                  className="chat-send-btn"
                  onClick={handleSend}
                  disabled={isStreaming || !input.trim()}
                >
                  ➤
                </button>
              </div>
              {responseTime > 0 && (
                <div style={{
                  fontSize: '12px',
                  color: 'var(--accent-secondary)',
                  marginTop: '8px',
                  textAlign: 'center',
                }}>
                  ⚡ Last response: {(responseTime / 1000).toFixed(1)}s | Manual search avg: 23 minutes | Time saved: ~22.9 minutes
                </div>
              )}
            </div>
          )}
        </div>

        {/* History Sidebar */}
        {historyOpen && (
          <div className="history-panel">
            <div className="history-panel-header">
              <span className="history-panel-title">🕘 Query History</span>
              {sessions.length > 0 && (
                <button
                  className="history-clear-btn"
                  onClick={() => { if (confirm('Clear all chat history?')) clearHistory(); }}
                  title="Clear all history"
                >
                  🗑
                </button>
              )}
            </div>

            <div className="history-panel-body">
              {sessions.length === 0 ? (
                <div className="history-empty">
                  <div style={{ fontSize: '32px', marginBottom: '8px' }}>💬</div>
                  <div>No history yet.</div>
                  <div style={{ fontSize: '12px', marginTop: '4px', color: 'var(--text-muted)' }}>
                    Your conversations will appear here.
                  </div>
                </div>
              ) : (
                groups.map((group) => (
                  <div key={group.label} className="history-group">
                    <div className="history-group-label">{group.label}</div>
                    {group.sessions.map((session) => (
                      <div
                        key={session.id}
                        className={`history-session ${activeSessionId === session.id ? 'active' : ''}`}
                        onClick={() => handleLoadSession(session)}
                      >
                        <div
                          className="history-session-agent-dot"
                          style={{ background: AGENT_COLORS[session.agent] || '#6B7890' }}
                        />
                        <div className="history-session-content">
                          <div className="history-session-title">{session.title}</div>
                          <div className="history-session-meta">
                            <span>{session.messages.filter(m => m.role === 'user').length} queries</span>
                            <span>·</span>
                            <span>{session.agent}</span>
                          </div>
                        </div>
                        <button
                          className="history-session-delete"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(session.id);
                            if (activeSessionId === session.id) {
                              handleNewChat();
                            }
                          }}
                          title="Delete this session"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatMessage(text: string): string {
  let html = escapeHtml(text);
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^- (.+)$/gm, '• $1');
  html = html.replace(/^\d+\. (.+)$/gm, (_, item) => `<span style="color:var(--accent-primary-light)">•</span> ${item}`);
  html = html.replace(
    /\[(?:Source|SOURCE):([^\]]+)\]/g,
    '<span style="display:inline-block;background:rgba(59,130,246,0.1);padding:2px 8px;border-radius:12px;font-size:11px;color:var(--accent-primary-light);margin:2px 0">📄 $1</span>'
  );
  html = html.replace(/⚠️/g, '<span style="color:var(--accent-warning)">⚠️</span>');
  html = html.replace(/\n/g, '<br/>');
  return html;
}
