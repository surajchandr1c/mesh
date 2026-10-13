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

        return (
          <div key={task.task_id} className="card task-item">
            <div className="task-item-header">
              <div className="task-id-group">
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
                    Generated Output ({task.assigned_node_id || 'Worker'})
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
