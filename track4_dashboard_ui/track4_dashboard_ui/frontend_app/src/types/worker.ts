export interface Worker {
  node_id: string;
  last_seen: string;
  is_active: boolean;
  cpu_utilization: number;
  ram_available_mb: number;
  is_ready: boolean;
  health: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | string;
}
