import json
import asyncio
from typing import Set, Optional
from fastapi import WebSocket
import redis.asyncio as aioredis
from app.config.logging import logger

class ConnectionManager:
    """
    Manages local WebSocket connections and integrates with Redis Pub/Sub
    for multi-node horizontal scaling.
    """
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.pubsub_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected", count=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a closed WebSocket connection from the registry."""
        self.active_connections.discard(websocket)
        logger.info("WebSocket disconnected", count=len(self.active_connections))

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """Sends a JSON message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("Failed to send WebSocket message", error=str(e))
            self.disconnect(websocket)

    async def broadcast_local(self, message: dict) -> None:
        """Broadcasts a JSON message to all connections on this server instance."""
        if not self.active_connections:
            return
        
        # Make a copy of connections to avoid modification errors during loop
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("Failed to broadcast local WebSocket message", error=str(e))
                self.disconnect(connection)

    async def start_pubsub_listener(self, redis_client: aioredis.Redis) -> None:
        """
        Subscribes to Redis Pub/Sub channel in the background
        to listen for broadcasts originating from other backend nodes.
        """
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("ws_broadcast")
        
        async def _listen_loop():
            logger.info("Starting Redis Pub/Sub WebSocket listener loop")
            try:
                async for message in pubsub.listen():
                    if message and message.get("type") == "message":
                        try:
                            data = json.loads(message["data"])
                            await self.broadcast_local(data)
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error("Invalid Pub/Sub payload format received", error=str(e))
            except asyncio.CancelledError:
                logger.info("Redis Pub/Sub WebSocket listener loop cancelled")
            except Exception as e:
                logger.error("Error in Redis Pub/Sub subscription channel", error=str(e))
            finally:
                await pubsub.unsubscribe("ws_broadcast")
                await pubsub.close()

        self.pubsub_task = asyncio.create_task(_listen_loop())

    async def stop_pubsub_listener(self) -> None:
        """Cancels and cleans up the active Pub/Sub subscription loop task."""
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass
            self.pubsub_task = None
            logger.info("Redis Pub/Sub WebSocket listener stopped")

    async def publish_broadcast(self, redis_client: aioredis.Redis, message: dict) -> None:
        """
        Publishes a broadcast payload to the Redis broker to synchronize other nodes.
        """
        try:
            await redis_client.publish("ws_broadcast", json.dumps(message))
        except Exception as e:
            logger.error("Failed to publish WebSocket broadcast to Redis", error=str(e))

# Global connection manager instance
manager = ConnectionManager()
