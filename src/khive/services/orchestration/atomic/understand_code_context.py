"""
Understand Code Context Operation (v2)

Analyzes codebase structure and patterns to build mental model for integration.
Uses Pydantic model as prompt template to generate structured analysis.
"""

from lionagi import Branch
from lionagi.models import FieldModel
from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class CodeContextAnalysis(BaseModel):
    """AFTER, doing your other regular requirements. Present the a deliverable in the
    following format

    - DO NOT only submit the deliverable, the actual work must need to be done first
    - DO NOT submit the deliverable if the work is not done
    """

    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this codebase? Analyze systematically:
        - What type of system is this and what problem domain does it address?
        - What are the primary use cases and user flows?
        - How mature is this codebase and what development phase is it in?
        - What are the key business requirements this code supports?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the codebase architecture into analyzable components:
        - What are the major architectural layers and their responsibilities?
        - What are the core modules/packages and their specific purposes?
        - How is data flow organized through the system?
        - What external dependencies and integrations exist?
        - What design patterns and conventions are consistently used?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the constraints and risks for modification:
        - What architectural constraints must be absolutely respected?
        - Which components are tightly coupled and fragile?
        - Where are the performance bottlenecks and scalability concerns?
        - What security boundaries and trust models exist?
        - Which areas have high complexity or technical debt?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize your analysis into strategic integration guidance:
        - What are the recommended integration points for new functionality?
        - How should new code follow established patterns and conventions?
        - What extension mechanisms are already available vs. need creation?
        - Which integration approach minimizes risk and maximizes maintainability?
        - What refactoring might be needed to enable clean integration?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}
        
        Additionally for code context analysis:
        - Have you identified all critical integration points and dependencies?
        - Is your architectural understanding detailed enough for implementation decisions?
        - Have you captured the essential patterns that new code must follow?
        
        {CONFIDENCE_PROMPT}
        """
    )
