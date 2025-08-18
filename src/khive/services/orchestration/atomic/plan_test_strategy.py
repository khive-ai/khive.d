"""
Plan Test Strategy Operation (v2)

Creates comprehensive testing strategy for implemented features.
Uses Pydantic model as prompt template to generate structured test plan.
"""

from lionagi import Branch
from lionagi.models import FieldModel
from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class TestStrategy(BaseModel):
    """AFTER, doing your other regular requirements. Present the a deliverable in the
    following format

    - DO NOT only submit the deliverable, the actual work must need to be done first
    - DO NOT submit the deliverable if the work is not done
    """

    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this testing challenge? Analyze systematically:
        - What functionality is being tested and what are the quality requirements?
        - What implementation characteristics and risk factors drive testing needs?
        - How does this testing fit into existing test infrastructure and practices?
        - What are the key failure scenarios and validation requirements?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the testing requirements into organized components:
        - What unit tests are needed for individual components and functions?
        - What integration tests validate component interactions and data flows?
        - What end-to-end scenarios test complete user workflows and system behavior?
        - What test data, fixtures, and infrastructure support these testing needs?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the testing challenges and risk factors systematically:
        - What are the primary testing risks and coverage gaps that could cause issues?
        - Which test scenarios are most critical for preventing production failures?
        - What testing constraints (time, resources, environment) affect strategy?
        - Where might testing become brittle, slow, or difficult to maintain?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize your analysis into strategic testing guidance:
        - What is the recommended overall testing strategy and coverage approach?
        - How should tests be prioritized and sequenced for maximum value?
        - What testing tools, frameworks, and automation provide optimal efficiency?
        - What test maintenance and continuous validation practices ensure long-term quality?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}
        
        Additionally for test strategy planning:
        - Does your testing strategy provide sufficient coverage for critical functionality?
        - Are your test scenarios realistic and likely to catch real issues?
        - Is the testing approach practical and maintainable for the development team?
        
        {CONFIDENCE_PROMPT}
        """
    )
