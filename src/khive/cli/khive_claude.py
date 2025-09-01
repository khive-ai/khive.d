"""
Claude Code Observability CLI

Command-line interface for managing hook monitoring, dashboard, and real-time server.
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Literal

import click

from khive import __version__ as version
from khive.services.claude.frontend.realtime_server import HookEventWebSocketServer
from khive.services.claude.hooks.hook_event import (
    HookEvent,
    HookEventBroadcaster,
    HookEventContent,
)


@click.group()
@click.version_option(version=version)
def cli():
    """Claude Code Observability - Hook monitoring and dashboard."""


@cli.command()
@click.option("--host", default="localhost", help="WebSocket server host")
@click.option("--port", default=8767, help="WebSocket server port")
def server(host: str, port: int):
    """Start the real-time WebSocket server for hook events."""
    click.echo(f"🚀 Starting WebSocket server on {host}:{port}")

    try:
        server = HookEventWebSocketServer(host=host, port=port)
        server.run_server()
    except KeyboardInterrupt:
        click.echo("\n🛑 Server stopped by user")
    except Exception as e:
        click.echo(f"❌ Server error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--port", default=8501, help="Streamlit dashboard port")
@click.option("--host", default="localhost", help="Dashboard host")
def dashboard(port: int, host: str):
    """Start the Streamlit observability dashboard."""
    click.echo(f"🎛️  Starting dashboard on http://{host}:{port}")

    try:
        # Get the path to the dashboard module
        dashboard_path = (
            Path(__file__).parent.parent
            / "services"
            / "claude"
            / "frontend"
            / "streamlit_dashboard.py"
        )

        # Start Streamlit
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(dashboard_path),
            "--server.port",
            str(port),
            "--server.address",
            host,
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ]

        click.echo(f"🔧 Running: {' '.join(cmd)}")
        subprocess.run(cmd)

    except KeyboardInterrupt:
        click.echo("\n🛑 Dashboard stopped by user")
    except Exception as e:
        click.echo(f"❌ Dashboard error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--dashboard-port", default=8501, help="Dashboard port")
@click.option("--server-port", default=8767, help="WebSocket server port")
@click.option("--host", default="localhost", help="Host for both services")
@click.option("--server-only", is_flag=True, help="Start only WebSocket server")
@click.option("--dashboard-only", is_flag=True, help="Start only dashboard")
def start(
    dashboard_port: int,
    server_port: int,
    host: str,
    server_only: bool,
    dashboard_only: bool,
):
    """Start both dashboard and WebSocket server."""

    if server_only and dashboard_only:
        click.echo(
            "❌ Cannot specify both --server-only and --dashboard-only", err=True
        )
        sys.exit(1)

    # Ensure daemon is running
    from khive.daemon.client import get_daemon_client

    daemon_client = get_daemon_client()

    if not daemon_client.is_running():
        click.echo("🚀 Starting khive daemon...")
        try:
            # Start daemon in background
            daemon_env = os.environ.copy()
            daemon_env["KHIVE_DAEMON_HOST"] = "127.0.0.1"
            daemon_env["KHIVE_DAEMON_PORT"] = "11634"

            daemon_process = subprocess.Popen(
                [sys.executable, "-m", "khive.daemon.server"],
                env=daemon_env,
                start_new_session=True,  # Detach from terminal
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for daemon to start
            time.sleep(3)

            # Verify daemon started
            if daemon_client.is_running():
                click.echo("✅ Daemon started successfully")
            else:
                click.echo(
                    "⚠️  Daemon may not have started properly, continuing anyway..."
                )

        except Exception as e:
            click.echo(f"⚠️  Could not start daemon: {e}")
            click.echo("   Continuing without daemon (some features may be limited)")
    else:
        click.echo("✅ Daemon is already running")

    from khive.utils import PROJECT_ROOT

    dot_claude = PROJECT_ROOT / ".claude"
    if not dot_claude.exists() or not dot_claude.is_dir():
        import shutil

        source_dot_claude = (
            Path(__file__).parent.parent / "toolkits" / "cc" / "dot_claude"
        )
        dest_dot_claude = PROJECT_ROOT / ".claude"
        shutil.copytree(
            source_dot_claude,
            dest_dot_claude,
            dirs_exist_ok=True,
        )
    processes = []

    try:
        if not dashboard_only:
            # Start WebSocket server in background
            click.echo(f"🚀 Starting WebSocket server on {host}:{server_port}")
            server_process = subprocess.Popen([
                sys.executable,
                "-m",
                "khive.cli.khive_claude",
                "server",
                "--host",
                host,
                "--port",
                str(server_port),
            ])
            processes.append(("WebSocket Server", server_process))
            time.sleep(2)  # Give server time to start

        if not server_only:
            # Start dashboard
            click.echo(f"🎛️  Starting dashboard on http://{host}:{dashboard_port}")
            dashboard_process = subprocess.Popen([
                sys.executable,
                "-m",
                "khive.cli.khive_claude",
                "dashboard",
                "--host",
                host,
                "--port",
                str(dashboard_port),
            ])
            processes.append(("Dashboard", dashboard_process))

        if processes:
            click.echo("✅ Services started successfully!")
            click.echo(
                f"📱 Dashboard: http://{host}:{dashboard_port}"
                if not server_only
                else ""
            )
            click.echo(
                f"🔌 WebSocket: ws://{host}:{server_port}" if not dashboard_only else ""
            )
            click.echo("🛑 Press Ctrl+C to stop all services")

            # Wait for processes
            try:
                for name, process in processes:
                    process.wait()
            except KeyboardInterrupt:
                click.echo("\n🛑 Shutting down services...")
                for name, process in processes:
                    process.terminate()
                    click.echo(f"   Stopped {name}")

    except Exception as e:
        click.echo(f"❌ Error starting services: {e}", err=True)
        # Clean up processes
        for name, process in processes:
            try:
                process.terminate()
            except (ProcessLookupError, OSError) as e:
                # Expected termination failure - process may already be stopped
                import logging

                logging.getLogger(__name__).debug(
                    f"Process {name} termination exception (expected): {e}"
                )
        sys.exit(1)


@cli.command()
@click.option("--limit", default=20, help="Number of recent events to show")
@click.option("--event-type", help="Filter by event type")
@click.option("--session-id", help="Filter by session ID")
def status(limit: int, event_type: str | None, session_id: str | None):
    """Show system status and recent hook events."""
    click.echo("🔍 Claude Code Observability Status")
    click.echo("=" * 40)

    async def get_status():
        try:
            # Get recent events
            if event_type:
                events = await HookEvent.get_by_type(event_type, limit=limit)
            elif session_id:
                events = await HookEvent.get_by_session(session_id, limit=limit)
            else:
                events = await HookEvent.get_recent(limit=limit)

            click.echo(f"📊 Total events retrieved: {len(events)}")

            if events:
                click.echo("\n📋 Recent Events:")
                click.echo("-" * 80)
                click.echo(
                    f"{'Time':<12} {'Type':<15} {'Tool':<10} {'Session':<10} {'Details':<30}"
                )
                click.echo("-" * 80)

                for event in reversed(events[-20:]):  # Show last 20, newest first
                    from khive.core import TimePolicy

                    if isinstance(event.created_at, int | float):
                        event_time = TimePolicy.from_timestamp_local(
                            event.created_at
                        ).strftime("%H:%M:%S")
                    else:
                        event_time = event.created_at.strftime("%H:%M:%S")
                    event_type_display = event.content.get("event_type", "unknown")[:14]
                    tool_name = event.content.get("tool_name", "unknown")[:9]
                    session_display = (
                        event.content.get("session_id", "unknown")[:8] + "..."
                        if event.content.get("session_id")
                        else "unknown"
                    )[:9]

                    # Get details based on event type
                    details = ""
                    if event_type_display == "pre_command":
                        command = event.content.get("command", "")
                        details = command[:25] + ("..." if len(command) > 25 else "")
                    elif event_type_display in ["pre_edit", "post_edit"]:
                        file_paths = event.content.get("file_paths", [])
                        if file_paths:
                            filename = (
                                file_paths[0].split("/")[-1]
                                if "/" in file_paths[0]
                                else file_paths[0]
                            )
                            details = filename[:25] + (
                                "..." if len(filename) > 25 else ""
                            )
                    elif event_type_display == "prompt_submitted":
                        prompt = event.content.get("metadata", {}).get("prompt", "")
                        details = prompt[:25] + ("..." if len(prompt) > 25 else "")

                    click.echo(
                        f"{event_time:<12} {event_type_display:<15} {tool_name:<10} {session_display:<10} {details:<30}"
                    )
            else:
                click.echo("📭 No events found")

            # Show subscriber count
            subscriber_count = HookEventBroadcaster.get_subscriber_count()
            click.echo(f"\n🔌 Real-time subscribers: {subscriber_count}")

        except Exception as e:
            click.echo(f"❌ Error retrieving status: {e}", err=True)

    # Run async function
    try:
        asyncio.run(get_status())
    except Exception as e:
        click.echo(f"❌ Status error: {e}", err=True)


@cli.command()
@click.option("--event-type", default="test", help="Event type to create")
@click.option("--tool-name", default="TestTool", help="Tool name for event")
@click.option("--session-id", help="Session ID for event")
def test(event_type: str, tool_name: str, session_id: str | None):
    """Create test hook events for testing the system."""
    click.echo(f"🧪 Creating test hook event: {event_type}")

    async def create_test_event():
        try:
            event = HookEvent(
                content=HookEventContent(
                    event_type=event_type,
                    tool_name=tool_name,
                    session_id=session_id,
                    metadata={
                        "test": True,
                        "created_by": "cli_test_command",
                        "description": "Test event created via CLI",
                    },
                )
            )

            result = await event.save()
            click.echo("✅ Test event created successfully")
            click.echo(f"   Event ID: {event.id}")
            click.echo(f"   Event Type: {event_type}")
            click.echo(f"   Tool: {tool_name}")
            click.echo(f"   Session: {session_id or 'None'}")

        except Exception as e:
            click.echo(f"❌ Error creating test event: {e}", err=True)

    try:
        asyncio.run(create_test_event())
    except Exception as e:
        click.echo(f"❌ Test error: {e}", err=True)


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to clear all hook events?")
def clear():
    """Clear all hook events from the database."""
    click.echo("🧹 Clearing all hook events...")

    async def clear_events():
        try:
            # This would require implementing a clear method on HookEvent
            # For now, we'll show a message
            click.echo("⚠️  Clear functionality not yet implemented")
            click.echo("   Database file: claude_hooks.db")
            click.echo("   You can manually delete this file to clear all events")

        except Exception as e:
            click.echo(f"❌ Error clearing events: {e}", err=True)

    try:
        asyncio.run(clear_events())
    except Exception as e:
        click.echo(f"❌ Clear error: {e}", err=True)


HOOK_TYPES = Literal[
    "pre_edit",
    "pre_command",
    "pre_agent_spawn",
    "post_edit",
    "post_agent_spawn",
    "post_command",
    "prompt_submitted",
    "notification",
]


@cli.command()
@click.option(
    "--kind",
    default="pre_command",
    help="Hook event kind, can be one of: pre_edit, pre_command, pre_agent_spawn, post_edit, post_agent_spawn, post_command, prompt_submitted, notification",
)
def hook(kind: HOOK_TYPES):
    try:
        # Get the path to the dashboard module

        hook_cmd = f"khive.services.claude.hooks.{kind}"

        # Start Streamlit
        cmd = [
            sys.executable,
            "-m",
            hook_cmd,
        ]

        click.echo(f"🔧 Running: {' '.join(cmd)}")
        subprocess.run(cmd)

    except KeyboardInterrupt:
        click.echo("\n🛑 Hook stopped by user")
    except Exception as e:
        click.echo(f"❌ Hook error: {e}", err=True)


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
