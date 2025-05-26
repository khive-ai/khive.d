# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Simplified CLI for Khive Information Service.

Examples:
    # Just ask naturally
    khive info "What is quantum computing?"
    khive info "Latest developments in AI safety" --mode realtime
    khive info "Compare Python vs Rust for system programming" --context "Building a high-performance database"

    # All responses are synthesized insights, not raw API data
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from khive.services.info.info_service import InfoServiceGroup
from khive.services.info.parts import InfoRequest, InsightMode


async def run_query(
    query: str, context: str | None, mode: str | None, time_budget: float
) -> None:
    """Execute query and print results."""
    service = InfoServiceGroup()

    try:
        # Build request
        request = InfoRequest(
            query=query,
            context=context,
            mode=InsightMode(mode) if mode else None,
            time_budget_seconds=time_budget,
        )

        # Get insights
        response = await service.handle_request(request)

        # Output results
        if response.success:
            # Print summary first
            print(f"\n✨ {response.summary}\n")

            # Print synthesis if available
            if response.synthesis:
                print("📊 Comprehensive Analysis:")
                print("-" * 50)
                print(response.synthesis)
                print("-" * 50)

            # Print key insights
            if response.insights:
                print(f"\n🔍 Key Insights (confidence: {response.confidence:.0%}):")
                for i, insight in enumerate(response.insights[:5], 1):
                    print(f"\n{i}. {insight.summary}")
                    if insight.details:
                        print(f"   Details: {insight.details[:150]}...")
                    if insight.sources:
                        source = insight.sources[0]
                        print(
                            f"   Source: {source.provider} ({source.type}, confidence: {source.confidence:.0%})"
                        )

            # Print suggestions
            if response.suggestions:
                print("\n💡 Follow-up suggestions:")
                for suggestion in response.suggestions:
                    print(f"   • {suggestion}")

            # JSON output for scripts
            if "--json" in sys.argv:
                print(
                    "\n" + json.dumps(response.model_dump(exclude_none=True), indent=2)
                )
        else:
            print(f"❌ {response.summary}")
            if response.error:
                print(f"Error: {response.error}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await service.close()


def main():
    parser = argparse.ArgumentParser(
        prog="khive info",
        description="Get intelligent insights on any topic",
        epilog="Just ask naturally - the service figures out the best way to help you.",
    )

    parser.add_argument(
        "query", help="Your question or information need in natural language"
    )

    parser.add_argument(
        "--context", "-c", help="Additional context about what you're working on"
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["quick", "comprehensive", "analytical", "realtime"],
        help="Insight gathering mode (auto-detected if not specified)",
    )

    parser.add_argument(
        "--time-budget",
        "-t",
        type=float,
        default=20.0,
        help="Maximum seconds to spend gathering insights (default: 20)",
    )

    parser.add_argument("--json", action="store_true", help="Output raw JSON response")

    args = parser.parse_args()

    # Run the query
    asyncio.run(run_query(args.query, args.context, args.mode, args.time_budget))


if __name__ == "__main__":
    main()
