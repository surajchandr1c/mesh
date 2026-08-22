import { Worker } from '../types/worker';
import { Task } from '../types/task';
import { FailoverEvent } from '../types/event';
import { MetricsSummary } from '../types/metrics';

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '';

// Default request timeout in milliseconds (configurable via env var)
const REQUEST_TIMEOUT_MS = parseInt(
  (import.meta as any).env?.VITE_REQUEST_TIMEOUT_MS || '8000',
  10
);

/**
 * Centralised API request wrapper with timeout, error handling,
 * and AbortController support for cleanup.
 */
async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  // If an external signal is provided (e.g., from unmounting component),
  // propagate its abort to our internal controller.
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      signal: controller.signal,
    });

    if (!response.ok) {
      // Parse error body if available, but never expose raw server details
      let errorMessage = `API error: ${response.status}`;
      try {
        const body = await response.json();
        if (body && body.message) {
          errorMessage = body.message;
        }
      } catch {
        // Could not parse JSON error body – use status text
      }
      throw new Error(errorMessage);
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('Request timed out or was cancelled');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  getHealth: (signal?: AbortSignal) => request<{ status: string }>('/health', signal),
  getNodes: (signal?: AbortSignal) => request<Worker[]>('/api/nodes', signal),
  getNode: (nodeId: string, signal?: AbortSignal) => request<Worker>(`/api/nodes/${encodeURIComponent(nodeId)}`, signal),
  getTasks: (signal?: AbortSignal) => request<Task[]>('/api/tasks', signal),
  getTask: (taskId: string, signal?: AbortSignal) => request<Task>(`/api/tasks/${encodeURIComponent(taskId)}`, signal),
  getEvents: (signal?: AbortSignal) => request<FailoverEvent[]>('/api/events', signal),
  getMetricsSummary: (signal?: AbortSignal) => request<MetricsSummary>('/api/metrics/summary', signal),
};
