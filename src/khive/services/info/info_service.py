# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import re
from typing import Any

from khive.clients.executor import AsyncExecutor
from khive.connections.match_endpoint import match_endpoint
from khive.services.info.parts import (
    InfoRequest,
    InfoResponse,
    Insight,
    InsightMode,
    InsightSource,
)
from khive.types import Service


class InfoServiceGroup(Service):
    """
    Redesigned Information Service that provides synthesized insights.

    Instead of making agents choose between search and consult,
    this service intelligently determines the best approach and
    returns unified, actionable insights.
    """

    def __init__(self):
        """Initialize with lazy-loaded endpoints."""
        self._perplexity = None
        self._exa = None
        self._openrouter = None
        self._executor = AsyncExecutor(max_concurrency=10)

        # Synthesis prompt for creating coherent narratives
        self._synthesis_prompt = """You are an insight synthesis expert.
Given multiple pieces of information, create a coherent narrative that:
1. Directly answers the user's query
2. Integrates all relevant findings
3. Notes any contradictions or uncertainties
4. Provides actionable insights

User Query: {query}
Context: {context}
Information Sources:
{sources}

Provide a clear, comprehensive synthesis that enhances understanding."""

    async def handle_request(self, request: InfoRequest) -> InfoResponse:
        """
        Handle information request with intelligent routing.

        This is the main entry point that:
        1. Analyzes the query to determine best approach
        2. Gathers information from appropriate sources
        3. Synthesizes insights into actionable intelligence
        """
        try:
            # Parse request if needed
            if isinstance(request, str):
                request = InfoRequest.model_validate_json(request)
            elif isinstance(request, dict):
                request = InfoRequest.model_validate(request)

            # Determine the best mode if not specified
            mode = request.mode or await self._detect_mode(request.query)

            # Route to appropriate handler based on mode
            if mode == InsightMode.QUICK:
                return await self._handle_quick_insights(request)
            elif mode == InsightMode.COMPREHENSIVE:
                return await self._handle_comprehensive_insights(request)
            elif mode == InsightMode.ANALYTICAL:
                return await self._handle_analytical_insights(request)
            elif mode == InsightMode.REALTIME:
                return await self._handle_realtime_insights(request)
            else:
                # Default to comprehensive
                return await self._handle_comprehensive_insights(request)

        except Exception as e:
            return InfoResponse(
                success=False,
                summary=f"Unable to gather insights: {e!s}",
                error=str(e),
                mode_used=request.mode or InsightMode.QUICK,
                confidence=0.0,
            )

    async def _detect_mode(self, query: str) -> InsightMode:
        """
        Intelligently detect the best mode based on query analysis.

        This removes the burden from agents to decide how to get information.
        """
        query_lower = query.lower()

        # Quick mode for simple factual questions
        quick_patterns = [
            r"^what is",
            r"^who is",
            r"^when did",
            r"^where is",
            r"^define",
            r"^\w+ definition",
        ]
        if any(re.match(pattern, query_lower) for pattern in quick_patterns):
            return InsightMode.QUICK

        # Realtime mode for current events
        realtime_keywords = [
            "latest",
            "current",
            "today",
            "recent",
            "breaking",
            "now",
            "trending",
            "update",
            "news",
        ]
        if any(keyword in query_lower for keyword in realtime_keywords):
            return InsightMode.REALTIME

        # Analytical mode for comparison/analysis questions
        analytical_keywords = [
            "compare",
            "contrast",
            "versus",
            "vs",
            "better",
            "pros and cons",
            "analyze",
            "evaluate",
            "which",
            "should i",
            "recommend",
        ]
        if any(keyword in query_lower for keyword in analytical_keywords):
            return InsightMode.ANALYTICAL

        # Default to comprehensive for complex questions
        return InsightMode.COMPREHENSIVE

    async def _handle_quick_insights(self, request: InfoRequest) -> InfoResponse:
        """Handle quick factual lookups with minimal latency."""
        # Initialize Perplexity for quick facts
        if self._perplexity is None:
            self._perplexity = match_endpoint("perplexity", "chat")

        try:
            # Quick lookup with concise model
            messages = [
                {
                    "role": "system",
                    "content": "Provide a brief, factual answer. Be concise and direct.",
                },
                {"role": "user", "content": request.query},
            ]

            response = await self._perplexity.call({
                "model": "sonar",
                "messages": messages,
                "temperature": 0.3,
            })

            # Extract the answer
            answer = (
                response.choices[0].message.content
                if hasattr(response, "choices")
                else str(response)
            )

            return InfoResponse(
                success=True,
                summary=answer.split(".")[0] + "." if "." in answer else answer,
                insights=[
                    Insight(
                        summary=answer,
                        sources=[
                            InsightSource(
                                type="search", provider="perplexity", confidence=0.9
                            )
                        ],
                        relevance=1.0,
                    )
                ],
                synthesis=answer,
                confidence=0.9,
                mode_used=InsightMode.QUICK,
            )

        except Exception as e:
            return self._error_response(str(e), InsightMode.QUICK)

    async def _handle_comprehensive_insights(
        self, request: InfoRequest
    ) -> InfoResponse:
        """
        Handle comprehensive research with multiple sources.

        This is the default mode that provides thorough insights.
        """
        insights = []
        raw_sources = []

        # Gather from multiple sources in parallel
        tasks = []

        # Search task
        if self._exa is None:
            self._exa = match_endpoint("exa", "search")
        tasks.append(self._search_with_exa(request.query))

        # Analysis task
        if self._perplexity is None:
            self._perplexity = match_endpoint("perplexity", "chat")
        tasks.append(self._analyze_with_perplexity(request.query, request.context))

        # Execute all tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=request.time_budget_seconds,
            )
        except asyncio.TimeoutError:
            results = []

        # Process results
        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, dict) and "insights" in result:
                insights.extend(result["insights"])
                raw_sources.append(result.get("raw", ""))

        # Synthesize all insights
        synthesis = await self._synthesize_insights(
            request.query, request.context, insights, raw_sources
        )

        # Create summary
        summary = (
            synthesis.split(".")[0] + "."
            if synthesis
            else "Unable to synthesize insights."
        )

        # Sort insights by relevance
        insights.sort(key=lambda x: x.relevance, reverse=True)

        # Generate follow-up suggestions
        suggestions = self._generate_suggestions(request.query, insights)

        return InfoResponse(
            success=True,
            summary=summary,
            insights=insights[:10],  # Top 10 insights
            synthesis=synthesis,
            confidence=self._calculate_confidence(insights),
            mode_used=InsightMode.COMPREHENSIVE,
            suggestions=suggestions,
        )

    async def _handle_analytical_insights(self, request: InfoRequest) -> InfoResponse:
        """
        Handle analytical queries that need multiple perspectives.

        This mode emphasizes balanced analysis over raw information.
        """
        if self._openrouter is None:
            self._openrouter = match_endpoint("openrouter", "chat")

        # Define perspectives for analysis
        perspectives = [
            (
                "practical",
                "Focus on practical implications and real-world applications",
            ),
            ("theoretical", "Examine theoretical foundations and principles"),
            (
                "critical",
                "Provide critical analysis including limitations and challenges",
            ),
        ]

        insights = []

        # Gather multiple perspectives
        for perspective_name, perspective_prompt in perspectives:
            try:
                messages = [
                    {
                        "role": "system",
                        "content": f"You are an expert analyst providing {perspective_name} analysis. {perspective_prompt}",
                    },
                    {"role": "user", "content": request.query},
                ]

                # Use a strong model for analysis
                response = await self._openrouter.call({
                    "model": "anthropic/claude-3-5-sonnet",
                    "messages": messages,
                    "temperature": 0.7,
                })

                content = self._extract_content(response)

                insights.append(
                    Insight(
                        summary=f"{perspective_name.capitalize()} perspective",
                        details=content,
                        sources=[
                            InsightSource(
                                type="analysis",
                                provider=f"claude-{perspective_name}",
                                confidence=0.85,
                            )
                        ],
                        relevance=0.9,
                    )
                )

            except Exception:
                continue

        # Synthesize analytical insights
        synthesis = await self._synthesize_analytical_insights(request.query, insights)

        return InfoResponse(
            success=True,
            summary=f"Multi-perspective analysis of: {request.query[:100]}",
            insights=insights,
            synthesis=synthesis,
            confidence=0.85,
            mode_used=InsightMode.ANALYTICAL,
            suggestions=[
                "Consider specific use cases for practical application",
                "Explore edge cases and exceptions",
                "Research empirical evidence supporting these analyses",
            ],
        )

    async def _handle_realtime_insights(self, request: InfoRequest) -> InfoResponse:
        """Handle requests for latest information with recency priority."""
        # Use Perplexity with recency filter
        if self._perplexity is None:
            self._perplexity = match_endpoint("perplexity", "chat")

        try:
            messages = [
                {
                    "role": "system",
                    "content": "Focus on the most recent and current information. Prioritize timeliness.",
                },
                {"role": "user", "content": request.query},
            ]

            response = await self._perplexity.call({
                "model": "sonar-pro",
                "messages": messages,
                "search_recency_filter": "day",
                "temperature": 0.5,
            })

            content = self._extract_content(response)

            # Parse for temporal markers
            temporal_confidence = (
                0.95
                if any(
                    marker in content.lower()
                    for marker in ["today", "hours ago", "just", "breaking"]
                )
                else 0.8
            )

            return InfoResponse(
                success=True,
                summary=content.split(".")[0] + ".",
                insights=[
                    Insight(
                        summary="Latest information available",
                        details=content,
                        sources=[
                            InsightSource(
                                type="search",
                                provider="perplexity-realtime",
                                confidence=temporal_confidence,
                            )
                        ],
                        relevance=1.0,
                    )
                ],
                synthesis=content,
                confidence=temporal_confidence,
                mode_used=InsightMode.REALTIME,
                suggestions=["Check back later for updates as this situation develops"],
            )

        except Exception as e:
            return self._error_response(str(e), InsightMode.REALTIME)

    # Helper methods

    async def _search_with_exa(self, query: str) -> dict[str, Any]:
        """Perform search and convert to insights."""
        try:
            response = await self._exa.call({
                "query": query,
                "numResults": 5,
                "useAutoprompt": True,
            })

            insights = []
            for result in response.results[:5]:
                insights.append(
                    Insight(
                        summary=result.title,
                        details=result.text[:500] if hasattr(result, "text") else None,
                        sources=[
                            InsightSource(
                                type="search",
                                provider="exa",
                                confidence=(
                                    result.score if hasattr(result, "score") else 0.8
                                ),
                                url=result.url if hasattr(result, "url") else None,
                            )
                        ],
                        relevance=0.8,
                    )
                )

            return {"insights": insights, "raw": str(response)}

        except Exception:
            return {"insights": [], "raw": ""}

    async def _analyze_with_perplexity(
        self, query: str, context: str | None
    ) -> dict[str, Any]:
        """Perform analysis and convert to insights."""
        try:
            system_content = "Provide comprehensive analysis with key insights."
            if context:
                system_content += f" Context: {context}"

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": query},
            ]

            response = await self._perplexity.call({
                "model": "sonar-pro",
                "messages": messages,
                "temperature": 0.7,
            })

            content = self._extract_content(response)

            # Extract key points as insights
            insights = []
            points = content.split("\n")
            for point in points[:3]:  # Top 3 points
                if point.strip():
                    insights.append(
                        Insight(
                            summary=point.strip(),
                            sources=[
                                InsightSource(
                                    type="analysis",
                                    provider="perplexity",
                                    confidence=0.85,
                                )
                            ],
                            relevance=0.9,
                        )
                    )

            return {"insights": insights, "raw": content}

        except Exception:
            return {"insights": [], "raw": ""}

    async def _synthesize_insights(
        self,
        query: str,
        context: str | None,
        insights: list[Insight],
        raw_sources: list[str],
    ) -> str:
        """Create a coherent narrative from multiple insights."""
        if not insights:
            return "Unable to gather sufficient insights for synthesis."

        # Prepare synthesis prompt
        sources_text = "\n\n".join([
            f"Source {i + 1} ({insight.sources[0].provider if insight.sources else 'unknown'}):\n{insight.summary}\n{insight.details or ''}"
            for i, insight in enumerate(insights[:5])  # Top 5 insights
        ])

        prompt = self._synthesis_prompt.format(
            query=query,
            context=context or "No additional context provided",
            sources=sources_text,
        )

        # Use best available LLM for synthesis
        if self._openrouter is None:
            self._openrouter = match_endpoint("openrouter", "chat")

        try:
            response = await self._openrouter.call({
                "model": "anthropic/claude-3-5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are a synthesis expert."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.6,
                "max_tokens": 800,
            })

            return self._extract_content(response)

        except Exception:
            # Fallback to simple concatenation
            return " ".join([insight.summary for insight in insights[:3]])

    async def _synthesize_analytical_insights(
        self, query: str, insights: list[Insight]
    ) -> str:
        """Synthesize multiple analytical perspectives."""
        if not insights:
            return "Unable to provide analytical synthesis."

        # Build balanced synthesis
        synthesis_parts = [
            f"Analyzing '{query}' from multiple perspectives reveals important insights:",
            "",
        ]

        for insight in insights:
            if insight.details:
                synthesis_parts.append(f"From a {insight.summary.lower()} standpoint:")
                synthesis_parts.append(insight.details[:300] + "...")
                synthesis_parts.append("")

        synthesis_parts.append(
            "These perspectives together suggest a nuanced understanding where practical considerations "
            "must be balanced with theoretical foundations while remaining aware of limitations."
        )

        return "\n".join(synthesis_parts)

    def _extract_content(self, response: Any) -> str:
        """Extract text content from various response formats."""
        if isinstance(response, str):
            return response
        elif hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content
        elif hasattr(response, "content"):
            return response.content
        elif isinstance(response, dict):
            return response.get("content", response.get("text", str(response)))
        else:
            return str(response)

    def _calculate_confidence(self, insights: list[Insight]) -> float:
        """Calculate overall confidence from insights."""
        if not insights:
            return 0.0

        # Weighted average based on relevance
        total_weight = sum(i.relevance for i in insights)
        if total_weight == 0:
            return 0.5

        weighted_confidence = sum(
            i.sources[0].confidence * i.relevance for i in insights if i.sources
        )

        return min(weighted_confidence / total_weight, 1.0)

    def _generate_suggestions(self, query: str, insights: list[Insight]) -> list[str]:
        """Generate intelligent follow-up suggestions."""
        suggestions = []

        # Based on query type
        if "how" in query.lower():
            suggestions.append("Would you like specific implementation steps?")
        elif "why" in query.lower():
            suggestions.append("Would you like to explore underlying causes?")
        elif "what" in query.lower():
            suggestions.append("Would you like more specific examples?")

        # Based on insights
        if len(insights) > 5:
            suggestions.append("Would you like me to focus on a specific aspect?")

        # Always helpful
        suggestions.append("Is there a particular angle you'd like to explore further?")

        return suggestions[:3]

    def _error_response(self, error: str, mode: InsightMode) -> InfoResponse:
        """Create a standardized error response."""
        return InfoResponse(
            success=False,
            summary=f"Unable to gather insights: {error}",
            error=error,
            mode_used=mode,
            confidence=0.0,
        )

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self, "_executor") and self._executor is not None:
            await self._executor.shutdown()

        for endpoint_attr in ("_perplexity", "_exa", "_openrouter"):
            endpoint = getattr(self, endpoint_attr, None)
            if endpoint is not None and hasattr(endpoint, "aclose"):
                await endpoint.aclose()
