"""Compatibility shim for legacy test patch points.

This file exists so tests can patch `khive.services.plan.planner_service.OpenAI`
without importing external SDKs. It is NOT used by the active planner.
"""

from __future__ import annotations


class OpenAI:  # pragma: no cover - placeholder for tests to patch
    def __init__(self, *_, **__):
        pass

