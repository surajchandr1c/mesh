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

  const cpuPercent = r.host_cpu_percent ?? r.avg_cpu;
  const ramUsedGb = r.ram_used_gb ?? 0;
  const ramTotalGb = r.ram_total_gb ?? 16;
  const ramPercent = r.ram_percent ?? 0;
  const ramAvailMb = r.ram_available_mb ?? r.avg_ram_mb;
  const diskUsedGb = r.disk_used_gb ?? 0;
  const diskTotalGb = r.disk_total_gb ?? 0;
  const diskFreeGb = r.disk_free_gb ?? 0;
  const diskPercent = r.disk_percent ?? 0;

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
              <span className="live-dot" /> Live PC Telemetry ({r.hostname || 'Local PC'})
            </span>
          </div>
          <span className="page-subtitle">
            Real-time PC hardware utilization ({r.os_platform || 'Windows'}), multi-node consensus, and task dispatch metrics
          </span>
        </div>

        <button className="icon-btn" onClick={refresh} title="Refresh Telemetry">
          <Activity size={16} />
        </button>
      </div>

      {/* Grid of Metric Cards showing Real PC Data */}
      <div className="metrics-grid">
        <MetricCard
          title="PC CPU Usage"
          value={`${cpuPercent.toFixed(1)}%`}
          subtitle={
            r.cpu_cores_physical
              ? `${r.cpu_cores_physical} Cores / ${r.cpu_cores_logical} Threads${r.cpu_freq_mhz ? ` • ${r.cpu_freq_mhz.toFixed(0)} MHz` : ''}`
              : `Mesh Avg: ${r.avg_cpu.toFixed(1)}%`
          }
          icon={<Cpu size={22} />}
          iconColor="#06B6D4"
        />
        <MetricCard
          title="PC Memory (RAM) Used"
          value={r.ram_used_gb !== undefined ? `${ramUsedGb.toFixed(2)} / ${ramTotalGb.toFixed(1)} GB` : `${ramAvailMb.toFixed(0)} MB Free`}
          subtitle={
            r.ram_percent !== undefined
              ? `${ramPercent.toFixed(1)}% Used • ${ramAvailMb.toFixed(0)} MB Free`
              : `Available RAM: ${ramAvailMb.toFixed(0)} MB`
          }
          icon={<HardDrive size={22} />}
          iconColor="#8B5CF6"
        />
        <MetricCard
          title="Workers Availability"
          value={`${(m.workers.availability_rate * 100).toFixed(1)}%`}
          subtitle={`${m.workers.active} Online / ${m.workers.total} Registered`}
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

      {/* Live Host PC Hardware Utilization Card */}
      <div className="card details-panel" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Monitor size={18} style={{ color: '#3B82F6' }} />
            <h3 className="panel-title" style={{ margin: 0 }}>
              Live PC Hardware Usage — {r.hostname || 'Main Host PC'} ({r.os_platform || 'Windows'})
            </h3>
          </div>
          <span style={{ fontSize: '12px', color: '#10B981', fontWeight: 600 }}>
            ● Real-Time OS Sensor Feed
          </span>
        </div>
        <hr />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px', marginTop: '14px' }}>
          {/* CPU Gauge */}
          <div style={{ background: 'rgba(148, 163, 184, 0.06)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontWeight: 600, fontSize: '13px' }}>Processor (CPU) Load</span>
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
              <span>{r.cpu_cores_physical || 8} Physical Cores / {r.cpu_cores_logical || 12} Logical</span>
              <span>{r.cpu_freq_mhz ? `${r.cpu_freq_mhz.toFixed(0)} MHz` : 'Active'}</span>
            </div>
          </div>

          {/* RAM Gauge */}
          <div style={{ background: 'rgba(148, 163, 184, 0.06)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontWeight: 600, fontSize: '13px' }}>System Memory (RAM)</span>
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
              <span>Used: {(r.ram_used_mb ?? 0).toFixed(0)} MB</span>
              <span>Free / Available: {ramAvailMb.toFixed(0)} MB</span>
            </div>
          </div>

          {/* Disk Gauge */}
          <div style={{ background: 'rgba(148, 163, 184, 0.06)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontWeight: 600, fontSize: '13px' }}>Storage Disk Usage</span>
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
              <span>Used: {diskUsedGb.toFixed(1)} GB</span>
              <span>Free Space: {diskFreeGb.toFixed(1)} GB</span>
            </div>
          </div>
        </div>

        {/* Connected Worker Nodes Live Telemetry Breakdown */}
        {workers.length > 0 && (
          <div style={{ marginTop: '18px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '10px', color: '#94A3B8' }}>
              Connected Mesh Worker Nodes ({workers.filter((w) => w.is_active).length} Active)
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
              {workers.map((w) => (
                <div
                  key={w.node_id}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '8px',
                    background: 'rgba(59, 130, 246, 0.06)',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '13px' }}>{w.node_id}</div>
                    <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                      {w.is_active ? '● Online' : '○ Offline'} • Health: {w.health}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: '12px' }}>
                    <div style={{ fontWeight: 700, color: '#06B6D4' }}>CPU: {w.cpu_utilization.toFixed(1)}%</div>
                    <div style={{ color: '#94A3B8' }}>Free RAM: {w.ram_available_mb.toFixed(0)} MB</div>
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
