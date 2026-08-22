import React, { useState } from 'react';
import { useWorkers } from '../hooks/useWorkers';
import { WorkerTable } from '../components/WorkerTable';
import { RefreshCw } from 'lucide-react';

interface WorkersProps {
  onSelectNode: (nodeId: string) => void;
}

export const Workers: React.FC<WorkersProps> = ({ onSelectNode }) => {
  const { workers, loading, error, refresh } = useWorkers();
  const [healthFilter, setHealthFilter] = useState('ALL');
  const [activeFilter, setActiveFilter] = useState('ALL');

  if (loading && workers.length === 0) {
    return <div className="loading-container"><div className="spinner"></div>Loading workers...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to load worker data.</p>
        <p className="error-message">{error}</p>
        <button className="btn" onClick={refresh}>Retry</button>
      </div>
    );
  }

  // Filter logic
  let filtered = workers;
  if (healthFilter !== 'ALL') {
    filtered = filtered.filter((w) => w.health.toUpperCase() === healthFilter.toUpperCase());
  }
  if (activeFilter !== 'ALL') {
    const shouldBeActive = activeFilter === 'ACTIVE';
    filtered = filtered.filter((w) => w.is_active === shouldBeActive);
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Mesh Contributor Workers</h1>
        <div className="filter-bar">
          <div className="filter-group">
            <label htmlFor="health-select">Health</label>
            <select
              id="health-select"
              value={healthFilter}
              onChange={(e) => setHealthFilter(e.target.value)}
            >
              <option value="ALL">ALL</option>
              <option value="HEALTHY">HEALTHY</option>
              <option value="DEGRADED">DEGRADED</option>
              <option value="UNHEALTHY">UNHEALTHY</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="status-select">Status</label>
            <select
              id="status-select"
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
            >
              <option value="ALL">ALL</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="OFFLINE">OFFLINE</option>
            </select>
          </div>

          <button className="icon-btn" onClick={refresh} title="Reload workers">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-container">No workers registered matching filters.</div>
      ) : (
        <WorkerTable workers={filtered} onSelectNode={onSelectNode} />
      )}
    </div>
  );
};
