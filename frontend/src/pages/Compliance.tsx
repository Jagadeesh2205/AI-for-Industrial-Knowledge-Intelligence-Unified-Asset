import { useState } from 'react';
import { useChat } from '../hooks/useChat';

const REGULATIONS = [
  { code: 'OISD-116', title: 'Fire Protection for Petroleum Installations', status: 'amber' },
  { code: 'OISD-105', title: 'Work Permit System', status: 'green' },
  { code: 'Factory Act 1948', title: 'Machinery Safety Requirements', status: 'green' },
  { code: 'IS-2148', title: 'Flameproof Enclosures', status: 'amber' },
];

export default function Compliance() {
  const [selectedReg, setSelectedReg] = useState('');
  const [scope, setScope] = useState('');
  const { messages, currentStream, isStreaming, sendMessage } = useChat();

  const handleCheck = () => {
    const query = selectedReg
      ? `Check compliance with ${selectedReg} for ${scope || 'all equipment in Unit-3'}. Identify gaps and required actions.`
      : 'Provide a general compliance overview for all tracked regulations.';
    sendMessage(query, 'compliance');
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Compliance Analysis</h1>
        <p className="page-subtitle">
          Regulatory Gap Detection · OISD · PESO · Factory Act · IS Standards
        </p>
      </div>

      {/* Compliance Matrix Overview */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: 'var(--text-primary)' }}>
          📋 Regulation Compliance Matrix
        </h3>
        <table className="compliance-table">
          <thead>
            <tr>
              <th>Regulation Code</th>
              <th>Title</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {REGULATIONS.map((reg) => (
              <tr key={reg.code}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {reg.code}
                </td>
                <td>{reg.title}</td>
                <td>
                  <span className={`status-badge ${reg.status}`}>
                    {reg.status === 'green' ? '🟢 Compliant' :
                     reg.status === 'amber' ? '🟡 Review Needed' :
                     '🔴 Non-Compliant'}
                  </span>
                </td>
                <td>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                    onClick={() => {
                      setSelectedReg(reg.code);
                      sendMessage(
                        `Detailed compliance check for ${reg.code}. Identify all gaps and required corrective actions for Unit-3 equipment.`,
                        'compliance'
                      );
                    }}
                  >
                    Analyze
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Custom Compliance Query */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: 'var(--text-secondary)' }}>
          Custom Compliance Check
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: '12px', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Regulation
            </label>
            <input
              type="text"
              value={selectedReg}
              onChange={(e) => setSelectedReg(e.target.value)}
              placeholder="e.g., OISD-116"
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
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Scope
            </label>
            <input
              type="text"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              placeholder="e.g., storage tanks in Unit-3"
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
          <button
            className="btn btn-primary"
            onClick={handleCheck}
            disabled={isStreaming}
          >
            {isStreaming ? '⏳' : '🔍'} Check
          </button>
        </div>
      </div>

      {/* Compliance Analysis Results */}
      {messages.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: 'var(--text-primary)' }}>
            📊 Compliance Analysis Results
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
              dangerouslySetInnerHTML={{
                __html: msg.content
                  .replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;')
                  .replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--accent-primary-light)">$1</strong>')
                  .replace(/🟢/g, '<span style="color:#10B981">🟢</span>')
                  .replace(/🟡/g, '<span style="color:#F59E0B">🟡</span>')
                  .replace(/🔴/g, '<span style="color:#EF4444">🔴</span>')
                  .replace(
                    /\[(?:Source|SOURCE):([^\]]+)\]/g,
                    '<span style="display:inline-block;background:rgba(59,130,246,0.1);padding:2px 8px;border-radius:12px;font-size:11px;color:var(--accent-primary-light)">📄 $1</span>'
                  )
                  .replace(/\n/g, '<br/>')
              }}
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
              dangerouslySetInnerHTML={{
                __html: currentStream
                  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                  .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\n/g, '<br/>')
              }}
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
