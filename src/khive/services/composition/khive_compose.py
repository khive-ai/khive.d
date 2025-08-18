"""
Simplified CLI for Khive Agent Composition Service.

Examples:
    # Basic composition
    khive compose researcher
    khive compose architect -d distributed-systems

    # With multiple domains
    khive compose analyst -d "machine-learning,statistics"

    # With context
    khive compose implementer -d rust -c "Building a high-performance web server"

    # JSON output for scripts
    khive compose tester -d security --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .composer_service import ComposerService
from .parts import ComposerRequest


async def run_composition(
    role: str,
    domains: str | None,
    context: str | None,
    json_output: bool,
    enhanced: bool = False,
    secure: bool = False,
) -> None:
    """Execute composition and print results."""
    service = ComposerService()

    try:
        # Build request
        request = ComposerRequest(
            role=role,
            domains=domains,
            context=context,
        )

        # Get composition
        response = await service.handle_request(request)

        # Output results
        if json_output:
            print(json.dumps(response.model_dump(exclude_none=True), indent=2))
        elif response.success:
            # Print summary
            print(f"\n🤖 {response.summary}")
            print(f"🆔 Agent ID: {response.agent_id}")
            print(f"👤 Role: {response.role}")
            print(
                f"🎯 Domains: {', '.join(response.domains) if response.domains else 'general'}"
            )
            print(f"✨ Confidence: {response.confidence:.0%}")

            if response.capabilities:
                print("\n🔧 Capabilities:")
                for cap in response.capabilities[:5]:  # Show first 5
                    if cap.strip():
                        print(f"  • {cap.strip()}")
                if len(response.capabilities) > 5:
                    print(
                        f"  ... and {len(response.capabilities) - 5} more capabilities"
                    )

            if response.tools:
                print(f"\n🛠️  Tools: {', '.join(response.tools)}")

            if response.domain_expertise:
                print("\n📚 Domain Expertise:")
                for expertise in response.domain_expertise[:3]:  # Show first 3
                    print(f"  • {expertise.domain_id}")
                    if expertise.knowledge_patterns:
                        pattern_count = sum(
                            len(v) if isinstance(v, list) else 1
                            for v in expertise.knowledge_patterns.values()
                        )
                        print(f"    Knowledge patterns: {pattern_count}")
                    if expertise.decision_rules:
                        rule_count = sum(
                            len(v) if isinstance(v, list) else 1
                            for v in expertise.decision_rules.values()
                        )
                        print(f"    Decision rules: {rule_count}")
                    if expertise.specialized_tools:
                        print(
                            f"    Specialized tools: {len(expertise.specialized_tools)}"
                        )
                if len(response.domain_expertise) > 3:
                    print(
                        f"  ... and {len(response.domain_expertise) - 3} more domains"
                    )

            print("\n📝 System Prompt Preview:")
            print("─" * 60)
            # Show first few lines of system prompt
            lines = response.system_prompt.split("\n")
            for line in lines[:10]:
                print(line)
            if len(lines) > 10:
                print(f"... and {len(lines) - 10} more lines")
            print("─" * 60)

            # **NEW: Show essential communication info for enhanced/secure mode**
            if (
                (enhanced or secure)
                and hasattr(response, "metadata")
                and response.metadata
            ):
                comm_info = response.metadata.get("communication", {})
                if comm_info:
                    artifact_id = comm_info.get("artifact_id", "none")
                    print("\n🔗 Communication Ready")
                    print(
                        f"📝 Publish findings: uv run khive communicate publish --artifact={artifact_id} --section=findings --content='...'"
                    )
                    print(
                        f"🚨 Check urgent: uv run khive communicate check-urgent --agent={response.agent_id}"
                    )
                    print(
                        f"📊 Get status: uv run khive communicate status --agent={response.agent_id}"
                    )

                # **NEW: Show security info for secure mode**
                if secure and "security" in response.metadata:
                    security_info = response.metadata["security"]
                    print("\n🛡️ Security Status")
                    print(
                        f"✅ Validation: {'Passed' if security_info.get('validation_passed') else 'Failed'}"
                    )
                    print(
                        f"✅ Resource Limits: {'Checked' if security_info.get('resource_limits_checked') else 'Not Checked'}"
                    )
                    print(
                        f"✅ Sanitization: {'Applied' if security_info.get('sanitization_applied') else 'Not Applied'}"
                    )
                    print(
                        f"🔍 Operation ID: {security_info.get('operation_id', 'unknown')}"
                    )

                    # Show performance info
                    if "performance" in response.metadata:
                        perf_info = response.metadata["performance"]
                        cached = perf_info.get("cached", False)
                        print(f"⚡ Performance: {'Cached' if cached else 'Generated'}")
                        if not cached:
                            gen_time = perf_info.get("generation_time_ms", 0)
                            if gen_time > 0:
                                print(f"⏱️  Generation Time: {gen_time:.2f}ms")

        else:
            print(f"❌ Composition failed: {response.summary}")
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
        prog="khive compose",
        description="Compose intelligent agents from role + domain specifications",
        epilog="Provide a role and optional domains to generate a specialized agent.",
    )

    parser.add_argument(
        "role", help="Agent role (e.g., researcher, architect, implementer)"
    )

    parser.add_argument(
        "--domains", "-d", help="Comma-separated list of domain expertise"
    )

    parser.add_argument("--context", "-c", help="Task context for agent composition")

    parser.add_argument("--json", action="store_true", help="Output raw JSON response")

    parser.add_argument(
        "--enhanced",
        action="store_true",
        help="Use enhanced LionAGI-native communication system",
    )

    parser.add_argument(
        "--secure",
        action="store_true",
        help="Use security-hardened LionAGI service with resource limits and validation",
    )

    args = parser.parse_args()

    # Run the composition
    asyncio.run(
        run_composition(
            args.role, args.domains, args.context, args.json, args.enhanced, args.secure
        )
    )


if __name__ == "__main__":
    main()
