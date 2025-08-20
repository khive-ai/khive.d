"""Centralized timezone policy for khive

This module provides standardized time handling across the entire khive codebase
to ensure consistent temporal behavior and comply with linting requirements (DTZ005/006/007).

Architecture Design:
- UTC-first policy for internal operations (logging, session management)
- Local timezone for user-facing display (CSV downloads, frontend)
- Explicit timezone handling to prevent datetime ambiguity
"""

import datetime


class TimePolicy:
    """Centralized timezone policy for consistent temporal behavior"""

    # Standard timezone constants
    UTC = datetime.timezone.utc
    LOCAL = datetime.datetime.now().astimezone().tzinfo

    @classmethod
    def now_utc(cls) -> datetime.datetime:
        """Get current time in UTC for internal operations

        Use for: logging, session management, internal timestamps
        Replaces: datetime.now() -> datetime.now(tz=TimePolicy.UTC)
        """
        return datetime.datetime.now(tz=cls.UTC)

    @classmethod
    def now_local(cls) -> datetime.datetime:
        """Get current time in local timezone for user-facing operations

        Use for: CSV downloads, frontend display, user-visible timestamps
        """
        return datetime.datetime.now(tz=cls.LOCAL)

    @classmethod
    def from_timestamp_utc(cls, timestamp: int | float) -> datetime.datetime:
        """Convert timestamp to UTC datetime

        Use for: converting stored timestamps, API responses
        Replaces: datetime.fromtimestamp(ts) -> datetime.fromtimestamp(ts, tz=TimePolicy.UTC)
        """
        return datetime.datetime.fromtimestamp(timestamp, tz=cls.UTC)

    @classmethod
    def from_timestamp_local(cls, timestamp: int | float) -> datetime.datetime:
        """Convert timestamp to local timezone datetime

        Use for: user-facing timestamp display
        """
        return datetime.datetime.fromtimestamp(timestamp, tz=cls.LOCAL)

    @classmethod
    def strptime_utc(cls, date_string: str, format_string: str) -> datetime.datetime:
        """Parse datetime string and assign UTC timezone

        Use for: parsing log timestamps, API timestamps
        Replaces: datetime.strptime(s, fmt) -> datetime.strptime(s, fmt).replace(tzinfo=TimePolicy.UTC)
        """
        dt = datetime.datetime.strptime(date_string, format_string)  # noqa: DTZ007
        return dt.replace(tzinfo=cls.UTC)

    @classmethod
    def format_for_filename(cls, dt: datetime.datetime | None = None) -> str:
        """Format datetime for use in filenames (safe characters only)

        Args:
            dt: datetime to format, defaults to current UTC time

        Returns:
            Filename-safe timestamp string: YYYYMMDD_HHMMSS
        """
        if dt is None:
            dt = cls.now_utc()
        return dt.strftime("%Y%m%d_%H%M%S")

    @classmethod
    def format_for_display(cls, dt: datetime.datetime | None = None) -> str:
        """Format datetime for user display

        Args:
            dt: datetime to format, defaults to current local time

        Returns:
            Human-readable timestamp: YYYY-MM-DD HH:MM:SS
        """
        if dt is None:
            dt = cls.now_local()
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def format_iso(cls, dt: datetime.datetime | None = None) -> str:
        """Format datetime as ISO string with timezone

        Args:
            dt: datetime to format, defaults to current UTC time

        Returns:
            ISO formatted string with timezone info
        """
        if dt is None:
            dt = cls.now_utc()
        return dt.isoformat()
