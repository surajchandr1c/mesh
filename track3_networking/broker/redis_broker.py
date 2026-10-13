"""
track3_networking/broker/redis_broker.py
Distributed Task Queue and Message Broker.
Supports Redis Streams & Priority Queues with graceful in-memory fallback.
"""

import asyncio
import json
import logging
from typing import Optional, AsyncGenerator, Dict, Any
from shared_contracts.schemas import TaskRequest, TokenChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MeshBroker")

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


import time as _time


class TaskBroker:
    _offline_until: float = 0.0

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client = None
        self._is_connected = False
        # In-memory fallback queues for offline testing
        self._memory_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._memory_streams: Dict[str, asyncio.Queue] = {}

    async def connect(self) -> bool:
        """Connects to Redis; if unavailable, falls back smoothly to in-memory mode."""
        if REDIS_AVAILABLE and _time.monotonic() >= TaskBroker._offline_until:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                    decode_responses=True,
                    protocol=2,
                )
                await self.redis_client.ping()
                self._is_connected = True
                logger.info("Connected successfully to Redis Broker at %s", self.redis_url)
                return True
            except Exception as e:
                TaskBroker._offline_until = _time.monotonic() + 60.0
                logger.warning("Redis connection failed (%s). Falling back to resilient In-Memory Broker.", e)
                if self.redis_client is not None:
                    try:
                        await self.redis_client.aclose()
                    except Exception:
                        pass
                self.redis_client = None
        elif not REDIS_AVAILABLE:
            logger.info("Redis library not found. Operating in In-Memory Broker mode.")

        self._is_connected = False
        return False

    async def enqueue_task(self, task: TaskRequest) -> bool:
        """Enqueues a task ordered by priority (higher priority number dequeued first)."""
        payload = task.model_dump_json()
        
        if self._is_connected and self.redis_client:
            try:
                # Priority queue in Redis sorted set or dedicated priority lists
                queue_name = f"mesh:tasks:priority_{task.priority.value}"
                await self.redis_client.lpush(queue_name, payload)
                return True
            except Exception as e:
                logger.error("Redis enqueue error: %s. Pushing to memory queue.", e)

        # In-memory fallback: store negative priority for standard min-heap behavior
        await self._memory_queue.put((-task.priority.value, task.created_at, payload))
        return True

    async def dequeue_task(self, timeout_sec: float = 2.0) -> Optional[TaskRequest]:
        """Dequeues the next highest-priority task."""
        if self._is_connected and self.redis_client:
            try:
                # Check priority queues descending
                for prio in [20, 10, 5, 1]:
                    queue_name = f"mesh:tasks:priority_{prio}"
                    raw = await self.redis_client.rpop(queue_name)
                    if raw:
                        return TaskRequest.model_validate_json(raw)
            except Exception as e:
                logger.error("Redis dequeue error: %s", e)

        # Memory queue fallback
        try:
            _, _, payload = await asyncio.wait_for(self._memory_queue.get(), timeout=timeout_sec)
            return TaskRequest.model_validate_json(payload)
        except asyncio.TimeoutError:
            return None

    async def publish_token_chunk(self, chunk: TokenChunk):
        """Publishes streaming token chunks to the task-specific channel."""
        channel_name = f"mesh:stream:{chunk.task_id}"
        payload = chunk.model_dump_json()

        if self._is_connected and self.redis_client:
            try:
                await self.redis_client.publish(channel_name, payload)
                return
            except Exception as e:
                logger.error("Redis publish error: %s", e)

        # Memory stream fallback
        if chunk.task_id not in self._memory_streams:
            self._memory_streams[chunk.task_id] = asyncio.Queue()
        await self._memory_streams[chunk.task_id].put(chunk)

    async def subscribe_token_stream(self, task_id: str, timeout_sec: float = 30.0) -> AsyncGenerator[TokenChunk, None]:
        """Streams tokens for a task until the final token is received or timeout."""
        start_time = asyncio.get_event_loop().time()
        
        if self._is_connected and self.redis_client:
            pubsub = self.redis_client.pubsub()
            channel_name = f"mesh:stream:{task_id}"
            await pubsub.subscribe(channel_name)
            try:
                while True:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > timeout_sec:
                        raise TimeoutError(f"Stream timed out for task {task_id}")

                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("data"):
                        chunk = TokenChunk.model_validate_json(message["data"])
                        yield chunk
                        if chunk.is_final:
                            break
                    await asyncio.sleep(0.01)
            finally:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            return

        # Memory stream fallback
        if task_id not in self._memory_streams:
            self._memory_streams[task_id] = asyncio.Queue()
        
        queue = self._memory_streams[task_id]
        while True:
            try:
                chunk: TokenChunk = await asyncio.wait_for(queue.get(), timeout=2.0)
                yield chunk
                if chunk.is_final:
                    break
            except asyncio.TimeoutError:
                if (asyncio.get_event_loop().time() - start_time) > timeout_sec:
                    break

    async def close(self):
        if self.redis_client and self._is_connected:
            await self.redis_client.close()
