import json
from pathlib import Path
from typing import Any, Literal

import aiofiles
from khive.services.composition import composer_service
from khive.toolkits.cc import create_cc
from khive.toolkits.cc.create_cc import create_orchestrator_cc_model
from khive.utils import KHIVE_CONFIG_DIR, get_logger
from lionagi import Branch, Builder, Operation, Session
from lionagi.fields import Instruct
from lionagi.models import FieldModel, OperableModel
from lionagi.protocols.types import ID, AssistantResponse, Graph, IDType, Pile

from .atomic import (
    CodeContextAnalysis,
    DocumentationPackage,
    FeatureImplementation,
    IntegrationStrategy,
    RequirementsAnalysis,
    RequirementValidation,
    TestStrategy,
    WorkSynthesis,
)
from .parts import (
    AgentRequest,
    ComposerRequest,
    FanoutResponse,
    FanoutWithGatedRefinementResponse,
    GateOptions,
    OrchestrationPlan,
)
from .prompts import ATOMIC_WORK_GUIDANCE

logger = get_logger("khive.services.orchestration")


class LionOrchestrator:
    # Mapping from analysis type to Pydantic model for FieldModel
    ATOMIC_ANALYSES = {
        "RequirementsAnalysis": RequirementsAnalysis,
        "CodeContextAnalysis": CodeContextAnalysis,
        "IntegrationStrategy": IntegrationStrategy,
        "FeatureImplementation": FeatureImplementation,
        "RequirementValidation": RequirementValidation,
        "DocumentationPackage": DocumentationPackage,
        "TestStrategy": TestStrategy,
        "WorkSynthesis": WorkSynthesis,
    }

    def __init__(self, flow_name: str):
        self.flow_name = flow_name
        self.session: Session = None
        self.builder: Builder = None

    async def initialize(self, model: str | None = None, system: str | None = None):
        orc_cc = await create_cc(
            as_orchestrator=True,
            verbose_output=True,
            model=model,
            auto_finish=True,
        )
        orc_branch = Branch(
            name=f"{self.flow_name}_orchestrator",
            system=system or f"You are an orchestrator for the {self.flow_name} flow",
            use_lion_system_message=True,
            system_datetime=True,
            chat_model=orc_cc,
            parse_model=orc_cc,
        )
        self.session = Session(default_branch=orc_branch, name=self.flow_name)
        self.builder = Builder(self.flow_name)

    @property
    def orc_branch(self):
        return self.session.default_branch

    async def create_cc_branch(
        self,
        compose_request: ComposerRequest,
        agent_suffix: str = "",
        clone_from: str | None = None,
        model: str | None = None,
        verbose_output: bool | None = None,
        permission_mode: str | None = None,
        auto_finish: bool | None = None,
        requires_root: bool = False,
        overwrite_config: bool = False,
        copy_mcp_config: bool = True,
        copy_settings: bool = True,
        copy_claude_md: bool = True,
    ) -> ID[Branch]:
        """Create LionAGI branch with khive composer integration."""
        role = compose_request.role
        suffix_counter = 0
        name = f"{self.flow_name}_{role}_{compose_request.domains}{agent_suffix or ''}"
        full_name = name

        while self.session._lookup_branch_by_name(full_name) is not None:
            full_name = f"{name}_{suffix_counter}"
            suffix_counter += 1
            if suffix_counter > 100:
                raise ValueError(
                    f"Too many branches with name {name}, please choose a different suffix"
                )

        setting_dir = KHIVE_CONFIG_DIR / "claude_roles" / role / ".claude"
        source_dir = (
            Path(__file__).parent.parent.parent
            / "toolkits"
            / "cc"
            / "claude_roles"
            / role
            / ".claude"
        )

        if not setting_dir.exists():
            import shutil

            shutil.copytree(source_dir, setting_dir, dirs_exist_ok=True)

        files_to_check = {"settings.json", "CLAUDE.md"}
        for f in files_to_check:
            if not (setting_dir / f).exists():
                import shutil

                shutil.copy(source_dir / f, setting_dir / f)

        mcp_fp = setting_dir / ".mcp.json"
        settings_fp = setting_dir / "settings.json"
        claude_md_fp = setting_dir / "CLAUDE.md"
        if not mcp_fp.exists() and copy_mcp_config:
            from khive.utils import PROJECT_ROOT

            if (PROJECT_ROOT / ".mcp.json").exists():
                import shutil

                shutil.copy(PROJECT_ROOT / ".mcp.json", mcp_fp)

        if role in ["implementer", "tester", "architect", "reviewer"]:
            requires_root = True
            copy_mcp_config = False
            copy_settings = False
            copy_claude_md = False
            overwrite_config = False

        cc = await create_cc(
            as_orchestrator=False,
            subdir=full_name if not requires_root else None,
            model=model,
            permission_mode=permission_mode,
            verbose_output=verbose_output,
            auto_finish=auto_finish,
            requires_root=requires_root,
            copy_mcp_config_from=mcp_fp if copy_mcp_config else None,
            copy_settings_from=settings_fp if copy_settings else None,
            copy_claude_md_from=claude_md_fp if copy_claude_md else None,
            overwrite_config=overwrite_config,
        )

        compose_response = await composer_service.handle_request(compose_request)

        if clone_from:
            _from = self.session.get_branch(clone_from)
            _new = _from.clone(sender=self.session)
            _new.chat_model = cc
            _new.parse_model = cc
            _new.name = full_name
            self.session.branches.include(_new)
            return _new.id

        # Secure system prompt construction with validation and JSON escaping
        base_system_prompt = compose_response.system_prompt or ""
        branch = Branch(
            chat_model=cc,
            parse_model=cc,
            system=base_system_prompt,
            use_lion_system_message=True,
            system_datetime=True,
            name=full_name,
        )
        self.session.branches.include(branch)
        return branch.id

    @staticmethod
    def generate_flow_plans_field(**plans_description: str):
        a = OperableModel()
        for plan, doc in plans_description.items():
            a.add_field(plan, annotation=OrchestrationPlan, description=doc)

        return FieldModel(
            base_type=a.new_model("FlowOrchestrationPlans"), name="flow_plans"
        )

    @staticmethod
    def generate_quality_gate_field(
        project_phase=None,
        is_critical_path=False,
        is_experimental=False,
        **gate_components,
    ):
        """
        Generate a context-aware quality gate field by composing validation components.

        Args:
            project_phase: Current phase ('exploration', 'development', 'integration', 'production')
            is_critical_path: Whether this issue blocks other work
            is_experimental: Whether this is experimental/exploratory work
            **gate_components: Gate components where keys are gate types and values are
                descriptions (str) or True for default behavior

        Example:
            generate_quality_gate_field(
                project_phase="development",
                is_critical_path=False,
                design="Assess database schema design completeness",
                security=True,  # Use default security validation
                custom_validation="Custom validation requirements"
            )
        """
        from khive.prompts.gates import get_gate_prompt, list_available_gates

        from .parts import BaseGate, GateComponent

        op = OperableModel()
        gates = list_available_gates()

        for k, doc in gate_components.items():
            if not isinstance(doc, str):
                if k not in gates:
                    raise ValueError(
                        f"Unknown gate component '{k}'. Available gates: {', '.join(gates)}"
                    )
                # Use context-aware gate prompt
                doc = get_gate_prompt(
                    k,
                    phase=project_phase,
                    is_critical_path=is_critical_path,
                    is_experimental=is_experimental,
                )
            if doc:
                op.add_field(k, annotation=GateComponent, description=doc)

        return FieldModel(
            base_type=op.new_model("QualityGate", base_type=BaseGate),
            name="quality_gate",
        )

    async def expand_with_plan(
        self,
        root: IDType | list[IDType],
        plan: OrchestrationPlan,
        max_agents: int = 8,
        auto_context: bool = True,
        skip_root_context: bool = True,
    ) -> list[ID[Operation]]:
        """Expand the orchestration plan by creating operations based on agent requests.

        - Args:
            root: Root operation ID or list of IDs to depend on
            plan: OrchestrationPlan containing agent requests
            max_agents: Maximum number of agents to process
            auto_context: Whether to automatically run flow after each step in sequential mode

        - Returns:
            List of operation IDs created for agent requests.
        """
        nodes = []
        root_set = {root} if isinstance(root, IDType) else set(root)
        dep_on = [root] if not isinstance(root, list) else root

        _ctx = {"step_ctx": {}}
        if auto_context and not skip_root_context:
            _ctx["root_ctx"] = self.opres_ctx(dep_on)

        for idx, item in enumerate(plan.agent_requests):
            item: AgentRequest
            if idx >= max_agents:
                break
            if (
                auto_context
                and idx != 0
                and plan.execution_strategy == "sequential"
                and set(dep_on) != root_set
            ):
                await self.run_flow(visualize=False)
                # step context from previous step
                _ctx["step_ctx"][f"{idx + 1}"] = self.opres_ctx(dep_on)

            b_id = await self.create_cc_branch(item.compose_request)
            c_ = plan.common_background + str(item.instruct.context or "")
            c_ = c_.strip()

            analysis_model = self.ATOMIC_ANALYSES[item.analysis_type]
            field_model = FieldModel(analysis_model, name="analysis")

            node = self.builder.add_operation(
                "operate",
                depends_on=dep_on,
                branch=b_id,
                instruct=Instruct(
                    instruction=item.instruct.instruction,
                    context={"task_context": c_, **_ctx},
                    guidance=ATOMIC_WORK_GUIDANCE + item.instruct.guidance,
                ),
                field_models=[field_model],
            )

            nodes.append(node)
            if plan.execution_strategy == "sequential":
                dep_on = [node]

        return nodes

    def opres_ctx(self, ops: IDType | list[IDType]) -> dict[str, Any]:
        """Get operation result context for a given operation ID.

        Args:
            session: LionAGI session
            operation: Operation object with branch_id

        Returns:
            Tool usage summary dict
        """
        g = self.builder.get_graph()
        ops = [ops] if not isinstance(ops, list) else ops

        def _get_ctx(op_id):
            try:
                op: Operation = g.internal_nodes[op_id]
                if not op.branch_id:
                    return {"error": f"Operation {op_id!s} has no branch_id"}

                branch = self.session.get_branch(op.branch_id, None)

                if branch and len(branch.messages) > 0:
                    for i in reversed(list(branch.messages.progression)):
                        if isinstance(msg := branch.messages[i], AssistantResponse):
                            return {
                                "branch_id": str(branch.id),
                                "branch_name": branch.name,
                                "result": msg.model_response.get("result", "N/A"),
                                "summary": msg.model_response.get("summary", "N/A"),
                            }

                return {"error": "No branch or messages found"}
            except Exception as e:
                return {"error": f"Failed to extract summary: {e!s}"}

        return [_get_ctx(o) for o in ops]

    async def run_flow(self, visualize: bool = False):
        """Run flow with timeout protection and security logging."""
        if visualize:
            self.builder.visualize(self.flow_name)
        return await self.session.flow(self.builder.get_graph())

    def new_orc_branch(self) -> Branch:
        cc = create_orchestrator_cc_model(permission_mode="bypassPermissions")
        b = Branch(
            name=f"{self.flow_name}_synthesis",
            chat_model=cc,
            parse_model=cc,
            system="You are a synthesis agent for the khive flow",
            use_lion_system_message=True,
            system_datetime=True,
        )
        self.session.branches.include(b)
        return b

    async def fanout(
        self,
        initial_desc: str,
        planning_instruction: str,
        synth_instruction: str,
        context: str | None = None,
        visualize: bool | Literal["step", "final"] = False,
        max_agents: int = 8,
    ):
        visualize_step = (
            visualize if isinstance(visualize, bool) else visualize == "step"
        )
        flow_plans_field = self.generate_flow_plans_field(
            initial=initial_desc,
        )
        orc_branch = self.new_orc_branch()
        params = {
            "operation": "operate",
            "branch": orc_branch.id,
            "field_models": [flow_plans_field],
            "instruct": Instruct(
                reason=True,
                instruction=planning_instruction,
                context=context,
            ),
        }
        if (ln := self.builder.last_operation_id) is not None:
            params["depends_on"] = [ln]

        # 1. establish root node ---------------------------------------------------------
        root = self.builder.add_operation(**params)

        # 2. run planning ----------------------------------------------------------------
        results = await self.run_flow(visualize_step)
        plans = results["operation_results"][root].flow_plans

        # 3. run initial phase ------------------------------------------------------------
        initial_nodes = await self.expand_with_plan(
            root=root,
            plan=plans.initial,
            max_agents=max_agents,
            auto_context=True,
            skip_root_context=True,
        )
        await self.run_flow(visualize_step)

        # 4. synthesis --------------------------------------------------------------------
        synth_node = self.builder.add_operation(
            "communicate",
            branch=orc_branch.id,
            depends_on=initial_nodes,
            instruction=synth_instruction,
            context=self.opres_ctx(initial_nodes),
        )

        result = await self.run_flow(bool(visualize))
        synth_result = result["operation_results"][synth_node]

        return FanoutResponse(
            synth_node=synth_node,
            synth_result=synth_result,
            flow_results=result,
            initial_nodes=initial_nodes,
        )

    async def fanout_w_gated_refinement(
        self,
        initial_desc: str,
        refinement_desc: str,
        gate_instruction: str,
        synth_instruction: str,
        planning_instruction: str,
        context: str | None = None,
        critic_domain: str = "software-architecture",
        critic_role: str = "critic",
        visualize: bool | Literal["step", "final"] = False,
        gates: list[GateOptions] | dict[str, str] | None = None,
        max_agents=8,
        project_phase=None,
        is_critical_path=False,
        is_experimental=False,
    ) -> dict:
        """
        Reusable conditional quality-gated workflow pattern.

        Pattern: Planning → Initial Phase → Quality Gate → [Conditional Refinement] → Synthesis

        Args:
            initial_desc: Description for initial phase
            refinement_desc: Description for refinement phase if quality insufficient
            gate_instruction: Instruction for quality gate evaluation
            gate_model: Pydantic model class for quality gate results
            synth_instruction: Instruction for final synthesis
            planning_instruction: Instruction for orchestrator planning
            context: Additional context for planning
            critic_domain: Domain expertise for quality critic
            critic_role: Role for quality critic (default: "critic")
            visualize: Whether to visualize the flow
            gates: List of gate components or dict mapping gate names to descriptions

        Returns:
            dict: Results including final gate, QA branch, refinement execution status,
                synthesis node, synthesis result and flow results.
        """

        # 1. validate inputs ---------------------------------------------------------------
        gate_components = {}
        if gates:
            if isinstance(gates, list):
                gates = dict.fromkeys(gates, True)
            for g, d in gates.items():
                if isinstance(d, str):
                    gate_components[g] = d
                elif d is True:
                    gate_components[g] = True
                else:
                    raise ValueError(
                        f"Invalid gate component '{g}': expected str or True, got {type(d)}"
                    )
        qa_field = self.generate_quality_gate_field(
            project_phase=project_phase,
            is_critical_path=is_critical_path,
            is_experimental=is_experimental,
            **gate_components,
        )
        visualize_step = (
            visualize if isinstance(visualize, bool) else visualize == "step"
        )

        # 2. establish root -----------------------------------------------------------------
        plan_field = self.generate_flow_plans_field(
            initial=initial_desc, refinement=refinement_desc
        )
        orc_branch = self.new_orc_branch()
        params = {
            "operation": "operate",
            "branch": orc_branch.id,
            "field_models": [plan_field],
            "instruct": Instruct(
                reason=True,
                instruction=planning_instruction,
                context=context,
            ),
        }

        if (ln := self.builder.last_operation_id) is not None:
            params["depends_on"] = [ln]

        root_node = self.builder.add_operation(**params)
        results = await self.run_flow(visualize_step)
        plans = results["operation_results"][root_node].flow_plans

        # 3. run initial phase ------------------------------------------------------------
        initial_nodes = await self.expand_with_plan(
            root=root_node,
            plan=plans.initial,
            auto_context=True,
            skip_root_context=True,
            max_agents=max_agents,
        )
        await self.run_flow(visualize_step)

        # 4. run quality gate -------------------------------------------------------------
        qa_branch = await self.create_cc_branch(
            compose_request=ComposerRequest(role=critic_role, domains=critic_domain),
            agent_suffix="_quality_assurant",
            auto_finish=True,
        )
        gate1 = self.builder.add_operation(
            operation="operate",
            branch=qa_branch,
            depends_on=initial_nodes,
            instruct=Instruct(
                instruction=gate_instruction,
                reason=True,
                context=self.opres_ctx(initial_nodes),
            ),
            field_models=[qa_field],
        )
        result = await self.run_flow(visualize_step)

        # 5. evaluate quality gate -------------------------------------------------------
        gate_eval = result["operation_results"][gate1].quality_gate

        final_gate = gate1
        refinement_executed = False
        gate_passed = True

        _refine = []
        # 6. conditional refinement --------------------------------------------------------
        if not gate_eval.threshold_met:
            gate_passed = False
            # expand with refinement plan
            refinement_nodes = await self.expand_with_plan(
                root=gate1,
                plan=plans.refinement,
                auto_context=True,
                skip_root_context=False,
            )
            _refine.extend(refinement_nodes)

            # Second quality gate
            gate2 = self.builder.add_operation(
                "operate",
                branch=qa_branch,
                depends_on=(
                    refinement_nodes
                    if plans.refinement.execution_strategy == "concurrent"
                    else [refinement_nodes[-1]]
                ),
                instruct=Instruct(
                    instruction=gate_instruction,
                    reason=True,
                ),
                field_models=[qa_field],
            )

            res = await self.run_flow(visualize_step)
            if res["operation_results"][gate2].quality_gate.threshold_met:
                gate_passed = True

            final_gate = gate2
            refinement_executed = True

        # 7. synthesis --------------------------------------------------------------------

        all_nodes = initial_nodes + _refine + [final_gate]
        synth_node = self.builder.add_operation(
            "communicate",
            branch=orc_branch.id,
            depends_on=[final_gate],
            instruction=synth_instruction,
            context=self.opres_ctx(all_nodes),
        )

        result = await self.run_flow(bool(visualize))
        synth_result = result["operation_results"][synth_node]

        return FanoutWithGatedRefinementResponse(
            synth_node=synth_node,
            synth_result=synth_result,
            flow_results=result,
            initial_nodes=initial_nodes,
            final_gate=final_gate,
            gate_passed=gate_passed,
            refinement_executed=bool(refinement_executed),
        )

    async def save_json(self):
        """Save the current session state to a file."""
        from lionagi.utils import create_path

        fp = create_path(
            directory=f"{KHIVE_CONFIG_DIR}/workspaces/{self.flow_name}/snapshots",
            filename=f"{self.flow_name}_session.json",
            dir_exist_ok=True,
            file_exist_ok=True,
            timestamp=True,
        )

        session_meta = {
            "id": str(self.session.id),
            "name": self.session.name,
            "created_at": self.session.created_at,
        }

        dict_ = {
            "branches": self.session.branches.to_dict(),
            "metadata": session_meta,
            "graph": self.builder.get_graph().to_dict(),
        }

        async with aiofiles.open(fp, "w") as f:
            await f.write(json.dumps(dict_, indent=2))
        logger.info(f"💾 Session saved to {fp}")

    @classmethod
    async def load_json(cls, fp: str | Path):
        """Load session state from a JSON file."""
        fp = Path(fp) if not isinstance(fp, Path) else fp
        if not fp.exists():
            raise FileNotFoundError(f"File {fp} does not exist")

        async with aiofiles.open(fp) as f:
            text = await f.read()

        dict_ = json.loads(text)
        branches = [Branch.from_dict(b) for b in dict_["branches"]]
        orc_branch = Branch.from_dict(dict_["session_default_branch"])

        metadata = {"prev_session_meta": dict_["metadata"]}

        session = Session(
            default_branch=orc_branch, metadata=metadata, name=dict_["metadata"]["name"]
        )
        session.branches.include(branches)

        internal_nodes = Pile.from_dict(dict_["graph"]["internal_nodes"])
        internal_edges = Pile.from_dict(dict_["graph"]["internal_edges"])
        g = Graph(
            internal_nodes=internal_nodes,
            internal_edges=internal_edges,
        )
        builder = Builder(name=session.name)
        builder.graph = g

        self = cls(flow_name=session.name)
        self.session = session
        self.builder = builder
        return self
