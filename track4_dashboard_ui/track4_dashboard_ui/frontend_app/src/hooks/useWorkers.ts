import { useState, useEffect, useCallback, useRef } from 'react';
import { Worker } from '../types/worker';
import { api } from '../services/api';

const POLL_INTERVAL_MS = parseInt(
  (import.meta as any).env?.VITE_POLL_INTERVAL_MS || '5000',
  10
);

export function useWorkers() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchWorkers = useCallback(async (isInitial = false) => {
    // Abort any in-flight request before starting a new one
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (isInitial) setLoading(true);
    try {
      const data = await api.getNodes(controller.signal);
      if (!controller.signal.aborted) {
        setWorkers(data);
        setError(null);
      }
    } catch (err: unknown) {
      if (controller.signal.aborted) return; // Component unmounted or request replaced
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
    fetchWorkers(true);

    const interval = setInterval(() => {
      fetchWorkers(false);
    }, POLL_INTERVAL_MS);

    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [fetchWorkers]);

  return { workers, loading, error, refresh: () => fetchWorkers(true) };
}
