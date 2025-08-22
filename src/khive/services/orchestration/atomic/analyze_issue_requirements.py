from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class RequirementsAnalysis(BaseModel):
    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this request? Analyze the issue systematically:
        - What problem is being solved and for whom?
        - What business or technical objectives drive this request?
        - How does this fit into the broader system and project goals?
        - What implicit requirements can you infer from the context?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the requirements into organized, actionable components:
        - What are the distinct functional requirements? (Use REQ-001, REQ-002 format)
        - What are the non-functional requirements (performance, security, usability)?
        - What technical constraints and dependencies exist?
        - How do these requirements prioritize against each other?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the challenges and risks systematically:
        - What are the primary implementation risks and mitigation strategies?
        - Where are the ambiguities that need stakeholder clarification?
        - What architectural or technical constraints could cause problems?
        - Which requirements conflict or create implementation tension?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize your analysis into strategic guidance for implementation:
        - What is the recommended implementation approach and sequencing?
        - How should the work be scoped and phased for maximum value delivery?
        - What are the key design decisions that must be made early?
        - What success criteria and acceptance tests validate completion?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}

        Additionally for requirements analysis:
        - Are the requirements specific enough for unambiguous implementation?
        - Have you identified all critical dependencies and integration points?
        - Do the requirements enable accurate effort estimation?

        {CONFIDENCE_PROMPT}
        """
    )
