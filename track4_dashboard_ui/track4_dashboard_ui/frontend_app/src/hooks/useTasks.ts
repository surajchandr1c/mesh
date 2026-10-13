import { useState, useEffect, useCallback, useRef } from 'react';
import { Task } from '../types/task';
import { api, getClientId, getMySubmittedTaskIds } from '../services/api';

const POLL_INTERVAL_MS = parseInt(
  (import.meta as any).env?.VITE_POLL_INTERVAL_MS || '2500',
  10
);

export function useTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchTasks = useCallback(async (isInitial = false) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (isInitial) setLoading(true);
    try {
      const data = await api.getTasks(controller.signal);
      if (!controller.signal.aborted) {
        const myClientId = getClientId();
        const myLocalTaskIds = new Set(getMySubmittedTaskIds());
        const ownTasks = data.filter(
          (t) =>
            t.client_id === myClientId ||
            myLocalTaskIds.has(t.task_id) ||
            (!t.client_id && Boolean(t.client_ip))
        );
        setTasks(ownTasks);
        setError(null);
      }
    } catch (err: unknown) {
      if (controller.signal.aborted || (err instanceof Error && err.name === 'AbortError')) return;
      if (!isInitial) return;
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      if (!controller.signal.aborted && isInitial) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks(true);

    const interval = setInterval(() => {
      fetchTasks(false);
    }, POLL_INTERVAL_MS);

    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [fetchTasks]);

  return { tasks, loading, error, refresh: () => fetchTasks(true) };
}
