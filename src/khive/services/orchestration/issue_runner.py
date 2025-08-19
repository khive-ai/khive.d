import logging
from pathlib import Path

from lionagi import Builder, ln

from .issue_parser import load_all_issues
from .parts import IssuePlan
from .workflows.factory import get_orc_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KhiveIssueRunner")


class IssueRunner:
    def __init__(
        self,
        issue_dir: str | Path,
        delay_before_start: float = 0.0,
        max_concurrent: int = 3,
        throttle_period: float = 10,
    ):
        self.session = get_orc_session()
        self.builder = Builder()
        self.issue_dir = issue_dir
        self.call_params = ln.AlcallParams(
            delay_before_start=delay_before_start,
            max_concurrent=max_concurrent,
            throttle_period=throttle_period,
        )

        self._all_issues_plans = load_all_issues(issue_dir)
        self._operations = {}

    def get_issue_plan(self, issue_num: str | int, /) -> IssuePlan:
        """Get the issue plan by issue number."""
        if isinstance(issue_num, int):
            issue_num = str(issue_num)
        return self._all_issues_plans.get(issue_num, None)

    def get_dep_on(self, issue_num: str | int, /):
        """Get the dependencies for the issue."""
        issue_plan = self.get_issue_plan(issue_num)
        if issue_plan is None:
            raise ValueError(f"Issue plan for {issue_num} not found")
        dep_on_ = issue_plan.dependencies
        out = []
        for i in dep_on_:
            if f"issue_{i}" in self._operations:
                out.append(self._operations[f"issue_{i}"])
        return out

    def add_issue(self, issue_num: str | int, /):
        """Add an issue to the orchestration builder."""
        branch = self.session.new_branch()
        op = self.builder.add_operation(
            operation="run_issue",
            issue_plan=self.get_issue_plan(issue_num),
            node_id="issue_" + str(issue_num),
            depends_on=self.get_dep_on(issue_num),
            branch=branch,
        )
        self._operations[f"issue_{issue_num}"] = op

    def load(self, issue_seq: list):
        for j in issue_seq:
            self.add_issue(j)

    async def run(self, visualize: bool = True):
        if visualize:
            self.builder.visualize("IssueRunner")

        g = self.builder.get_graph()
        await self.session.flow(g, alcall_params=self.call_params)
