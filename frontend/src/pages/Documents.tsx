import { useState, useRef } from 'react';
import { useDocuments } from '../hooks/useData';

const DOC_ICONS: Record<string, string> = {
  maintenance_record: '🔧',
  safety_procedure: '🛡️',
  inspection_report: '🔍',
  oem_manual: '📘',
  regulatory: '📋',
  incident_report: '⚠️',
  operating_procedure: '📝',
  general: '📄',
};

const DOC_COLORS: Record<string, string> = {
  maintenance_record: 'blue',
  safety_procedure: 'green',
  inspection_report: 'amber',
  oem_manual: 'purple',
  regulatory: 'red',
  incident_report: 'red',
  operating_procedure: 'cyan',
  general: 'blue',
};

export default function Documents() {
  const { documents, loading, uploading, uploadProgress, uploadFiles, deleteDocument } = useDocuments();
  const [dragActive, setDragActive] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) uploadFiles(files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) uploadFiles(files);
  };

  const filteredDocs = filter
    ? documents.filter((d) => d.doc_type === filter)
    : documents;

  const categories = [...new Set(documents.map((d) => d.doc_type))];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Document Library</h1>
        <p className="page-subtitle">
          {documents.length} documents indexed · Upload files to expand the knowledge base
        </p>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone ${dragActive ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.docx,.xlsx,.csv"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        {uploading ? (
          <>
            <div className="upload-zone-icon">⏳</div>
            <div className="upload-zone-text">{uploadProgress}</div>
          </>
        ) : (
          <>
            <div className="upload-zone-icon">📁</div>
            <div className="upload-zone-text">
              {dragActive ? 'Drop files here' : 'Drag & drop documents or click to browse'}
            </div>
            <div className="upload-zone-hint">
              Supports: PDF, TXT, DOCX, XLSX, CSV
            </div>
          </>
        )}
      </div>

      {/* Filter Bar */}
      {categories.length > 0 && (
        <div className="filter-bar" style={{ marginTop: '24px' }}>
          <button
            className={`filter-chip ${!filter ? 'active' : ''}`}
            onClick={() => setFilter(null)}
          >
            All ({documents.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              className={`filter-chip ${filter === cat ? 'active' : ''}`}
              onClick={() => setFilter(filter === cat ? null : cat)}
            >
              {DOC_ICONS[cat] || '📄'} {cat.replace(/_/g, ' ')} (
              {documents.filter((d) => d.doc_type === cat).length})
            </button>
          ))}
        </div>
      )}

      {/* Document Grid */}
      {filteredDocs.length > 0 ? (
        <div className="doc-grid" style={{ marginTop: '20px' }}>
          {filteredDocs.map((doc) => (
            <div key={doc.doc_id} className="doc-card" onClick={() => setSelectedDoc(doc)}>
              <div className="doc-card-header">
                <div>
                  <div style={{ fontSize: '28px', marginBottom: '8px' }}>
                    {DOC_ICONS[doc.doc_type] || '📄'}
                  </div>
                  <div className="doc-title">{doc.title || doc.filename}</div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete this document?')) deleteDocument(doc.doc_id);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '16px',
                    padding: '4px',
                  }}
                  title="Delete document"
                >
                  🗑️
                </button>
              </div>
              <div className="doc-meta">
                <span className={`doc-tag ${DOC_COLORS[doc.doc_type] || ''}`}>
                  {(doc.doc_type || 'general').replace(/_/g, ' ')}
                </span>
                {doc.chunk_count > 0 && (
                  <span className="doc-tag green">{doc.chunk_count} chunks</span>
                )}
                {doc.entity_count > 0 && (
                  <span className="doc-tag amber">{doc.entity_count} entities</span>
                )}
                {doc.page_count > 0 && (
                  <span className="doc-tag">{doc.page_count} pages</span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state" style={{ marginTop: '48px' }}>
          <div className="empty-state-icon">📄</div>
          <div className="empty-state-title">
            {loading ? 'Loading...' : 'No Documents Yet'}
          </div>
          <div className="empty-state-text">
            Upload industrial documents to build your knowledge base.
            Supported formats: PDF, TXT, DOCX, XLSX, CSV
          </div>
        </div>
      )}

      {/* Document Preview Modal */}
      {selectedDoc && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.7)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '32px',
          }}
          onClick={() => setSelectedDoc(null)}
        >
          <div
            className="card"
            style={{
              maxWidth: '700px',
              width: '100%',
              maxHeight: '80vh',
              overflow: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 600 }}>
                {DOC_ICONS[selectedDoc.doc_type]} {selectedDoc.title || selectedDoc.filename}
              </h2>
              <button
                onClick={() => setSelectedDoc(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px' }}
              >
                ✕
              </button>
            </div>
            <div className="doc-meta" style={{ marginBottom: '16px' }}>
              <span className={`doc-tag ${DOC_COLORS[selectedDoc.doc_type]}`}>
                {selectedDoc.doc_type?.replace(/_/g, ' ')}
              </span>
              <span className="doc-tag">{selectedDoc.chunk_count} chunks</span>
              <span className="doc-tag">{selectedDoc.entity_count} entities</span>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Document ID: {selectedDoc.doc_id}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
