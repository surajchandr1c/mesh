import React from 'react';
import { Task } from '../types/task';
import { WorkerStatusBadge } from './WorkerStatusBadge';

interface TaskTableProps {
  tasks: Task[];
}

export const TaskTable: React.FC<TaskTableProps> = ({ tasks }) => {
  return (
    <div className="task-list">
      {tasks.map((task) => (
        <div key={task.task_id} className="card task-item">
          <div className="task-item-header">
            <span className="task-item-id">Task: {task.task_id}</span>
            <WorkerStatusBadge status={task.status} />
          </div>
          <div className="task-item-body">
            <p className="task-prompt">{task.prompt}</p>
            <div className="task-details-row">
              <div className="detail-col">
                <span className="detail-label">Assigned Node</span>
                <span className="detail-value">{task.assigned_node_id || 'Unassigned'}</span>
              </div>
              <div className="detail-col">
                <span className="detail-label">Failover Retries</span>
                <span className="detail-value">{task.retries}</span>
              </div>
              <div className="detail-col right-align">
                <span className="detail-label">Last Updated</span>
                <span className="detail-value italic">{task.updated_at}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
