import { describe, it, expect } from 'vitest';
import { formatDate } from './formatters';
import { Worker } from '../types/worker';
import { Task } from '../types/task';
import { FailoverEvent } from '../types/event';
import { MetricsSummary } from '../types/metrics';

describe('formatDate Utility', () => {
  it('correctly parses ISO date strings', () => {
    const output = formatDate('2026-08-18T10:48:22+00:00');
    expect(output).toBeDefined();
    expect(output).not.toBe('N/A');
  });

  it('handles empty date string inputs safely', () => {
    expect(formatDate('')).toBe('N/A');
  });
});

describe('TypeScript Model Declarations', () => {
  it('instantiates Worker interfaces successfully', () => {
    const sampleWorker: Worker = {
      node_id: 'worker-1',
      last_seen: '2026-08-18',
      is_active: true,
      cpu_utilization: 35.5,
      ram_available_mb: 2048,
      is_ready: true,
      health: 'HEALTHY'
    };
    expect(sampleWorker.node_id).toBe('worker-1');
    expect(sampleWorker.cpu_utilization).toBe(35.5);
  });

  it('instantiates Task interfaces successfully', () => {
    const sampleTask: Task = {
      task_id: 'task-1',
      assigned_node_id: 'worker-1',
      status: 'completed',
      prompt: 'Summarize text',
      max_tokens: 256,
      retries: 0,
      updated_at: '2026-08-18'
    };
    expect(sampleTask.task_id).toBe('task-1');
    expect(sampleTask.status).toBe('completed');
  });

  it('instantiates FailoverEvent interfaces successfully', () => {
    const sampleEvent: FailoverEvent = {
      event_id: 42,
      timestamp: '2026-08-18',
      failed_node_id: 'worker-1',
      reassigned_node_id: 'worker-2',
      task_id: 'task-1',
      reason: 'Heartbeat timeout'
    };
    expect(sampleEvent.event_id).toBe(42);
    expect(sampleEvent.reason).toBe('Heartbeat timeout');
  });

  it('instantiates MetricsSummary interfaces successfully', () => {
    const sampleMetrics: MetricsSummary = {
      workers: {
        total: 2,
        active: 2,
        offline: 0,
        busy: 1,
        health_states: { healthy: 2, degraded: 0, unhealthy: 0 },
        availability_rate: 1.0
      },
      resources: {
        avg_cpu: 22.0,
        avg_ram_mb: 1024
      },
      tasks: {
        total: 10,
        processing: 1,
        completed: 9,
        failed: 0,
        total_retries: 2,
        retry_rate: 0.2
      },
      reliability: {
        failover_count: 1,
        failure_rate: 0.1
      }
    };
    expect(sampleMetrics.workers.total).toBe(2);
    expect(sampleMetrics.tasks.total_retries).toBe(2);
  });
});
