import React, { useState, useEffect, useCallback } from 'react';
import { Worker } from '../types/worker';
import { api } from '../services/api';
import { WorkerStatusBadge } from '../components/WorkerStatusBadge';
import { ArrowLeft, HardDrive } from 'lucide-react';

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
    }, 5000);

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

  return (
    <div className="page-content">
      <div className="page-header" style={{ justifyContent: 'flex-start', gap: '16px' }}>
        <button className="icon-btn" onClick={onBack} title="Back to Workers">
          <ArrowLeft size={20} />
        </button>
        <h1 className="page-title">{w.node_id}</h1>
      </div>

      <div className="card details-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Worker Node UUID</span>
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
          <span style={{ fontSize: '11px', color: 'grey', display: 'block', marginBottom: '4px' }}>Last Heartbeat Received</span>
          <span style={{ fontSize: '14px', fontWeight: 'bold' }}>{w.last_seen}</span>
        </div>
      </div>

      <h3 style={{ margin: '24px 0 12px 0', fontFamily: 'var(--font-title)', fontWeight: 'bold' }}>Host System Metrics</h3>

      <div className="hardware-grid">
        {/* CPU Util Card */}
        <div className="card hardware-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>CPU Utilization</span>
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
        <div className="card hardware-card" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="hardware-icon-wrapper" style={{ color: 'green', backgroundColor: '#81C78414' }}>
            <HardDrive size={36} />
          </div>
          <div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Available Memory</span>
            <span style={{ fontSize: '20px', fontWeight: 'bold', display: 'block', marginTop: '4px' }}>
              {w.ram_available_mb} MB
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
