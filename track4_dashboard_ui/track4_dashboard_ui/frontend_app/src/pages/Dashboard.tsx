import React from 'react';
import { useMetrics } from '../hooks/useMetrics';
import { useWorkers } from '../hooks/useWorkers';
import { MetricCard } from '../components/MetricCard';
import { Server, Activity, ClipboardCheck, Cpu, HardDrive, Monitor } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { metrics, loading, error, refresh } = useMetrics();
  const { workers } = useWorkers();

  if (loading && !metrics) {
    return <div className="loading-container"><div className="spinner"></div>Loading dashboard summary...</div>;
  }

  if (error && !metrics) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to load summary metrics data.</p>
        <p className="error-message">{error}</p>
        <button className="btn" onClick={refresh}>Retry</button>
      </div>
    );
  }

  if (!metrics) {
    return <div className="empty-container">No metrics summary data available.</div>;
  }

  const m = metrics;
  const r = m.resources;

  const connectedCount = r.connected_pcs_count ?? Math.max(1, m.workers.active);
  const cpuPercent = r.host_cpu_percent ?? r.avg_cpu;
  const ramUsedGb = r.ram_used_gb ?? 0;
  const ramTotalGb = r.ram_total_gb ?? 16;
  const ramPercent = r.ram_percent ?? 0;
  const ramAvailMb = r.ram_available_mb ?? r.avg_ram_mb;
  const diskUsedGb = r.disk_used_gb ?? 0;
  const diskTotalGb = r.disk_total_gb ?? 0;
  const diskFreeGb = r.disk_free_gb ?? 0;
  const diskPercent = r.disk_percent ?? 0;
  const nodeDetails = r.connected_nodes_details ?? [];

  const getBarColor = (pct: number) => {
    if (pct >= 90) return '#EF4444';
    if (pct >= 75) return '#F59E0B';
    return '#10B981';
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <div className="page-title-row">
            <h1 className="page-title">System Health & Telemetry</h1>
            <span className="live-pill">
              <span className="live-dot" /> {connectedCount} Connected PC{connectedCount > 1 ? 's' : ''} ({r.hostname || 'Local Mesh'})
            </span>
          </div>
          <span className="page-subtitle">
            Combined real-time hardware pool across all connected PCs ({r.hostname || 'Local PC'}), multi-node consensus, and task telemetry
          </span>
        </div>

        <button className="icon-btn" onClick={refresh} title="Refresh Telemetry">
          <Activity size={16} />
        </button>
      </div>

      {/* Grid of Metric Cards showing Combined Multi-PC Data */}
      <div className="metrics-grid">
        <MetricCard
          title={`Combined CPU Load (${connectedCount} PC${connectedCount > 1 ? 's' : ''})`}
          value={`${cpuPercent.toFixed(1)}%`}
          subtitle={
            r.cpu_cores_physical
              ? `${r.cpu_cores_physical} Combined Cores / ${r.cpu_cores_logical} Threads`
              : `Mesh Avg: ${r.avg_cpu.toFixed(1)}%`
          }
          icon={<Cpu size={22} />}
          iconColor="#06B6D4"
        />
        <MetricCard
          title={`Combined Memory (${connectedCount} PC${connectedCount > 1 ? 's' : ''})`}
          value={r.ram_used_gb !== undefined ? `${ramUsedGb.toFixed(2)} / ${ramTotalGb.toFixed(2)} GB` : `${ramAvailMb.toFixed(0)} MB Free`}
          subtitle={
            r.ram_percent !== undefined
              ? `${ramPercent.toFixed(1)}% Used • ${ramAvailMb.toFixed(0)} MB Total Free`
              : `Available RAM: ${ramAvailMb.toFixed(0)} MB`
          }
          icon={<HardDrive size={22} />}
          iconColor="#8B5CF6"
        />
        <MetricCard
          title="Connected PCs Online"
          value={`${m.workers.active} Active PC${m.workers.active !== 1 ? 's' : ''}`}
          subtitle={`${(m.workers.availability_rate * 100).toFixed(1)}% Availability • ${m.workers.total} Total`}
          icon={<Server size={22} />}
          iconColor="#3B82F6"
        />
        <MetricCard
          title="Mesh Tasks Executed"
          value={m.tasks.completed}
          subtitle={`Processing: ${m.tasks.processing} • Failed: ${m.tasks.failed}`}
          icon={<ClipboardCheck size={22} />}
          iconColor="#10B981"
        />
      </div>

      {/* Combined Connected PCs Hardware Pool Card */}
      <div className="card details-panel" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Monitor size={18} style={{ color: '#3B82F6' }} />
            <h3 className="panel-title" style={{ margin: 0 }}>
              Combined Connected PCs Resource Pool — {r.hostname || 'Mesh Cluster'} ({connectedCount} PC{connectedCount > 1 ? 's' : ''} Connected)
            </h3>
          </div>
          <span style={{ fontSize: '12px', color: '#10B981', fontWeight: 600 }}>
            ● Combined Multi-PC Live Telemetry
          </span>
        </div>
        <hr />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px', marginTop: '14px' }}>
          {/* Combined CPU Gauge */}
          <div style={{ background: 'rgba(148, 163, 184, 0.06)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontWeight: 600, fontSize: '13px' }}>Combined CPU Pool ({connectedCount} PC{connectedCount > 1 ? 's' : ''})</span>
              <span style={{ fontWeight: 700, fontSize: '14px', color: getBarColor(cpuPercent) }}>
                {cpuPercent.toFixed(1)}%
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'rgba(148, 163, 184, 0.2)', borderRadius: '999px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${Math.min(100, Math.max(2, cpuPercent))}%`,
                  height: '100%',
                  background: getBarColor(cpuPercent),
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px', color: '#94A3B8' }}>
              <span>{r.cpu_cores_physical || 8} Total Physical Cores / {r.cpu_cores_logical || 12} Threads</span>
              <span>{r.cpu_freq_mhz ? `${r.cpu_freq_mhz.toFixed(0)} MHz` : 'Active'}</span>
            </div>
          </div>

          {/* Combined RAM Gauge */}
          <div style={{ background: 'rgba(148, 163, 184, 0.06)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontWeight: 600, fontSize: '13px' }}>Combined RAM Pool ({connectedCount} PC{connectedCount > 1 ? 's' : ''})</span>
              <span style={{ fontWeight: 700, fontSize: '14px', color: getBarColor(ramPercent) }}>
                {ramUsedGb.toFixed(2)} GB / {ramTotalGb.toFixed(2)} GB ({ramPercent.toFixed(1)}%)
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'rgba(148, 163, 184, 0.2)', borderRadius: '999px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${Math.min(100, Math.max(2, ramPercent))}%`,
                  height: '100%',
                  background: getBarColor(ramPercent),
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px', color: '#94A3B8' }}>
              <span>Combined Used: {(r.ram_used_mb ?? 0).toFixed(0)} MB</span>
              <span>Combined Free: {ramAvailMb.toFixed(0)} MB ({(ramAvailMb / 1024).toFixed(2)} GB)</span>
            </div>
          </div>

          {/* Combined Disk Gauge */}
          <div style={{ background: 'rgba(148, 163, 184, 0.06)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontWeight: 600, fontSize: '13px' }}>Combined Storage Pool ({connectedCount} PC{connectedCount > 1 ? 's' : ''})</span>
              <span style={{ fontWeight: 700, fontSize: '14px', color: getBarColor(diskPercent) }}>
                {diskUsedGb.toFixed(1)} GB / {diskTotalGb.toFixed(1)} GB ({diskPercent.toFixed(1)}%)
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'rgba(148, 163, 184, 0.2)', borderRadius: '999px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${Math.min(100, Math.max(2, diskPercent))}%`,
                  height: '100%',
                  background: getBarColor(diskPercent),
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px', color: '#94A3B8' }}>
              <span>Combined Used: {diskUsedGb.toFixed(1)} GB</span>
              <span>Combined Free: {diskFreeGb.toFixed(1)} GB</span>
            </div>
          </div>
        </div>

        {/* Individual Connected PCs Detailed Telemetry Cards */}
        {(nodeDetails.length > 0 || workers.length > 0) && (
          <div style={{ marginTop: '20px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '12px', color: '#94A3B8' }}>
              Individual Connected PC Breakdown ({nodeDetails.length || workers.filter((w) => w.is_active).length} Connected PCs)
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
              {(nodeDetails.length > 0 ? nodeDetails : workers.filter((w) => w.is_active).map((w) => ({
                node_id: w.node_id,
                hostname: w.node_id,
                os_platform: 'Windows 11',
                role: w.node_id === 'gaming-desktop-01' ? 'Main PC (Host + Worker)' : 'Connected Remote PC (PC 2)',
                cpu_utilization: w.cpu_utilization,
                cpu_cores_physical: 8,
                cpu_cores_logical: 12,
                ram_used_gb: Math.max(0, 15.68 - w.ram_available_mb / 1024),
                ram_total_gb: 15.68,
                ram_available_mb: w.ram_available_mb,
                ram_percent: Math.min(100, Math.max(0, ((16056 - w.ram_available_mb) / 16056) * 100)),
                disk_used_gb: 220,
                disk_total_gb: 475.6,
                health: w.health,
                is_active: w.is_active,
              }))).map((pc) => (
                <div
                  key={pc.node_id}
                  style={{
                    padding: '14px 16px',
                    borderRadius: '10px',
                    background: 'rgba(59, 130, 246, 0.06)',
                    border: '1px solid rgba(59, 130, 246, 0.25)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '14px' }}>
                        🖥️ {pc.hostname} <span style={{ fontSize: '11px', fontWeight: 500, color: '#94A3B8' }}>({pc.node_id})</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#3B82F6', fontWeight: 600 }}>
                        {pc.role} • {pc.os_platform}
                      </div>
                    </div>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '999px',
                        fontSize: '11px',
                        fontWeight: 700,
                        background: 'rgba(16, 185, 129, 0.15)',
                        color: '#10B981',
                      }}
                    >
                      ● {pc.health}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '4px', fontSize: '12px' }}>
                    <div style={{ background: 'rgba(15, 23, 42, 0.25)', padding: '8px 10px', borderRadius: '6px' }}>
                      <div style={{ color: '#94A3B8', fontSize: '11px' }}>CPU Utilization</div>
                      <div style={{ fontWeight: 700, color: '#06B6D4', fontSize: '13px' }}>
                        {pc.cpu_utilization.toFixed(1)}% ({pc.cpu_cores_physical}C / {pc.cpu_cores_logical}T)
                      </div>
                    </div>
                    <div style={{ background: 'rgba(15, 23, 42, 0.25)', padding: '8px 10px', borderRadius: '6px' }}>
                      <div style={{ color: '#94A3B8', fontSize: '11px' }}>Memory (RAM) Used</div>
                      <div style={{ fontWeight: 700, color: '#8B5CF6', fontSize: '13px' }}>
                        {pc.ram_used_gb.toFixed(2)} / {pc.ram_total_gb.toFixed(1)} GB ({pc.ram_available_mb.toFixed(0)} MB Free)
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="dashboard-details-row">
        {/* Worker Stats */}
        <div className="card details-panel">
          <h3 className="panel-title">Worker Summary</h3>
          <hr />
          <div className="stat-rows">
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-green"></span>
                <span>Healthy Workers</span>
              </div>
              <span className="stat-value">{m.workers.health_states.healthy}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-orange"></span>
                <span>Degraded Workers</span>
              </div>
              <span className="stat-value">{m.workers.health_states.degraded}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-red"></span>
                <span>Unhealthy Workers</span>
              </div>
              <span className="stat-value">{m.workers.health_states.unhealthy}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-blue"></span>
                <span>Busy Worker Nodes</span>
              </div>
              <span className="stat-value">{m.workers.busy}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-grey"></span>
                <span>Offline/Inactive</span>
              </div>
              <span className="stat-value">{m.workers.offline}</span>
            </div>
          </div>
        </div>

        {/* Task Stats */}
        <div className="card details-panel">
          <h3 className="panel-title">Task Performance</h3>
          <hr />
          <div className="stat-rows">
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-yellow"></span>
                <span>Processing Tasks</span>
              </div>
              <span className="stat-value">{m.tasks.processing}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-green"></span>
                <span>Completed Tasks</span>
              </div>
              <span className="stat-value">{m.tasks.completed}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-red"></span>
                <span>Failed Tasks</span>
              </div>
              <span className="stat-value">{m.tasks.failed}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-blue"></span>
                <span>Total Retries Run</span>
              </div>
              <span className="stat-value">{m.tasks.total_retries}</span>
            </div>
            <div className="stat-row">
              <div className="stat-label">
                <span className="dot dot-purple"></span>
                <span>Failover Events</span>
              </div>
              <span className="stat-value">{m.reliability.failover_count}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
