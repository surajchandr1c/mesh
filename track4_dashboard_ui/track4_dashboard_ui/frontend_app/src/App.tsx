import React, { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Workers } from './pages/Workers';
import { WorkerDetails } from './pages/WorkerDetails';
import { Tasks } from './pages/Tasks';
import { Events } from './pages/Events';
import { Metrics } from './pages/Metrics';
import { LayoutDashboard, Server, ClipboardList, Shield, BarChart, Sun, Moon, Layers } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workers' | 'tasks' | 'events' | 'metrics'>('dashboard');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    const root = document.documentElement;
    if (nextTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  };

  // Initialize theme class
  React.useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'workers':
        if (selectedNodeId) {
          return (
            <WorkerDetails
              nodeId={selectedNodeId}
              onBack={() => setSelectedNodeId(null)}
            />
          );
        }
        return <Workers onSelectNode={(id) => setSelectedNodeId(id)} />;
      case 'tasks':
        return <Tasks />;
      case 'events':
        return <Events />;
      case 'metrics':
        return <Metrics />;
      default:
        return <Dashboard />;
    }
  };

  const handleTabChange = (tab: typeof activeTab) => {
    setActiveTab(tab);
    // Reset worker details navigation whenever tab changes
    setSelectedNodeId(null);
  };

  return (
    <div className="app-root">
      {/* Header bar */}
      <header className="app-header">
        <div className="header-left">
          <div className="app-logo">
            <div className="app-logo-icon">
              <Layers size={20} />
            </div>
            <div className="app-title-group">
              <span className="app-title">QTHORIUM</span>
              <span className="app-tag">COMPUTE MESH</span>
            </div>
          </div>

          <div className="header-status-pill">
            <span className="pulse-indicator" />
            <span className="status-text">Mesh Active</span>
            <span className="model-chip">Llama 3.2 1B</span>
          </div>
        </div>

        <div className="header-right">
          <button
            className="btn btn-sm btn-outline-primary"
            onClick={() => handleTabChange('tasks')}
            title="Dispatch prompt to mesh"
          >
            <ClipboardList size={15} />
            <span>+ Dispatch Task</span>
          </button>

          <button
            className="icon-btn theme-toggle"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          >
            {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </div>
      </header>

      {/* Main layout container */}
      <div className="app-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-nav">
            <span className="sidebar-heading">CONSOLE</span>

            <div
              className={`sidebar-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => handleTabChange('dashboard')}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </div>
            <div
              className={`sidebar-item ${activeTab === 'workers' ? 'active' : ''}`}
              onClick={() => handleTabChange('workers')}
            >
              <Server size={18} />
              <span>Workers</span>
            </div>
            <div
              className={`sidebar-item ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => handleTabChange('tasks')}
            >
              <ClipboardList size={18} />
              <span>Task Registry</span>
            </div>
            <div
              className={`sidebar-item ${activeTab === 'events' ? 'active' : ''}`}
              onClick={() => handleTabChange('events')}
            >
              <Shield size={18} />
              <span>Failover Events</span>
            </div>
            <div
              className={`sidebar-item ${activeTab === 'metrics' ? 'active' : ''}`}
              onClick={() => handleTabChange('metrics')}
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

        {/* Main Content Area */}
        <main className="main-content">
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
};
