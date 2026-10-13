import { Worker } from '../types/worker';
import { Task } from '../types/task';
import { FailoverEvent } from '../types/event';
import { MetricsSummary } from '../types/metrics';

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '';

// Default request timeout in milliseconds (configurable via env var)
const REQUEST_TIMEOUT_MS = parseInt(
  (import.meta as any).env?.VITE_REQUEST_TIMEOUT_MS || '25000',
  10
);

function getAuthToken(): string {
  if (typeof window !== 'undefined' && window.localStorage) {
    const token = localStorage.getItem('auth_token');
    if (token) return token;
  }
  return 'dev-token';
}

/**
 * Centralised API request wrapper with timeout, error handling,
 * and AbortController support for cleanup.
 */
async function request<T>(path: string, signal?: AbortSignal, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  // If an external signal is provided (e.g., from unmounting component),
  // propagate its abort to our internal controller.
  if (signal) {
    if (signal.aborted) {
      clearTimeout(timeoutId);
      controller.abort();
    } else {
      signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  const headers = new Headers(options?.headers || {});
  if (!headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${getAuthToken()}`);
  }

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      // Parse error body if available, but never expose raw server details
      let errorMessage = `API error: ${response.status}`;
      try {
        const body = await response.json();
        if (body && body.message) {
          errorMessage = body.message;
        } else if (body && body.detail) {
          errorMessage = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
        }
      } catch {
        // Could not parse JSON error body – use status text
      }
      throw new Error(errorMessage);
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    if ((err instanceof DOMException && err.name === 'AbortError') || controller.signal.aborted) {
      if (signal?.aborted && !timedOut) {
        // Cancelled by caller (e.g. poll refresh or component unmount)
        const abortErr = new Error('Request cancelled');
        abortErr.name = 'AbortError';
        throw abortErr;
      }
      throw new Error('Request timed out — please check that the Orchestrator server is running on port 8000');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  getHealth: (signal?: AbortSignal) => request<{ status: string; service?: string; redis?: string }>('/health', signal),
  getNodes: (signal?: AbortSignal) => request<Worker[]>('/api/nodes', signal),
  getNode: (nodeId: string, signal?: AbortSignal) => request<Worker>(`/api/nodes/${encodeURIComponent(nodeId)}`, signal),
  getTasks: (signal?: AbortSignal) => request<Task[]>('/api/tasks', signal),
  getTask: (taskId: string, signal?: AbortSignal) => request<Task>(`/api/tasks/${encodeURIComponent(taskId)}`, signal),
  getEvents: (signal?: AbortSignal) => request<FailoverEvent[]>('/api/events', signal),
  getMetricsSummary: (signal?: AbortSignal) => request<MetricsSummary>('/api/metrics/summary', signal),
  submitTask: (payload: { prompt: string; max_tokens?: number; rag_enabled?: boolean; target_model?: string }, signal?: AbortSignal) =>
    request<{ task_id: string; status: string; message: string; enriched_prompt?: string }>(
      '/api/v1/tasks/submit',
      signal,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({
          prompt: payload.prompt,
          max_tokens: payload.max_tokens ?? 256,
          rag_enabled: payload.rag_enabled ?? false,
          target_model: payload.target_model ?? 'llama3.2:1b',
        }),
      }
    ),
};
