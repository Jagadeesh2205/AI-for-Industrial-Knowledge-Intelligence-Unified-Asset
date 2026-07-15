import { useState, useCallback, useRef, useEffect } from 'react';
import { useGraph } from '../hooks/useData';

const NODE_COLORS: Record<string, string> = {
  Equipment: '#F59E0B',
  Document: '#3B82F6',
  Person: '#8B5CF6',
  Event: '#6B7890',
  Parameter: '#06B6D4',
  Regulation: '#00D4B8',
  FailureMode: '#EF4444',
  Unknown: '#3E4C5E',
};

const NODE_ICONS: Record<string, string> = {
  Equipment: '⚙️',
  Document: '📄',
  Person: '👤',
  Event: '📅',
  Parameter: '📊',
  Regulation: '📋',
  FailureMode: '⚠️',
};

export default function KnowledgeGraph() {
  const { graphData, stats, loading, selectedNode, setSelectedNode, fetchGraph } = useGraph();
  const [filter, setFilter] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const canvasRef = useRef<HTMLDivElement>(null);
  const [GraphComponent, setGraphComponent] = useState<any>(null);

  // Dynamically import react-force-graph-2d
  useEffect(() => {
    import('react-force-graph-2d').then((mod) => {
      setGraphComponent(() => mod.default);
    }).catch(() => {
      console.log('react-force-graph-2d not available');
    });
  }, []);

  // Filter nodes and links
  const filteredData = {
    nodes: graphData.nodes.filter((node) => {
      if (filter && node.type !== filter) return false;
      if (searchTerm) {
        const label = (node.label || '').toLowerCase();
        const id = (node.id || '').toLowerCase();
        return label.includes(searchTerm.toLowerCase()) || id.includes(searchTerm.toLowerCase());
      }
      return true;
    }),
    links: graphData.links.filter((link) => {
      const filteredNodeIds = new Set(
        graphData.nodes
          .filter((node) => {
            if (filter && node.type !== filter) return false;
            if (searchTerm) {
              const label = (node.label || '').toLowerCase();
              return label.includes(searchTerm.toLowerCase());
            }
            return true;
          })
          .map((n) => n.id)
      );
      return filteredNodeIds.has(link.source?.id || link.source) && filteredNodeIds.has(link.target?.id || link.target);
    }),
  };

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
  }, [setSelectedNode]);

  const nodeTypes = Object.keys(NODE_COLORS);

  return (
    <div className="page-container" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h1 className="page-title">Knowledge Graph</h1>
          <p className="page-subtitle">
            {graphData.nodes.length} nodes · {graphData.links.length} relationships
          </p>
        </div>
        <button className="btn btn-secondary" onClick={fetchGraph}>
          ↻ Refresh
        </button>
      </div>

      <div className="graph-container" ref={canvasRef}>
        {/* Controls */}
        <div className="graph-controls">
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-steel)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 14px',
              color: 'var(--text-primary)',
              fontSize: '13px',
              width: '200px',
              outline: 'none',
              fontFamily: 'var(--font-sans)',
            }}
          />
          <div className="filter-bar" style={{ marginBottom: 0 }}>
            <button
              className={`filter-chip ${!filter ? 'active' : ''}`}
              onClick={() => setFilter(null)}
            >
              All
            </button>
            {nodeTypes.map((type) => (
              <button
                key={type}
                className={`filter-chip ${filter === type ? 'active' : ''}`}
                onClick={() => setFilter(filter === type ? null : type)}
                style={{
                  borderColor: filter === type ? NODE_COLORS[type] : undefined,
                  color: filter === type ? NODE_COLORS[type] : undefined,
                }}
              >
                {NODE_ICONS[type] || '●'} {type}
              </button>
            ))}
          </div>
        </div>

        {/* Graph Visualization */}
        {GraphComponent && filteredData.nodes.length > 0 ? (
          <GraphComponent
            graphData={filteredData}
            nodeLabel="label"
            nodeColor={(node: any) => NODE_COLORS[node.type] || '#9CA3AF'}
            nodeRelSize={6}
            nodeVal={(node: any) => {
              // Size by number of connections
              const connections = filteredData.links.filter(
                (l: any) => (l.source?.id || l.source) === node.id || (l.target?.id || l.target) === node.id
              ).length;
              return Math.max(2, connections + 1);
            }}
            linkColor={() => 'rgba(148, 163, 184, 0.2)'}
            linkWidth={1.5}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            linkLabel={(link: any) => link.relation}
            onNodeClick={handleNodeClick}
            backgroundColor="#0a0e1a"
            width={canvasRef.current?.clientWidth || 800}
            height={canvasRef.current?.clientHeight || 600}
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const label = node.label || '';
              const fontSize = Math.max(10 / globalScale, 3);
              const nodeSize = Math.max(4, (node.val || 3));
              
              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x!, node.y!, nodeSize, 0, 2 * Math.PI);
              ctx.fillStyle = NODE_COLORS[node.type] || '#9CA3AF';
              ctx.fill();
              
              // Glow effect
              ctx.shadowColor = NODE_COLORS[node.type] || '#9CA3AF';
              ctx.shadowBlur = 8;
              ctx.fill();
              ctx.shadowBlur = 0;
              
              // Draw label
              if (globalScale > 0.5) {
                ctx.font = `${fontSize}px Inter, sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillStyle = '#f1f5f9';
                ctx.fillText(label.substring(0, 20), node.x!, node.y! + nodeSize + 2);
              }
            }}
          />
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">🔗</div>
            <div className="empty-state-title">
              {loading ? 'Loading graph...' : 'No Graph Data'}
            </div>
            <div className="empty-state-text">
              Upload and index documents to build the knowledge graph.
              The graph shows relationships between equipment, documents,
              events, and regulations.
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="graph-legend">
          {nodeTypes.map((type) => (
            <div key={type} className="graph-legend-item">
              <div
                className="graph-legend-dot"
                style={{ backgroundColor: NODE_COLORS[type] }}
              />
              <span>{type}</span>
              <span style={{ marginLeft: 'auto', fontWeight: 600 }}>
                {stats?.node_types?.[type] || 0}
              </span>
            </div>
          ))}
        </div>

        {/* Node Info Panel */}
        {selectedNode && (
          <div className="graph-info-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>
                {NODE_ICONS[selectedNode.type]} {selectedNode.label}
              </h3>
              <button
                onClick={() => setSelectedNode(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '18px' }}
              >
                ✕
              </button>
            </div>
            <div style={{ fontSize: '13px' }}>
              <div style={{ color: 'var(--text-muted)', marginBottom: '12px' }}>
                <span className="doc-tag">{selectedNode.type}</span>
              </div>
              {Object.entries(selectedNode)
                .filter(([key]) => !['id', 'x', 'y', 'vx', 'vy', 'fx', 'fy', 'index', '__indexColor', 'color', 'icon', 'val'].includes(key))
                .map(([key, value]) => (
                  <div key={key} style={{ marginBottom: '8px' }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>{key}:</span>
                    <div style={{ color: 'var(--text-primary)' }}>{String(value)}</div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
