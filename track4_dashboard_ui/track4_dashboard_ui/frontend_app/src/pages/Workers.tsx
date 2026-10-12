import React, { useState } from 'react';
import { useWorkers } from '../hooks/useWorkers';
import { WorkerTable } from '../components/WorkerTable';
import {
  RefreshCw,
  Laptop,
  Radio,
  Loader2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Zap,
} from 'lucide-react';

interface WorkersProps {
  onSelectNode: (nodeId: string) => void;
}

export const Workers: React.FC<WorkersProps> = ({ onSelectNode }) => {
  const { workers, loading, error, refresh } = useWorkers();
  const [healthFilter, setHealthFilter] = useState('ALL');
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [isScanning, setIsScanning] = useState(false);
  const [showConnectGuide, setShowConnectGuide] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);

  const handleScanMesh = () => {
    setIsScanning(true);
    refresh();
    setTimeout(() => {
      setIsScanning(false);
    }, 1500);
  };

  const connectCommand = 'python track1_worker_node/main.py';

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(connectCommand);
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  // Dedicated Full-Page Scanner while initial connection is loading
  if (loading && workers.length === 0) {
    return (
      <div className="page-content">
        <div className="radar-scanner-container card">
          <div className="radar-dish">
            <div className="radar-ring radar-ring-1" />
            <div className="radar-ring radar-ring-2" />
            <div className="radar-ring radar-ring-3" />
            <div className="radar-beacon">
              <Laptop size={24} />
            </div>
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '6px' }}>
            Connecting to Compute Mesh...
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '420px', marginBottom: '16px' }}>
            Scanning local network for contributor laptops and worker nodes. Listening on gRPC Port 50051 and Redis broker.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#06B6D4', fontSize: '12px', fontWeight: 600 }}>
            <Loader2 size={15} className="spin-animate" />
            <span>Awaiting device handshake & telemetry...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to connect to worker registry.</p>
        <p className="error-message">{error}</p>
        <button className="btn btn-primary" onClick={refresh}>Retry Connection</button>
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
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title-row">
            <h1 className="page-title">Mesh Contributor Workers & Laptops</h1>
            <span className="live-pill">
              <span className="live-dot" /> gRPC :50051 Active
            </span>
          </div>
          <span className="page-subtitle">
            Real-time telemetry from active laptops and compute server nodes powering Llama 3.2 1B
          </span>
        </div>

        <div className="header-actions">
          <button
            className="btn btn-secondary"
            onClick={() => setShowConnectGuide(!showConnectGuide)}
          >
            <Laptop size={15} />
            <span>Connect Laptop</span>
            {showConnectGuide ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          <button
            className="btn btn-primary"
            onClick={handleScanMesh}
            disabled={isScanning}
          >
            {isScanning ? (
              <Loader2 size={15} className="spin-animate" />
            ) : (
              <RefreshCw size={15} />
            )}
            <span>{isScanning ? 'Scanning Mesh...' : 'Scan Network'}</span>
          </button>
        </div>
      </div>

      {/* Quick Laptop Connection Guide Drawer */}
      {showConnectGuide && (
        <div className="connect-guide-card">
          <div className="connect-guide-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={16} style={{ color: '#06B6D4' }} />
              <strong style={{ fontSize: '13px' }}>How to Connect Any Contributor Laptop to this Mesh</strong>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>LAN Discovery</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '4px 0 8px 0' }}>
            Run the worker engine on any laptop connected to the same Wi-Fi/network. It will automatically detect this server, register its CPU/RAM, and begin executing distributed inference tasks.
          </p>
          <div className="connect-code-box">
            <code>{connectCommand}</code>
            <button className="copy-mini-btn" onClick={handleCopyCommand}>
              {copiedCmd ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
              <span>{copiedCmd ? 'Copied' : 'Copy Command'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Filter and Control Bar */}
      <div className="filter-bar" style={{ marginBottom: '16px' }}>
        <div className="filter-group">
          <label htmlFor="health-select">Health Status</label>
          <select
            id="health-select"
            value={healthFilter}
            onChange={(e) => setHealthFilter(e.target.value)}
          >
            <option value="ALL">ALL ({workers.length})</option>
            <option value="HEALTHY">HEALTHY</option>
            <option value="DEGRADED">DEGRADED</option>
            <option value="UNHEALTHY">UNHEALTHY</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="status-select">Connection</label>
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

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <Radio size={14} style={{ color: '#10B981' }} />
          <span>Listening on 0.0.0.0:50051</span>
        </div>
      </div>

      {/* Main Display: Active Worker Grid OR Live Radar Scanner */}
      {filtered.length === 0 ? (
        <div className="radar-scanner-container card">
          <div className="radar-dish">
            <div className="radar-ring radar-ring-1" />
            <div className="radar-ring radar-ring-2" />
            <div className="radar-ring radar-ring-3" />
            <div className="radar-beacon">
              <Laptop size={24} />
            </div>
          </div>
          <h2 style={{ fontSize: '17px', fontWeight: 700, marginBottom: '6px' }}>
            Awaiting Contributor Laptop Connection
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '440px', marginBottom: '16px' }}>
            No contributor laptops are currently registered on the mesh. Start the worker node on your laptop or server to join the compute mesh.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div className="connect-code-box" style={{ maxWidth: '380px' }}>
              <code>python track1_worker_node/main.py</code>
              <button className="copy-mini-btn" onClick={handleCopyCommand}>
                {copiedCmd ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                <span>{copiedCmd ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#06B6D4', fontSize: '12px', fontWeight: 600 }}>
            <Loader2 size={14} className="spin-animate" />
            <span>Scanning for incoming heartbeat pings every 5s...</span>
          </div>
        </div>
      ) : (
        <WorkerTable workers={filtered} onSelectNode={onSelectNode} />
      )}
    </div>
  );
};
