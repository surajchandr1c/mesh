export interface Task {
  task_id: string;
  assigned_node_id: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  prompt: string;
  output?: string | null;
  max_tokens: number;
  retries: number;
  updated_at: string;
}
