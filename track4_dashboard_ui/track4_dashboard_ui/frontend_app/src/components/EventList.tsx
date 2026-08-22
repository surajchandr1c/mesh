import React from 'react';
import { FailoverEvent } from '../types/event';
import { AlertTriangle } from 'lucide-react';

interface EventListProps {
  events: FailoverEvent[];
}

export const EventList: React.FC<EventListProps> = ({ events }) => {
  return (
    <div className="event-list">
      {events.map((event) => (
        <div key={event.event_id} className="card event-item">
          <div className="event-icon">
            <AlertTriangle color="orange" size={24} />
          </div>
          <div className="event-details">
            <div className="event-header">
              <span className="event-title">Failover Case #{event.event_id}</span>
              <span className="event-time">{event.timestamp}</span>
            </div>
            <hr className="event-divider" />
            <div className="event-body">
              <span className="event-task-id">Task ID: {event.task_id}</span>
              <div className="event-nodes">
                <span>Failed Node: <strong>{event.failed_node_id}</strong></span>
                <span>Reassigned Node:{' '}
                  <strong style={{ color: event.reassigned_node_id ? 'green' : 'red' }}>
                    {event.reassigned_node_id || 'NONE (Marked Failed)'}
                  </strong>
                </span>
              </div>
              <span className="event-reason">Reason: {event.reason}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
