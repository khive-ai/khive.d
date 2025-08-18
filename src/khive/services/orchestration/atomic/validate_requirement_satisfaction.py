from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class RequirementValidation(BaseModel):
    """AFTER, doing your other regular requirements. Present the a deliverable in the
    following format

    - DO NOT only submit the deliverable, the actual work must need to be done first
    - DO NOT submit the deliverable if the work is not done
    """

    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this validation? Analyze systematically:
        - What were the original requirements and success criteria?
        - What implementation is being validated and what claims does it make?
        - What testing evidence and quality metrics are available?
        - Who are the stakeholders and what are their approval criteria?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the validation into organized assessment components:
        - How does the implementation address each functional requirement?
        - What non-functional requirements (performance, security, usability) are satisfied?
        - What quality attributes (maintainability, testability, reliability) are achieved?
        - What gaps, partial implementations, or deviations exist?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the validation findings and concerns systematically:
        - What critical issues or deficiencies were identified?
        - Which requirements are at risk or insufficiently satisfied?
        - What quality, security, or performance concerns need attention?
        - Where might the implementation fail in production scenarios?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize your validation into strategic guidance for stakeholders:
        - What is the overall readiness assessment and recommendation?
        - What specific actions must be completed before approval?
        - How should identified issues be prioritized and addressed?
        - What validation criteria determine final acceptance?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}
        
        Additionally for requirement validation:
        - Have you thoroughly assessed all critical requirements and quality criteria?
        - Is your validation evidence-based and defensible to stakeholders?
        - Does your assessment enable confident approval or rejection decisions?
        
        {CONFIDENCE_PROMPT}
        """
    )
