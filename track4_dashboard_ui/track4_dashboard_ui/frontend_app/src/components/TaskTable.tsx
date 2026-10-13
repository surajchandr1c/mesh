import React, { useState } from 'react';
import { Task } from '../types/task';
import { WorkerStatusBadge } from './WorkerStatusBadge';
import { formatDate } from '../utils/formatters';
import { Copy, Check, Server, RefreshCw, Calendar, Terminal } from 'lucide-react';

interface TaskTableProps {
  tasks: Task[];
}

export const TaskTable: React.FC<TaskTableProps> = ({ tasks }) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="task-list">
      {tasks.map((task) => {
        const displayDate = task.updated_at
          ? formatDate(task.updated_at)
          : formatDate(new Date().toISOString());

        const isFromPc2 =
          task.prompt.toLowerCase().includes('pc 2') ||
          task.prompt.toLowerCase().includes('pc2') ||
          (task.assigned_node_id && task.assigned_node_id !== 'gaming-desktop-01');

        const isExecutedOnPc2 =
          task.assigned_node_id && task.assigned_node_id !== 'gaming-desktop-01';

        return (
          <div key={task.task_id} className="card task-item">
            <div className="task-item-header">
              <div className="task-id-group" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span className="task-item-id">
                  <span className="task-id-prefix">TASK</span>
                  <span className="task-id-hash">{task.task_id}</span>
                </span>
                <button
                  className="icon-btn-inline"
                  onClick={(e) => handleCopy(task.task_id, e)}
                  title="Copy Task UUID"
                >
                  {copiedId === task.task_id ? (
                    <Check size={13} style={{ color: '#10B981' }} />
                  ) : (
                    <Copy size={13} />
                  )}
                </button>
                {isFromPc2 && (
                  <span
                    style={{
                      padding: '2px 8px',
                      borderRadius: '999px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      background: 'rgba(59, 130, 246, 0.15)',
                      color: '#3B82F6',
                      border: '1px solid rgba(59, 130, 246, 0.35)',
                    }}
                  >
                    📥 Task Received from PC 2
                  </span>
                )}
                {isExecutedOnPc2 && (
                  <span
                    style={{
                      padding: '2px 8px',
                      borderRadius: '999px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      background: 'rgba(16, 185, 129, 0.15)',
                      color: '#10B981',
                      border: '1px solid rgba(16, 185, 129, 0.35)',
                    }}
                  >
                    ⚡ Generated on PC 2 ({task.assigned_node_id})
                  </span>
                )}
              </div>
              <div className="task-header-right">
                <WorkerStatusBadge status={task.status} />
              </div>
            </div>

            <div className="task-item-body">
              <div className="task-prompt-container">
                <Terminal size={14} className="task-prompt-icon" />
                <p className="task-prompt">{task.prompt}</p>
              </div>

              {task.output && (
                <div
                  className="task-output-container"
                  style={{
                    marginTop: '10px',
                    padding: '10px 14px',
                    backgroundColor: '#F8FAFC',
                    borderLeft: '3px solid #10B981',
                    borderRadius: '6px',
                    fontSize: '0.88rem',
                    color: '#1E293B',
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.5,
                  }}
                >
                  <div
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      color: '#059669',
                      marginBottom: '4px',
                    }}
                  >
                    {isExecutedOnPc2
                      ? `⚡ Generated Output on PC 2 (${task.assigned_node_id})`
                      : `Generated Output (${task.assigned_node_id || 'Worker'})`}
                  </div>
                  {task.output}
                </div>
              )}

              <div className="task-details-row">
                <div className="detail-col">
                  <span className="detail-label">
                    <Server size={12} /> Assigned Node
                  </span>
                  <span className="detail-value node-pill">
                    {task.assigned_node_id || 'Unassigned (In Queue)'}
                  </span>
                </div>

                <div className="detail-col">
                  <span className="detail-label">
                    <RefreshCw size={12} /> Failover Retries
                  </span>
                  <span className={`detail-value ${task.retries > 0 ? 'warning-text' : ''}`}>
                    {task.retries} {task.retries === 1 ? 'retry' : 'retries'}
                  </span>
                </div>

                <div className="detail-col right-align">
                  <span className="detail-label">
                    <Calendar size={12} /> Last Updated
                  </span>
                  <span className="detail-value italic">{displayDate}</span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
