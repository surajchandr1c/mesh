import React from 'react';

interface WorkerStatusBadgeProps {
  status: 'ONLINE' | 'OFFLINE' | 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'READY' | 'NOT READY' | string;
}

export const WorkerStatusBadge: React.FC<WorkerStatusBadgeProps> = ({ status }) => {
  const getColors = () => {
    switch (status.toUpperCase()) {
      case 'ONLINE':
      case 'HEALTHY':
      case 'READY':
        return { bg: '#81C78414', border: '#81C78480', text: '#81C784' };
      case 'DEGRADED':
      case 'NOT READY':
        return { bg: '#FFB74D14', border: '#FFB74D80', text: '#FFB74D' };
      case 'OFFLINE':
      case 'UNHEALTHY':
        return { bg: '#E5737314', border: '#E5737380', text: '#E57373' };
      default:
        return { bg: '#9E9E9E14', border: '#9E9E9E80', text: '#9E9E9E' };
    }
  };

  const colors = getColors();

  return (
    <span
      className="status-badge"
      style={{
        backgroundColor: colors.bg,
        border: `1px solid ${colors.border}`,
        color: colors.text,
        padding: '2px 6px',
        borderRadius: '4px',
        fontSize: '10px',
        fontWeight: 'bold',
        textTransform: 'uppercase',
        display: 'inline-flex',
        alignItems: 'center',
      }}
    >
      {status}
    </span>
  );
};
