# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
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
        """Initialize with lazy-loaded endpoints and knowledge sources."""
        self._perplexity = None
        self._exa = None
        self._openrouter = None
        self._executor = AsyncExecutor(max_concurrency=10)

        # Project knowledge sources
        self._project_root = Path.cwd()
        self._docs_path = self._project_root / "docs"
        self._readme_path = self._project_root / "README.md"
        self._project_files = self._project_root / "src"

        # Knowledge sources are implemented as methods:
        # _search_project_knowledge, _search_technical_knowledge, _search_with_exa

        # Synthesis prompt for creating coherent narratives
        self._synthesis_prompt = """You are an insight synthesis expert with access to project-specific knowledge.
Given multiple pieces of information, create a coherent narrative that:
1. Directly answers the user's query
2. Prioritizes project-specific information when available
3. Integrates all relevant findings
4. Notes any contradictions or uncertainties
5. Provides actionable insights

User Query: {query}
Context: {context}
Information Sources:
{sources}

Provide a clear, comprehensive synthesis that enhances understanding."""

    async def search(self, request: InfoRequest) -> InfoResponse:
        """
        Search for information based on the request.
        
        This is an alias for handle_request for backward compatibility.
        """
        return await self.handle_request(request)

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

        # Project-specific queries should use comprehensive mode for better synthesis
        project_keywords = [
            "khive",
            "this project",
            "our project",
            "this codebase",
            "our codebase",
            "this application",
            "our application",
        ]
        if any(keyword in query_lower for keyword in project_keywords):
            return InsightMode.COMPREHENSIVE

        # Technical queries need comprehensive analysis
        technical_keywords = [
            "best practices",
            "testing",
            "pytest",
            "python",
            "cli",
            "implementation",
            "architecture",
            "design patterns",
            "how to implement",
            "tutorial",
            "guide",
        ]
        if any(keyword in query_lower for keyword in technical_keywords):
            return InsightMode.COMPREHENSIVE

        # Quick mode for simple factual questions (but not project-related)
        quick_patterns = [
            r"^what is (?!khive)",  # Exclude "what is khive"
            r"^who is",
            r"^when did",
            r"^where is",
            r"^define (?!khive)",
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

            # Extract the answer using the helper method
            answer = self._extract_content(response)

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
        Handle comprehensive research with multiple sources including project knowledge.

        This is the default mode that provides thorough insights with priority on project-specific information.
        """
        insights = []
        raw_sources = []

        # Gather from multiple sources in parallel
        tasks = []

        # 1. Project knowledge (highest priority)
        tasks.append(self._search_project_knowledge(request.query))

        # 2. Technical knowledge for technical queries
        if self._is_technical_query(request.query):
            tasks.append(self._search_technical_knowledge(request.query))

        # 3. External search (lower priority, for additional context)
        if self._exa is None:
            self._exa = match_endpoint("exa", "search")
        if self._exa is not None:
            tasks.append(self._search_with_exa(request.query))

        # 4. Analysis task (for synthesis)
        if self._perplexity is None:
            self._perplexity = match_endpoint("perplexity", "chat")
        if self._perplexity is not None:
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

        # If no insights found, provide helpful fallback
        if not insights:
            fallback_insight = Insight(
                summary="No specific information found for this query.",
                details="Consider rephrasing your question or checking if the topic exists in the project documentation.",
                sources=[
                    InsightSource(
                        type="analysis",
                        provider="khive-fallback",
                        confidence=0.5,
                    )
                ],
                relevance=0.5,
            )
            insights.append(fallback_insight)

        # Synthesize all insights
        synthesis = await self._synthesize_insights(
            request.query, request.context, insights, raw_sources
        )

        # Create summary
        summary = (
            synthesis.split(".")[0] + "."
            if synthesis and "Unable to" not in synthesis
            else "Information gathered from available sources."
        )

        # Sort insights by relevance (project sources get higher relevance)
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

    def _is_technical_query(self, query: str) -> bool:
        """Check if the query is technical in nature."""
        technical_indicators = [
            "best practices",
            "testing",
            "pytest",
            "python",
            "cli",
            "implementation",
            "architecture",
            "design patterns",
            "how to",
            "tutorial",
            "guide",
            "framework",
            "library",
            "api",
            "configuration",
            "setup",
            "install",
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in technical_indicators)

    async def _search_project_knowledge(self, query: str) -> dict[str, Any]:
        """Search project-specific knowledge sources."""
        insights = []
        raw_content = []

        try:
            # Check if query is about khive specifically
            if "khive" in query.lower() or "this project" in query.lower():
                # Read README.md for project overview
                if self._readme_path.exists():
                    readme_content = self._readme_path.read_text(encoding="utf-8")
                    insights.append(
                        Insight(
                            summary="Khive Project Overview from README",
                            details=readme_content[:1000] + "..."
                            if len(readme_content) > 1000
                            else readme_content,
                            sources=[
                                InsightSource(
                                    type="search",
                                    provider="project-readme",
                                    confidence=0.95,
                                    url=str(self._readme_path),
                                )
                            ],
                            relevance=1.0,
                        )
                    )
                    raw_content.append(readme_content)

                # Search documentation
                if self._docs_path.exists():
                    doc_insights = self._search_documentation(query)
                    insights.extend(doc_insights)

            return {"insights": insights, "raw": "\n".join(raw_content)}

        except Exception as e:
            print(f"Project knowledge search error: {e}")
            return {"insights": [], "raw": ""}

    def _search_documentation(self, query: str) -> list[Insight]:
        """Search through project documentation."""
        insights = []
        query_lower = query.lower()

        try:
            # Search through markdown files in docs/
            for doc_file in self._docs_path.rglob("*.md"):
                content = doc_file.read_text(encoding="utf-8")

                # Simple relevance scoring based on keyword matches
                relevance_score = 0.0
                for word in query_lower.split():
                    if word in content.lower():
                        relevance_score += 0.1

                if relevance_score > 0.1:  # Only include if somewhat relevant
                    insights.append(
                        Insight(
                            summary=f"Documentation: {doc_file.name}",
                            details=content[:800] + "..."
                            if len(content) > 800
                            else content,
                            sources=[
                                InsightSource(
                                    type="search",
                                    provider="project-docs",
                                    confidence=min(relevance_score, 0.9),
                                    url=str(doc_file),
                                )
                            ],
                            relevance=min(relevance_score, 1.0),
                        )
                    )

        except Exception as e:
            print(f"Documentation search error: {e}")

        return insights

    async def _search_technical_knowledge(self, query: str) -> dict[str, Any]:
        """Search technical knowledge sources for best practices and guides."""
        insights = []

        try:
            # Use Perplexity with technical context for better results
            if self._perplexity is None:
                self._perplexity = match_endpoint("perplexity", "chat")

            if self._perplexity is not None:
                technical_prompt = f"""You are a technical expert. Provide comprehensive guidance on: {query}

Focus on:
1. Best practices and industry standards
2. Practical implementation steps
3. Common pitfalls and how to avoid them
4. Code examples where relevant
5. Tool recommendations

Query: {query}"""

                response = await self._perplexity.call({
                    "model": "sonar-pro",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a technical expert providing practical guidance.",
                        },
                        {"role": "user", "content": technical_prompt},
                    ],
                    "temperature": 0.3,
                })

                content = self._extract_content(response)

                if content:
                    insights.append(
                        Insight(
                            summary="Technical Best Practices and Guidance",
                            details=content,
                            sources=[
                                InsightSource(
                                    type="analysis",
                                    provider="perplexity-technical",
                                    confidence=0.9,
                                )
                            ],
                            relevance=0.9,
                        )
                    )

            return {"insights": insights, "raw": content if insights else ""}

        except Exception as e:
            print(f"Technical knowledge search error: {e}")
            return {"insights": [], "raw": ""}

    async def _search_with_exa(self, query: str) -> dict[str, Any]:
        """Perform search and convert to insights."""
        try:
            # Initialize endpoint if needed
            if self._exa is None:
                self._exa = match_endpoint("exa", "search")

            response = await self._exa.call({
                "query": query,
                "numResults": 5,
                "useAutoprompt": True,
            })

            insights = []
            # Handle both dict and object response formats
            results = (
                response.get("results", [])
                if isinstance(response, dict)
                else getattr(response, "results", [])
            )

            for result in results[:5]:
                # Handle both dict and object result formats
                if isinstance(result, dict):
                    title = result.get("title", "No title")
                    url = result.get("url")
                    score = result.get("score", 0.8)
                    text = result.get("text")
                else:
                    title = getattr(result, "title", "No title")
                    url = getattr(result, "url", None)
                    score = getattr(result, "score", 0.8)
                    text = getattr(result, "text", None)

                insights.append(
                    Insight(
                        summary=title,
                        details=text[:500] if text else None,
                        sources=[
                            InsightSource(
                                type="search",
                                provider="exa",
                                confidence=score,
                                url=url,
                            )
                        ],
                        relevance=0.8,
                    )
                )

            return {"insights": insights, "raw": str(response)}

        except Exception as e:
            # Log the exception for debugging
            print(f"Exa search error: {e}")
            return {"insights": [], "raw": ""}

    async def _analyze_with_perplexity(
        self, query: str, context: str | None
    ) -> dict[str, Any]:
        """Perform analysis and convert to insights."""
        try:
            # Initialize endpoint if needed
            if self._perplexity is None:
                self._perplexity = match_endpoint("perplexity", "chat")

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
        """Create a coherent narrative from multiple insights with project-first priority."""
        if not insights:
            return "Unable to gather sufficient insights for synthesis."

        # Separate project-specific insights from external ones
        project_insights = [
            insight
            for insight in insights
            if insight.sources
            and any(
                source.provider.startswith(("project-", "khive-"))
                for source in insight.sources
            )
        ]
        external_insights = [
            insight for insight in insights if insight not in project_insights
        ]

        # Prepare synthesis prompt with project-first structure
        sources_text_parts = []

        if project_insights:
            sources_text_parts.append("=== PROJECT-SPECIFIC SOURCES (PRIORITY) ===")
            for i, insight in enumerate(project_insights[:3]):
                provider = insight.sources[0].provider if insight.sources else "unknown"
                sources_text_parts.append(
                    f"Project Source {i + 1} ({provider}):\n{insight.summary}\n{insight.details or ''}"
                )

        if external_insights:
            sources_text_parts.append("\n=== EXTERNAL SOURCES (SUPPLEMENTARY) ===")
            for i, insight in enumerate(external_insights[:3]):
                provider = insight.sources[0].provider if insight.sources else "unknown"
                sources_text_parts.append(
                    f"External Source {i + 1} ({provider}):\n{insight.summary}\n{insight.details or ''}"
                )

        sources_text = "\n\n".join(sources_text_parts)

        prompt = self._synthesis_prompt.format(
            query=query,
            context=context or "No additional context provided",
            sources=sources_text,
        )

        # Use best available LLM for synthesis
        if self._openrouter is None:
            self._openrouter = match_endpoint("openrouter", "chat")

        try:
            if self._openrouter is not None:
                response = await self._openrouter.call({
                    "model": "anthropic/claude-3-5-sonnet",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a synthesis expert. Prioritize project-specific information over external sources.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.6,
                    "max_tokens": 800,
                })

                return self._extract_content(response)
            else:
                # Fallback if openrouter is not available
                return self._create_simple_synthesis(
                    query, project_insights, external_insights
                )

        except Exception:
            # Fallback to simple synthesis
            return self._create_simple_synthesis(
                query, project_insights, external_insights
            )

    def _create_simple_synthesis(
        self,
        query: str,
        project_insights: list[Insight],
        external_insights: list[Insight],
    ) -> str:
        """Create a simple synthesis when LLM synthesis fails."""
        parts = []

        if project_insights:
            parts.append("Based on project documentation:")
            parts.extend([insight.summary for insight in project_insights[:2]])

        if external_insights:
            if project_insights:
                parts.append("\nAdditional context from external sources:")
            parts.extend([insight.summary for insight in external_insights[:2]])

        if not parts:
            parts.append("No specific information found for this query.")

        return " ".join(parts)

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
        elif isinstance(response, dict):
            # Handle Perplexity response format
            if "choices" in response and response["choices"]:
                choice = response["choices"][0]
                if isinstance(choice, dict) and "message" in choice:
                    return choice["message"].get("content", "")
            # Fallback for other dict formats
            return response.get("content", response.get("text", str(response)))
        elif hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content
        elif hasattr(response, "content"):
            return response.content
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
        """Generate intelligent follow-up suggestions based on query type and available insights."""
        suggestions = []
        query_lower = query.lower()

        # Project-specific suggestions
        if "khive" in query_lower or "this project" in query_lower:
            suggestions.extend([
                "Would you like to explore specific khive commands or services?",
                "Need information about khive architecture or implementation details?",
                "Want to know about khive's development workflow or contribution guidelines?",
            ])

        # Technical query suggestions
        elif self._is_technical_query(query):
            if "testing" in query_lower:
                suggestions.extend([
                    "Would you like examples of test implementation patterns?",
                    "Need information about test configuration and setup?",
                    "Want to explore advanced testing strategies?",
                ])
            elif "python" in query_lower or "cli" in query_lower:
                suggestions.extend([
                    "Would you like to see code examples and implementation patterns?",
                    "Need information about CLI framework comparisons?",
                    "Want to explore deployment and distribution strategies?",
                ])
            else:
                suggestions.extend([
                    "Would you like specific implementation examples?",
                    "Need information about related tools and frameworks?",
                    "Want to explore advanced techniques and patterns?",
                ])

        # General query suggestions
        else:
            # Based on query type
            if "how" in query_lower:
                suggestions.append("Would you like specific implementation steps?")
            elif "why" in query_lower:
                suggestions.append("Would you like to explore underlying causes?")
            elif "what" in query_lower:
                suggestions.append("Would you like more specific examples?")

            # Based on insights
            if len(insights) > 5:
                suggestions.append("Would you like me to focus on a specific aspect?")

            # Always helpful fallback
            if not suggestions:
                suggestions.append(
                    "Is there a particular angle you'd like to explore further?"
                )

        # Check if we have project insights to suggest diving deeper
        has_project_insights = any(
            insight.sources
            and any(
                source.provider.startswith(("project-", "khive-"))
                for source in insight.sources
            )
            for insight in insights
        )

        if has_project_insights and "khive" not in query_lower:
            suggestions.append(
                "Would you like to see how this relates to the khive project specifically?"
            )

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
