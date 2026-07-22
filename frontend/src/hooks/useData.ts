import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../config';

interface GraphData {
  nodes: any[];
  links: any[];
}

interface GraphStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
}

export function useGraph() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/graph`);
      const data = await resp.json();
      setGraphData(data.graph || { nodes: [], links: [] });
      setStats(data.stats || null);
    } catch (err) {
      console.log('Graph fetch failed:', err);
    }
    setLoading(false);
  }, []);

  const fetchEquipmentSubgraph = useCallback(async (tag: string) => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/graph/equipment/${tag}`);
      const data = await resp.json();
      setGraphData(data.graph || { nodes: [], links: [] });
      return data;
    } catch (err) {
      console.log('Subgraph fetch failed:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchGraph();
    const handleRefresh = () => fetchGraph();
    window.addEventListener('data-updated', handleRefresh);
    return () => window.removeEventListener('data-updated', handleRefresh);
  }, [fetchGraph]);

  return {
    graphData,
    stats,
    loading,
    selectedNode,
    setSelectedNode,
    fetchGraph,
    fetchEquipmentSubgraph,
  };
}

export function useDocuments() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/documents`);
      const data = await resp.json();
      setDocuments(data.documents || []);
    } catch (err) {
      console.log('Documents fetch failed:', err);
    }
    setLoading(false);
  }, []);

  const uploadFiles = useCallback(async (files: File[]) => {
    setUploading(true);
    setUploadProgress('Uploading...');

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));

      const resp = await fetch(`${API_BASE}/api/ingest`, {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();

      setUploadProgress('Processing documents...');

      // Poll for completion
      const jobId = data.job_id;
      let attempts = 0;
      const maxAttempts = 30;

      while (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 2000));
        const statusResp = await fetch(`${API_BASE}/api/ingest/status/${jobId}`);
        const status = await statusResp.json();

        if (status.status === 'completed' || status.status === 'completed_with_errors') {
          setUploadProgress(
            `✓ ${status.processed_files}/${status.total_files} documents processed`
          );
          window.dispatchEvent(new Event('data-updated'));
          break;
        }

        setUploadProgress(
          `Processing ${status.processed_files}/${status.total_files}...`
        );
        attempts++;
      }
    } catch (err) {
      setUploadProgress('⚠️ Upload failed. Is the backend running?');
    }

    setTimeout(() => {
      setUploading(false);
      setUploadProgress('');
    }, 3000);
  }, []);

  const deleteDocument = useCallback(async (docId: string) => {
    try {
      await fetch(`${API_BASE}/api/documents/${docId}`, { method: 'DELETE' });
      window.dispatchEvent(new Event('data-updated'));
    } catch (err) {
      console.log('Delete failed:', err);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
    const handleRefresh = () => fetchDocuments();
    window.addEventListener('data-updated', handleRefresh);
    return () => window.removeEventListener('data-updated', handleRefresh);
  }, [fetchDocuments]);

  return {
    documents,
    loading,
    uploading,
    uploadProgress,
    fetchDocuments,
    uploadFiles,
    deleteDocument,
  };
}

export function useStats() {
  const [stats, setStats] = useState<any>(null);

  const fetchStats = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/stats`);
      const data = await resp.json();
      setStats(data);
    } catch (err) {
      console.log('Stats fetch failed:', err);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const handleRefresh = () => fetchStats();
    window.addEventListener('data-updated', handleRefresh);
    const interval = setInterval(fetchStats, 10000); // Refresh every 10s
    return () => {
      window.removeEventListener('data-updated', handleRefresh);
      clearInterval(interval);
    };
  }, [fetchStats]);

  return { stats, fetchStats };
}
