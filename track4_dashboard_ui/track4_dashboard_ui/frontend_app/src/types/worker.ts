export interface Worker {
  node_id: string;
  last_seen: string;
  is_active: boolean;
  cpu_utilization: number;
  ram_available_mb: number;
  is_ready: boolean;
  health: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | string;
  hostname?: string;
  os_platform?: string;
  role?: string;
  cpu_cores_physical?: number;
  cpu_cores_logical?: number;
  ram_used_gb?: number;
  ram_total_gb?: number;
  ram_percent?: number;
  disk_used_gb?: number;
  disk_total_gb?: number;
  disk_free_gb?: number;
  disk_percent?: number;
}
