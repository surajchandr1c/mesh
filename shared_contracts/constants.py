"""Redis key helper functions and constants for the Distributed AI Inference Mesh."""


class RedisKeys:
    # Stream key for pending task dispatch
    PENDING_TASKS = "mesh:tasks:pending"

    # Set key for active worker node IDs
    ACTIVE_NODES = "mesh:nodes:active"

    # PubSub channel for global dashboard activity feed
    EVENTS_BROADCAST = "mesh:events:broadcast"

    @staticmethod
    def task_stream(task_id: str) -> str:
        """Stream key carrying token chunks and control frames for a task."""
        return f"mesh:stream:{task_id}"

    @staticmethod
    def task_meta(task_id: str) -> str:
        """Hash key holding task state metadata (status, assigned_node, retry_count, updated_at)."""
        return f"mesh:tasks:{task_id}:meta"

    @staticmethod
    def task_abort(task_id: str) -> str:
        """String key set to signal cancellation to the assigned worker node."""
        return f"mesh:tasks:{task_id}:abort"

    @staticmethod
    def node_heartbeat(node_id: str) -> str:
        """String key holding worker node heartbeat timestamp."""
        return f"mesh:nodes:{node_id}:heartbeat"
