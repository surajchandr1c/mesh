import React from 'react';
import { Worker } from '../types/worker';
import { WorkerStatusBadge } from './WorkerStatusBadge';
import { Server, Laptop, Cpu, HardDrive, ChevronRight, Loader2, Sparkles, Radio } from 'lucide-react';

interface WorkerTableProps {
  workers: Worker[];
  onSelectNode: (nodeId: string) => void;
}

export const WorkerTable: React.FC<WorkerTableProps> = ({ workers, onSelectNode }) => {
  return (
    <div className="worker-grid">
      {workers.map((w) => {
        // Distinguish device type
        const isLaptop =
          /laptop|macbook|desktop|thinkpad|dell|hp|worker|contributor|client/i.test(w.node_id) ||
          !/server|central/i.test(w.node_id);

        const isConnecting =
          !w.is_ready ||
          w.health.toUpperCase() === 'CONNECTING' ||
          w.health.toUpperCase() === 'HANDSHAKING';

        // CPU color calculation
        const cpuColor =
          w.cpu_utilization > 85 ? '#EF4444' : w.cpu_utilization > 60 ? '#F59E0B' : '#10B981';

        return (
          <div
            key={w.node_id}
            className={`card worker-card clickable ${isConnecting ? 'worker-card-connecting' : ''}`}
            onClick={() => onSelectNode(w.node_id)}
          >
            <div className="worker-card-header">
              <div className="worker-id-group">
                <div className={`worker-icon-box ${isLaptop ? 'icon-box-laptop' : ''}`}>
                  {isLaptop ? <Laptop size={18} /> : <Server size={18} />}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="worker-card-id">{w.node_id}</span>
                  </div>
                  <span className="worker-subtext">
                    {isLaptop ? 'Contributor Laptop Node' : 'Primary Server Host'}
                  </span>
                </div>
              </div>

              {isConnecting ? (
                <WorkerStatusBadge status="CONNECTING" />
              ) : (
                <WorkerStatusBadge status={w.is_active ? 'ONLINE' : 'OFFLINE'} />
              )}
            </div>

            {/* Connecting status bar if laptop is actively handshaking */}
            {isConnecting && (
              <div className="laptop-connecting-strip">
                <Loader2 size={13} className="spin-animate" />
                <span>Establishing gRPC stream • Negotiating Llama 3.2 1B</span>
              </div>
            )}

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

              {/* Model Capability & Protocol Info */}
              <div className="worker-model-info">
                <div className="model-chip">
                  <Sparkles size={12} style={{ color: '#8B5CF6' }} />
                  <span>Model: Llama 3.2 1B</span>
                </div>
                <div className="protocol-chip">
                  <Radio size={11} style={{ color: '#10B981' }} />
                  <span>gRPC :50051</span>
                </div>
              </div>

              {/* Bottom Badges */}
              <div className="worker-card-footer">
                <div className="footer-badges">
                  <WorkerStatusBadge status={isConnecting ? 'CONNECTING' : w.health} />
                  <WorkerStatusBadge status={w.is_ready ? 'READY' : 'CONNECTING'} />
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
