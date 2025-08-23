import logging

from lionagi.libs.concurrency import get_cancelled_exc_class

from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (FanoutPatterns, Issue,
                                                IssueExecution, IssuePlan,
                                                IssueResult)
from khive.services.orchestration.prompts import (
    KHIVE_PLAN_REMINDER, REDO_ORCHESTRATOR_INSTRUCTION, SYNTHESIS_INSTRUCTION)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KhiveOperations")


async def execute_issue(
    issue: Issue, issue_plan: IssuePlan | None = None, **_kw
) -> tuple[bool, Issue]:
    """Execute an issue through the orchestration framework.

    Args:
        issue: Issue to execute
        issue_plan: Execution plan for the issue
        **_kw: Framework parameters (branch, depends_on) passed by orchestration registry
    """
    if issue.content.git_processed is True:
        logger.info(f"🔵 Skipping already processed issue #{issue.content.issue_num}")
        return True, None
    issue_result: IssueResult = issue.content.issue_result
    is_redo = issue.content.needs_redo
    redo_ctx = issue.content.redo_ctx

    orc = LionOrchestrator(issue_plan.flow_name)
    await orc.initialize("sonnet")

    # 1. handle parameters and instructions -------------------------------------------------------
    result: dict = {}
    success = True
    planning_instruction = (
        KHIVE_PLAN_REMINDER.format(issue_num=issue.content.issue_num)
        + issue_plan.fanout_config.planning_instruction
    )

    if is_redo:
        planning_instruction = (
            REDO_ORCHESTRATOR_INSTRUCTION.format(
                issue_num=issue.content.issue_num, redo_ctx=redo_ctx
            )
            + planning_instruction
        )

    params = issue_plan.fanout_config.model_dump()
    params["planning_instruction"] = planning_instruction

    meth = orc.fanout

    # 2. handle refinement pattern if applicable ---------------------------------------------------
    if issue_plan.pattern == FanoutPatterns.W_REFINEMENT:
        params.update(issue_plan.refinement_config.model_dump())
        # Add context parameters for gate evaluation (only needed for gated refinement)
        params["project_phase"] = issue_plan.project_phase
        params["is_critical_path"] = issue_plan.is_critical_path
        params["is_experimental"] = issue_plan.is_experimental
        meth = orc.fanout_w_gated_refinement

    params["synth_instruction"] = (
        issue_plan.fanout_config.synth_instruction
        + SYNTHESIS_INSTRUCTION.format(flow_name=issue_plan.flow_name)
    )

    # 3. run the orchestration method -----------------------------------------------------------------
    try:
        result = await meth(**params)
        success = True
    except get_cancelled_exc_class():
        logger.warning(f"⚠️ Issue #{issue_plan.issue_num} was cancelled.")
        success = False
    except Exception as e:
        logger.exception(f"💥 Issue #{issue_plan.issue_num} error: {e}")
        success = False

    issue_result.executions.append(
        IssueExecution(success=success, result=result, is_redo=is_redo)
    )
    logger.info(
        f"{'✅' if success else '❌'} Issue #{issue_plan.issue_num} {'completed' if success else 'failed'}"
    )
    await orc.save_json()
    await issue.sync()
    return success, issue
