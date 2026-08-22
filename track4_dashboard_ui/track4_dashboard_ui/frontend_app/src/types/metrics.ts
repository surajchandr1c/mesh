export interface WorkerMetrics {
  total: number;
  active: number;
  offline: number;
  busy: number;
  health_states: {
    healthy: number;
    degraded: number;
    unhealthy: number;
  };
  availability_rate: number;
}

export interface ResourceMetrics {
  avg_cpu: number;
  avg_ram_mb: number;
}

export interface TaskMetrics {
  total: number;
  processing: number;
  completed: number;
  failed: number;
  total_retries: number;
  retry_rate: number;
}

export interface ReliabilityMetrics {
  failover_count: number;
  failure_rate: number;
}

export interface MetricsSummary {
  workers: WorkerMetrics;
  resources: ResourceMetrics;
  tasks: TaskMetrics;
  reliability: ReliabilityMetrics;
}
