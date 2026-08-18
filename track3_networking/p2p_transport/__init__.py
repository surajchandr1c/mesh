"""
Transport module for low-latency streaming and P2P communication.

gRPC is the primary transport. WebSocket is retained as a fallback path.
"""
from .grpc_service import MeshGrpcClient, MeshGrpcServer, MeshNodeService
from .ws_transport import MeshWebSocketRelay, WorkerWebSocketClient

__all__ = [
    "MeshGrpcClient",
    "MeshGrpcServer",
    "MeshNodeService",
    "MeshWebSocketRelay",
    "WorkerWebSocketClient",
]
