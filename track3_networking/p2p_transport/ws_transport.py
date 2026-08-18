"""
track3_networking/p2p_transport/ws_transport.py
Full WebSocket bidirectional streaming transport for Orchestrator and Worker Nodes.
"""

import asyncio
import json
import logging
from inspect import isawaitable
import websockets
from typing import Dict, Callable, Awaitable, Optional
from shared_contracts.schemas import TokenChunk, TaskRequest, HeartbeatPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WSTransport")


class MeshWebSocketRelay:
    """Server run by Orchestrator/Relay to route streams between worker nodes and clients."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.active_nodes: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.token_handlers: Dict[str, Callable[[TokenChunk], Awaitable[None]]] = {}
        self.heartbeat_handler: Optional[Callable[[HeartbeatPayload], Awaitable[None]]] = None
        self._server = None

    async def start(self):
        self._server = await websockets.serve(self._handle_connection, self.host, self.port)
        logger.info("Mesh WebSocket Relay running on ws://%s:%d", self.host, self.port)

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def register_heartbeat_handler(self, handler: Callable[[HeartbeatPayload], Awaitable[None]]):
        self.heartbeat_handler = handler

    def register_token_handler(self, task_id: str, handler: Callable[[TokenChunk], Awaitable[None]]):
        self.token_handlers[task_id] = handler

    def unregister_token_handler(self, task_id: str):
        self.token_handlers.pop(task_id, None)

    async def _handle_connection(self, websocket, path: str = ""):
        node_id = None
        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                    msg_type = data.get("type")

                    if msg_type == "REGISTER":
                        node_id = data.get("node_id")
                        self.active_nodes[node_id] = websocket
                        logger.info("Worker Node connected: %s", node_id)
                        await websocket.send(json.dumps({"type": "REGISTER_ACK", "status": "CONNECTED"}))

                    elif msg_type == "HEARTBEAT":
                        payload = HeartbeatPayload.model_validate(data.get("payload"))
                        if self.heartbeat_handler:
                            result = self.heartbeat_handler(payload)
                            if isawaitable(result):
                                await result
                        await websocket.send(json.dumps({"type": "HEARTBEAT_ACK", "timestamp": payload.timestamp}))

                    elif msg_type == "TOKEN_CHUNK":
                        chunk = TokenChunk.model_validate(data.get("payload"))
                        handler = self.token_handlers.get(chunk.task_id)
                        if handler:
                            await handler(chunk)

                except Exception as parse_err:
                    logger.error("Error parsing incoming message: %s", parse_err)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Node %s disconnected.", node_id)
        finally:
            if node_id and node_id in self.active_nodes:
                del self.active_nodes[node_id]


class WorkerWebSocketClient:
    """Client run by Teammate 1 (Worker Node) to stream tokens back to the orchestrator."""

    def __init__(self, relay_url: str = "ws://localhost:8765", node_id: str = "worker-01"):
        self.relay_url = relay_url
        self.node_id = node_id
        self.websocket = None
        self._running = False

    async def connect(self):
        """Connects and automatically registers the node."""
        self.websocket = await websockets.connect(self.relay_url)
        await self.websocket.send(json.dumps({
            "type": "REGISTER",
            "node_id": self.node_id
        }))
        ack = await self.websocket.recv()
        logger.info("Connected to Relay: %s", ack)
        self._running = True

    async def send_heartbeat(self, heartbeat: HeartbeatPayload):
        if not self.websocket or not self._running:
            return
        await self.websocket.send(json.dumps({
            "type": "HEARTBEAT",
            "payload": heartbeat.model_dump()
        }))

    async def stream_token(self, chunk: TokenChunk):
        if not self.websocket or not self._running:
            return
        await self.websocket.send(json.dumps({
            "type": "TOKEN_CHUNK",
            "payload": chunk.model_dump()
        }))

    async def close(self):
        self._running = False
        if self.websocket:
            await self.websocket.close()
