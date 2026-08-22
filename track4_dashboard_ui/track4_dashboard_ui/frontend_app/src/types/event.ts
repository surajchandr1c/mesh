export interface FailoverEvent {
  event_id: number;
  timestamp: string;
  failed_node_id: string;
  reassigned_node_id: string | null;
  task_id: string;
  reason: string;
}
