import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  iconColor?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  iconColor = 'var(--primary)',
}) => {
  return (
    <div className="card metric-card">
      <div className="metric-card-icon" style={{ backgroundColor: `${iconColor}14`, color: iconColor }}>
        {icon}
      </div>
      <div className="metric-card-content">
        <span className="metric-card-title">{title}</span>
        <span className="metric-card-value">{value}</span>
        <span className="metric-card-subtitle">{subtitle}</span>
      </div>
    </div>
  );
};
