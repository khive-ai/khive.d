from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class DocumentationPackage(BaseModel):
    """AFTER, doing your other regular requirements. Present the a deliverable in the
    following format

    - DO NOT only submit the deliverable, the actual work must need to be done first
    - DO NOT submit the deliverable if the work is not done
    """

    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this documentation need? Analyze systematically:
        - What functionality is being documented and who are the target audiences?
        - What implementation details and requirements drive the documentation scope?
        - How does this documentation fit into existing documentation architecture?
        - What user workflows and use cases must the documentation support?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the documentation requirements into organized components:
        - What API documentation is needed (endpoints, parameters, responses, examples)?
        - What technical documentation covers architecture and implementation details?
        - What user-facing documentation enables effective feature adoption?
        - What code documentation (docstrings, comments) supports maintainability?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the documentation challenges and quality requirements systematically:
        - What are the primary documentation gaps and user knowledge barriers?
        - Which areas require the most clarity to prevent user confusion or errors?
        - What maintenance and update requirements will this documentation create?
        - Where might documentation become stale or inconsistent with implementation?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize your analysis into strategic documentation guidance:
        - What is the recommended documentation strategy and information architecture?
        - How should the documentation be structured for maximum user value?
        - What examples, tutorials, and practical guidance are most critical?
        - What documentation maintenance and versioning approach ensures long-term quality?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}

        Additionally for documentation generation:
        - Does your documentation plan address all critical user needs and scenarios?
        - Is the documentation clear, accurate, and immediately actionable?
        - Have you provided sufficient examples and practical guidance for successful adoption?

        {CONFIDENCE_PROMPT}
        """
    )
