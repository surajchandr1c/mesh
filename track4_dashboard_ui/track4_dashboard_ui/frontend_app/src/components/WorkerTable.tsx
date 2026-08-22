import React from 'react';
import { Worker } from '../types/worker';
import { WorkerStatusBadge } from './WorkerStatusBadge';
import { HardDrive } from 'lucide-react';

interface WorkerTableProps {
  workers: Worker[];
  onSelectNode: (nodeId: string) => void;
}

export const WorkerTable: React.FC<WorkerTableProps> = ({ workers, onSelectNode }) => {
  return (
    <div className="worker-grid">
      {workers.map((w) => (
        <div
          key={w.node_id}
          className="card worker-card clickable"
          onClick={() => onSelectNode(w.node_id)}
        >
          <div className="worker-card-header">
            <span className="worker-card-id">{w.node_id}</span>
            <WorkerStatusBadge status={w.is_active ? 'ONLINE' : 'OFFLINE'} />
          </div>
          <div className="worker-card-body">
            <div className="telemetry-row">
              <div className="telemetry-field">
                <span className="telemetry-label">CPU Load</span>
                <span className="telemetry-value">{w.cpu_utilization.toFixed(1)}%</span>
              </div>
              <div className="telemetry-field">
                <span className="telemetry-label">RAM Free</span>
                <span className="telemetry-value">{w.ram_available_mb} MB</span>
              </div>
            </div>
            <div className="worker-card-footer">
              <div className="footer-health">
                <HardDrive size={14} style={{ marginRight: '4px' }} />
                <WorkerStatusBadge status={w.health} />
              </div>
              <WorkerStatusBadge status={w.is_ready ? 'READY' : 'NOT READY'} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
