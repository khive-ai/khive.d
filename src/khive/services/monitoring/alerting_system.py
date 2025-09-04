"""
Multi-tier alerting system with notification integrations.

Provides comprehensive alerting capabilities with multiple notification channels,
alert suppression, escalation policies, and integration with existing systems.
"""

import asyncio
import json
import smtplib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
import logging
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from khive.services.claude.hooks.notification import handle_notification

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING" 
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


@dataclass
class Alert:
    """Individual alert with comprehensive metadata."""
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str  # "system", "application", "business"
    metric_name: str
    current_value: Any
    threshold_value: Any
    timestamp: datetime
    
    # Alert lifecycle
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Escalation and suppression
    escalation_level: int = 0
    max_escalations: int = 3
    suppress_until: Optional[datetime] = None
    
    # Notification tracking
    notifications_sent: List[str] = field(default_factory=list)
    last_notification: Optional[datetime] = None
    
    # Additional context
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_alerts: List[str] = field(default_factory=list)


@dataclass
class NotificationChannel:
    """Configuration for a notification channel."""
    name: str
    type: str  # "email", "webhook", "slack", "console", "system"
    config: Dict[str, Any]
    enabled: bool = True
    alert_levels: List[AlertLevel] = field(default_factory=lambda: list(AlertLevel))
    rate_limit_minutes: int = 5  # Minimum time between notifications
    last_notification: Optional[datetime] = None


@dataclass
class EscalationPolicy:
    """Escalation policy configuration."""
    name: str
    levels: List[Dict[str, Any]]  # Each level has channels and delay
    enabled: bool = True


class MultiTierAlertingSystem:
    """
    Production-grade multi-tier alerting system.
    
    Features:
    - Multiple notification channels (email, webhook, Slack, etc.)
    - Alert suppression and rate limiting
    - Escalation policies
    - Alert correlation and grouping
    - Integration with existing notification system
    """
    
    def __init__(self):
        # Active alerts
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 5000
        
        # Notification channels
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self._setup_default_channels()
        
        # Escalation policies
        self.escalation_policies: Dict[str, EscalationPolicy] = {}
        self._setup_default_escalation_policies()
        
        # Alert correlation rules
        self.correlation_rules: List[Callable] = []
        self._setup_correlation_rules()
        
        # Rate limiting and suppression
        self.global_rate_limits: Dict[str, datetime] = {}
        self.suppression_rules: List[Dict[str, Any]] = []
        
        # Notification statistics
        self.notification_stats = {
            "sent": 0,
            "failed": 0,
            "suppressed": 0,
            "acknowledged": 0
        }
        
        # Session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _setup_default_channels(self):
        """Setup default notification channels."""
        
        # Console/System notification (always available)
        self.notification_channels["console"] = NotificationChannel(
            name="console",
            type="console",
            config={},
            alert_levels=[AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
        )
        
        # System notification (integrates with existing khive notification system)
        self.notification_channels["system"] = NotificationChannel(
            name="system",
            type="system",
            config={},
            alert_levels=list(AlertLevel)
        )
        
        # Email notification (placeholder - would need SMTP configuration)
        self.notification_channels["email"] = NotificationChannel(
            name="email", 
            type="email",
            config={
                "smtp_host": "localhost",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "khive-alerts@localhost",
                "to_emails": ["admin@localhost"]
            },
            enabled=False,  # Disabled by default
            alert_levels=[AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
        )
        
        # Webhook notification 
        self.notification_channels["webhook"] = NotificationChannel(
            name="webhook",
            type="webhook",
            config={
                "url": "",
                "headers": {"Content-Type": "application/json"},
                "timeout": 10
            },
            enabled=False,  # Disabled by default
            alert_levels=[AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
        )
        
        # Slack notification (placeholder)
        self.notification_channels["slack"] = NotificationChannel(
            name="slack",
            type="slack", 
            config={
                "webhook_url": "",
                "channel": "#alerts"
            },
            enabled=False,  # Disabled by default
            alert_levels=[AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
        )
    
    def _setup_default_escalation_policies(self):
        """Setup default escalation policies."""
        
        self.escalation_policies["default"] = EscalationPolicy(
            name="default",
            levels=[
                {
                    "delay_minutes": 0,
                    "channels": ["console", "system"],
                    "description": "Immediate notification"
                },
                {
                    "delay_minutes": 15,
                    "channels": ["email", "webhook"],
                    "description": "15-minute escalation"
                },
                {
                    "delay_minutes": 60,
                    "channels": ["slack", "email"],
                    "description": "1-hour escalation"
                }
            ]
        )
        
        self.escalation_policies["critical"] = EscalationPolicy(
            name="critical",
            levels=[
                {
                    "delay_minutes": 0,
                    "channels": ["console", "system", "email"],
                    "description": "Immediate critical alert"
                },
                {
                    "delay_minutes": 5,
                    "channels": ["slack", "webhook"],
                    "description": "5-minute critical escalation"
                },
                {
                    "delay_minutes": 30,
                    "channels": ["email", "slack"],
                    "description": "30-minute final escalation"
                }
            ]
        )
    
    def _setup_correlation_rules(self):
        """Setup alert correlation rules to group related alerts."""
        
        def correlate_system_alerts(alert: Alert, existing_alerts: List[Alert]) -> List[str]:
            """Correlate system-related alerts."""
            related = []
            if alert.source == "system":
                for existing in existing_alerts:
                    if (existing.source == "system" and 
                        existing.status == AlertStatus.ACTIVE and
                        existing.id != alert.id):
                        related.append(existing.id)
            return related
        
        def correlate_api_alerts(alert: Alert, existing_alerts: List[Alert]) -> List[str]:
            """Correlate API-related alerts."""
            related = []
            if "api" in alert.metric_name.lower():
                for existing in existing_alerts:
                    if ("api" in existing.metric_name.lower() and
                        existing.status == AlertStatus.ACTIVE and
                        existing.id != alert.id):
                        related.append(existing.id)
            return related
        
        self.correlation_rules = [correlate_system_alerts, correlate_api_alerts]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    def _generate_alert_id(self, source: str, metric_name: str) -> str:
        """Generate unique alert ID."""
        timestamp_ms = int(time.time() * 1000)
        return f"{source}_{metric_name}_{timestamp_ms}"
    
    def _should_suppress_alert(self, alert: Alert) -> bool:
        """Check if alert should be suppressed."""
        
        # Check time-based suppression
        if alert.suppress_until and datetime.now() < alert.suppress_until:
            return True
        
        # Check rate limiting
        rate_key = f"{alert.source}_{alert.metric_name}"
        if rate_key in self.global_rate_limits:
            time_diff = datetime.now() - self.global_rate_limits[rate_key]
            if time_diff < timedelta(minutes=5):  # Global 5-minute rate limit
                return True
        
        # Check suppression rules
        for rule in self.suppression_rules:
            if self._matches_suppression_rule(alert, rule):
                return True
        
        return False
    
    def _matches_suppression_rule(self, alert: Alert, rule: Dict[str, Any]) -> bool:
        """Check if alert matches a suppression rule."""
        # Simple rule matching - can be extended
        if "source" in rule and alert.source not in rule["source"]:
            return False
        if "level" in rule and alert.level not in rule["level"]:
            return False
        if "metric_pattern" in rule:
            import re
            if not re.search(rule["metric_pattern"], alert.metric_name):
                return False
        return True
    
    def _correlate_alert(self, alert: Alert) -> List[str]:
        """Apply correlation rules to find related alerts."""
        related_alerts = []
        existing_alerts = list(self.active_alerts.values()) + self.alert_history[-100:]  # Recent history
        
        for correlation_rule in self.correlation_rules:
            try:
                related = correlation_rule(alert, existing_alerts)
                related_alerts.extend(related)
            except Exception as e:
                logger.warning(f"Correlation rule failed: {e}")
        
        return list(set(related_alerts))  # Remove duplicates
    
    async def _send_console_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send notification to console/logs."""
        try:
            level_emoji = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️", 
                AlertLevel.CRITICAL: "🚨",
                AlertLevel.EMERGENCY: "🔥"
            }
            
            emoji = level_emoji.get(alert.level, "📢")
            message = f"{emoji} {alert.level.value}: {alert.title}\n{alert.message}"
            
            if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                logger.critical(message)
            elif alert.level == AlertLevel.WARNING:
                logger.warning(message)
            else:
                logger.info(message)
            
            print(f"[KHIVE ALERT {alert.level.value}] {alert.title}")
            print(f"  {alert.message}")
            print(f"  Metric: {alert.metric_name} = {alert.current_value} (threshold: {alert.threshold_value})")
            print(f"  Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
        except Exception as e:
            logger.error(f"Console notification failed: {e}")
            return False
    
    async def _send_system_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send notification through existing khive notification system."""
        try:
            message = f"{alert.level.value}: {alert.title}\n{alert.message}\nMetric: {alert.metric_name} = {alert.current_value}"
            
            # Use existing notification system
            result = handle_notification(message)
            
            return result.get("event_logged", False)
        except Exception as e:
            logger.error(f"System notification failed: {e}")
            return False
    
    async def _send_email_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send email notification."""
        try:
            config = channel.config
            if not all(config.get(key) for key in ["smtp_host", "from_email", "to_emails"]):
                logger.warning("Email configuration incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg["From"] = config["from_email"]
            msg["To"] = ", ".join(config["to_emails"])
            msg["Subject"] = f"[KHIVE {alert.level.value}] {alert.title}"
            
            body = f"""
Alert Details:
- Level: {alert.level.value}
- Title: {alert.title}
- Message: {alert.message}
- Source: {alert.source}
- Metric: {alert.metric_name}
- Current Value: {alert.current_value}
- Threshold: {alert.threshold_value}
- Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Alert ID: {alert.id}

This alert was generated by the Khive monitoring system.
            """.strip()
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(config["smtp_host"], config.get("smtp_port", 587)) as server:
                if config.get("username") and config.get("password"):
                    server.starttls()
                    server.login(config["username"], config["password"])
                server.send_message(msg)
            
            return True
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False
    
    async def _send_webhook_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send webhook notification."""
        try:
            config = channel.config
            if not config.get("url"):
                logger.warning("Webhook URL not configured")
                return False
            
            payload = {
                "alert_id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "source": alert.source,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status.value,
                "tags": alert.tags,
                "metadata": alert.metadata
            }
            
            session = await self._get_session()
            async with session.post(
                config["url"],
                json=payload,
                headers=config.get("headers", {}),
                timeout=config.get("timeout", 10)
            ) as response:
                return 200 <= response.status < 300
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False
    
    async def _send_slack_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send Slack notification."""
        try:
            config = channel.config
            if not config.get("webhook_url"):
                logger.warning("Slack webhook URL not configured")
                return False
            
            color_map = {
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#ff9500", 
                AlertLevel.CRITICAL: "#ff0000",
                AlertLevel.EMERGENCY: "#800080"
            }
            
            payload = {
                "channel": config.get("channel", "#alerts"),
                "username": "Khive Monitoring",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": color_map.get(alert.level, "#cccccc"),
                        "title": f"{alert.level.value}: {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Metric",
                                "value": f"{alert.metric_name} = {alert.current_value}",
                                "short": True
                            },
                            {
                                "title": "Threshold", 
                                "value": str(alert.threshold_value),
                                "short": True
                            },
                            {
                                "title": "Source",
                                "value": alert.source,
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            }
                        ],
                        "footer": "Khive Monitoring",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            session = await self._get_session()
            async with session.post(config["webhook_url"], json=payload) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False
    
    async def _send_notification(self, alert: Alert, channel_name: str) -> bool:
        """Send notification through specified channel."""
        channel = self.notification_channels.get(channel_name)
        if not channel or not channel.enabled:
            return False
        
        # Check alert level is supported by channel
        if alert.level not in channel.alert_levels:
            return False
        
        # Check channel rate limiting
        if channel.last_notification:
            time_diff = datetime.now() - channel.last_notification
            if time_diff < timedelta(minutes=channel.rate_limit_minutes):
                self.notification_stats["suppressed"] += 1
                return False
        
        # Send notification based on channel type
        try:
            success = False
            if channel.type == "console":
                success = await self._send_console_notification(alert, channel)
            elif channel.type == "system":
                success = await self._send_system_notification(alert, channel)
            elif channel.type == "email":
                success = await self._send_email_notification(alert, channel)
            elif channel.type == "webhook":
                success = await self._send_webhook_notification(alert, channel)
            elif channel.type == "slack":
                success = await self._send_slack_notification(alert, channel)
            
            if success:
                channel.last_notification = datetime.now()
                alert.notifications_sent.append(channel_name)
                alert.last_notification = datetime.now()
                self.notification_stats["sent"] += 1
            else:
                self.notification_stats["failed"] += 1
            
            return success
        except Exception as e:
            logger.error(f"Notification failed for channel {channel_name}: {e}")
            self.notification_stats["failed"] += 1
            return False
    
    async def create_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str,
        metric_name: str,
        current_value: Any,
        threshold_value: Any,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create a new alert."""
        
        alert = Alert(
            id=self._generate_alert_id(source, metric_name),
            level=level,
            title=title,
            message=message,
            source=source,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            timestamp=datetime.now(),
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Apply correlation rules
        alert.related_alerts = self._correlate_alert(alert)
        
        # Check suppression
        if self._should_suppress_alert(alert):
            alert.status = AlertStatus.SUPPRESSED
            self.notification_stats["suppressed"] += 1
            logger.debug(f"Alert {alert.id} suppressed")
            return alert
        
        # Add to active alerts
        self.active_alerts[alert.id] = alert
        
        # Update rate limiting
        rate_key = f"{alert.source}_{alert.metric_name}"
        self.global_rate_limits[rate_key] = datetime.now()
        
        # Send immediate notifications
        await self._send_immediate_notifications(alert)
        
        # Schedule escalations if needed
        await self._schedule_escalations(alert)
        
        logger.info(f"Alert created: {alert.id} - {alert.title}")
        return alert
    
    async def _send_immediate_notifications(self, alert: Alert):
        """Send immediate notifications for new alert."""
        escalation_policy = self._get_escalation_policy(alert)
        
        # Send level 0 (immediate) notifications
        if escalation_policy.levels:
            immediate_level = escalation_policy.levels[0]
            for channel_name in immediate_level.get("channels", []):
                await self._send_notification(alert, channel_name)
    
    async def _schedule_escalations(self, alert: Alert):
        """Schedule future escalation notifications."""
        # This is a simplified implementation
        # In production, you'd use a proper task scheduler like Celery or similar
        
        escalation_policy = self._get_escalation_policy(alert)
        
        for level_idx, level_config in enumerate(escalation_policy.levels[1:], 1):
            delay_minutes = level_config.get("delay_minutes", 0)
            if delay_minutes > 0:
                # Schedule escalation (simplified - would need proper scheduler)
                asyncio.create_task(
                    self._escalate_alert_after_delay(alert, level_idx, delay_minutes)
                )
    
    async def _escalate_alert_after_delay(self, alert: Alert, level: int, delay_minutes: int):
        """Escalate alert after specified delay."""
        await asyncio.sleep(delay_minutes * 60)  # Convert to seconds
        
        # Check if alert still exists and is active
        if alert.id not in self.active_alerts or alert.status != AlertStatus.ACTIVE:
            return
        
        alert.escalation_level = level
        
        escalation_policy = self._get_escalation_policy(alert)
        if level < len(escalation_policy.levels):
            level_config = escalation_policy.levels[level]
            for channel_name in level_config.get("channels", []):
                await self._send_notification(alert, channel_name)
    
    def _get_escalation_policy(self, alert: Alert) -> EscalationPolicy:
        """Get appropriate escalation policy for alert."""
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            return self.escalation_policies.get("critical", self.escalation_policies["default"])
        return self.escalation_policies["default"]
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        self.notification_stats["acknowledged"] += 1
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        
        # Move to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history_size:
            self.alert_history.pop(0)
        
        # Remove from active alerts
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert {alert_id} resolved")
        return True
    
    def add_suppression_rule(self, rule: Dict[str, Any]):
        """Add alert suppression rule."""
        self.suppression_rules.append(rule)
    
    def configure_notification_channel(
        self, 
        channel_name: str, 
        config: Dict[str, Any],
        enabled: bool = True
    ):
        """Configure a notification channel."""
        if channel_name in self.notification_channels:
            channel = self.notification_channels[channel_name]
            channel.config.update(config)
            channel.enabled = enabled
            logger.info(f"Notification channel {channel_name} configured")
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get comprehensive alert statistics."""
        active_by_level = {}
        for level in AlertLevel:
            active_by_level[level.value] = sum(
                1 for alert in self.active_alerts.values() 
                if alert.level == level
            )
        
        recent_history = [
            alert for alert in self.alert_history
            if alert.timestamp >= datetime.now() - timedelta(hours=24)
        ]
        
        return {
            "active_alerts": len(self.active_alerts),
            "active_by_level": active_by_level,
            "total_history": len(self.alert_history),
            "last_24h_alerts": len(recent_history),
            "notification_stats": self.notification_stats,
            "channels_configured": len(self.notification_channels),
            "channels_enabled": sum(
                1 for ch in self.notification_channels.values() 
                if ch.enabled
            ),
            "escalation_policies": len(self.escalation_policies),
            "suppression_rules": len(self.suppression_rules)
        }
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts from history."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
    
    async def close(self):
        """Close alerting system resources."""
        if self._session and not self._session.closed:
            await self._session.close()