"""
Synthesize Work Operation (v2)

Creates comprehensive synthesis of all completed work for handoff and PR creation.
Uses Pydantic model as prompt template to generate structured work summary.
"""

from lionagi import Branch
from lionagi.models import FieldModel
from pydantic import BaseModel, Field

from .base import CONFIDENCE_PROMPT, QUALITY_PROMPT


class WorkSynthesis(BaseModel):
    """AFTER, doing your other regular requirements. Present the a deliverable in the
    following format

    - DO NOT only submit the deliverable, the actual work must need to be done first
    - DO NOT submit the deliverable if the work is not done
    """

    # 1. Context Analysis - Understanding inputs and scope
    context_analysis: str = Field(
        description="""
        What is the complete context of this work synthesis? Analyze systematically:
        - What was the original scope and objectives of this work?
        - Which deliverables and artifacts are being synthesized?
        - Who are the intended consumers of this synthesis (stakeholders, implementers, maintainers)?
        - How does this work fit into the broader project timeline and dependencies?
        """
    )

    # 2. Systematic Breakdown - Methodical decomposition
    systematic_breakdown: str = Field(
        description="""
        Break down the accomplishments into organized, comprehensive components:
        - What functional capabilities were delivered and how do they work?
        - What technical architecture and design decisions were implemented?
        - Which requirements were satisfied and which remain outstanding?
        - What testing, documentation, and quality assurance was completed?
        - What external dependencies and integrations were established?
        """
    )

    # 3. Critical Assessment - Challenges, constraints, risks
    critical_assessment: str = Field(
        description="""
        Evaluate the risks, limitations, and considerations systematically:
        - What implementation risks and technical debt were introduced?
        - Which architectural decisions create long-term constraints or opportunities?
        - What performance, security, or scalability concerns need attention?
        - Where are the knowledge gaps or areas requiring additional expertise?
        - What maintenance and operational considerations must be understood?
        """
    )

    # 4. Strategic Synthesis - Integration into actionable insights
    strategic_synthesis: str = Field(
        description="""
        Synthesize the work into strategic guidance for next phases:
        - What is the recommended deployment strategy and rollout plan?
        - How should this work be monitored and validated in production?
        - What are the priority areas for follow-up development or improvement?
        - Which learnings should inform similar future work?
        - What handoff knowledge is critical for ongoing maintenance?
        """
    )

    # 5. Quality Validation - Self-assessment and confidence
    quality_validation: str = Field(
        description=f"""
        {QUALITY_PROMPT}
        
        Additionally for work synthesis:
        - Does this synthesis provide complete handoff knowledge for new team members?
        - Have you captured all critical deployment and operational requirements?
        - Is the synthesis actionable for both immediate next steps and long-term planning?
        
        {CONFIDENCE_PROMPT}
        """
    )
