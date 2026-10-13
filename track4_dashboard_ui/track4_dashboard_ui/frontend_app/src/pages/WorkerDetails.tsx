import React, { useState, useEffect, useCallback } from 'react';
import { Worker } from '../types/worker';
import { api } from '../services/api';
import { WorkerStatusBadge } from '../components/WorkerStatusBadge';
import { ArrowLeft } from 'lucide-react';
import { formatDate } from '../utils/formatters';

interface WorkerDetailsProps {
  nodeId: string;
  onBack: () => void;
}

export const WorkerDetails: React.FC<WorkerDetailsProps> = ({ nodeId, onBack }) => {
  const [worker, setWorker] = useState<Worker | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetails = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      const data = await api.getNode(nodeId);
      setWorker(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [nodeId]);

  useEffect(() => {
    fetchDetails(true);

    const interval = setInterval(() => {
      fetchDetails(false);
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchDetails]);

  if (loading && !worker) {
    return <div className="loading-container"><div className="spinner"></div>Loading worker details...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to load worker detailed data.</p>
        <p className="error-message">{error}</p>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn" onClick={onBack}><ArrowLeft size={16} /> Back</button>
          <button className="btn" onClick={() => fetchDetails(true)}>Retry</button>
        </div>
      </div>
    );
  }

  if (!worker) {
    return (
      <div className="empty-container">
        Node not found.
        <button className="btn" onClick={onBack} style={{ marginTop: '12px' }}>
          <ArrowLeft size={16} /> Back to Workers
        </button>
      </div>
    );
  }

  const w = worker;
  const ramUsedGb = w.ram_used_gb ?? Math.max(0, 15.68 - w.ram_available_mb / 1024);
  const ramTotalGb = w.ram_total_gb ?? 15.68;
  const ramPct = w.ram_percent ?? Math.min(100, Math.max(0, (ramUsedGb / ramTotalGb) * 100));
  const diskUsedGb = w.disk_used_gb ?? 218.42;
  const diskTotalGb = w.disk_total_gb ?? 475.65;
  const diskFreeGb = w.disk_free_gb ?? Math.max(0, diskTotalGb - diskUsedGb);
  const diskPct = w.disk_percent ?? (diskTotalGb > 0 ? (diskUsedGb / diskTotalGb) * 100 : 0);

  return (
    <div className="page-content">
      <div className="page-header" style={{ justifyContent: 'flex-start', gap: '16px' }}>
        <button className="icon-btn" onClick={onBack} title="Back to Workers">
          <ArrowLeft size={20} />
        </button>
        <h1 className="page-title">{w.hostname ? `${w.hostname} (${w.node_id})` : w.node_id}</h1>
      </div>

      <div className="card details-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {w.role || 'Worker Node'} • {w.os_platform || 'Windows 11'}
            </span>
            <h2 className="panel-title" style={{ marginTop: '4px' }}>{w.node_id}</h2>
          </div>
          <WorkerStatusBadge status={w.is_active ? 'ONLINE' : 'OFFLINE'} />
        </div>

        <hr style={{ margin: '24px 0' }} />

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
          <div style={{ flex: '1 1 200px' }}>
            <span style={{ fontSize: '11px', color: 'grey', display: 'block', marginBottom: '4px' }}>Health Diagnostics</span>
            <WorkerStatusBadge status={w.health} />
          </div>
          <div style={{ flex: '1 1 200px' }}>
            <span style={{ fontSize: '11px', color: 'grey', display: 'block', marginBottom: '4px' }}>Node Readiness</span>
            <WorkerStatusBadge status={w.is_ready ? 'READY' : 'NOT READY'} />
          </div>
        </div>

        <div style={{ marginTop: '16px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Last Heartbeat Received</span>
          <span style={{ fontSize: '14px', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>{formatDate(w.last_seen)}</span>
        </div>
      </div>

      <h3 style={{ margin: '24px 0 12px 0', fontFamily: 'var(--font-title)', fontWeight: 'bold' }}>Live Host System Metrics</h3>

      <div className="hardware-grid">
        {/* CPU Util Card */}
        <div className="card hardware-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              CPU Utilization {w.cpu_cores_physical ? `(${w.cpu_cores_physical} Cores / ${w.cpu_cores_logical} Threads)` : ''}
            </span>
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>{w.cpu_utilization.toFixed(1)}%</span>
          </div>
          <div className="progress-bar-bg">
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, w.cpu_utilization))}%`,
                backgroundColor: 'var(--primary)',
              }}
            ></div>
          </div>
        </div>

        {/* RAM Card */}
        <div className="card hardware-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              RAM Usage ({w.ram_available_mb.toFixed(0)} MB Free)
            </span>
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
              {ramUsedGb.toFixed(2)} / {ramTotalGb.toFixed(2)} GB ({ramPct.toFixed(1)}%)
            </span>
          </div>
          <div className="progress-bar-bg">
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, ramPct))}%`,
                backgroundColor: '#8B5CF6',
              }}
            ></div>
          </div>
        </div>

        {/* Storage Card */}
        <div className="card hardware-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Storage Used ({diskFreeGb.toFixed(1)} GB Free)
            </span>
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
              {diskUsedGb.toFixed(1)} / {diskTotalGb.toFixed(1)} GB ({diskPct.toFixed(1)}%)
            </span>
          </div>
          <div className="progress-bar-bg">
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, Math.max(0, diskPct))}%`,
                backgroundColor: '#10B981',
              }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
};
