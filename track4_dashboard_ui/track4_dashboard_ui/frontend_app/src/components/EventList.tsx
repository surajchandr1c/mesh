import React from 'react';
import { FailoverEvent } from '../types/event';
import { ShieldAlert, ArrowRight, Server, Terminal, Calendar } from 'lucide-react';
import { formatDate } from '../utils/formatters';

interface EventListProps {
  events: FailoverEvent[];
}

export const EventList: React.FC<EventListProps> = ({ events }) => {
  return (
    <div className="event-list">
      {events.map((event) => (
        <div key={event.event_id} className="card event-item">
          <div className="event-icon">
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                color: '#EF4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(239, 68, 68, 0.3)',
              }}
            >
              <ShieldAlert size={20} />
            </div>
          </div>
          <div className="event-details">
            <div className="event-header">
              <span className="event-title">Dynamic Reassignment #{event.event_id}</span>
              <span className="event-time">
                <Calendar size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                {formatDate(event.timestamp)}
              </span>
            </div>
            <hr className="event-divider" />
            <div className="event-body">
              <span className="event-task-id">
                <Terminal size={12} style={{ marginRight: '4px', verticalAlign: 'middle', color: '#3B82F6' }} />
                Target Task: {event.task_id}
              </span>
              <div className="event-nodes">
                <span className="node-route-badge failed">
                  <Server size={12} /> {event.failed_node_id} (Unresponsive)
                </span>
                <ArrowRight size={14} style={{ color: '#94A3B8', margin: '0 4px' }} />
                <span className={`node-route-badge ${event.reassigned_node_id ? 'recovered' : 'failed'}`}>
                  <Server size={12} /> {event.reassigned_node_id ? `${event.reassigned_node_id} (Assigned)` : 'None (Marked Failed)'}
                </span>
              </div>
              <div style={{ marginTop: '8px' }}>
                <span className="event-reason">Diagnosis: {event.reason}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
