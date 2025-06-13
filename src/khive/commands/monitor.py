# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Khive Monitor Command

Provides comprehensive health monitoring for all 8 core khive services.
Displays real-time status, metrics, and alerts in various formats.
"""

import argparse
import asyncio
import json
import sys
import time
from typing import Any, Dict, List

from khive.services.monitoring.monitoring_service import MonitoringService
from khive.services.monitoring.parts import AlertConfig, MonitoringRequest


class MonitorCLI:
    """CLI interface for the monitoring service."""

    def __init__(self):
        self.monitoring_service = MonitoringService()

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser for the monitor command."""
        parser = argparse.ArgumentParser(
            prog="khive monitor",
            description="Monitor the health of all khive services",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  khive monitor                    # Show status dashboard
  khive monitor status             # Quick status check
  khive monitor health             # Detailed health check
  khive monitor metrics            # Show detailed metrics
  khive monitor --service info     # Monitor specific service
  khive monitor --watch            # Continuous monitoring
  khive monitor --json             # JSON output format
  khive monitor start              # Start continuous background monitoring
  khive monitor stop               # Stop background monitoring
  khive monitor server             # Start HTTP API server on port 8765
  khive monitor server --port 9000 # Start API server on custom port
            """,
        )

        # Subcommands
        parser.add_argument(
            "command",
            nargs="?",
            default="dashboard",
            choices=[
                "status",
                "health",
                "metrics",
                "dashboard",
                "start",
                "stop",
                "server",
            ],
            help="Monitoring command to execute (default: dashboard)",
        )

        # Service selection
        parser.add_argument(
            "--service",
            "-s",
            help="Specific service to monitor (dev, git, info, fmt, ci, mcp, new-doc, init)",
        )

        # Output format
        parser.add_argument(
            "--format",
            "-f",
            choices=["table", "json", "dashboard", "compact"],
            default="dashboard",
            help="Output format (default: dashboard)",
        )

        # Monitoring options
        parser.add_argument(
            "--watch",
            "-w",
            action="store_true",
            help="Continuously monitor and refresh display",
        )

        parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Refresh interval in seconds for watch mode (default: 5)",
        )

        parser.add_argument(
            "--include-metrics",
            action="store_true",
            help="Include detailed metrics in output",
        )

        parser.add_argument(
            "--include-history",
            action="store_true",
            help="Include historical data in output",
        )

        # JSON output
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output in JSON format",
        )

        # Quiet mode
        parser.add_argument(
            "--quiet",
            "-q",
            action="store_true",
            help="Minimal output, suitable for scripts",
        )

        # Server options
        parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Host to bind API server to (default: 127.0.0.1)",
        )

        parser.add_argument(
            "--port",
            type=int,
            default=8765,
            help="Port for API server (default: 8765)",
        )

        return parser

    async def execute(self, args: argparse.Namespace) -> int:
        """Execute the monitor command."""
        try:
            # Override format if --json is specified
            if args.json:
                args.format = "json"

            if args.command == "server":
                return await self._server_mode(args)
            elif args.watch:
                return await self._watch_mode(args)
            else:
                return await self._single_check(args)

        except KeyboardInterrupt:
            if not args.quiet:
                print("\nMonitoring interrupted by user")
            return 0
        except Exception as e:
            if not args.quiet:
                print(f"Error: {e}", file=sys.stderr)
            return 1
        finally:
            await self.monitoring_service.close()

    async def _single_check(self, args: argparse.Namespace) -> int:
        """Perform a single monitoring check."""
        request = MonitoringRequest(
            command=args.command,
            service_name=args.service,
            include_metrics=args.include_metrics,
            include_history=args.include_history,
            format=args.format,
        )

        response = await self.monitoring_service.handle_request(request)

        if args.format == "json":
            print(json.dumps(response.model_dump(), indent=2))
        else:
            self._display_response(response, args)

        # Return appropriate exit code
        if not response.success:
            return 1
        elif response.overall_status in ["unhealthy", "degraded"]:
            return 2 if response.overall_status == "unhealthy" else 1
        else:
            return 0

    async def _watch_mode(self, args: argparse.Namespace) -> int:
        """Continuous monitoring mode with auto-refresh."""
        if not args.quiet:
            print("Starting continuous monitoring... (Press Ctrl+C to stop)")
            print(f"Refresh interval: {args.interval} seconds\n")

        try:
            while True:
                # Clear screen for dashboard view
                if not args.quiet and args.format == "dashboard":
                    print("\033[2J\033[H", end="")  # ANSI clear screen

                await self._single_check(args)

                if not args.quiet and args.format != "json":
                    print(f"\nLast updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print("Press Ctrl+C to stop monitoring...")

                await asyncio.sleep(args.interval)

        except KeyboardInterrupt:
            if not args.quiet:
                print("\nMonitoring stopped by user")
            return 0

    async def _server_mode(self, args: argparse.Namespace) -> int:
        """Start the HTTP API server."""
        try:
            from khive.services.monitoring.api_server import MonitoringAPIServer

            server = MonitoringAPIServer(args.host, args.port)
            await server.start()

            if not args.quiet:
                print(
                    f"✅ Monitoring API server running on http://{args.host}:{args.port}"
                )
                print(f"🌐 Dashboard: http://{args.host}:{args.port}")
                print("📡 API endpoints available at:")
                print(f"   • GET http://{args.host}:{args.port}/health")
                print(f"   • GET http://{args.host}:{args.port}/status")
                print(f"   • GET http://{args.host}:{args.port}/metrics")
                print(f"   • GET http://{args.host}:{args.port}/alerts")
                print(
                    f"   • GET http://{args.host}:{args.port}/services/{{service_name}}"
                )
                print("\nPress Ctrl+C to stop the server...")

            # Keep the server running
            await server.server.serve_forever()

        except KeyboardInterrupt:
            if not args.quiet:
                print("\n🛑 Stopping monitoring API server...")
            return 0
        except Exception as e:
            if not args.quiet:
                print(f"❌ Server error: {e}", file=sys.stderr)
            return 1
        finally:
            if "server" in locals():
                await server.stop()

    def _display_response(self, response, args: argparse.Namespace) -> None:
        """Display the monitoring response in the specified format."""
        if args.quiet:
            # Minimal output for scripting
            if args.service:
                service = response.services[0] if response.services else {}
                print(service.get("status", "unknown"))
            else:
                print(response.overall_status)
            return

        if args.format == "compact":
            self._display_compact(response)
        elif args.format == "table":
            self._display_table(response, args)
        elif args.format == "dashboard":
            self._display_dashboard(response, args)
        else:
            # Default to table
            self._display_table(response, args)

    def _display_compact(self, response) -> None:
        """Display compact status information."""
        status_icon = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌",
            "unknown": "❓",
        }

        if response.services:
            for service in response.services:
                icon = status_icon.get(service["status"], "❓")
                name = service["name"]
                if "metrics" in service:
                    success_rate = service["metrics"]["success_rate"]
                    print(f"{icon} {name}: {service['status']} ({success_rate:.1f}%)")
                else:
                    print(f"{icon} {name}: {service['status']}")

        overall_icon = status_icon.get(response.overall_status, "❓")
        print(f"\nOverall: {overall_icon} {response.overall_status}")

        if response.summary:
            print(f"Summary: {response.summary}")

    def _display_table(self, response, args: argparse.Namespace) -> None:
        """Display information in table format."""
        if not response.services:
            print("No service data available")
            return

        # Table headers
        headers = [
            "Service",
            "Status",
            "Success Rate",
            "Avg Response",
            "Requests",
            "Last Check",
        ]
        if args.include_metrics:
            headers.extend(["Uptime", "Error Rate"])

        # Calculate column widths
        col_widths = [len(h) for h in headers]

        # Process data and calculate widths
        rows = []
        for service in response.services:
            name = service.get("display_name", service["name"])
            status = service["status"]

            if "metrics" in service:
                metrics = service["metrics"]
                success_rate = f"{metrics['success_rate']:.1f}%"
                avg_time = f"{metrics['average_response_time']:.3f}s"
                requests = str(metrics["total_requests"])
                last_check = time.strftime(
                    "%H:%M:%S", time.localtime(service["last_check"])
                )

                row = [name, status, success_rate, avg_time, requests, last_check]

                if args.include_metrics:
                    uptime = f"{metrics['uptime_seconds']:.1f}s"
                    error_rate = f"{metrics['error_rate']:.1f}%"
                    row.extend([uptime, error_rate])
            else:
                row = [name, status, "N/A", "N/A", "N/A", "N/A"]
                if args.include_metrics:
                    row.extend(["N/A", "N/A"])

            rows.append(row)

            # Update column widths
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Print table
        self._print_table_row(headers, col_widths)
        self._print_table_separator(col_widths)

        for row in rows:
            self._print_table_row(row, col_widths)

        # Summary
        print(f"\nOverall Status: {response.overall_status.upper()}")
        if response.summary:
            print(f"Summary: {response.summary}")

        # Alerts
        if response.alerts:
            print(f"\nActive Alerts ({len(response.alerts)}):")
            for alert in response.alerts:
                level_icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
                    alert["level"], "!"
                )
                timestamp = time.strftime(
                    "%H:%M:%S", time.localtime(alert["timestamp"])
                )
                print(
                    f"  {level_icon} [{timestamp}] {alert['service_name']}: {alert['message']}"
                )

    def _display_dashboard(self, response, args: argparse.Namespace) -> None:
        """Display dashboard-style information."""
        print("=" * 70)
        print("🔍 KHIVE SERVICE HEALTH MONITOR")
        print("=" * 70)

        if response.services:
            # Service grid
            services_per_row = 2
            services = response.services

            for i in range(0, len(services), services_per_row):
                row_services = services[i : i + services_per_row]

                # Service names
                for service in row_services:
                    name = service.get("display_name", service["name"])
                    print(f"┌─ {name:<30}", end="")
                print()

                # Status and metrics
                for service in row_services:
                    status_icon = {
                        "healthy": "✅",
                        "degraded": "⚠️",
                        "unhealthy": "❌",
                        "unknown": "❓",
                    }.get(service["status"], "❓")

                    if "metrics" in service:
                        metrics = service["metrics"]
                        print(
                            f"│ {status_icon} {service['status']:<12} {metrics['success_rate']:6.1f}%",
                            end="",
                        )
                    else:
                        print(
                            f"│ {status_icon} {service['status']:<12}   N/A  ", end=""
                        )
                print()

                # Additional metrics if available
                if args.include_metrics:
                    for service in row_services:
                        if "metrics" in service:
                            metrics = service["metrics"]
                            print(
                                f"│ {metrics['total_requests']:4d} req  {metrics['average_response_time']:6.3f}s",
                                end="",
                            )
                        else:
                            print(f"│      N/A       N/A   ", end="")
                    print()

                # Bottom border
                for service in row_services:
                    print("└" + "─" * 32, end="")
                print("\n")

        # Overall status
        overall_icon = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌",
            "unknown": "❓",
        }.get(response.overall_status, "❓")

        print(
            f"🌐 OVERALL STATUS: {overall_icon} {response.overall_status.upper()}"
        )
        if response.summary:
            print(f"📊 {response.summary}")

        # Alerts section
        if response.alerts:
            print(f"\n🚨 ACTIVE ALERTS ({len(response.alerts)}):")
            for alert in response.alerts:
                level_icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
                    alert["level"], "!"
                )
                timestamp = time.strftime(
                    "%H:%M:%S", time.localtime(alert["timestamp"])
                )
                print(
                    f"   {level_icon} [{timestamp}] {alert['service_name']}: {alert['message']}"
                )
        else:
            print("\n✨ No active alerts")

        print("=" * 70)

    def _print_table_row(self, row: List[str], widths: List[int]) -> None:
        """Print a table row with proper spacing."""
        formatted_cells = []
        for i, cell in enumerate(row):
            formatted_cells.append(f"{str(cell):<{widths[i]}}")
        print("│ " + " │ ".join(formatted_cells) + " │")

    def _print_table_separator(self, widths: List[int]) -> None:
        """Print table separator line."""
        parts = []
        for width in widths:
            parts.append("─" * width)
        print("├─" + "─┼─".join(parts) + "─┤")


async def async_main() -> int:
    """Async main function for the monitor command."""
    cli = MonitorCLI()
    parser = cli.create_parser()
    args = parser.parse_args()

    return await cli.execute(args)


def cli_entry() -> None:
    """Entry point for the monitor command."""
    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_entry()
