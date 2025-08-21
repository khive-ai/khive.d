from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import aiofiles
from lionagi.fields import Instruct  # noqa: TC002
from lionagi.protocols.types import Node
from lionagi.utils import Enum, create_path
from pydantic import Field, field_validator, model_validator

from khive._types import BaseModel
from khive.services.composition.parts import AgentRole, ComposerRequest  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import Path  # type: ignore[import-untyped]

DeliverableType = Literal[
    "RequirementsAnalysis",
    "CodeContextAnalysis",
    "IntegrationStrategy",
    "FeatureImplementation",
    "RequirementValidation",
    "DocumentationPackage",
    "TestStrategy",
    "WorkSynthesis",
]


class AgentRequest(BaseModel):
    instruct: Instruct
    compose_request: ComposerRequest
    analysis_type: DeliverableType | None = None
    """Type of operation deliverable (e.g., 'RequirementsAnalysis', 'CodeContextAnalysis')"""


class OrchestrationPlan(BaseModel):
    """Plan for orchestrating agent tasks. Each plan is meant for either concurrent
    or sequential execution, default is concurrent for efficiency. Remember to instruct agents
    to actually do work, not just analyze. Every agent must produce at least one markdown
    deliverable with optional analysis type
    """

    common_background: str
    """Common background information for all agents in the orchestration plan."""

    agent_requests: list[AgentRequest]
    """List of requests for each agent in the orchestration plan."""

    execution_strategy: Literal["sequential", "concurrent"] = "concurrent"
    """Execution strategy for the agents in the orchestration plan."""


class ComplexityAssessment(BaseModel):
    """Complexity assessment with overall score and explanation."""

    overall_complexity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall complexity score (0.0=trivial, 0.3=simple, 0.5=moderate, 0.7=complex, 1.0=very complex). Consider actual work needed, not theoretical complexity.",
    )
    explanation: str = Field(
        description="Brief rationale for complexity assessment focused on practical implementation challenges, not hypothetical issues"
    )
    comment: str | None = Field(
        default=None, description="Additional context, risks, or implementation notes"
    )


# Base quality gate that can be composed with additional validation components
class BaseGate(BaseModel):
    """Base quality gate with pass/fail and reasoning"""

    threshold_met: bool = Field(
        description="Does the work meet the requirements appropriate for THIS issue's scope and current project phase? Consider: Is this exploration, development, or production? What's the actual risk? What would block progress? Return `true` if the work achieves its stated objectives with quality appropriate to context."
    )
    feedback: str | None = Field(
        default=None,
        description="Provide constructive summary of what's working well and what needs improvement. Be specific and actionable in your feedback.",
    )


class GateComponent(BaseModel):
    is_acceptable: bool
    """Does this component meet requirements appropriate for the current context and phase?"""

    problems: list[str] = Field(default_factory=list)
    """List specific problems that would actually block progress or create unacceptable risk"""


GateOptions = Literal["design", "security", "performance", "testing", "documentation"]


class FanoutPatterns(str, Enum):
    """Enumeration for orchestration patterns used in issues"""

    __slots__ = ()

    FANOUT = "fanout"
    W_REFINEMENT = "fanout_with_gated_refinement"
    COMPOSITE = "composite"


class FanoutConfig(BaseModel):
    initial_desc: str
    """Description for initial phase"""

    synth_instruction: str
    """Instruction for synthesis phase to generate deliverables"""

    planning_instruction: str
    """Instruction for planning phase to guide agent actions"""

    context: str | None = None
    """Context for the orchestration, can be None if not needed"""


class RefinementConfig(BaseModel):
    refinement_desc: str
    """Description for refinement phase if quality insufficient"""

    critic_domain: str = "software-architecture"
    """Domain for the critic to evaluate quality"""

    critic_role: AgentRole = "critic"
    """Role of the critic in the orchestration process"""

    gate_instruction: str
    """Instruction for the gate to evaluate quality of deliverables"""

    gates: Any = None  # type: ignore[assignment]
    """Optional gates for additional quality checks, can be a list or dict"""


class MultiPhaseOrchestrationResponse(BaseModel):
    """Response from multi-phase orchestration with dynamic planning."""

    synth_node: Any | None = Field(None, exclude=True)
    """The synthesis node from the orchestration graph, if applicable"""

    synth_result: Any | None = None
    """The result from the synthesis node, if applicable"""

    flow_results: dict | None = Field(None, exclude=True)
    """The results from the flow execution, if applicable"""

    initial_nodes: list[Any] | None = Field(None, exclude=True)
    """The initial nodes from the orchestration graph, if applicable"""

    execution_sequence: list[dict] | None = None
    """Execution sequence showing phase order for concurrency control"""


class GatedMultiPhaseOrchestrationResponse(MultiPhaseOrchestrationResponse):
    """Response from quality-gated multi-phase orchestration with conditional refinement."""

    final_gate: Any | None = Field(None, exclude=True)
    """The final gate node from the orchestration graph, if applicable"""

    qa_branch: Any | None = Field(None, exclude=True)
    """The quality assurance branch from the orchestration graph, if applicable"""

    gate_passed: bool | None = None
    """Whether the final gate was passed, if applicable"""

    refinement_executed: bool | None = None
    """Whether refinement was executed, if applicable"""


IssueNum = int


class IssueExecution(BaseModel):
    success: bool
    result: MultiPhaseOrchestrationResponse | GatedMultiPhaseOrchestrationResponse
    is_redo: bool = False


class IssueResult(BaseModel):
    issue_num: IssueNum
    executions: list[IssueExecution] = Field(default_factory=list)
    success: bool = False

    @field_validator("issue_num", mode="before")
    def validate_issue_num(cls, v: str | int) -> str:
        if isinstance(v, int):
            return str(v)
        return v


class IssuePlan(BaseModel):
    issue_num: IssueNum
    """github issue number"""

    flow_name: str
    """The name of the flow to execute for this issue"""

    system: str
    """the system prompt for the orchestrator"""

    pattern: FanoutPatterns
    """the orchestration pattern to use for this issue"""

    fanout_config: FanoutConfig
    """Configuration for the fanout orchestration pattern"""

    refinement_config: RefinementConfig | None = None
    """Configuration for the conditional refinement pattern, if applicable"""

    blocks_issues: list[IssueNum] = Field(default_factory=list)
    """List of issue numbers that this issue blocks, if any"""

    enables_issues: list[IssueNum] = Field(default_factory=list)
    """List of issue numbers that this issue enables, if any"""

    dependencies: list[IssueNum] = Field(default_factory=list)
    """List of issue numbers that this issue depends on, if any"""

    # Context-aware gate configuration
    project_phase: (
        Literal["exploration", "development", "integration", "production"] | None
    ) = None
    """Project phase for context-aware gate evaluation (auto-detected if not specified)"""

    is_critical_path: bool = Field(default=False)
    """Whether this issue is on the critical path (blocks many other issues)"""

    is_experimental: bool = Field(default=False)
    """Whether this is experimental/exploratory work (reduces gate strictness)"""

    skip_refinement: bool = Field(default=False)
    """Whether to skip refinement entirely (useful for pure exploration)"""

    max_refinement_iterations: int | None = Field(default=None)
    """Maximum refinement iterations (auto-determined based on phase if not set)"""

    @model_validator(mode="after")
    def validate_conditional_refinement(self):
        if self.pattern == FanoutPatterns.W_REFINEMENT:
            if not self.refinement_config:
                raise ValueError(
                    "refinement_config must be set if pattern is 'fanout_with_conditional_refinement'"
                )
        elif self.refinement_config:
            raise ValueError(
                "conditional_refinement_config can only be set if pattern is 'fanout_with_conditional_refinement'"
            )

        return self


class IssueContent(BaseModel):
    issue_num: IssueNum
    """GitHub issue number or string identifier"""

    issue_plan: IssuePlan
    """The orchestration plan for this issue"""

    issue_result: IssueResult
    """The result of executing this issue, if available"""

    operation_status: Literal[
        "pending", "in_progress", "completed", "failed", "cancelled"
    ] = "pending"
    """Status of the operation, e.g., 'pending', 'in_progress', 'completed', 'failed'"""

    gate_passed: bool = False

    git_processed: bool = False
    """Whether the git cycle has been processed for this issue"""

    redo_ctx: str | dict | list | None = None
    """Context from the last review gate, if applicable"""

    needs_redo: bool = False
    """Whether the issue needs to be redone based on gate review"""


class Issue(Node):
    _table_name: ClassVar[str] = "issues"
    content: IssueContent

    @staticmethod
    def create_file_path(issue_num: IssueNum, exists_ok: bool = True) -> Path:
        from khive.utils import KHIVE_CONFIG_DIR

        return create_path(
            directory=f"{KHIVE_CONFIG_DIR}/issues/storage",
            filename=f"issue_{issue_num}.json",
            dir_exist_ok=True,
            file_exist_ok=exists_ok,
        )

    @staticmethod
    def issue_exists(issue_num: IssueNum) -> bool:
        """Check if an issue with the given number exists in the file"""
        try:
            Issue.create_file_path(issue_num, exists_ok=False)
            return False
        except Exception:
            return True

    @classmethod
    async def get(cls, issue_num: IssueNum, plan: IssuePlan) -> Issue:
        res = await cls.load(issue_num)
        if isinstance(res, cls):
            return res

        # Create a new issue if it doesn't exist
        issue = cls(
            content=IssueContent(
                issue_num=issue_num,
                issue_plan=plan,
                issue_result=IssueResult(issue_num=issue_num),
            ),
        )
        await issue.sync()
        return issue

    @classmethod
    async def load(cls, issue_num):
        if cls.issue_exists(issue_num):
            fp = cls.create_file_path(issue_num)
            async with aiofiles.open(fp) as fp:
                text = await fp.read()
            return cls.from_dict(json.loads(text))
        return None

    async def sync(self):
        file_path = self.create_file_path(self.content.issue_num)
        async with aiofiles.open(file_path, "w") as fp:
            await fp.write(json.dumps(self.to_dict()))

    @property
    def last_execution_success(self) -> bool | None:
        if self.content.issue_result.executions:
            return self.content.issue_result.executions[-1].success
        return None


# Rebuild models to resolve forward references
RefinementConfig.model_rebuild()
MultiPhaseOrchestrationResponse.model_rebuild()
GatedMultiPhaseOrchestrationResponse.model_rebuild()
IssuePlan.model_rebuild()


__all__ = (
    "AgentRequest",
    "BaseGate",
    "ComplexityAssessment",
    "FanoutConfig",
    "FanoutPatterns",
    "GateComponent",
    "GatedMultiPhaseOrchestrationResponse",
    "IssueExecution",
    "IssueNum",
    "IssuePlan",
    "IssueResult",
    "MultiPhaseOrchestrationResponse",
    "OrchestrationPlan",
    "RefinementConfig",
)
