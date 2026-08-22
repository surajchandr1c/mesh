import { useState, useEffect, useCallback, useRef } from 'react';
import { Task } from '../types/task';
import { api } from '../services/api';

const POLL_INTERVAL_MS = parseInt(
  (import.meta as any).env?.VITE_POLL_INTERVAL_MS || '5000',
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
        setTasks(data);
        setError(null);
      }
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
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
