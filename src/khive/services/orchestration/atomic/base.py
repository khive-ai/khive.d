from typing import Protocol


class AtomicMetaPrompt(Protocol):
    """Protocol defining the atomic meta-prompting pattern"""

    context_analysis: str
    """Context Analysis - Understanding inputs and scope"""

    systematic_breakdown: str
    """Systematic Breakdown - Methodical decomposition"""

    critical_assessment: str
    """Critical Assessment - Challenges, constraints, risks"""

    strategic_synthesis: str
    """Strategic Synthesis - Integration into actionable insights"""

    quality_validation: str
    """Quality Validation - Self-assessment and confidence"""


# Universal confidence assessment pattern
CONFIDENCE_PROMPT = """
Assess your confidence in this analysis on a scale of 1-10 and explain your reasoning:
- What aspects are you most confident about and why?
- What uncertainties or knowledge gaps remain?
- What additional information would improve this analysis?
- How should the consumer of this analysis interpret its limitations?
"""

# Universal quality validation pattern
QUALITY_PROMPT = """
Evaluate the quality and completeness of your analysis:
- Have you addressed all essential aspects of this cognitive task?
- Are your insights specific and actionable rather than generic?
- What evidence supports your key conclusions?
- How does this analysis enable effective next steps?
"""
