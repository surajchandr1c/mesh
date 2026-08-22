import React, { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Workers } from './pages/Workers';
import { WorkerDetails } from './pages/WorkerDetails';
import { Tasks } from './pages/Tasks';
import { Events } from './pages/Events';
import { Metrics } from './pages/Metrics';
import { LayoutDashboard, Server, ClipboardList, Shield, BarChart, Sun, Moon } from 'lucide-react';

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header bar */}
      <header className="app-header">
        <span className="app-title">QTHORIUM AICOMPUTEMESH</span>
        <button className="icon-btn" onClick={toggleTheme} title="Toggle Theme">
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </header>

      {/* Main layout container */}
      <div className="app-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div
            className={`sidebar-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => handleTabChange('dashboard')}
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </div>
          <div
            className={`sidebar-item ${activeTab === 'workers' ? 'active' : ''}`}
            onClick={() => handleTabChange('workers')}
          >
            <Server size={20} />
            <span>Workers</span>
          </div>
          <div
            className={`sidebar-item ${activeTab === 'tasks' ? 'active' : ''}`}
            onClick={() => handleTabChange('tasks')}
          >
            <ClipboardList size={20} />
            <span>Tasks</span>
          </div>
          <div
            className={`sidebar-item ${activeTab === 'events' ? 'active' : ''}`}
            onClick={() => handleTabChange('events')}
          >
            <Shield size={20} />
            <span>Events</span>
          </div>
          <div
            className={`sidebar-item ${activeTab === 'metrics' ? 'active' : ''}`}
            onClick={() => handleTabChange('metrics')}
          >
            <BarChart size={20} />
            <span>Metrics</span>
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
