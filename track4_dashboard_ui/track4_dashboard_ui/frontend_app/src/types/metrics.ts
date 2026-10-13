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
  hostname?: string;
  os_platform?: string;
  host_cpu_percent?: number;
  cpu_cores_physical?: number;
  cpu_cores_logical?: number;
  cpu_freq_mhz?: number;
  ram_used_mb?: number;
  ram_total_mb?: number;
  ram_used_gb?: number;
  ram_total_gb?: number;
  ram_available_mb?: number;
  ram_percent?: number;
  disk_used_gb?: number;
  disk_total_gb?: number;
  disk_free_gb?: number;
  disk_percent?: number;
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
