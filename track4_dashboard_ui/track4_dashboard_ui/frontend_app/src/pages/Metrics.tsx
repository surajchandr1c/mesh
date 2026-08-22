import React from 'react';
import { useMetrics } from '../hooks/useMetrics';
import { RefreshCw, Info } from 'lucide-react';

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

        {/* Averages Card */}
        <div className="card details-panel">
          <h3 className="panel-title">Telemetry Resource Averages</h3>
          <hr />
          <div className="metrics-rows">
            {_buildMetricRow(
              "Mean Active CPU utilization",
              `${m.resources.avg_cpu.toFixed(1)}%`,
              "Average processing load across all active online node units.",
              "green"
            )}
            {_buildMetricRow(
              "Mean Active RAM available",
              `${m.resources.avg_ram_mb.toFixed(0)} MB`,
              "Average available RAM memory across active worker hosts.",
              "orange"
            )}
          </div>
        </div>

        {/* Future Time-Series notice */}
        <div
          className="card"
          style={{
            padding: '16px',
            backgroundColor: 'rgba(33, 150, 243, 0.08)',
            border: '1px solid rgba(33, 150, 243, 0.3)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#2196F3', fontWeight: 'bold' }}>
            <Info size={20} />
            <span>Time-Series Telemetry & Charts</span>
          </div>
          <p style={{ fontSize: '12px', lineHeight: '1.6', margin: 0 }}>
            Historical line charts and resource timeline series represent planned enhancements in Phase 10. The current SQLite schemas log instantaneous telemetry samples. Adding a time-series aggregator backend daemon will allow plotting dynamic historical graphs.
          </p>
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
