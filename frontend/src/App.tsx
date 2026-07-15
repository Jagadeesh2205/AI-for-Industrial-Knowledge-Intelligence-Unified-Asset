import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import Copilot from './pages/Copilot';
import KnowledgeGraph from './pages/KnowledgeGraph';
import Documents from './pages/Documents';
import Maintenance from './pages/Maintenance';
import Compliance from './pages/Compliance';
import './index.css';

const navItems = [
  { path: '/', icon: '📊', label: 'Dashboard' },
  { path: '/copilot', icon: '🤖', label: 'AI Copilot' },
  { path: '/graph', icon: '🔗', label: 'Knowledge Graph' },
  { path: '/documents', icon: '📄', label: 'Documents' },
  { path: '/maintenance', icon: '🔧', label: 'Maintenance RCA' },
  { path: '/compliance', icon: '📋', label: 'Compliance' },
];

function Sidebar() {
  const [llmProvider, setLlmProvider] = useState('...');

  useEffect(() => {
    fetch((import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/stats')
      .then((r) => r.json())
      .then((d) => setLlmProvider(d.llm_provider || 'mock'))
      .catch(() => setLlmProvider('offline'));
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">🧠</div>
        <div className="sidebar-brand">
          <span className="sidebar-brand-name">Plant Brain</span>
          <span className="sidebar-brand-sub">Knowledge Intelligence</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Main</div>
        {navItems.slice(0, 4).map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
            end={item.path === '/'}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}

        <div className="nav-section-title">Intelligence</div>
        {navItems.slice(4).map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}

        <div className="nav-section-title">System</div>
        <div className="nav-item" style={{ cursor: 'default', opacity: 0.6 }}>
          <span className="nav-icon">⚡</span>
          <span className="nav-label" style={{ fontSize: '12px' }}>
            LLM: {llmProvider}
          </span>
        </div>
      </nav>
    </aside>
  );
}

function MobileHeader() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      <div className="mobile-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '20px' }}>🧠</span>
          <span style={{ fontWeight: 700, fontSize: '16px' }}>Plant Brain</span>
        </div>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-primary)',
            fontSize: '24px',
            cursor: 'pointer',
          }}
        >
          {menuOpen ? '✕' : '☰'}
        </button>
      </div>
      {menuOpen && (
        <div
          style={{
            position: 'fixed',
            top: '52px',
            left: 0,
            right: 0,
            bottom: 0,
            background: 'var(--bg-secondary)',
            zIndex: 99,
            padding: '16px',
          }}
        >
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
              onClick={() => setMenuOpen(false)}
              end={item.path === '/'}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <MobileHeader />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/copilot" element={<Copilot />} />
            <Route path="/graph" element={<KnowledgeGraph />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/maintenance" element={<Maintenance />} />
            <Route path="/compliance" element={<Compliance />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
