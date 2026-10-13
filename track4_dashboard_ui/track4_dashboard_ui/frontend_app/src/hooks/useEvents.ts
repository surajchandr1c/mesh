import { useState, useEffect, useCallback, useRef } from 'react';
import { FailoverEvent } from '../types/event';
import { api } from '../services/api';

const POLL_INTERVAL_MS = parseInt(
  (import.meta as any).env?.VITE_POLL_INTERVAL_MS || '5000',
  10
);

export function useEvents() {
  const [events, setEvents] = useState<FailoverEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchEvents = useCallback(async (isInitial = false) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (isInitial) setLoading(true);
    try {
      const data = await api.getEvents(controller.signal);
      if (!controller.signal.aborted) {
        setEvents(data);
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
    fetchEvents(true);

    const interval = setInterval(() => {
      fetchEvents(false);
    }, POLL_INTERVAL_MS);

    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [fetchEvents]);

  return { events, loading, error, refresh: () => fetchEvents(true) };
}
