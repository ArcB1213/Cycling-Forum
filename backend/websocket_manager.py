"""
WebSocket Connection Manager for Forum Comments
Manages WebSocket connections for real-time comment updates
"""
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class CommentWebSocketManager:
    """Manages WebSocket connections for forum post comments"""

    def __init__(self):
        # Store connections: {post_id: Set[WebSocket]}
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Reverse lookup: {WebSocket: post_id}
        self.connection_post_map: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, post_id: int) -> None:
        """
        Connect a WebSocket to a specific post
        Note: WebSocket should already be accepted before calling this method
        """
        if post_id not in self.active_connections:
            self.active_connections[post_id] = set()

        self.active_connections[post_id].add(websocket)
        self.connection_post_map[websocket] = post_id

        logger.info(f"WebSocket connected to post {post_id}. Total connections: {len(self.active_connections.get(post_id, set()))}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket from its post
        """
        post_id = self.connection_post_map.pop(websocket, None)

        if post_id and post_id in self.active_connections:
            self.active_connections[post_id].discard(websocket)

            # Clean up empty sets
            if not self.active_connections[post_id]:
                del self.active_connections[post_id]

        logger.info(f"WebSocket disconnected. Post: {post_id}, Remaining connections: {len(self.active_connections)}")

    async def broadcast_to_post(self, post_id: int, message: dict) -> None:
        """
        Broadcast a message to all connected clients of a specific post
        """
        if post_id not in self.active_connections:
            logger.debug(f"No active connections for post {post_id}")
            return

        # Prepare message once for all connections
        message_str = json.dumps(message, ensure_ascii=False, default=str)

        # Collect disconnected websockets to remove
        disconnected = set()

        for websocket in self.active_connections[post_id]:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send message to websocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            await self.disconnect(ws)

        logger.info(f"Broadcasted message to {len(self.active_connections.get(post_id, [])) - len(disconnected)} clients for post {post_id}")

    def get_connection_count(self, post_id: int) -> int:
        """
        Get the number of active connections for a post
        """
        return len(self.active_connections.get(post_id, set()))

    def get_total_connections(self) -> int:
        """
        Get the total number of active connections across all posts
        """
        return sum(len(connections) for connections in self.active_connections.values())


# Global singleton instance
comment_manager = CommentWebSocketManager()
