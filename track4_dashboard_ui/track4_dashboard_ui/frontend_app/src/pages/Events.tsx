import React from 'react';
import { useEvents } from '../hooks/useEvents';
import { EventList } from '../components/EventList';
import { RefreshCw, ShieldAlert } from 'lucide-react';

export const Events: React.FC = () => {
  const { events, loading, error, refresh } = useEvents();

  if (loading && events.length === 0) {
    return <div className="loading-container"><div className="spinner"></div>Loading failover events...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to load failover event logs.</p>
        <p className="error-message">{error}</p>
        <button className="btn" onClick={refresh}>Retry</button>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Failover Reassignment Events Log</h1>
        <button className="icon-btn" onClick={refresh} title="Reload events">
          <RefreshCw size={16} />
        </button>
      </div>

      {events.length === 0 ? (
        <div className="empty-container" style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center' }}>
          <ShieldAlert size={48} color="green" />
          <span>No failover events detected. Mesh is stable.</span>
        </div>
      ) : (
        <EventList events={events} />
      )}
    </div>
  );
};
