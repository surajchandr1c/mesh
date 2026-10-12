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
  iconColor = '#3B82F6',
}) => {
  return (
    <div className="card metric-card">
      <div
        className="metric-card-icon"
        style={{
          background: `linear-gradient(135deg, ${iconColor}22 0%, ${iconColor}0a 100%)`,
          border: `1px solid ${iconColor}33`,
          color: iconColor,
        }}
      >
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
