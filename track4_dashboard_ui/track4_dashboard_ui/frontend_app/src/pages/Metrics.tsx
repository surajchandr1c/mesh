import React from 'react';
import { useMetrics } from '../hooks/useMetrics';
import { RefreshCw } from 'lucide-react';

export const Metrics: React.FC = () => {
  const { metrics, loading, error, refresh } = useMetrics();

  if (loading && !metrics) {
    return <div className="loading-container"><div className="spinner"></div>Loading metrics...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to load metrics.</p>
        <p className="error-message">{error}</p>
        <button className="btn" onClick={refresh}>Retry</button>
      </div>
    );
  }

  if (!metrics) {
    return <div className="empty-container">No metrics available.</div>;
  }

  const m = metrics;

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Aggregated Telemetry Signals</h1>
        <button className="icon-btn" onClick={refresh} title="Reload metrics">
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="metrics-page-content" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Ratios Card */}
        <div className="card details-panel">
          <h3 className="panel-title">System Ratios & Status Rates</h3>
          <hr />
          <div className="metrics-rows">
            {_buildMetricRow(
              "Node Availability Rate",
              `${(m.workers.availability_rate * 100).toFixed(1)}%`,
              "Ratio of active contributors over total registered nodes.",
              "blue"
            )}
            {_buildMetricRow(
              "Task Retry Frequency",
              `${(m.tasks.retry_rate * 100).toFixed(1)}%`,
              "Average number of reassignment retries executed per registered task.",
              "purple"
            )}
            {_buildMetricRow(
              "Failover Incidence Rate",
              `${(m.reliability.failure_rate * 100).toFixed(1)}%`,
              "Ratio of failover logs count against completed and failed tasks.",
              "red"
            )}
          </div>
        </div>

        {/* Averages & Real PC Telemetry Card */}
        <div className="card details-panel">
          <h3 className="panel-title">
            Real-Time PC & Mesh Resource Telemetry ({m.resources.hostname || 'Local PC'})
          </h3>
          <hr />
          <div className="metrics-rows">
            {_buildMetricRow(
              "Host PC CPU Utilization",
              `${(m.resources.host_cpu_percent ?? m.resources.avg_cpu).toFixed(1)}%`,
              `Real-time processor load across ${m.resources.cpu_cores_physical || 8} physical cores / ${m.resources.cpu_cores_logical || 12} logical threads.`,
              "green"
            )}
            {_buildMetricRow(
              "Host PC Memory (RAM) Used",
              m.resources.ram_used_gb !== undefined
                ? `${m.resources.ram_used_gb.toFixed(2)} GB / ${m.resources.ram_total_gb?.toFixed(2)} GB (${m.resources.ram_percent?.toFixed(1)}%)`
                : `${m.resources.avg_ram_mb.toFixed(0)} MB Free`,
              `Used RAM: ${(m.resources.ram_used_mb ?? 0).toFixed(0)} MB • Available Free RAM: ${(m.resources.ram_available_mb ?? m.resources.avg_ram_mb).toFixed(0)} MB.`,
              "orange"
            )}
            {m.resources.disk_used_gb !== undefined &&
              _buildMetricRow(
                "Host PC Disk Storage Used",
                `${m.resources.disk_used_gb.toFixed(1)} GB / ${m.resources.disk_total_gb?.toFixed(1)} GB (${m.resources.disk_percent?.toFixed(1)}%)`,
                `Free storage capacity remaining: ${m.resources.disk_free_gb?.toFixed(1)} GB.`,
                "blue"
              )}
            {_buildMetricRow(
              "Mesh Active Workers Mean CPU",
              `${m.resources.avg_cpu.toFixed(1)}%`,
              "Average processing load reported across all currently online worker nodes.",
              "purple"
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const _buildMetricRow = (
  label: string,
  value: string,
  description: string,
  markerColor: string
) => {
  return (
    <div className="metric-row-item" key={label}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`dot dot-${markerColor}`}></span>
          <span style={{ fontSize: '13px', fontWeight: 600 }}>{label}</span>
        </div>
        <span style={{ fontSize: '14px', fontWeight: 'bold' }}>{value}</span>
      </div>
      <p style={{ margin: '4px 0 0 16px', fontSize: '11px', color: 'grey' }}>{description}</p>
    </div>
  );
};
