# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Monitoring API Server

Provides HTTP endpoints for external monitoring integration.
Lightweight server that exposes service health data via REST API.
"""

import asyncio
import json
import logging
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .monitoring_service import MonitoringService
from .parts import MonitoringRequest

logger = logging.getLogger(__name__)


class MonitoringAPIServer:
    """Simple HTTP server for monitoring API endpoints."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.monitoring_service = MonitoringService()
        self.server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        """Start the monitoring API server."""
        self.server = await asyncio.start_server(
            self.handle_request, self.host, self.port
        )

        logger.info(f"Monitoring API server started on http://{self.host}:{self.port}")
        logger.info("Available endpoints:")
        logger.info("  GET /health - Overall system health")
        logger.info("  GET /status - Service status summary")
        logger.info("  GET /metrics - Detailed metrics")
        logger.info("  GET /services/{service_name} - Specific service info")
        logger.info("  GET /alerts - Active alerts")

    async def stop(self) -> None:
        """Stop the monitoring API server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            await self.monitoring_service.close()
            logger.info("Monitoring API server stopped")

    async def handle_request(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming HTTP requests."""
        try:
            # Read the request
            request_line = await reader.readline()
            request_line = request_line.decode("utf-8").strip()

            if not request_line:
                await self._send_error_response(writer, 400, "Bad Request")
                return

            # Parse the request line
            method, path, _ = request_line.split(" ", 2)

            # Read headers (we don't need them for this simple server)
            while True:
                header = await reader.readline()
                if header == b"\r\n":
                    break

            # Route the request
            await self._route_request(writer, method, path)

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            await self._send_error_response(writer, 500, "Internal Server Error")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _route_request(
        self, writer: asyncio.StreamWriter, method: str, path: str
    ) -> None:
        """Route the request to the appropriate handler."""
        if method != "GET":
            await self._send_error_response(writer, 405, "Method Not Allowed")
            return

        # Parse URL and query parameters
        parsed_url = urlparse(path)
        path_parts = parsed_url.path.strip("/").split("/")
        query_params = parse_qs(parsed_url.query)

        try:
            if path_parts[0] == "health":
                await self._handle_health_endpoint(writer, query_params)
            elif path_parts[0] == "status":
                await self._handle_status_endpoint(writer, query_params)
            elif path_parts[0] == "metrics":
                await self._handle_metrics_endpoint(writer, query_params)
            elif path_parts[0] == "alerts":
                await self._handle_alerts_endpoint(writer, query_params)
            elif path_parts[0] == "services" and len(path_parts) > 1:
                await self._handle_service_endpoint(writer, path_parts[1], query_params)
            elif path_parts[0] == "" or path_parts[0] == "index.html":
                await self._handle_index_endpoint(writer)
            else:
                await self._send_error_response(writer, 404, "Not Found")
        except Exception as e:
            logger.error(f"Error in route handler: {e}", exc_info=True)
            await self._send_error_response(writer, 500, "Internal Server Error")

    async def _handle_health_endpoint(
        self, writer: asyncio.StreamWriter, query_params: dict
    ) -> None:
        """Handle /health endpoint."""
        request = MonitoringRequest(command="health", format="json")
        response = await self.monitoring_service.handle_request(request)

        # Simple health check response format
        health_data = {
            "status": response.overall_status.value,
            "timestamp": response.timestamp,
            "healthy": response.overall_status.value == "healthy",
            "services_count": len(response.services),
            "healthy_services": len([
                s for s in response.services if s.get("status") == "healthy"
            ]),
        }

        await self._send_json_response(writer, health_data)

    async def _handle_status_endpoint(
        self, writer: asyncio.StreamWriter, query_params: dict
    ) -> None:
        """Handle /status endpoint."""
        request = MonitoringRequest(command="status", format="json")
        response = await self.monitoring_service.handle_request(request)

        await self._send_json_response(writer, response.model_dump())

    async def _handle_metrics_endpoint(
        self, writer: asyncio.StreamWriter, query_params: dict
    ) -> None:
        """Handle /metrics endpoint."""
        include_metrics = "detailed" in query_params

        request = MonitoringRequest(
            command="metrics",
            format="json",
            include_metrics=include_metrics,
        )
        response = await self.monitoring_service.handle_request(request)

        await self._send_json_response(writer, response.model_dump())

    async def _handle_alerts_endpoint(
        self, writer: asyncio.StreamWriter, query_params: dict
    ) -> None:
        """Handle /alerts endpoint."""
        request = MonitoringRequest(command="status", format="json")
        response = await self.monitoring_service.handle_request(request)

        alerts_data = {
            "alerts": response.alerts,
            "count": len(response.alerts),
            "timestamp": response.timestamp,
        }

        await self._send_json_response(writer, alerts_data)

    async def _handle_service_endpoint(
        self, writer: asyncio.StreamWriter, service_name: str, query_params: dict
    ) -> None:
        """Handle /services/{service_name} endpoint."""
        request = MonitoringRequest(
            command="status",
            service_name=service_name,
            format="json",
            include_metrics=True,
        )
        response = await self.monitoring_service.handle_request(request)

        if response.services:
            await self._send_json_response(writer, response.services[0])
        else:
            await self._send_error_response(
                writer, 404, f"Service '{service_name}' not found"
            )

    async def _handle_index_endpoint(self, writer: asyncio.StreamWriter) -> None:
        """Handle index page with simple dashboard."""
        html_content = self._generate_dashboard_html()

        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html_content)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        writer.write(response.encode("utf-8"))
        writer.write(html_content.encode("utf-8"))
        await writer.drain()

    def _generate_dashboard_html(self) -> str:
        """Generate a simple HTML dashboard."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Khive Service Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .service { border: 1px solid #ddd; border-radius: 4px; padding: 15px; }
        .healthy { border-left: 4px solid #4CAF50; }
        .degraded { border-left: 4px solid #FF9800; }
        .unhealthy { border-left: 4px solid #F44336; }
        .unknown { border-left: 4px solid #9E9E9E; }
        .status { font-weight: bold; text-transform: uppercase; margin-bottom: 10px; }
        .metrics { font-size: 0.9em; color: #666; }
        .api-docs { background: #f9f9f9; padding: 15px; border-radius: 4px; margin-top: 20px; }
        code { background: #eee; padding: 2px 4px; border-radius: 2px; font-family: monospace; }
        .refresh-btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 10px 0; }
        .refresh-btn:hover { background: #45a049; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Khive Service Health Monitor</h1>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        
        <div id="services" class="services">
            <div class="service">Loading services...</div>
        </div>
        
        <div class="api-docs">
            <h3>📡 API Endpoints</h3>
            <p><strong>Health Check:</strong> <code>GET /health</code> - Simple health status</p>
            <p><strong>Full Status:</strong> <code>GET /status</code> - Complete service status</p>
            <p><strong>Metrics:</strong> <code>GET /metrics</code> - Detailed metrics</p>
            <p><strong>Alerts:</strong> <code>GET /alerts</code> - Active alerts</p>
            <p><strong>Service Info:</strong> <code>GET /services/{service_name}</code> - Specific service</p>
        </div>
    </div>
    
    <script>
        async function loadServices() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                
                const servicesDiv = document.getElementById('services');
                servicesDiv.innerHTML = '';
                
                data.services.forEach(service => {
                    const serviceDiv = document.createElement('div');
                    serviceDiv.className = `service ${service.status}`;
                    
                    const metrics = service.metrics || {};
                    
                    serviceDiv.innerHTML = `
                        <div class="status">${service.status} ${getStatusIcon(service.status)}</div>
                        <h4>${service.display_name || service.name}</h4>
                        <div class="metrics">
                            <div>Success Rate: ${metrics.success_rate?.toFixed(1) || 'N/A'}%</div>
                            <div>Avg Response: ${metrics.average_response_time?.toFixed(3) || 'N/A'}s</div>
                            <div>Total Requests: ${metrics.total_requests || 0}</div>
                            <div>Uptime: ${metrics.uptime_seconds?.toFixed(1) || 'N/A'}s</div>
                        </div>
                    `;
                    
                    servicesDiv.appendChild(serviceDiv);
                });
                
                // Update page title with overall status
                document.title = `Khive Monitor - ${data.overall_status.toUpperCase()}`;
                
            } catch (error) {
                console.error('Failed to load services:', error);
                document.getElementById('services').innerHTML = 
                    '<div class="service unknown">❌ Failed to load service data</div>';
            }
        }
        
        function getStatusIcon(status) {
            const icons = {
                'healthy': '✅',
                'degraded': '⚠️',
                'unhealthy': '❌',
                'unknown': '❓'
            };
            return icons[status] || '❓';
        }
        
        // Load services on page load
        loadServices();
        
        // Auto-refresh every 30 seconds
        setInterval(loadServices, 30000);
    </script>
</body>
</html>
        """

    async def _send_json_response(
        self, writer: asyncio.StreamWriter, data: dict
    ) -> None:
        """Send a JSON response."""
        json_data = json.dumps(data, indent=2)

        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(json_data)}\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        writer.write(response.encode("utf-8"))
        writer.write(json_data.encode("utf-8"))
        await writer.drain()

    async def _send_error_response(
        self, writer: asyncio.StreamWriter, status_code: int, message: str
    ) -> None:
        """Send an error response."""
        error_data = {"error": message, "status_code": status_code}
        json_data = json.dumps(error_data)

        response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(json_data)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        writer.write(response.encode("utf-8"))
        writer.write(json_data.encode("utf-8"))
        await writer.drain()


async def start_monitoring_server(
    host: str = "127.0.0.1", port: int = 8765
) -> MonitoringAPIServer:
    """Start the monitoring API server."""
    server = MonitoringAPIServer(host, port)
    await server.start()
    return server


if __name__ == "__main__":

    async def main():
        server = await start_monitoring_server()
        try:
            await server.server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down monitoring server...")
        finally:
            await server.stop()

    asyncio.run(main())
