# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: MIT

"""
Claude Code Observability - Real-time hook monitoring and dashboard.
"""

__version__ = "0.1.2"

from .frontend.realtime_server import HookEventWebSocketServer
from .frontend.streamlit_dashboard import ClaudeCodeObservabilityDashboard
from .hooks.hook_event import HookEvent, HookEventBroadcaster, HookEventContent

__all__ = [
    "HookEvent",
    "HookEventContent",
    "HookEventBroadcaster",
    "ClaudeCodeObservabilityDashboard",
    "HookEventWebSocketServer",
]
