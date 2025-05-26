# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP server for Khive Information Service.

Presents the service as intelligence enhancement, not peer consultation.
"""

from fastmcp import FastMCP

from khive.services.info.info_service import InfoServiceGroup
from khive.services.info.parts import InfoRequest, InsightMode

# Agent-friendly description that emphasizes enhancement, not delegation
instruction = """
Khive Info enhances your intelligence with real-time insights and comprehensive analysis.

This is NOT about asking other agents - it's about augmenting YOUR capabilities with:
- Real-time information synthesis from multiple sources
- Deep analytical perspectives on complex topics  
- Fact-checking and verification capabilities
- Comprehensive research synthesis

You remain in control - this service simply gives you superpowers for information gathering.
"""

mcp = FastMCP(
    name="khive_info",
    instructions=instruction,
    tags=["intelligence", "enhancement", "research", "analysis", "insights"],
)


@mcp.tool(
    name="get_insights",
    description="Enhance your intelligence with synthesized insights on any topic",
    tags=["research", "analysis", "synthesis", "enhancement"],
)
async def get_insights(
    query: str,
    context: str | None = None,
    depth: str = "auto",
):
    """
    Get intelligent insights on any topic.

    This enhances YOUR capabilities - it doesn't delegate to others.
    You get synthesized, actionable intelligence, not raw search results.

    Args:
        query: Natural language question or information need
        context: Optional context about what you're working on
        depth: How deep to go - 'quick', 'comprehensive', 'analytical', 'realtime', or 'auto'

    Returns:
        Synthesized insights that enhance your understanding
    """
    service = InfoServiceGroup()

    try:
        # Map depth to mode
        mode_map = {
            "quick": InsightMode.QUICK,
            "comprehensive": InsightMode.COMPREHENSIVE,
            "analytical": InsightMode.ANALYTICAL,
            "realtime": InsightMode.REALTIME,
            "auto": None,
        }

        request = InfoRequest(
            query=query,
            context=context,
            mode=mode_map.get(depth),
            time_budget_seconds=15.0,  # Reasonable default for agents
        )

        response = await service.handle_request(request)

        if response.success:
            # Return agent-friendly format
            result = {
                "summary": response.summary,
                "confidence": f"{response.confidence:.0%}",
                "insights": [
                    {
                        "finding": insight.summary,
                        "details": insight.details,
                        "confidence": (
                            f"{insight.sources[0].confidence:.0%}"
                            if insight.sources
                            else "unknown"
                        ),
                    }
                    for insight in response.insights[:5]
                ],
                "synthesis": response.synthesis,
                "suggestions": response.suggestions,
            }

            # Add mode information
            result["approach_used"] = response.mode_used.value

            return result
        else:
            return {
                "error": response.error or "Unable to gather insights",
                "summary": response.summary,
            }

    except Exception as e:
        return {
            "error": str(e),
            "summary": "An error occurred while gathering insights",
        }
    finally:
        await service.close()


@mcp.tool(
    name="analyze_topic",
    description="Get multi-perspective analysis on complex topics",
    tags=["analysis", "perspectives", "deep-dive"],
)
async def analyze_topic(
    topic: str,
    specific_aspects: list[str] | None = None,
):
    """
    Get comprehensive multi-perspective analysis.

    This provides YOU with different analytical lenses to understand complex topics.
    Not delegation - augmentation.

    Args:
        topic: The topic to analyze deeply
        specific_aspects: Optional list of specific aspects to focus on

    Returns:
        Multi-faceted analysis from practical, theoretical, and critical perspectives
    """
    service = InfoServiceGroup()

    try:
        # Build analytical query
        query = topic
        if specific_aspects:
            query += f". Focus on: {', '.join(specific_aspects)}"

        request = InfoRequest(
            query=query,
            mode=InsightMode.ANALYTICAL,
            time_budget_seconds=20.0,  # More time for deep analysis
        )

        response = await service.handle_request(request)

        if response.success:
            return {
                "topic": topic,
                "analysis": response.synthesis,
                "perspectives": [
                    {
                        "viewpoint": insight.summary,
                        "analysis": insight.details,
                        "strength": f"{insight.relevance:.0%}",
                    }
                    for insight in response.insights
                ],
                "key_takeaway": response.summary,
                "explore_further": response.suggestions,
            }
        else:
            return {"error": response.error, "topic": topic}

    except Exception as e:
        return {"error": str(e), "topic": topic}
    finally:
        await service.close()


@mcp.tool(
    name="check_latest",
    description="Get the most current information on rapidly changing topics",
    tags=["realtime", "current", "latest", "updates"],
)
async def check_latest(
    topic: str,
    time_window: str = "day",
):
    """
    Get the latest information on time-sensitive topics.

    Enhances your awareness with current developments.

    Args:
        topic: What you want current information about
        time_window: How recent - 'day', 'week', or 'month'

    Returns:
        Latest synthesized information with temporal context
    """
    service = InfoServiceGroup()

    try:
        # Add temporal context to query
        time_phrases = {
            "day": "in the last 24 hours",
            "week": "in the past week",
            "month": "in the past month",
        }

        query = f"Latest updates on {topic} {time_phrases.get(time_window, '')}"

        request = InfoRequest(
            query=query, mode=InsightMode.REALTIME, time_budget_seconds=10.0
        )

        response = await service.handle_request(request)

        if response.success:
            return {
                "topic": topic,
                "current_status": response.summary,
                "latest_developments": response.synthesis,
                "last_updated": time_window,
                "confidence_in_recency": f"{response.confidence:.0%}",
                "next_steps": response.suggestions,
            }
        else:
            return {"error": response.error, "topic": topic}

    except Exception as e:
        return {"error": str(e), "topic": topic}
    finally:
        await service.close()


if __name__ == "__main__":
    mcp.run()
