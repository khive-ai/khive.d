"""
Khive agent coordination commands.

Commands:
  khive coordinate pre-task     - Initialize task coordination (before work)  
  khive coordinate check        - Check for conflicts before editing
  khive coordinate post-edit    - Report file operation (during work)
  khive coordinate post-task    - Complete task coordination (after work)
  khive coordinate status       - Get coordination status
"""

import sys
from typing import Optional

import click

from ..khive_coordinate import (
    pre_task,
    post_edit, 
    check_conflicts,
    post_task,
    get_status
)


@click.group()
def cli_entry():
    """Agent coordination commands for explicit multi-agent protocols."""
    pass


@cli_entry.command("pre-task")
@click.option("--description", required=True, help="Task description")
@click.option("--agent-id", required=True, help="Agent identifier")
@click.option("--coordination-id", help="Coordination session ID")
def cmd_pre_task(description: str, agent_id: str, coordination_id: Optional[str]):
    """Initialize task coordination - BEFORE starting work."""
    result = pre_task(agent_id, description, coordination_id)
    
    if result.get("success"):
        if result.get("warning"):
            click.echo(f"⚠️  {result['warning']}: {result.get('existing_task', '')}", err=True)
        click.echo(f"✅ {result['message']}")
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)


@cli_entry.command("check")
@click.option("--file", "file_path", required=True, help="File path to check")
@click.option("--agent-id", required=True, help="Agent identifier")  
def cmd_check_conflicts(file_path: str, agent_id: str):
    """Check for file conflicts - BEFORE editing files."""
    result = check_conflicts(agent_id, file_path)
    
    if result.get("success"):
        click.echo(f"🔓 {result['message']}")
    elif result.get("conflict"):
        click.echo(f"🚫 CONFLICT: {result['message']}", err=True)
        click.echo(f"   Locked by: {result.get('locked_by')}", err=True)
        click.echo(f"   Expires in: {result.get('expires_in')}s", err=True)
        sys.exit(2)  # Special exit code for conflicts
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)


@cli_entry.command("post-edit")
@click.option("--file", "file_path", required=True, help="File that was edited")
@click.option("--agent-id", required=True, help="Agent identifier")
@click.option("--operation", default="edit", help="Type of operation")
def cmd_post_edit(file_path: str, agent_id: str, operation: str):
    """Report file operation - AFTER editing files."""
    result = post_edit(agent_id, file_path, operation)
    
    if result.get("success"):
        click.echo(f"📝 {result['message']}")
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)


@cli_entry.command("post-task")
@click.option("--agent-id", required=True, help="Agent identifier")
@click.option("--summary", help="Task completion summary")
def cmd_post_task(agent_id: str, summary: Optional[str]):
    """Complete task coordination - AFTER finishing work."""
    result = post_task(agent_id, summary or "")
    
    if result.get("success"):
        click.echo(f"✅ {result['message']}")
        stats = result.get("coordination_stats", {})
        click.echo(f"📊 Active agents: {stats.get('active_agents', 0)}")
        click.echo(f"🛡️  Conflicts prevented: {stats.get('conflicts_prevented', 0)}")
        click.echo(f"🔄 Duplicates avoided: {stats.get('duplicates_avoided', 0)}")
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)


@cli_entry.command("status")
def cmd_status():
    """Get current coordination status."""
    result = get_status()
    
    if result.get("success"):
        status = result["status"]
        click.echo("📊 Coordination Status:")
        click.echo(f"  Active agents: {status.get('active_agents', 0)}")
        click.echo(f"  Locked files: {len(status.get('locked_files', []))}")
        click.echo(f"  Available artifacts: {len(status.get('available_artifacts', []))}")
        
        metrics = status.get("metrics", {})
        click.echo("📈 Metrics:")
        click.echo(f"  Conflicts prevented: {metrics.get('conflicts_prevented', 0)}")
        click.echo(f"  Duplicates avoided: {metrics.get('duplicates_avoided', 0)}")
        click.echo(f"  Artifacts shared: {metrics.get('artifacts_shared', 0)}")
        
        if status.get("active_work"):
            click.echo("\n👥 Active Work:")
            for work in status["active_work"]:
                duration = work.get("duration_seconds", 0)
                minutes = int(duration // 60)
                click.echo(f"  • {work['agent']}: {work['task']} ({minutes}m ago)")
                
        if status.get("locked_files"):
            click.echo("\n🔒 Locked Files:")
            for lock in status["locked_files"]:
                expires = lock.get("expires_in", 0)
                click.echo(f"  • {lock['file']} (by {lock['locked_by']}, expires {expires:.0f}s)")
                
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)