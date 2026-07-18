import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import { Hexagon, Activity, Database, Server, Clock } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';


export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<any>(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [qqText, setQqText] = useState('');
  const [qqResult, setQqResult] = useState('');
  const [qqLoading, setQqLoading] = useState(false);
  const [feed, setFeed] = useState<string[]>([]);
  const feedEndRef = useRef<HTMLDivElement>(null);

  // Animated counters
  const [kpiDocs, setKpiDocs] = useState(0);
  const [kpiNodes, setKpiNodes] = useState(0);
  const kpiQueries = 127;
  const kpiCompliance = 72;

  const equipmentStatus = [
    { tag: 'P-101', status: 'critical', desc: 'Vibration Trip' },
    { tag: 'V-201', status: 'warn', desc: 'CUI Found' },
    { tag: 'M-101', status: 'warn', desc: 'Temp High' },
    { tag: 'P-102', status: 'safe', desc: 'Running' },
    { tag: 'C-201', status: 'safe', desc: 'Running' },
    { tag: 'HX-301', status: 'safe', desc: 'Online' },
    { tag: 'V-110', status: 'critical', desc: 'Expired Insp' },
  ];

  const terminalMessages = [
    "SYS_INIT: Connecting to ChromaDB... OK",
    "SYS_INIT: Loading Graph Store... OK",
    "[EVENT] Operator queried P-101 maintenance history",
    "[WARN] High vibration detected on P-101 (7.2 mm/s)",
    "[ALERT] V-110 inspection certificate expired",
    "[INGEST] Processed 5 new documents",
    "[GRAPH] Extracted 47 new relationships",
    "[EVENT] Shift handover completed",
    "[QUERY] Compliance matrix for Unit 3 generated",
    "[WARN] M-101 Phase W temp asymmetric",
    "[SYSTEM] Automated DB backup completed",
  ];

  useEffect(() => {
    // Fetch stats
    fetch(`${API_BASE}/api/stats`)
      .then(res => res.json())
      .then(data => {
        setStats(data);
        animateValue(setKpiDocs, 0, data.graph_store?.node_types?.Document || 0, 1000);
        animateValue(setKpiNodes, 0, data.graph_store?.total_nodes || 0, 1000);
      });

    // Fetch graph preview
    fetch(`${API_BASE}/api/graph`)
      .then(res => res.json())
      .then(data => {
        // Just take a subset for preview
        const previewNodes = data.graph.nodes.slice(0, 50);
        const nodeIds = new Set(previewNodes.map((n: any) => n.id));
        const previewLinks = data.graph.links.filter((l: any) => 
          nodeIds.has(l.source) && nodeIds.has(l.target)
        );
        setGraphData({ nodes: previewNodes, links: previewLinks });
      });

    // Terminal feed generator
    let msgIdx = 0;
    setFeed([terminalMessages[0], terminalMessages[1]]);
    msgIdx = 2;
    
    const interval = setInterval(() => {
      setFeed(prev => {
        const next = [...prev, terminalMessages[msgIdx % terminalMessages.length]];
        if (next.length > 20) return next.slice(next.length - 20);
        return next;
      });
      msgIdx++;
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [feed]);

  const animateValue = (setter: any, start: number, end: number, duration: number) => {
    if (start === end) return setter(end);
    let startTimestamp: number | null = null;
    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // easeOutExpo
      const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setter(Math.floor(easeProgress * (end - start) + start));
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  };

  const handleQuickQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qqText.trim()) return;
    
    setQqLoading(true);
    setQqResult("Processing query...");
    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: qqText, agent: 'copilot' })
      });
      const data = await res.json();
      setQqResult(data.answer);
    } catch (err) {
      setQqResult("Error processing query.");
    } finally {
      setQqLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-void)' }}>
      
      {/* Top Bar */}
      <div className="terminal-topbar">
        <div className="terminal-title">
          <Hexagon size={24} color="var(--accent-teal)" />
          OPERATIONS BRAIN // UNIT 3
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <div className="live-dot"></div>
            LIVE
          </div>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--accent-teal)', color: 'var(--accent-teal)', padding: '4px 8px', borderRadius: '4px', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
            LLM: {stats?.llm_provider || 'READY'}
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-code">[DO: DOCUMENTS]</div>
          <div className="kpi-value">{kpiDocs}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-code">[GN: GRAPH NODES]</div>
          <div className="kpi-value">{kpiNodes}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-code">[QR: QUERIES TODAY]</div>
          <div className="kpi-value">{kpiQueries}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-code">[CM: COMPLIANCE]</div>
          <div className="kpi-value" style={{ color: 'var(--status-warn)' }}>{kpiCompliance}%</div>
        </div>
      </div>

      {/* Main Content */}
      <div className="dash-main">
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <div className="panel" style={{ height: '350px' }}>
            <div className="panel-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} />
                KNOWLEDGE GRAPH PREVIEW
              </div>
              <button onClick={() => navigate('/graph')} style={{ background: 'none', border: 'none', color: 'var(--accent-teal)', cursor: 'pointer', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                VIEW FULL →
              </button>
            </div>
            <div style={{ flex: 1, background: 'var(--bg-void)', position: 'relative' }}>
              <ForceGraph2D
                graphData={graphData}
                width={800} // Will overflow hidden nicely
                height={300}
                nodeColor={(node: any) => {
                  const typeColors: Record<string, string> = {
                    'Equipment': '#F59E0B',
                    'Document': '#3B82F6',
                    'FailureMode': '#EF4444',
                    'Regulation': '#00D4B8'
                  };
                  return typeColors[node.group] || '#6B7890';
                }}
                nodeRelSize={6}
                linkColor={() => '#252B35'}
                backgroundColor="#0A0C0F"
                enableZoomInteraction={false}
              />
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              EQUIPMENT STATUS GRID
            </div>
            <div className="status-grid">
              {equipmentStatus.map(eq => (
                <div key={eq.tag} className={`status-chip ${eq.status}`}>
                  <div className="dot"></div>
                  {eq.tag}: {eq.desc}
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <div className="panel">
            <div className="panel-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Server size={16} />
                LIVE ACTIVITY TERMINAL
              </div>
            </div>
            <div className="terminal-feed">
              {feed.map((msg, i) => (
                <div key={i} className="terminal-entry">
                  &gt; {msg}
                </div>
              ))}
              <div ref={feedEndRef} />
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              QUICK QUERY
            </div>
            <div className="quick-query">
              <form onSubmit={handleQuickQuery}>
                <input 
                  type="text" 
                  className="qq-input"
                  placeholder="Ask a question about the facility..."
                  value={qqText}
                  onChange={e => setQqText(e.target.value)}
                  disabled={qqLoading}
                />
              </form>
              {qqResult && (
                <div style={{ 
                  background: 'var(--bg-void)', 
                  padding: '12px', 
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '13px',
                  color: 'var(--text-secondary)',
                  maxHeight: '120px',
                  overflowY: 'auto'
                }}>
                  {qqLoading ? '...' : qqResult.length > 150 ? qqResult.substring(0, 150) + '...' : qqResult}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Bottom Status Bar */}
      <div style={{ marginTop: 'auto' }}>
        <div className="status-bar">
          <div>VERSION 1.0.0 // OISD-116 COMPLIANT</div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Database size={12} />
              VECTOR: {stats?.vector_store?.total_chunks || 0}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Hexagon size={12} />
              GRAPH: {stats?.graph_store?.total_edges || 0} E
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--status-safe)' }}>
              <Clock size={12} />
              SYSTEM NORMAL
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
