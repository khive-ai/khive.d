import logging

from lionagi.fields import Instruct

from ..orchestrator import LionOrchestrator
from ..parts import (
    BaseGate,
    ComposerRequest,
    FanoutPatterns,
    FanoutWithGatedRefinementResponse,
    Issue,
    IssuePlan,
    IssueResult,
)
from ..prompts import CRITIC_REVIEW_INSTRUCTION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KhiveOperations")


async def review_gate(issue: Issue, **kw) -> tuple[bool, Issue]:
    issue_plan: IssuePlan = issue.content.issue_plan
    issue_result: IssueResult = issue.content.issue_result

    logging.info(
        f"\n🔍 Critic Review Gate for Issue #{issue_plan.issue_number}, Execution Number {len(issue_result.executions)}"
    )
    orc = LionOrchestrator(issue_plan.flow_name)
    await orc.initialize("sonnet", system="You are acting as a critic reviewer")

    # 1. gather context needed for critic review ---------------------------------------------
    def _gather_critic_context():
        execution = issue_result.executions[-1]
        res = execution.result
        _ctx = f"Final fanout result: {res.synth_result}\n"

        if issue_plan.pattern == FanoutPatterns.W_REFINEMENT and hasattr(
            res, "final_gate"
        ):
            res: FanoutWithGatedRefinementResponse
            _ctx += f"Final gate summary: {orc.opres_ctx(res.final_gate)}"
        _ctx += res.model_dump_json(
            exclude={"synth_node", "flow_results", "initial_nodes"}
        )

        _domain = "software-architecture"
        if issue_plan.refinement_config and issue_plan.refinement_config.critic_domain:
            _domain = issue_plan.refinement_config.critic_domain

        return _ctx, _domain

    # 2. create critic nodes ----------------------------------------------------------------
    critic_nodes = []
    ctx, domain = _gather_critic_context()

    # Use context-aware gate generation from issue configuration
    qa_field = orc.generate_quality_gate_field(
        project_phase=issue_plan.project_phase,
        is_critical_path=issue_plan.is_critical_path,
        is_experimental=issue_plan.is_experimental,
        design=True,
        security=True,
        performance=True,
    )
    root = orc.builder.last_operation_id

    for _ in range(5):
        critic = await orc.create_cc_branch(
            compose_request=ComposerRequest(role="critic", domain=domain),
            verbose_output=False,
            auto_finish=True,
            overwrite_config=True,
            agent_suffix=f"issue_{issue_plan.issue_number}_gate_review",  # ensure unique agent names
        )
        node = orc.builder.add_operation(
            operation="operate",
            depends_on=[root],
            branch=critic,
            instruct=Instruct(
                instruction=CRITIC_REVIEW_INSTRUCTION,
                context=ctx,
                reason=True,
            ),
            field_models=[qa_field],
        )
        critic_nodes.append(node)

    # 3. Execute critic review flow ------------------------------------------------
    try:
        results = await orc.run_flow()
        gates: list[BaseGate] = [
            getattr(results["operation_results"][n], "quality_gate", None)
            for n in critic_nodes
        ]
        score = sum(
            1 if gate and getattr(gate, "threshold_met", False) else 0 for gate in gates
        )
        if score >= 3:
            logging.info(
                f"✅ Critic review gate PASSED for issue #{issue_plan.issue_number} ({score}/5 votes)"
            )
            issue.content.gate_passed = True
            issue.content.redo_ctx = None
            issue.content.needs_redo = False
        else:
            logger.info(
                f"❌ Critic review gate FAILED for issue #{issue_plan.issue_number} ({score}/5 votes)"
            )
            logger.info(f"🔄 Issue #{issue_plan.issue_number} will be re-executed")

            synth_node = orc.builder.add_operation(
                operation="communicate",
                depends_on=critic_nodes,
                branch=critic_nodes[0],
                instruction="synthesize critic feedback into actionable items for orchestrator to re-execute the issue",
                context=orc.opres_ctx(critic_nodes),
            )
            results = await orc.run_flow()
            synth_result = results["operation_results"][synth_node]

            issue.content.redo_ctx = synth_result
            issue.content.gate_passed = False
            issue.content.needs_redo = True

    except Exception as e:
        logger.error(
            f"💥 Critic review gate failed for issue #{issue_plan.issue_number}: {e}"
        )
        issue.content.redo_ctx = None
        issue.content.gate_passed = False
        issue.content.needs_redo = True

    await issue.sync()
    return issue.content.gate_passed, issue
