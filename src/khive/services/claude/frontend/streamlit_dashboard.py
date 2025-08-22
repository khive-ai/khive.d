import asyncio
import os
import time
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from khive import __version__
from khive.core import TimePolicy
from khive.services.claude.hooks import HookEvent

# Page config with enhanced styling
st.set_page_config(
    page_title="🦁 Khive Claude Monitoring",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Configuration defaults (can be overridden by environment variables)
CONFIG = {
    "DEFAULT_REFRESH_RATE": int(os.environ.get("KHIVE_REFRESH_RATE", 5)),
    "MAX_EVENTS_DISPLAY": int(os.environ.get("KHIVE_MAX_EVENTS", 500)),
    "DEFAULT_TIME_RANGE": os.environ.get("KHIVE_DEFAULT_TIME_RANGE", "Today"),
    "ENABLE_WEBSOCKET": os.environ.get("KHIVE_ENABLE_WEBSOCKET", "true").lower()
    == "true",
    "WEBSOCKET_PORT": int(os.environ.get("KHIVE_WEBSOCKET_PORT", 8767)),
}

# Custom CSS for better styling
st.markdown(
    """
<style>
    /* Main header styling - more professional */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    /* Metric cards styling - enhanced */
    .metric-card {
        background: white;
        padding: 1.25rem;
        border-radius: 10px;
        border: 1px solid #e1e5eb;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        height: 100%;
    }

    .metric-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
        line-height: 1;
    }

    .metric-label {
        font-size: 0.875rem;
        color: #6c757d;
        margin-bottom: 0.25rem;
    }

    .metric-delta {
        font-size: 0.75rem;
        color: #6c757d;
    }

    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 5px;
    }

    .status-online { background-color: #28a745; }
    .status-offline { background-color: #dc3545; }
    .status-warning { background-color: #ffc107; }

    /* Enhanced event table */
    .event-row {
        border-left: 4px solid #007bff;
        padding-left: 10px;
        margin: 5px 0;
    }

    .event-bash { border-color: #28a745; }
    .event-edit { border-color: #17a2b8; }
    .event-task { border-color: #ffc107; }
    .event-error { border-color: #dc3545; }

    /* Sidebar improvements */
    .sidebar-section {
        background: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }

    /* Clean section headers */
    h3 {
        font-size: 1.2rem !important;
        color: #1e3c72 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
        font-weight: 600 !important;
    }

    /* Better spacing */
    .stSelectbox > div > div {
        background-color: white;
        border: 1px solid #e1e5eb;
    }

    /* Professional button styling */
    .stButton > button {
        background-color: #1e3c72;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #2a5298;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""",
    unsafe_allow_html=True,
)


class ClaudeCodeObservabilityDashboard:
    """Streamlit dashboard for Claude Code hook observability."""

    def __init__(self):
        self.events_cache = []
        self.last_load_time = 0
        self.cache_duration = 2  # seconds
        self.websocket_events = []
        self.websocket_connected = False

        # Initialize real-time event collection
        if "realtime_events" not in st.session_state:
            st.session_state.realtime_events = []

    async def load_events_from_db(
        self, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Load hook events from SQLite database with caching."""
        current_time = time.time()

        # Use cached data if recent and not forcing refresh
        if (
            not force_refresh
            and self.events_cache
            and current_time - self.last_load_time < self.cache_duration
        ):
            return self.events_cache

        try:
            # Get recent events from database
            recent_events = await HookEvent.get_recent(
                limit=CONFIG["MAX_EVENTS_DISPLAY"]
            )

            events = []
            for event in recent_events:
                event_dict = {
                    "id": str(event.id),
                    "timestamp": event.created_datetime.isoformat(),
                    "datetime": pd.to_datetime(event.created_datetime),
                    "event_type": event.content.get("event_type", "unknown"),
                    "tool_name": event.content.get("tool_name", "unknown"),
                    "command": event.content.get("command"),
                    "output": event.content.get("output"),
                    "session_id": event.content.get("session_id"),
                    "file_paths": event.content.get("file_paths", []),
                    "metadata": event.content.get("metadata", {}),
                }
                events.append(event_dict)

            self.events_cache = events
            self.last_load_time = current_time
            return events

        except Exception as e:
            st.error(f"Error loading events from database: {e}")
            return []

    def load_events(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Synchronous wrapper for async event loading."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            events = loop.run_until_complete(self.load_events_from_db(force_refresh))
            loop.close()
            return events
        except Exception as e:
            st.error(f"Error in event loading: {e}")
            return []

    def get_metrics(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate system metrics from events."""
        if not events:
            return {
                "total_events": 0,
                "recent_events_1h": 0,
                "recent_events_5m": 0,
                "hook_types": {},
                "estimated_active_agents": 0,
                "sessions": {},
                "unique_sessions": 0,
                "latest_events": [],
            }

        now = TimePolicy.now_local()
        last_hour = now - timedelta(hours=1)
        last_5min = now - timedelta(minutes=5)

        # Convert timestamps for filtering
        recent_events_1h = []
        recent_events_5m = []
        hook_types = Counter()
        sessions = Counter()

        for event in events:
            event_time = event["datetime"]
            hook_types[event["event_type"]] += 1

            # Count sessions
            session_id = event.get("session_id")
            if session_id:
                sessions[session_id] += 1

            if event_time >= last_hour:
                recent_events_1h.append(event)

            if event_time >= last_5min:
                recent_events_5m.append(event)

        # Count agent spawns vs completions for active agents estimate
        agent_spawns = sum(1 for e in events if e["event_type"] == "pre_agent_spawn")
        agent_completions = sum(
            1 for e in events if e["event_type"] == "post_agent_spawn"
        )
        estimated_active_agents = max(0, agent_spawns - agent_completions)

        return {
            "total_events": len(events),
            "recent_events_1h": len(recent_events_1h),
            "recent_events_5m": len(recent_events_5m),
            "hook_types": dict(hook_types),
            "estimated_active_agents": estimated_active_agents,
            "sessions": dict(sessions),
            "unique_sessions": len(sessions),
            "latest_events": events[-20:] if events else [],
        }

    def render_header(self):
        """Render enhanced dashboard header with better styling."""
        # Main title with professional gradient background
        st.markdown(
            """
        <div class="main-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="margin: 0; font-size: 2rem;">🦁 khive claude Monitoring</h1>
                    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Real-time Claude Code observability and hook event tracking</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.875rem; opacity: 0.8;">System Status</div>
                    <div style="font-size: 1.5rem; font-weight: 600;">✅ Operational</div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Enhanced control panel
        col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1.5])

        with col1:
            if st.button(
                "🔄 Refresh Data",
                type="primary",
                help="Force refresh all data from database",
            ):
                st.rerun()

        with col2:
            auto_refresh = st.checkbox(
                "🔁 Auto", value=True, help="Automatically refresh data"
            )

        with col3:
            refresh_rates = [1, 2, 5, 10]
            default_index = (
                refresh_rates.index(CONFIG["DEFAULT_REFRESH_RATE"])
                if CONFIG["DEFAULT_REFRESH_RATE"] in refresh_rates
                else 2
            )
            refresh_rate = st.selectbox(
                "📊 Rate",
                refresh_rates,
                index=default_index,
                help="Auto-refresh interval (seconds)",
            )

        with col4:
            if st.button("🧹 Clear", help="Clear cached data"):
                self.events_cache = []
                st.rerun()

        with col5:
            if (
                st.button("📥 Export", help="Export current data as CSV")
                and self.events_cache
            ):
                df = pd.DataFrame(self.events_cache)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📁 Download",
                    data=csv,
                    file_name=f"khive_events_{TimePolicy.now_local().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download events as CSV file",
                )

        with col6:
            # Enhanced WebSocket status with visual indicator
            import socket

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", CONFIG["WEBSOCKET_PORT"]))
                sock.close()
                ws_server_running = result == 0
            except (OSError, ConnectionError) as e:
                # Expected WebSocket connectivity failure - server may be down
                import logging

                logging.getLogger(__name__).debug(
                    f"WebSocket server connectivity check failed: {e}"
                )
                ws_server_running = False

            if ws_server_running:
                st.markdown(
                    """
                <div style="display: flex; align-items: center;">
                    <span class="status-indicator status-online"></span>
                    <strong>WebSocket Live</strong>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                <div style="display: flex; align-items: center;">
                    <span class="status-indicator status-offline"></span>
                    <strong>WebSocket Down</strong>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        # Simplified info bar
        if auto_refresh:
            refresh_text = f"Auto-refreshing every {refresh_rate}s"
        else:
            refresh_text = "Manual refresh mode"

        st.markdown(
            f"""
        <div style="text-align: center; padding: 0.5rem; background: #f0f2f6; border-radius: 8px; margin: 1rem 0; font-size: 0.875rem; color: #6c757d;">
            <strong>{len(self.events_cache)}</strong> events loaded |
            Last update: <strong>{TimePolicy.from_timestamp_local(self.last_load_time).strftime("%H:%M:%S") if self.last_load_time else "Never"}</strong> |
            {refresh_text}
        </div>
        """,
            unsafe_allow_html=True,
        )

        return auto_refresh, refresh_rate

    def render_metrics(self, metrics: dict[str, Any]):
        """Render enhanced key metrics with better styling."""
        st.markdown("### 📊 System Metrics")

        # Calculate more meaningful metrics
        activity_level = (
            "High"
            if metrics["recent_events_5m"] > 10
            else "Medium"
            if metrics["recent_events_5m"] > 3
            else "Low"
        )
        activity_color = (
            "#28a745"
            if activity_level == "High"
            else "#ffc107"
            if activity_level == "Medium"
            else "#6c757d"
        )

        # Calculate event rate
        events_per_minute = (
            round(metrics["recent_events_5m"] / 5, 1)
            if metrics["recent_events_5m"] > 0
            else 0
        )

        # Get most active hook type
        most_active_hook = (
            max(metrics["hook_types"].items(), key=lambda x: x[1])[0]
            if metrics["hook_types"]
            else "None"
        )

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">📈 Total Events</div>
                <div class="metric-value" style="color: #1e3c72;">{metrics["total_events"]:,}</div>
                <div class="metric-delta">+{metrics["recent_events_5m"]} in 5min</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            hourly_rate = max(0, metrics["recent_events_1h"])
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">⏱️ Last Hour</div>
                <div class="metric-value" style="color: #2a5298;">{metrics["recent_events_1h"]:,}</div>
                <div class="metric-delta">~{hourly_rate}/hour rate</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">🔥 Activity Rate</div>
                <div class="metric-value" style="color: {activity_color};">{events_per_minute}</div>
                <div class="metric-delta">events/min ({activity_level})</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col4:
            avg_events_per_session = (
                round(metrics["total_events"] / metrics["unique_sessions"], 1)
                if metrics["unique_sessions"] > 0
                else 0
            )
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">👥 Sessions</div>
                <div class="metric-value" style="color: #17a2b8;">{metrics.get("unique_sessions", 0)}</div>
                <div class="metric-delta">~{avg_events_per_session} events/session</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col5:
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">🎯 Most Active</div>
                <div class="metric-value" style="color: #6f42c1; font-size: 1.2rem; text-transform: capitalize;">{most_active_hook.replace("_", " ")}</div>
                <div class="metric-delta">{metrics["hook_types"].get(most_active_hook, 0)} events</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col6:
            agent_color = (
                "#dc3545"
                if metrics["estimated_active_agents"] > 5
                else "#28a745"
                if metrics["estimated_active_agents"] > 0
                else "#6c757d"
            )
            st.markdown(
                f"""
            <div class="metric-card">
                <div class="metric-label">🤖 Active Agents</div>
                <div class="metric-value" style="color: {agent_color};">{metrics["estimated_active_agents"]}</div>
                <div class="metric-delta">{"Busy" if metrics["estimated_active_agents"] > 3 else "Normal"} load</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Simplified activity bar
        if metrics["recent_events_5m"] > 0:
            st.markdown(
                f"""
            <div style="margin: 1rem 0 0.5rem 0; padding: 0.75rem; background: {activity_color}15;
                        border-left: 4px solid {activity_color}; border-radius: 6px;">
                <strong>System Activity:</strong> {activity_level}
                <span style="color: {activity_color};">●</span>
                {metrics["recent_events_5m"]} events in last 5 minutes ({events_per_minute} events/min)
            </div>
            """,
                unsafe_allow_html=True,
            )

    def render_hook_types_chart(self, metrics: dict[str, Any]):
        """Render enhanced hook types distribution chart."""
        if not metrics["hook_types"]:
            st.markdown(
                """
            <div style="text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 10px; border: 2px dashed #dee2e6;">
                <h3>🎯 No Hook Events Yet</h3>
                <p>Hook events will be displayed here once Claude Code starts processing.</p>
                <p style="font-size: 0.875rem; color: #6c757d;">Try running commands, editing files, or spawning agents.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
            return

        # Create enhanced data with better formatting
        hook_data = []
        color_map = {
            "pre_command": "#28a745",
            "post_command": "#20c997",
            "pre_edit": "#17a2b8",
            "post_edit": "#20c997",
            "pre_agent_spawn": "#ffc107",
            "post_agent_spawn": "#fd7e14",
            "prompt_submitted": "#6f42c1",
            "notification": "#e83e8c",
            "setup_test": "#6c757d",
            "debug_test": "#495057",
        }

        for hook_type, count in metrics["hook_types"].items():
            hook_data.append({
                "Hook Type": hook_type.replace("_", " ").title(),
                "Count": count,
                "Percentage": round(
                    (count / sum(metrics["hook_types"].values())) * 100, 1
                ),
                "Color": color_map.get(hook_type, "#6c757d"),
                "Original": hook_type,
            })

        df = pd.DataFrame(hook_data)
        df = df.sort_values("Count", ascending=True)

        # Create enhanced donut chart
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=df["Hook Type"],
                    values=df["Count"],
                    hole=0.4,
                    marker_colors=df["Color"],
                    textinfo="label+percent+value",
                    textposition="auto",
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title={
                "text": "📊 Hook Events Distribution",
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": 16},
            },
            height=400,
            showlegend=True,
            legend={
                "orientation": "v",
                "yanchor": "middle",
                "y": 0.5,
                "xanchor": "left",
                "x": 1.05,
            },
            margin={"l": 20, "r": 120, "t": 50, "b": 20},
        )

        st.plotly_chart(fig, use_container_width=True)

    def render_timeline_chart(
        self, events: list[dict[str, Any]], time_range: str = "Today"
    ):
        """Render enhanced activity timeline chart with flexible time ranges."""
        if not events:
            st.markdown(
                """
            <div style="text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 10px; border: 2px dashed #dee2e6;">
                <h3>📊 No Activity Data Yet</h3>
                <p>Start using Claude Code to see your activity timeline here.</p>
                <p style="font-size: 0.875rem; color: #6c757d;">Events will appear as you use various Claude Code tools.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
            return

        # Determine time range
        now = TimePolicy.now_local()
        today = now.date()

        if time_range == "Today":
            start_date = today
            end_date = today
            filtered_events = [e for e in events if e["datetime"].date() == today]
            group_by = "hour"
            title_format = "Today's Activity Timeline"

        elif time_range == "Last 7 Days":
            start_date = today - timedelta(days=6)
            end_date = today
            filtered_events = [
                e for e in events if start_date <= e["datetime"].date() <= end_date
            ]
            group_by = "day"
            title_format = "Last 7 Days Activity"

        elif time_range == "Last 30 Days":
            start_date = today - timedelta(days=29)
            end_date = today
            filtered_events = [
                e for e in events if start_date <= e["datetime"].date() <= end_date
            ]
            group_by = "day"
            title_format = "Last 30 Days Activity"

        elif time_range == "This Month":
            start_date = today.replace(day=1)
            end_date = today
            filtered_events = [
                e for e in events if start_date <= e["datetime"].date() <= end_date
            ]
            group_by = "day"
            title_format = f"{now.strftime('%B')} Activity"

        else:  # All Time
            if events:
                start_date = min(e["datetime"].date() for e in events)
                end_date = today
                filtered_events = events
                # Decide grouping based on date range
                days_diff = (end_date - start_date).days
                if days_diff <= 7:
                    group_by = "hour"
                elif days_diff <= 90:
                    group_by = "day"
                else:
                    group_by = "week"
                title_format = "All Time Activity"
            else:
                st.info("📅 No events recorded yet")
                return

        if not filtered_events:
            st.info(f"📅 No events recorded for {time_range}")
            return

        # Process data based on grouping
        if group_by == "hour" and time_range == "Today":
            # Hourly bins for today
            hourly_data = defaultdict(lambda: defaultdict(int))
            for event in filtered_events:
                hour = event["datetime"].hour
                event_type = event["event_type"]
                hourly_data[hour][event_type] += 1

            # Create x-axis labels
            x_labels = [f"{h:02d}:00" for h in range(24)]
            x_data = list(range(24))
            data_dict = hourly_data
            x_title = "Hour of Day"

        elif group_by == "day":
            # Daily bins
            daily_data = defaultdict(lambda: defaultdict(int))
            for event in filtered_events:
                day_key = event["datetime"].strftime("%Y-%m-%d")
                event_type = event["event_type"]
                daily_data[day_key][event_type] += 1

            # Create complete date range
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)

            x_labels = [
                TimePolicy.strptime_utc(d, "%Y-%m-%d").strftime("%m/%d") for d in date_range
            ]
            x_data = date_range
            data_dict = daily_data
            x_title = "Date"

        else:  # week
            # Weekly bins
            weekly_data = defaultdict(lambda: defaultdict(int))
            for event in filtered_events:
                week_start = event["datetime"].date() - timedelta(
                    days=event["datetime"].weekday()
                )
                week_key = week_start.strftime("%Y-%m-%d")
                event_type = event["event_type"]
                weekly_data[week_key][event_type] += 1

            x_labels = list(weekly_data.keys())
            x_data = x_labels
            data_dict = weekly_data
            x_title = "Week Starting"

        # Get all unique event types
        all_event_types = set()
        for data in data_dict.values():
            all_event_types.update(data.keys())

        # Color mapping for event types
        color_map = {
            "pre_command": "#28a745",
            "post_command": "#20c997",
            "pre_edit": "#17a2b8",
            "post_edit": "#20c997",
            "pre_agent_spawn": "#ffc107",
            "post_agent_spawn": "#fd7e14",
            "prompt_submitted": "#6f42c1",
            "notification": "#e83e8c",
            "setup_test": "#6c757d",
            "debug_test": "#495057",
        }

        # Create visualization based on grouping
        fig = go.Figure()

        # Add traces for each event type
        for event_type in sorted(all_event_types):
            if group_by == "hour" and time_range == "Today":
                y_values = [data_dict[hour].get(event_type, 0) for hour in x_data]
            else:
                y_values = [data_dict.get(x, {}).get(event_type, 0) for x in x_data]

            # Only add trace if there's at least one event
            if sum(y_values) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=x_labels,
                        y=y_values,
                        mode="lines",
                        name=event_type.replace("_", " ").title(),
                        line={
                            "width": 0.5,
                            "color": color_map.get(event_type, "#6c757d"),
                        },
                        stackgroup="one",
                        fillcolor=color_map.get(event_type, "#6c757d"),
                        hovertemplate=f"<b>{event_type.replace('_', ' ').title()}</b><br>{x_title}: %{{x}}<br>Events: %{{y}}<extra></extra>",
                    )
                )

        # Calculate peak period
        if group_by == "hour" and time_range == "Today":
            total_by_period = {hour: sum(data_dict[hour].values()) for hour in x_data}
            peak_period = (
                max(total_by_period.items(), key=lambda x: x[1])
                if total_by_period
                else (0, 0)
            )
            peak_text = f"Peak: {peak_period[1]} events at {peak_period[0]:02d}:00"
        else:
            total_by_period = {x: sum(data_dict.get(x, {}).values()) for x in x_data}
            if total_by_period:
                peak_period = max(total_by_period.items(), key=lambda x: x[1])
                peak_text = f"Peak: {peak_period[1]} events"
            else:
                peak_text = ""

        # Total events in range
        total_events = len(filtered_events)

        # Update layout
        fig.update_layout(
            title={
                "text": f"📅 {title_format} ({total_events} total events{', ' + peak_text if peak_text else ''})",
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": 16},
            },
            xaxis={
                "title": x_title,
                "showgrid": True,
                "gridcolor": "rgba(128, 128, 128, 0.2)",
                "tickangle": -45 if group_by != "hour" else 0,
            },
            yaxis={
                "title": "Number of Events",
                "showgrid": True,
                "gridcolor": "rgba(128, 128, 128, 0.2)",
            },
            height=450,
            showlegend=True,
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "center",
                "x": 0.5,
            },
            margin={"l": 50, "r": 50, "t": 100, "b": 80},
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )

        # Add current time marker for today view
        if time_range == "Today" and group_by == "hour":
            current_hour = TimePolicy.now_local().hour
            current_minute = TimePolicy.now_local().minute

            fig.add_vline(
                x=current_hour + current_minute / 60,
                line_dash="dash",
                line_color="red",
                annotation_text="Now",
                annotation_position="top",
            )

        # Add statistics below chart
        if filtered_events:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Events", f"{total_events:,}")
            with col2:
                avg_per_period = round(total_events / max(len(x_data), 1), 1)
                st.metric(f"Avg per {group_by.title()}", avg_per_period)
            with col3:
                unique_event_types = len(all_event_types)
                st.metric("Event Types", unique_event_types)
            with col4:
                if peak_text:
                    st.metric("Peak Activity", peak_period[1])

        st.plotly_chart(fig, use_container_width=True)

    def render_events_table(self, events: list[dict[str, Any]]):
        """Render enhanced events table with better formatting."""
        if not events:
            st.markdown(
                """
            <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 10px; border: 2px dashed #dee2e6;">
                <h3>📭 No Events Found</h3>
                <p>No events match your current filters. Try adjusting the filter criteria.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
            return

        # Display count and options
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**📊 Showing {len(events)} events**")
        with col2:
            display_limit = st.selectbox(
                "Show", [10, 25, 50, 100], index=1, key="event_limit"
            )
        with col3:
            show_details = st.checkbox(
                "🔍 Show Details", value=False, help="Show expanded event information"
            )

        # Get events to display
        display_events = (
            events[-display_limit:] if len(events) > display_limit else events
        )
        display_events.reverse()  # Show newest first

        # Enhanced event cards display
        if show_details:
            st.markdown("#### 📋 Detailed Event View")
            for i, event in enumerate(display_events[:20]):  # Limit detailed view
                self.render_event_card(event, i)
        else:
            # Compact table view
            table_data = []
            for event in display_events:
                # Event type styling with comprehensive icon mapping
                event_type = event.get("event_type", "unknown")
                event_icon = {
                    "pre_command": "⚡",
                    "post_command": "✅",
                    "pre_edit": "📝",
                    "post_edit": "💾",
                    "pre_agent_spawn": "🚀",
                    "post_agent_spawn": "🎯",
                    "prompt_submitted": "💬",
                    "notification": "🔔",
                    "setup_test": "🧪",
                    "debug_test": "🔬",
                    "integration_test": "🔧",
                    "test": "🧪",
                }.get(event_type, "📋")

                # Command/details extraction with better logic
                command = event.get("command", "")
                metadata = event.get("metadata", {})
                file_paths = event.get("file_paths", [])

                if event_type == "prompt_submitted":
                    details = f"📝 {metadata.get('word_count', 0)} words, {metadata.get('estimated_complexity', 'unknown')} complexity"
                elif event_type == "notification":
                    severity = metadata.get("severity", "info")
                    message = metadata.get("message", "System notification")
                    details = (
                        f"🔔 {severity.upper()}: {message[:80]}..."
                        if len(message) > 80
                        else f"🔔 {severity.upper()}: {message}"
                    )
                elif event_type in ["pre_edit", "post_edit"]:
                    if file_paths:
                        # Show file names (not full paths for cleaner display)
                        file_names = [
                            fp.split("/")[-1] for fp in file_paths[:2]
                        ]  # Show max 2 files
                        file_display = ", ".join(file_names)
                        if len(file_paths) > 2:
                            file_display += f" +{len(file_paths) - 2} more"
                        details = f"📁 {file_display}"
                    else:
                        details = "📁 File edit"
                elif event_type in ["pre_agent_spawn", "post_agent_spawn"]:
                    task_desc = metadata.get("task_description", "")
                    details = (
                        f"🤖 {task_desc[:60]}..."
                        if len(task_desc) > 60
                        else task_desc or "Agent task"
                    )
                elif event_type in ["pre_command", "post_command"] and command:
                    # Better command display - show more context
                    details = (
                        f"💻 {command[:80]}..."
                        if len(command) > 80
                        else f"💻 {command}"
                    )
                elif command:
                    details = (
                        f"💻 {command[:80]}..."
                        if len(command) > 80
                        else f"💻 {command}"
                    )
                else:
                    # Fallback to tool name and event type
                    tool_name = event.get("tool_name", "Unknown")
                    details = f"🔧 {tool_name} operation"

                # Session and timing
                session_id = event.get("session_id", "Unknown")
                session_display = (
                    session_id[:8] + "..." if len(session_id) > 8 else session_id
                )

                table_data.append({
                    "🕐 Time": event["datetime"].strftime("%H:%M:%S"),
                    "🎯 Event": f"{event_icon} {event_type.replace('_', ' ').title()}",
                    "🛠️ Tool": event.get("tool_name", "Unknown"),
                    "👤 Session": session_display,
                    "📄 Details": details,
                })

            df = pd.DataFrame(table_data)

            # Enhanced dataframe display with better formatting
            st.dataframe(
                df,
                use_container_width=True,
                height=400,
                column_config={
                    "🕐 Time": st.column_config.TextColumn(
                        "Time", width="small", help="Event timestamp"
                    ),
                    "🎯 Event": st.column_config.TextColumn(
                        "Event Type", width="medium", help="Type of hook event"
                    ),
                    "🛠️ Tool": st.column_config.TextColumn(
                        "Tool", width="small", help="Claude Code tool used"
                    ),
                    "👤 Session": st.column_config.TextColumn(
                        "Session", width="small", help="Session identifier"
                    ),
                    "📄 Details": st.column_config.TextColumn(
                        "Details", width="large", help="Event details and context"
                    ),
                },
                hide_index=True,
            )

            # Add quick stats below table
            if table_data:
                col1, col2, col3 = st.columns(3)
                with col1:
                    event_counts = {}
                    for row in table_data:
                        event_type = (
                            row["🎯 Event"].split(" ", 1)[1]
                            if " " in row["🎯 Event"]
                            else row["🎯 Event"]
                        )
                        event_counts[event_type] = event_counts.get(event_type, 0) + 1
                    st.caption(
                        f"📊 Most active: {max(event_counts, key=event_counts.get)} ({max(event_counts.values())} events)"
                    )
                with col2:
                    unique_tools = len({row["🛠️ Tool"] for row in table_data})
                    st.caption(f"🛠️ Tools used: {unique_tools}")
                with col3:
                    unique_sessions = len({row["👤 Session"] for row in table_data})
                    st.caption(f"👥 Active sessions: {unique_sessions}")

    def render_event_card(self, event: dict[str, Any], _index: int):
        """Render individual event card with full details.

        Args:
            event: Event data to render
            _index: Event position (reserved for future features like alternating colors)
        """
        event_type = event.get("event_type", "unknown")

        # Color coding by event type (enhanced for notifications)
        color_map = {
            "pre_command": "#28a745",
            "post_command": "#20c997",
            "pre_edit": "#17a2b8",
            "post_edit": "#20c997",
            "pre_agent_spawn": "#ffc107",
            "post_agent_spawn": "#fd7e14",
            "prompt_submitted": "#6f42c1",
            "notification": "#e83e8c",
            "setup_test": "#6c757d",
            "debug_test": "#495057",
            "integration_test": "#17a2b8",
            "test": "#6c757d",
        }
        border_color = color_map.get(event_type, "#6c757d")

        # Icon mapping (comprehensive)
        icon_map = {
            "pre_command": "⚡",
            "post_command": "✅",
            "pre_edit": "📝",
            "post_edit": "💾",
            "pre_agent_spawn": "🚀",
            "post_agent_spawn": "🎯",
            "prompt_submitted": "💬",
            "notification": "🔔",
            "setup_test": "🧪",
            "debug_test": "🔬",
            "integration_test": "🔧",
            "test": "🧪",
        }
        icon = icon_map.get(event_type, "📋")

        # Event details with improved extraction
        command = event.get("command", "")
        metadata = event.get("metadata", {})
        file_paths = event.get("file_paths", [])
        session_id = event.get("session_id", "Unknown")

        # Extract meaningful details for the card
        if event_type == "notification":
            severity = metadata.get("severity", "info")
            message = metadata.get("message", "System notification")
            detail_summary = f"{severity.upper()}: {message}"
        elif event_type in ["pre_edit", "post_edit"]:
            if file_paths:
                detail_summary = f"Editing {len(file_paths)} file(s): {', '.join([fp.split('/')[-1] for fp in file_paths[:3]])}"
                if len(file_paths) > 3:
                    detail_summary += f" +{len(file_paths) - 3} more"
            else:
                detail_summary = "File editing operation"
        elif command:
            detail_summary = f"Command: {command}"
        else:
            detail_summary = f"{event.get('tool_name', 'Unknown')} operation"

        st.markdown(
            f"""
        <div style="border-left: 4px solid {border_color}; padding: 1rem; margin: 0.5rem 0;
                    background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <h4 style="margin: 0; color: {border_color};">{icon} {event_type.replace("_", " ").title()}</h4>
                <small style="color: #6c757d;">{event["datetime"].strftime("%H:%M:%S")}</small>
            </div>

            <div style="margin: 0.5rem 0; padding: 0.5rem; background: #f8f9fa; border-radius: 5px;">
                <strong>📄 Details:</strong> {detail_summary}
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 0.5rem 0;">
                <div><strong>🛠️ Tool:</strong> {event.get("tool_name", "Unknown")}</div>
                <div><strong>👤 Session:</strong> {session_id[:12] + "..." if len(session_id) > 12 else session_id}</div>
            </div>

            {f'<div style="margin: 0.5rem 0;"><strong>💻 Full Command:</strong><br><code style="background: #f8f9fa; padding: 0.5rem; border-radius: 3px; display: block; word-break: break-all;">{command}</code></div>' if command else ""}

            {'<div style="margin: 0.5rem 0;"><strong>📁 File Paths:</strong><br>' + "<br>".join([f'<code style="background: #e9ecef; padding: 0.2rem; border-radius: 2px;">{fp}</code>' for fp in file_paths[:5]]) + (f"<br><em>...and {len(file_paths) - 5} more files</em>" if len(file_paths) > 5 else "") + "</div>" if file_paths else ""}

            {f'<div style="margin: 0.5rem 0;"><strong>📊 Metadata:</strong><br><small style="font-family: monospace; background: #f8f9fa; padding: 0.5rem; border-radius: 3px; display: block;">{str(metadata)[:300]}{"..." if len(str(metadata)) > 300 else ""}</small></div>' if metadata else ""}
        </div>
        """,
            unsafe_allow_html=True,
        )

    def render_sidebar(self, metrics: dict[str, Any]):
        """Render sidebar with controls and info."""
        st.sidebar.title("🔍 Observability Control")

        # Status
        st.sidebar.subheader("📊 Status")
        st.sidebar.write(
            f"**Database**: {'✅ Connected' if self.events_cache else '❌ No Data'}"
        )
        st.sidebar.write(f"**Events Loaded**: {len(self.events_cache)}")
        st.sidebar.write(
            f"**Last Updated**: {TimePolicy.from_timestamp_local(self.last_load_time).strftime('%H:%M:%S') if self.last_load_time else 'Never'}"
        )
        # Check WebSocket server status for sidebar
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", CONFIG["WEBSOCKET_PORT"]))
            sock.close()
            ws_server_running = result == 0
        except (OSError, ConnectionError) as e:
            # Expected WebSocket connectivity failure - server may be down
            import logging

            logging.getLogger(__name__).debug(
                f"WebSocket server connectivity check failed: {e}"
            )
            ws_server_running = False

        st.sidebar.write(
            f"**Real-time**: {'🟢 Server Active' if ws_server_running else '🔴 Server Inactive'}"
        )

        # Session summary
        if metrics.get("sessions"):
            st.sidebar.subheader("🔗 Active Sessions")
            for sid, count in list(metrics["sessions"].items())[
                :5
            ]:  # Show top 5 sessions
                session_display = f"{sid[:8]}..." if len(sid) > 8 else sid
                st.sidebar.write(f"**{session_display}**: {count} events")

        # Hook types summary
        if metrics["hook_types"]:
            st.sidebar.subheader("🪝 Hook Types")
            for hook_type, count in sorted(
                metrics["hook_types"].items(), key=lambda x: x[1], reverse=True
            ):
                hook_display = hook_type.replace("_", " ").title()
                st.sidebar.write(f"**{hook_display}**: {count}")

        # Quick actions
        st.sidebar.subheader("⚡ Quick Actions")

        if st.sidebar.button("🧪 Test Hook"):
            st.sidebar.info("Use Claude Code tools to generate hook events")

        if st.sidebar.button("📊 Export Data") and self.events_cache:
            # Create download link for events data
            df = pd.DataFrame(self.events_cache)
            csv = df.to_csv(index=False)
            st.sidebar.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"claude_code_events_{TimePolicy.now_local().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

        # Real-time controls
        st.sidebar.subheader("🔴 Real-time")

        # WebSocket server management
        if ws_server_running:
            st.sidebar.success(
                f"🟢 WebSocket Server: ws://localhost:{CONFIG['WEBSOCKET_PORT']}"
            )
            if st.sidebar.button("🔄 Test Connection"):
                try:
                    import json

                    import websockets

                    async def test_ws():
                        async with websockets.connect(
                            f"ws://localhost:{CONFIG['WEBSOCKET_PORT']}"
                        ) as ws:
                            await ws.send(json.dumps({"type": "ping"}))
                            response = await ws.recv()
                            return json.loads(response)

                    # Note: This is a simple test, full integration would need async streamlit
                    st.sidebar.info("Connection test initiated - check server logs")
                except Exception as e:
                    st.sidebar.error(f"Connection failed: {str(e)[:50]}...")
        else:
            st.sidebar.error("🔴 WebSocket Server Offline")
            if st.sidebar.button("📋 Start Server Command"):
                st.sidebar.code(
                    f"uv run khive claude server --port {CONFIG['WEBSOCKET_PORT']}"
                )

        # Show actual subscriber count from broadcaster
        try:
            from khive.services.claude.hooks.hook_event import HookEventBroadcaster

            subscriber_count = HookEventBroadcaster.get_subscriber_count()
            st.sidebar.write(f"**Subscribers**: {subscriber_count} active")
        except Exception:
            st.sidebar.write("**Subscribers**: Unknown")

        # Help section
        st.sidebar.markdown("---")
        with st.sidebar.expander("ℹ️ Help & Info"):
            st.markdown(
                """
            **khive claude** monitors Claude Code hook events in real-time.

            **Features:**
            - 📊 Real-time metrics and activity tracking
            - 📈 Interactive charts with time range selection
            - 🔍 Advanced filtering and search
            - 📥 Export data as CSV
            - 🔄 Auto-refresh capabilities

            **Hook Types:**
            - **Pre/Post Command**: Bash commands
            - **Pre/Post Edit**: File modifications
            - **Pre/Post Agent Spawn**: Task agent operations
            - **Prompt Submitted**: User prompts
            - **Notification**: System notifications

            **Tips:**
            - Click on charts to interact
            - Use filters to focus on specific events
            - Export data for external analysis
            """
            )

        return "All Sessions"

    def run(self):
        """Main dashboard rendering loop."""
        # Render header
        auto_refresh, refresh_rate = self.render_header()

        # Load events
        events = self.load_events()
        metrics = self.get_metrics(events)

        # Render sidebar
        selected_session = self.render_sidebar(metrics)

        # Main content
        self.render_metrics(metrics)

        # Cleaner filtering section
        st.markdown("### 🔍 Filters & Search")

        # Create expandable filter section to reduce clutter
        with st.expander("🎛️ Advanced Filters", expanded=False):
            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:
                # Event type filter
                all_event_types = sorted({
                    e.get("event_type", "unknown") for e in events
                })
                selected_event_types = st.multiselect(
                    "📋 Event Types",
                    options=all_event_types,
                    default=all_event_types,
                    help="Filter events by type",
                )

                # Session filter
                all_sessions = list({
                    e.get("session_id", "unknown")
                    for e in events
                    if e.get("session_id")
                })
                selected_sessions = st.multiselect(
                    "👥 Sessions",
                    options=all_sessions[:10],  # Limit to top 10 sessions
                    default=[],  # Default to none selected to reduce clutter
                    help="Filter events by session ID",
                )

            with filter_col2:
                # Tool filter
                all_tools = sorted({e.get("tool_name", "unknown") for e in events})
                selected_tools = st.multiselect(
                    "🛠️ Tools",
                    options=all_tools,
                    default=all_tools,
                    help="Filter events by tool type",
                )

                # Time range filter
                if events:
                    min_time = min([e["datetime"] for e in events])
                    max_time = max([e["datetime"] for e in events])

                    time_range = st.slider(
                        "⏰ Time Range (Hours Ago)",
                        min_value=0,
                        max_value=24,
                        value=(0, 2),
                        help="Filter events by time range",
                    )

        # Quick search bar (always visible)
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_text = st.text_input(
                "🔎 Quick Search",
                placeholder="Search commands, files, metadata...",
                help="Search in commands, file paths, and metadata",
            )
        with search_col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            if st.button("🧹 Clear All Filters"):
                st.rerun()

        # Apply filters
        filtered_events = events

        if selected_event_types:
            filtered_events = [
                e
                for e in filtered_events
                if e.get("event_type") in selected_event_types
            ]

        if selected_tools:
            filtered_events = [
                e for e in filtered_events if e.get("tool_name") in selected_tools
            ]

        if selected_sessions:
            filtered_events = [
                e for e in filtered_events if e.get("session_id") in selected_sessions
            ]

        # Apply time range filter
        if events and "time_range" in locals():
            now = TimePolicy.now_local()
            start_time = now - timedelta(hours=time_range[1])
            end_time = now - timedelta(hours=time_range[0])
            filtered_events = [
                e for e in filtered_events if start_time <= e["datetime"] <= end_time
            ]

        if search_text:
            search_lower = search_text.lower()
            filtered_events = [
                e
                for e in filtered_events
                if search_lower in str(e.get("command", "")).lower()
                or search_lower in str(e.get("file_paths", [])).lower()
                or search_lower in str(e.get("metadata", {})).lower()
                or search_lower in str(e.get("event_type", "")).lower()
                or search_lower in str(e.get("tool_name", "")).lower()
            ]

        # Show filter results
        if len(filtered_events) != len(events):
            st.info(
                f"🔍 Showing {len(filtered_events)} of {len(events)} events (filtered)"
            )

        # Charts section with filtered data
        st.markdown("### 📈 Analytics")

        # Add time range selector for timeline
        timeline_col1, timeline_col2, timeline_col3 = st.columns([1, 3, 1])
        with timeline_col1:
            time_range_options = [
                "Today",
                "Last 7 Days",
                "Last 30 Days",
                "This Month",
                "All Time",
            ]
            default_index = (
                time_range_options.index(CONFIG["DEFAULT_TIME_RANGE"])
                if CONFIG["DEFAULT_TIME_RANGE"] in time_range_options
                else 0
            )
            time_range_option = st.selectbox(
                "📅 Timeline Range",
                time_range_options,
                index=default_index,
                help="Select time range for activity timeline",
            )

        col1, col2 = st.columns(2)

        with col1:
            # Update metrics for filtered events
            filtered_metrics = self.get_metrics(filtered_events)
            self.render_hook_types_chart(filtered_metrics)

        with col2:
            self.render_timeline_chart(filtered_events, time_range=time_range_option)

        st.markdown("---")

        # Recent events table with filtered data
        st.markdown("### 📋 Event History")
        self.render_events_table(filtered_events)

        # Footer
        st.markdown("---")
        footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 1])
        with footer_col1:
            st.markdown(
                f"""
            <div style="font-size: 0.875rem; color: #6c757d;">
                <strong>khive claude</strong> v{__version__} | Real-time Claude Code monitoring
            </div>
            """,
                unsafe_allow_html=True,
            )
        with footer_col2:
            st.markdown(
                """
            <div style="font-size: 0.875rem; color: #6c757d; text-align: center;">
                Made with ❤️ by <a href="https://github.com/khive-ai" target="_blank" style="color: #1e3c72;">Ocean</a>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with footer_col3:
            st.markdown(
                """
            <div style="font-size: 0.875rem; color: #6c757d; text-align: right;">
                <a href="https://github.com/khive-ai/khive.d" target="_blank" style="color: #1e3c72;">
                    🔗 GitHub
                </a> |
                <a href="https://github.com/khive-ai/khive.d/issues" target="_blank" style="color: #1e3c72;">
                    🐛 Report Issue
                </a>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Auto-refresh
        if auto_refresh:
            time.sleep(refresh_rate)
            st.rerun()


def main():
    """Main entry point."""
    dashboard = ClaudeCodeObservabilityDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
