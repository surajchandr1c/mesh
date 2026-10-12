import React from 'react';
import { Worker } from '../types/worker';
import { WorkerStatusBadge } from './WorkerStatusBadge';
import { Server, Cpu, HardDrive, ChevronRight } from 'lucide-react';

interface WorkerTableProps {
  workers: Worker[];
  onSelectNode: (nodeId: string) => void;
}

export const WorkerTable: React.FC<WorkerTableProps> = ({ workers, onSelectNode }) => {
  return (
    <div className="worker-grid">
      {workers.map((w) => {
        // CPU color calculation
        const cpuColor =
          w.cpu_utilization > 85 ? '#EF4444' : w.cpu_utilization > 60 ? '#F59E0B' : '#10B981';

        return (
          <div
            key={w.node_id}
            className="card worker-card clickable"
            onClick={() => onSelectNode(w.node_id)}
          >
            <div className="worker-card-header">
              <div className="worker-id-group">
                <div className="worker-icon-box">
                  <Server size={18} />
                </div>
                <div>
                  <span className="worker-card-id">{w.node_id}</span>
                  <span className="worker-subtext">Compute Node</span>
                </div>
              </div>
              <WorkerStatusBadge status={w.is_active ? 'ONLINE' : 'OFFLINE'} />
            </div>

            <div className="worker-card-body">
              {/* CPU Meter */}
              <div className="telemetry-meter-group">
                <div className="meter-label-row">
                  <span className="telemetry-label">
                    <Cpu size={13} /> CPU Utilization
                  </span>
                  <span className="telemetry-value" style={{ color: cpuColor }}>
                    {w.cpu_utilization.toFixed(1)}%
                  </span>
                </div>
                <div className="meter-bar-track">
                  <div
                    className="meter-bar-fill"
                    style={{
                      width: `${Math.min(100, Math.max(2, w.cpu_utilization))}%`,
                      backgroundColor: cpuColor,
                    }}
                  />
                </div>
              </div>

              {/* RAM Meter */}
              <div className="telemetry-meter-group">
                <div className="meter-label-row">
                  <span className="telemetry-label">
                    <HardDrive size={13} /> Available Memory
                  </span>
                  <span className="telemetry-value">
                    {w.ram_available_mb.toFixed(0)} MB
                  </span>
                </div>
                <div className="meter-bar-track">
                  <div
                    className="meter-bar-fill"
                    style={{
                      width: `${Math.min(100, Math.max(5, (w.ram_available_mb / 8192) * 100))}%`,
                      backgroundColor: '#3B82F6',
                    }}
                  />
                </div>
              </div>

              {/* Bottom Badges */}
              <div className="worker-card-footer">
                <div className="footer-badges">
                  <WorkerStatusBadge status={w.health} />
                  <WorkerStatusBadge status={w.is_ready ? 'READY' : 'NOT READY'} />
                </div>
                <span className="inspect-link">
                  Details <ChevronRight size={14} />
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
