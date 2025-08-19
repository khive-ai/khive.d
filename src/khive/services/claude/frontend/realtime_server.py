import asyncio
import json
import logging
import signal
from datetime import datetime
from typing import Set

import websockets

from khive.services.claude.hooks import HookEvent, HookEventBroadcaster
from khive.utils import get_logger

logger = get_logger("HookEventWebSocketServer", "🪝 [HOOK-EVENT-WSS]")

class HookEventWebSocketServer:
    """WebSocket server for real-time hook event broadcasting."""

    def __init__(self, host: str = "localhost", port: int = 8767):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.server = None
        self.running = False

        # Subscribe to hook event broadcasts
        HookEventBroadcaster.subscribe_async(self.broadcast_to_clients)

    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new WebSocket client."""
        self.clients.add(websocket)
        logger.info(
            f"Client connected from {websocket.remote_address}. Total clients: {len(self.clients)}"
        )

        # Send welcome message with recent events
        try:
            welcome_data = {
                "type": "welcome",
                "message": "Connected to Claude Code hook event stream",
                "timestamp": datetime.now().isoformat(),
                "server_info": {
                    "host": self.host,
                    "port": self.port,
                    "clients_connected": len(self.clients),
                },
            }

            await websocket.send(json.dumps(welcome_data))

            # Send recent events as initial data
            recent_events = await HookEvent.get_recent(limit=10)
            for event in recent_events:
                event_data = {
                    "type": "hook_event",
                    "timestamp": datetime.now().isoformat(),
                    "event": {
                        "id": event.id,
                        "timestamp": event.created_datetime.isoformat(),
                        "event_type": event.content.get("event_type"),
                        "tool_name": event.content.get("tool_name"),
                        "command": event.content.get("command"),
                        "output": event.content.get("output"),
                        "session_id": event.content.get("session_id"),
                        "file_paths": event.content.get("file_paths", []),
                        "metadata": event.content.get("metadata", {}),
                    },
                }
                await websocket.send(json.dumps(event_data))

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected during welcome message")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a WebSocket client."""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast_to_clients(self, hook_event: HookEvent):
        """Broadcast hook event to all connected WebSocket clients."""
        if not self.clients:
            return

        # Prepare event data for broadcasting
        event_data = {
            "type": "hook_event",
            "timestamp": datetime.now().isoformat(),
            "event": {
                "id": str(hook_event.id),
                "timestamp": hook_event.created_datetime.isoformat(),
                "event_type": hook_event.content.get("event_type"),
                "tool_name": hook_event.content.get("tool_name"),
                "command": hook_event.content.get("command"),
                "output": hook_event.content.get("output"),
                "session_id": hook_event.content.get("session_id"),
                "file_paths": hook_event.content.get("file_paths", []),
                "metadata": hook_event.content.get("metadata", {}),
            },
        }

        message = json.dumps(event_data)

        # Send to all clients
        disconnected_clients = []
        for client in self.clients.copy():
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.append(client)

        # Remove disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)

    async def handle_client_message(
        self, websocket: websockets.WebSocketServerProtocol, message: str
    ):
        """Handle incoming message from WebSocket client."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")

            if message_type == "ping":
                # Respond to ping with pong
                pong_data = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "server_time": datetime.now().isoformat(),
                }
                await websocket.send(json.dumps(pong_data))

            elif message_type == "get_recent_events":
                # Send recent events
                limit = data.get("limit", 20)
                recent_events = await HookEvent.get_recent(limit=limit)

                for event in recent_events:
                    event_data = {
                        "type": "hook_event",
                        "timestamp": datetime.now().isoformat(),
                        "event": {
                            "id": event.id,
                            "timestamp": event.created_datetime.isoformat(),
                            "event_type": event.content.get("event_type"),
                            "tool_name": event.content.get("tool_name"),
                            "command": event.content.get("command"),
                            "output": event.content.get("output"),
                            "session_id": event.content.get("session_id"),
                            "file_paths": event.content.get("file_paths", []),
                            "metadata": event.content.get("metadata", {}),
                        },
                    }
                    await websocket.send(json.dumps(event_data))

            elif message_type == "get_statistics":
                # Send server statistics
                total_events = len(await HookEvent.get_recent(limit=1000))
                stats_data = {
                    "type": "statistics",
                    "timestamp": datetime.now().isoformat(),
                    "stats": {
                        "connected_clients": len(self.clients),
                        "total_events": total_events,
                        "server_uptime": "N/A",  # TODO: Track server start time
                        "subscribers": HookEventBroadcaster.get_subscriber_count(),
                    },
                }
                await websocket.send(json.dumps(stats_data))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from client: {message}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    async def handle_client(
        self, websocket: websockets.WebSocketServerProtocol, path: str
    ):
        """Handle individual WebSocket client connection."""
        await self.register_client(websocket)

        try:
            # Listen for messages from client
            async for message in websocket:
                await self.handle_client_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed normally")
        except Exception as e:
            logger.error(f"Error in client handler: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start_server(self):
        """Start the WebSocket server."""
        if self.running:
            logger.warning("Server is already running")
            return

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
            )

            self.running = True
            logger.info(
                f"WebSocket server started successfully on ws://{self.host}:{self.port}"
            )

            # Send server start notification
            start_notification = {
                "type": "server_start",
                "timestamp": datetime.now().isoformat(),
                "message": f"WebSocket server started on {self.host}:{self.port}",
            }

            # Keep server running
            await self.server.wait_closed()

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            self.running = False
            raise

    async def stop_server(self):
        """Stop the WebSocket server."""
        if not self.running or not self.server:
            logger.warning("Server is not running")
            return

        logger.info("Stopping WebSocket server...")

        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients], return_exceptions=True
            )

        # Close server
        self.server.close()
        await self.server.wait_closed()

        self.running = False
        logger.info("WebSocket server stopped")

    def run_server(self):
        """Run the WebSocket server (blocking)."""
        try:
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down...")
                loop = asyncio.get_event_loop()
                loop.create_task(self.stop_server())

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Run server
            asyncio.run(self.start_server())

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("WebSocket server shutdown complete")


def main():
    """Main entry point for WebSocket server."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run server
    server = HookEventWebSocketServer()
    server.run_server()


if __name__ == "__main__":
    main()
