import React, { useState } from 'react';
import { useTasks } from '../hooks/useTasks';
import { TaskTable } from '../components/TaskTable';
import { api } from '../services/api';
import {
  RefreshCw,
  Search,
  PlusCircle,
  Send,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  X,
  Layers,
} from 'lucide-react';

export const Tasks: React.FC = () => {
  const { tasks, loading, error, refresh } = useTasks();
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Dispatch task form state
  const [showDispatchForm, setShowDispatchForm] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [maxTokens, setMaxTokens] = useState(256);
  const [ragEnabled, setRagEnabled] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccessMsg, setSubmitSuccessMsg] = useState<string | null>(null);
  const [submitErrorMsg, setSubmitErrorMsg] = useState<string | null>(null);

  const handleDispatchTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptText.trim()) return;

    setIsSubmitting(true);
    setSubmitSuccessMsg(null);
    setSubmitErrorMsg(null);

    try {
      const resp = await api.submitTask({
        prompt: promptText.trim(),
        max_tokens: maxTokens,
        rag_enabled: ragEnabled,
      });
      setSubmitSuccessMsg(`Task successfully dispatched! (ID: ${resp.task_id})`);
      setPromptText('');
      setTimeout(() => {
        refresh();
      }, 800);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setSubmitErrorMsg(err.message);
      } else {
        setSubmitErrorMsg(String(err));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading && tasks.length === 0) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <span>Retrieving mesh tasks from registry...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <p className="error-title">Unable to load task registry data.</p>
        <p className="error-message">{error}</p>
        <button className="btn" onClick={refresh}>Retry Connection</button>
      </div>
    );
  }

  // Count by status
  const counts = {
    all: tasks.length,
    pending: tasks.filter((t) => t.status.toUpperCase() === 'PENDING').length,
    processing: tasks.filter((t) => t.status.toUpperCase() === 'PROCESSING').length,
    completed: tasks.filter((t) => t.status.toUpperCase() === 'COMPLETED').length,
    failed: tasks.filter((t) => t.status.toUpperCase() === 'FAILED').length,
  };

  // Filter tasks by status & search query
  let filtered = tasks;
  if (statusFilter !== 'ALL') {
    filtered = filtered.filter((t) => t.status.toUpperCase() === statusFilter.toUpperCase());
  }
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(
      (t) =>
        t.task_id.toLowerCase().includes(q) ||
        t.prompt.toLowerCase().includes(q) ||
        (t.assigned_node_id && t.assigned_node_id.toLowerCase().includes(q))
    );
  }

  return (
    <div className="page-content">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title-row">
            <h1 className="page-title">Task Execution Registry</h1>
            <span className="live-pill">
              <span className="live-dot" /> Live Registry
            </span>
          </div>
          <span className="page-subtitle">
            Current Date: {new Date().toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })} • {tasks.length} total tasks recorded
          </span>
        </div>

        <div className="header-actions">
          <button
            className="btn btn-primary"
            onClick={() => setShowDispatchForm(!showDispatchForm)}
          >
            {showDispatchForm ? <X size={16} /> : <PlusCircle size={16} />}
            <span>{showDispatchForm ? 'Close Form' : 'Dispatch Task'}</span>
          </button>

          <button className="icon-btn" onClick={refresh} title="Refresh Task Registry">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Interactive Task Dispatch Form Drawer */}
      {showDispatchForm && (
        <div className="card dispatch-card">
          <div className="dispatch-card-header">
            <div className="dispatch-card-title">
              <Sparkles size={18} style={{ color: '#3B82F6' }} />
              <h3>Submit AI Inference Task to Compute Mesh</h3>
            </div>
            <span className="target-pill">Target: Llama 3.2 1B</span>
          </div>

          <form onSubmit={handleDispatchTask} className="dispatch-form">
            <div className="form-group">
              <label htmlFor="prompt-input">Prompt / Instruction</label>
              <textarea
                id="prompt-input"
                className="form-textarea"
                rows={3}
                placeholder="E.g., Explain quantum entanglement in simple terms, or write a Python binary search..."
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label htmlFor="max-tokens-select">Max Generation Tokens</label>
                <select
                  id="max-tokens-select"
                  className="form-select"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                >
                  <option value={128}>128 tokens (Fast)</option>
                  <option value={256}>256 tokens (Standard)</option>
                  <option value={512}>512 tokens (Detailed)</option>
                  <option value={1024}>1024 tokens (Long)</option>
                </select>
              </div>

              <div className="form-group-checkbox">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={ragEnabled}
                    onChange={(e) => setRagEnabled(e.target.checked)}
                  />
                  <span>Enable RAG Knowledge Retrieval</span>
                </label>
              </div>

              <div className="form-actions">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting || !promptText.trim()}
                >
                  <Send size={15} />
                  <span>{isSubmitting ? 'Dispatching...' : 'Submit to Mesh'}</span>
                </button>
              </div>
            </div>

            {submitSuccessMsg && (
              <div className="alert alert-success">
                <CheckCircle2 size={16} />
                <span>{submitSuccessMsg}</span>
              </div>
            )}

            {submitErrorMsg && (
              <div className="alert alert-error">
                <AlertCircle size={16} />
                <span>{submitErrorMsg}</span>
              </div>
            )}
          </form>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="control-bar">
        {/* Status Filter Tabs */}
        <div className="filter-tabs">
          <button
            className={`filter-tab ${statusFilter === 'ALL' ? 'active' : ''}`}
            onClick={() => setStatusFilter('ALL')}
          >
            All <span className="tab-count">{counts.all}</span>
          </button>
          <button
            className={`filter-tab ${statusFilter === 'PROCESSING' ? 'active' : ''}`}
            onClick={() => setStatusFilter('PROCESSING')}
          >
            Processing <span className="tab-count count-blue">{counts.processing}</span>
          </button>
          <button
            className={`filter-tab ${statusFilter === 'COMPLETED' ? 'active' : ''}`}
            onClick={() => setStatusFilter('COMPLETED')}
          >
            Completed <span className="tab-count count-green">{counts.completed}</span>
          </button>
          <button
            className={`filter-tab ${statusFilter === 'PENDING' ? 'active' : ''}`}
            onClick={() => setStatusFilter('PENDING')}
          >
            Pending <span className="tab-count count-amber">{counts.pending}</span>
          </button>
          <button
            className={`filter-tab ${statusFilter === 'FAILED' ? 'active' : ''}`}
            onClick={() => setStatusFilter('FAILED')}
          >
            Failed <span className="tab-count count-red">{counts.failed}</span>
          </button>
        </div>

        {/* Search Input */}
        <div className="search-box">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search prompt or Task ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="clear-btn" onClick={() => setSearchQuery('')}>
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Task List or Empty State */}
      {filtered.length === 0 ? (
        <div className="empty-container card">
          <Layers size={36} style={{ color: '#94A3B8', marginBottom: '12px' }} />
          <p className="empty-title">No tasks found matching current filters</p>
          <p className="empty-subtitle">
            {searchQuery
              ? `No task matches query "${searchQuery}". Clear search to view all.`
              : 'Dispatch a new task above or submit a request from PC 1.'}
          </p>
        </div>
      ) : (
        <TaskTable tasks={filtered} />
      )}
    </div>
  );
};
