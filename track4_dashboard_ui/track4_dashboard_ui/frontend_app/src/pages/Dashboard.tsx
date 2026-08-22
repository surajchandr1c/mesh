import React from 'react';
import { useMetrics } from '../hooks/useMetrics';
import { MetricCard } from '../components/MetricCard';
import { Server, Activity, ClipboardCheck, Shield } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { metrics, loading, error, refresh } = useMetrics();

  if (loading && !metrics) {
    return <div className="loading-container"><div className="spinner"></div>Loading dashboard summary...</div>;
  }

  if (error) {
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

  return (
    <div className="page-content">
      <h1 className="page-title">System Health Dashboard</h1>

      {/* Grid of Metric Cards */}
      <div className="metrics-grid">
        <MetricCard
          title="Workers Availability"
          value={`${(m.workers.availability_rate * 100).toFixed(1)}%`}
          subtitle={`${m.workers.active} Active / ${m.workers.total} Total`}
          icon={<Server size={24} />}
          iconColor="var(--primary)"
        />
        <MetricCard
          title="Resource Utilization"
          value={`CPU: ${m.resources.avg_cpu.toFixed(1)}%`}
          subtitle={`RAM: ${m.resources.avg_ram_mb.toFixed(0)} MB avg`}
          icon={<Activity size={24} />}
          iconColor="#2196F3"
        />
        <MetricCard
          title="Active Tasks"
          value={m.tasks.processing}
          subtitle={`Completed: ${m.tasks.completed}`}
          icon={<ClipboardCheck size={24} />}
          iconColor="#FFC107"
        />
        <MetricCard
          title="Mesh Failovers"
          value={m.reliability.failover_count}
          subtitle={`Fail rate: ${(m.reliability.failure_rate * 100).toFixed(1)}%`}
          icon={<Shield size={24} />}
          iconColor="#F44336"
        />
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
                <span>Retry Frequency Rate</span>
              </div>
              <span className="stat-value">{(m.tasks.retry_rate * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
