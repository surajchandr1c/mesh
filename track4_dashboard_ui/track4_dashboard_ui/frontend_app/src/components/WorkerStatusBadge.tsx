import React from 'react';

interface WorkerStatusBadgeProps {
  status: 'ONLINE' | 'OFFLINE' | 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'READY' | 'NOT READY' | 'COMPLETED' | 'PROCESSING' | 'PENDING' | 'FAILED' | string;
}

export const WorkerStatusBadge: React.FC<WorkerStatusBadgeProps> = ({ status }) => {
  const normalized = (status || '').toUpperCase();

  const getBadgeConfig = () => {
    switch (normalized) {
      case 'ONLINE':
      case 'HEALTHY':
      case 'READY':
      case 'COMPLETED':
        return {
          bg: 'rgba(16, 185, 129, 0.12)',
          border: 'rgba(16, 185, 129, 0.3)',
          text: '#10B981',
          dot: '#10B981',
          pulse: false,
        };
      case 'PROCESSING':
        return {
          bg: 'rgba(59, 130, 246, 0.14)',
          border: 'rgba(59, 130, 246, 0.4)',
          text: '#3B82F6',
          dot: '#3B82F6',
          pulse: true,
        };
      case 'PENDING':
      case 'DEGRADED':
      case 'NOT READY':
        return {
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.35)',
          text: '#F59E0B',
          dot: '#F59E0B',
          pulse: false,
        };
      case 'OFFLINE':
      case 'UNHEALTHY':
      case 'FAILED':
        return {
          bg: 'rgba(239, 68, 68, 0.12)',
          border: 'rgba(239, 68, 68, 0.35)',
          text: '#EF4444',
          dot: '#EF4444',
          pulse: false,
        };
      default:
        return {
          bg: 'rgba(148, 163, 184, 0.12)',
          border: 'rgba(148, 163, 184, 0.3)',
          text: '#94A3B8',
          dot: '#94A3B8',
          pulse: false,
        };
    }
  };

  const config = getBadgeConfig();

  return (
    <span
      className="status-badge"
      style={{
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        color: config.text,
        padding: '3px 8px',
        borderRadius: '9999px',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        lineHeight: 1.2,
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: config.dot,
          boxShadow: config.pulse ? `0 0 8px ${config.dot}` : 'none',
        }}
      />
      {status}
    </span>
  );
};
