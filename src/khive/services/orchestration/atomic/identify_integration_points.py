"""
Identify Integration Points Operation (v2)

Determines where new functionality integrates with existing code.
Uses Pydantic model as prompt template to generate structured integration plan.
"""

from lionagi import Branch
from lionagi.models import FieldModel
from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class IntegrationStrategy(BaseModel):
    """AFTER, doing your other regular requirements. Present the a deliverable in the
    following format

    - DO NOT only submit the deliverable, the actual work must need to be done first
    - DO NOT submit the deliverable if the work is not done
    """

    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this integration challenge? Analyze systematically:
        - What functionality needs to be integrated and why?
        - What is the target system architecture and current state?
        - How does this integration fit into broader system goals?
        - What are the key stakeholder requirements and constraints?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the integration requirements into organized components:
        - What are the specific integration points and their characteristics?
        - What modifications are needed to existing code at each point?
        - How do the integration points relate and depend on each other?
        - What is the optimal sequence and approach for implementation?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the risks and challenges systematically:
        - What are the primary integration risks and mitigation strategies?
        - Which integration points pose backward compatibility concerns?
        - What performance, security, or scalability impacts must be considered?
        - Where are the architectural constraints that could cause problems?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize your analysis into strategic integration guidance:
        - What is the recommended overall integration strategy and phasing?
        - How should the work be sequenced to minimize risk and maximize value?
        - What validation and testing approach ensures integration success?
        - What rollback and contingency plans provide safety nets?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}
        
        Additionally for integration strategy:
        - Have you identified all critical integration points and dependencies?
        - Is your strategy specific enough for implementation teams to execute?
        - Does the approach minimize risk while maintaining architectural integrity?
        
        {CONFIDENCE_PROMPT}
        """
    )
