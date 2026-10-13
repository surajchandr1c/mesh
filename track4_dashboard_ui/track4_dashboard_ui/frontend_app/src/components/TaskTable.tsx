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
  const [copiedOutputId, setCopiedOutputId] = useState<string | null>(null);

  const handleCopy = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCopyOutput = (taskId: string, outputText: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(outputText);
    setCopiedOutputId(taskId);
    setTimeout(() => setCopiedOutputId(null), 2000);
  };

  return (
    <div className="task-list">
      {tasks.map((task) => {
        const displayDate = task.updated_at
          ? formatDate(task.updated_at)
          : formatDate(new Date().toISOString());

        const isPendingOrProcessing =
          task.status.toUpperCase() === 'PENDING' || task.status.toUpperCase() === 'PROCESSING';

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
                  🔒 Your Task (Private to This PC)
                </span>
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

              {!task.output && isPendingOrProcessing && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '10px 14px',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    borderLeft: '3px solid #3B82F6',
                    borderRadius: '6px',
                    fontSize: '0.84rem',
                    color: '#60A5FA',
                    fontWeight: 500,
                  }}
                >
                  ⏳ Generating AI solution for your task on Llama 3.2 1B...
                </div>
              )}

              {task.output && (
                <div
                  className="task-output-container"
                  style={{
                    marginTop: '10px',
                    padding: '12px 14px',
                    backgroundColor: '#F8FAFC',
                    borderLeft: '3px solid #10B981',
                    borderRadius: '6px',
                    fontSize: '0.88rem',
                    color: '#1E293B',
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.55,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '6px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        color: '#059669',
                      }}
                    >
                      ✨ Generated Solution ({task.assigned_node_id || 'Llama 3.2 1B Worker'})
                    </span>
                    <button
                      className="icon-btn-inline"
                      onClick={(e) => handleCopyOutput(task.task_id, task.output || '', e)}
                      title="Copy Generated Solution"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '0.72rem',
                        color: '#059669',
                        fontWeight: 600,
                      }}
                    >
                      {copiedOutputId === task.task_id ? (
                        <>
                          <Check size={12} style={{ color: '#10B981' }} /> Copied
                        </>
                      ) : (
                        <>
                          <Copy size={12} /> Copy Answer
                        </>
                      )}
                    </button>
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
