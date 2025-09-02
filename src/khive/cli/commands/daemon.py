"""
Khive daemon management commands - Ollama-style.

Commands:
  khive daemon start    - Start the daemon in background
  khive daemon stop     - Stop the daemon
  khive daemon status   - Check daemon status
  khive daemon logs     - View daemon logs
  khive daemon restart  - Restart the daemon
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import click
import psutil

from khive.daemon.client import get_daemon_client
from khive.utils import get_logger

logger = get_logger("KhiveDaemonCLI", "🎮 [DAEMON-CLI]")

# Daemon paths
PID_FILE = Path.home() / ".khive" / "daemon.pid"
LOG_FILE = Path.home() / ".khive" / "daemon.log"


@click.group()
def daemon():
    """Manage the khive daemon service."""


@daemon.command()
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
@click.option("--port", "-p", type=int, default=11634, help="Port to listen on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
def start(foreground: bool, port: int, host: str):
    """Start the khive daemon."""
    # Check if already running
    if _is_daemon_running():
        click.echo("✅ Khive daemon is already running")
        _show_status()
        return

    # Ensure directories exist
    PID_FILE.parent.mkdir(exist_ok=True)

    if foreground:
        # Run in foreground
        click.echo(f"Starting khive daemon in foreground on {host}:{port}...")
        os.environ["KHIVE_DAEMON_HOST"] = host
        os.environ["KHIVE_DAEMON_PORT"] = str(port)

        from khive.daemon.server import run_daemon_server
        import asyncio

        asyncio.run(run_daemon_server(host, port))
    else:
        # Start in background
        click.echo(f"Starting khive daemon on {host}:{port}...")

        env = os.environ.copy()
        env["KHIVE_DAEMON_HOST"] = host
        env["KHIVE_DAEMON_PORT"] = str(port)

        # Start daemon process
        with open(LOG_FILE, "a") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "khive.daemon.server"],
                stdout=log,
                stderr=log,
                env=env,
                start_new_session=True,  # Detach from terminal
            )

        # Wait a moment for startup
        time.sleep(2)

        # Check if started successfully
        client = get_daemon_client()
        client.base_url = f"http://{host}:{port}"

        if client.is_running():
            click.echo("✅ Khive daemon started successfully")
            _show_status()
        else:
            click.echo("❌ Failed to start daemon. Check logs with: khive daemon logs")
            sys.exit(1)


@daemon.command()
def stop():
    """Stop the khive daemon."""
    if not _is_daemon_running():
        click.echo("Khive daemon is not running")
        return

    # Try graceful shutdown via API first
    client = get_daemon_client()
    if client.shutdown():
        click.echo("Shutting down daemon gracefully...")
        time.sleep(1)

    # If still running, use PID file
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            os.kill(pid, signal.SIGTERM)
            click.echo("✅ Khive daemon stopped")
            PID_FILE.unlink()
        except (ProcessLookupError, ValueError):
            click.echo("Daemon process not found")
            PID_FILE.unlink()
    else:
        click.echo("No PID file found")


@daemon.command()
def status():
    """Check daemon status."""
    _show_status()


@daemon.command()
@click.option("--tail", "-n", type=int, default=50, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
def logs(tail: int, follow: bool):
    """View daemon logs."""
    if not LOG_FILE.exists():
        click.echo("No log file found")
        return

    if follow:
        # Follow logs
        subprocess.run(["tail", "-f", str(LOG_FILE)])
    else:
        # Show last N lines
        subprocess.run(["tail", f"-{tail}", str(LOG_FILE)])


@daemon.command()
def restart():
    """Restart the daemon."""
    click.echo("Restarting khive daemon...")

    # Stop if running
    if _is_daemon_running():
        client = get_daemon_client()
        client.shutdown()
        time.sleep(1)

    # Clean up PID file
    if PID_FILE.exists():
        PID_FILE.unlink()

    # Start again
    ctx = click.get_current_context()
    ctx.invoke(start)


@daemon.command()
def ps():
    """Show daemon process information."""
    if not _is_daemon_running():
        click.echo("Khive daemon is not running")
        return

    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            proc = psutil.Process(pid)

            click.echo(f"PID: {pid}")
            click.echo(f"Status: {proc.status()}")
            click.echo(f"CPU: {proc.cpu_percent()}%")
            click.echo(f"Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
            click.echo(
                f"Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc.create_time()))}"
            )

            # Get connections
            connections = proc.connections()
            if connections:
                click.echo("\nListening on:")
                for conn in connections:
                    if conn.status == "LISTEN":
                        click.echo(f"  {conn.laddr.ip}:{conn.laddr.port}")

        except (psutil.NoSuchProcess, ValueError):
            click.echo("Daemon process not found")


def _is_daemon_running() -> bool:
    """Check if daemon is running."""
    client = get_daemon_client()
    return client.is_running()


def _show_status():
    """Show daemon status."""
    client = get_daemon_client()

    if not client.is_running():
        click.echo("❌ Khive daemon is not running")
        click.echo("Start it with: khive daemon start")
        return

    # Get health info
    health = client.health()

    click.echo("✅ Khive daemon is running")
    click.echo(f"  Version: {health.get('version', 'unknown')}")
    click.echo(f"  Uptime: {health.get('uptime', 'unknown')}")

    stats = health.get("stats", {})
    if stats:
        click.echo(f"  Requests: {stats.get('requests', 0)}")
        click.echo(f"  Errors: {stats.get('errors', 0)}")

    click.echo("  API: http://127.0.0.1:11634/")


def cli_entry():
    """Entry point for khive CLI."""
    daemon()


if __name__ == "__main__":
    daemon()
