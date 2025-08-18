"""
Implement Feature Increment Operation (v2)

Generates actual code changes based on requirements and integration strategy.
Uses Pydantic model as prompt template to generate structured implementation.
"""

from lionagi import Branch
from lionagi.models import FieldModel
from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class FeatureImplementation(BaseModel):
    """AFTER, doing your other regular requirements. Present the a deliverable in the
    following format

    - DO NOT only submit the deliverable, the actual work must need to be done first
    - DO NOT submit the deliverable if the work is not done
    """

    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this implementation? Analyze systematically:
        - What feature is being implemented and what problem does it solve?
        - How do the requirements and integration strategy guide this implementation?
        - What existing system components will this implementation interact with?
        - What are the success criteria and quality expectations?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the implementation into organized, actionable components:
        - What are the specific code changes needed for each file and module?
        - How should the implementation be structured and sequenced?
        - What new components, functions, or classes need to be created?
        - What existing code needs modification and what are the exact changes?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the implementation challenges and constraints systematically:
        - What are the primary implementation risks and how can they be mitigated?
        - Which technical constraints or dependencies could cause issues?
        - What performance, security, or maintainability concerns need attention?
        - Where might this implementation create technical debt or coupling issues?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize your analysis into strategic implementation guidance:
        - What is the recommended implementation approach and development sequence?
        - How should testing be integrated throughout the development process?
        - What documentation and deployment considerations are critical?
        - What quality gates and validation checkpoints ensure successful delivery?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}
        
        Additionally for feature implementation:
        - Is your implementation plan specific enough for developers to execute?
        - Have you addressed all critical technical and quality requirements?
        - Does the approach maintain code quality and follow established patterns?
        
        {CONFIDENCE_PROMPT}
        """
    )
