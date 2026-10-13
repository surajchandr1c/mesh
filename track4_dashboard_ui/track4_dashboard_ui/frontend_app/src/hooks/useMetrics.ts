import { useState, useEffect, useCallback, useRef } from 'react';
import { MetricsSummary } from '../types/metrics';
import { api } from '../services/api';

const POLL_INTERVAL_MS = parseInt(
  (import.meta as any).env?.VITE_POLL_INTERVAL_MS || '3000',
  10
);

export function useMetrics() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchMetrics = useCallback(async (isInitial = false) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (isInitial) setLoading(true);
    try {
      const data = await api.getMetricsSummary(controller.signal);
      if (!controller.signal.aborted) {
        setMetrics(data);
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
    fetchMetrics(true);

    const interval = setInterval(() => {
      fetchMetrics(false);
    }, POLL_INTERVAL_MS);

    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [fetchMetrics]);

  return { metrics, loading, error, refresh: () => fetchMetrics(true) };
}
