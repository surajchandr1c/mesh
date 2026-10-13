import React from 'react';
import { LayoutDashboard, Server, ClipboardList, Shield, BarChart } from 'lucide-react';

export type ActiveTab = 'dashboard' | 'workers' | 'tasks' | 'events' | 'metrics';

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-nav">
        <span className="sidebar-heading">CONSOLE</span>

        <div
          className={`sidebar-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onTabChange('dashboard')}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </div>
        <div
          className={`sidebar-item ${activeTab === 'workers' ? 'active' : ''}`}
          onClick={() => onTabChange('workers')}
        >
          <Server size={18} />
          <span>Workers</span>
        </div>
        <div
          className={`sidebar-item ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => onTabChange('tasks')}
        >
          <ClipboardList size={18} />
          <span>Task Registry</span>
        </div>
        <div
          className={`sidebar-item ${activeTab === 'events' ? 'active' : ''}`}
          onClick={() => onTabChange('events')}
        >
          <Shield size={18} />
          <span>Failover Events</span>
        </div>
        <div
          className={`sidebar-item ${activeTab === 'metrics' ? 'active' : ''}`}
          onClick={() => onTabChange('metrics')}
        >
          <BarChart size={18} />
          <span>Metrics & Stats</span>
        </div>
      </div>

      {/* Sidebar System Footer Card */}
      <div className="sidebar-footer">
        <div className="system-status-card">
          <div className="status-card-header">
            <span className="status-card-title">LOCAL MESH NODE</span>
            <span className="status-dot-active" />
          </div>
          <div className="status-spec-row">
            <span className="spec-label">Model:</span>
            <span className="spec-value">llama3.2:1b</span>
          </div>
          <div className="status-spec-row">
            <span className="spec-label">gRPC:</span>
            <span className="spec-value">:50051</span>
          </div>
          <div className="status-spec-row">
            <span className="spec-label">Gateway:</span>
            <span className="spec-value">:8000</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
