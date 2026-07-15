import { useState } from 'react';
import { useChat } from '../hooks/useChat';

export default function Maintenance() {
  const [equipmentTag, setEquipmentTag] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const { messages, currentStream, isStreaming, sendMessage } = useChat();

  const handleAnalyze = () => {
    if (!equipmentTag.trim()) return;
    const query = symptoms
      ? `Equipment ${equipmentTag}: ${symptoms}. Perform root cause analysis.`
      : `Show maintenance history and analysis for equipment ${equipmentTag}`;
    sendMessage(query, 'maintenance');
  };

  const QUICK_ANALYSES = [
    { tag: 'P-101', symptom: 'High vibration (7.2 mm/s) and bearing temperature 78°C' },
    { tag: 'C-201', symptom: 'Bearing noise detected during routine inspection' },
    { tag: 'HX-301', symptom: 'Reduced heat transfer efficiency, minor flange leak' },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Maintenance RCA</h1>
        <p className="page-subtitle">
          Root Cause Analysis · Equipment History · Failure Pattern Detection
        </p>
      </div>

      {/* Input Form */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: 'var(--text-primary)' }}>
          🔧 Equipment Analysis Request
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Equipment Tag
            </label>
            <input
              type="text"
              value={equipmentTag}
              onChange={(e) => setEquipmentTag(e.target.value.toUpperCase())}
              placeholder="e.g., P-101"
              style={{
                width: '100%',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                outline: 'none',
                fontFamily: 'var(--font-mono)',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Symptoms / Observations
            </label>
            <input
              type="text"
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              placeholder="e.g., High vibration, unusual noise, elevated temperature"
              style={{
                width: '100%',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                outline: 'none',
                fontFamily: 'var(--font-sans)',
              }}
            />
          </div>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleAnalyze}
          disabled={isStreaming || !equipmentTag.trim()}
          style={{ marginTop: '16px' }}
        >
          {isStreaming ? '⏳ Analyzing...' : '🔍 Run RCA Analysis'}
        </button>
      </div>

      {/* Quick Analysis */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: 'var(--text-secondary)' }}>
          Quick Analysis Scenarios
        </h3>
        <div className="suggestions">
          {QUICK_ANALYSES.map((qa, i) => (
            <button
              key={i}
              className="suggestion-chip"
              onClick={() => {
                setEquipmentTag(qa.tag);
                setSymptoms(qa.symptom);
                sendMessage(
                  `Equipment ${qa.tag}: ${qa.symptom}. Perform root cause analysis.`,
                  'maintenance'
                );
              }}
            >
              ⚙️ {qa.tag}: {qa.symptom.substring(0, 40)}...
            </button>
          ))}
        </div>
      </div>

      {/* Analysis Results */}
      {messages.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: 'var(--text-primary)' }}>
            📊 Analysis Results
          </h3>
          {messages.filter(m => m.role === 'assistant').map((msg, i) => (
            <div key={i} style={{
              padding: '16px',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              marginBottom: '12px',
              fontSize: '14px',
              lineHeight: 1.7,
              color: 'var(--text-primary)',
            }}
              dangerouslySetInnerHTML={{ __html: formatRCA(msg.content) }}
            />
          ))}
          {currentStream && (
            <div style={{
              padding: '16px',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              fontSize: '14px',
              lineHeight: 1.7,
              color: 'var(--text-primary)',
            }}
              dangerouslySetInnerHTML={{ __html: formatRCA(currentStream) }}
            />
          )}
          {isStreaming && !currentStream && (
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatRCA(text: string): string {
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--accent-primary-light)">$1</strong>');
  html = html.replace(/^### (.+)$/gm, '<h3 style="margin:12px 0 8px;font-size:15px">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 style="margin:16px 0 8px;font-size:17px">$1</h2>');
  html = html.replace(
    /\[(?:Source|SOURCE):([^\]]+)\]/g,
    '<span style="display:inline-block;background:rgba(59,130,246,0.1);padding:2px 8px;border-radius:12px;font-size:11px;color:var(--accent-primary-light)">📄 $1</span>'
  );
  html = html.replace(/\n/g, '<br/>');
  return html;
}
