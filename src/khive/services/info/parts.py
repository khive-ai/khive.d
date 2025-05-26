# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class InsightMode(str, Enum):
    """How to gather insights - auto-selected based on query analysis."""

    QUICK = "quick"  # Fast lookup for factual questions
    COMPREHENSIVE = "comprehensive"  # Deep research with multiple sources
    ANALYTICAL = "analytical"  # Multi-perspective analysis
    REALTIME = "realtime"  # Latest information priority


class InfoRequest(BaseModel):
    """
    Simplified request model - agents just ask questions naturally.

    The service figures out how to best answer them.
    """

    query: str = Field(..., description="Natural language question or information need")

    context: str | None = Field(
        None, description="Optional context about what you're working on"
    )

    mode: InsightMode | None = Field(
        None,
        description="Optional hint about depth needed (auto-detected if not provided)",
    )

    time_budget_seconds: float = Field(
        20.0, description="How long to spend gathering insights", ge=1.0, le=60.0
    )


class InsightSource(BaseModel):
    """Where an insight came from."""

    type: Literal["search", "analysis", "synthesis"] = Field(
        ..., description="How this insight was generated"
    )

    provider: str = Field(..., description="Which service provided this")

    confidence: float = Field(
        ..., description="Confidence in this insight (0-1)", ge=0.0, le=1.0
    )

    url: str | None = Field(None, description="Source URL if applicable")


class Insight(BaseModel):
    """A single insight or finding."""

    summary: str = Field(..., description="Brief summary of the insight")

    details: str | None = Field(None, description="Detailed explanation if needed")

    sources: list[InsightSource] = Field(
        default_factory=list, description="Where this insight comes from"
    )

    relevance: float = Field(
        1.0, description="How relevant to the query (0-1)", ge=0.0, le=1.0
    )


class InfoResponse(BaseModel):
    """
    Response that provides synthesized insights, not raw data.

    Designed to feel like enhanced intelligence, not external consultation.
    """

    success: bool = Field(
        ..., description="Whether insights were successfully gathered"
    )

    summary: str = Field(
        ..., description="Direct answer to your query in 1-2 sentences"
    )

    insights: list[Insight] = Field(
        default_factory=list,
        description="Key insights discovered, ordered by relevance",
    )

    synthesis: str | None = Field(
        None, description="Comprehensive narrative combining all insights"
    )

    confidence: float = Field(
        0.0, description="Overall confidence in the response (0-1)", ge=0.0, le=1.0
    )

    mode_used: InsightMode = Field(..., description="Which insight mode was used")

    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions or areas to explore",
    )

    error: str | None = Field(None, description="Error message if success is False")


# For backward compatibility, keep minimal provider-specific models
class SearchConfig(BaseModel):
    """Configuration for search operations."""

    max_results: int = Field(10, ge=1, le=50)
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    recency: Literal["day", "week", "month", "year", None] = None


class AnalysisConfig(BaseModel):
    """Configuration for analytical operations."""

    perspectives: int = Field(
        3, description="How many analytical perspectives to include", ge=1, le=5
    )
    include_examples: bool = Field(
        True, description="Whether to include concrete examples"
    )
    technical_depth: Literal["basic", "intermediate", "advanced"] = "intermediate"
