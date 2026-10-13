import React, { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Workers } from './pages/Workers';
import { WorkerDetails } from './pages/WorkerDetails';
import { Tasks } from './pages/Tasks';
import { Events } from './pages/Events';
import { Metrics } from './pages/Metrics';
import { Sidebar, ActiveTab } from './components/Sidebar';
import { ClipboardList, Sun, Moon, Layers } from 'lucide-react';

const VALID_TABS: ActiveTab[] = ['dashboard', 'workers', 'tasks', 'events', 'metrics'];
const STORAGE_TAB_KEY = 'websync_active_tab';
const STORAGE_NODE_KEY = 'websync_selected_node_id';
const STORAGE_THEME_KEY = 'websync_theme';

function getInitialTab(): ActiveTab {
  if (typeof window !== 'undefined') {
    const hash = window.location.hash.replace('#', '').trim().toLowerCase() as ActiveTab;
    if (VALID_TABS.includes(hash)) {
      return hash;
    }
    const saved = window.localStorage?.getItem(STORAGE_TAB_KEY) as ActiveTab | null;
    if (saved && VALID_TABS.includes(saved)) {
      return saved;
    }
  }
  return 'dashboard';
}

function getInitialNodeId(): string | null {
  if (typeof window !== 'undefined') {
    return window.localStorage?.getItem(STORAGE_NODE_KEY) || null;
  }
  return null;
}

function getInitialTheme(): 'dark' | 'light' {
  if (typeof window !== 'undefined') {
    const saved = window.localStorage?.getItem(STORAGE_THEME_KEY);
    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
  }
  return 'dark';
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>(getInitialTab);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(getInitialNodeId);
  const [theme, setTheme] = useState<'dark' | 'light'>(getInitialTheme);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    try {
      window.localStorage?.setItem(STORAGE_THEME_KEY, nextTheme);
    } catch {
      // Ignore storage errors
    }
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

  // Persist activeTab and sync URL hash so refreshing stays on the same page
  React.useEffect(() => {
    try {
      window.localStorage?.setItem(STORAGE_TAB_KEY, activeTab);
      if (window.location.hash !== `#${activeTab}`) {
        window.history.replaceState(null, '', `#${activeTab}`);
      }
    } catch {
      // Ignore storage errors
    }
  }, [activeTab]);

  // Persist selectedNodeId across refreshes
  React.useEffect(() => {
    try {
      if (selectedNodeId) {
        window.localStorage?.setItem(STORAGE_NODE_KEY, selectedNodeId);
      } else {
        window.localStorage?.removeItem(STORAGE_NODE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  }, [selectedNodeId]);

  // Support browser back/forward hash navigation
  React.useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace('#', '').trim().toLowerCase() as ActiveTab;
      if (VALID_TABS.includes(hash)) {
        setActiveTab(hash);
      }
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

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

  const handleTabChange = (tab: ActiveTab) => {
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
              <span className="app-title">WebSync AI</span>
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
        {/* Sidebar Component */}
        <Sidebar activeTab={activeTab} onTabChange={handleTabChange} />

        {/* Main Content Area */}
        <main className="main-content">
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
};
