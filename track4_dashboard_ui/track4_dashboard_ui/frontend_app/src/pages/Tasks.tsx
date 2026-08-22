import React, { useState } from 'react';
import { useTasks } from '../hooks/useTasks';
import { TaskTable } from '../components/TaskTable';
import { RefreshCw } from 'lucide-react';

export const Tasks: React.FC = () => {
  const { tasks, loading, error, refresh } = useTasks();
  const [statusFilter, setStatusFilter] = useState('ALL');

  if (loading && tasks.length === 0) {
    return <div className="loading-container"><div className="spinner"></div>Loading tasks...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to load task registry data.</p>
        <p className="error-message">{error}</p>
        <button className="btn" onClick={refresh}>Retry</button>
      </div>
    );
  }

  // Filter tasks
  let filtered = tasks;
  if (statusFilter !== 'ALL') {
    filtered = filtered.filter((t) => t.status.toUpperCase() === statusFilter.toUpperCase());
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Task Registry Execution Logs</h1>
        <div className="filter-bar">
          <div className="filter-group">
            <label htmlFor="status-select">Status</label>
            <select
              id="status-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">ALL</option>
              <option value="PENDING">PENDING</option>
              <option value="PROCESSING">PROCESSING</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="FAILED">FAILED</option>
            </select>
          </div>

          <button className="icon-btn" onClick={refresh} title="Reload tasks">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-container">No tasks in registry matching filters.</div>
      ) : (
        <TaskTable tasks={filtered} />
      )}
    </div>
  );
};
