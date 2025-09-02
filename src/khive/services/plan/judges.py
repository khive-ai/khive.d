"""
Cross-judgment system for plan evaluation and pairwise comparison.
Implements rubric scoring and pairwise battles as per ChatGPT's design.
"""
from __future__ import annotations
import asyncio
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from itertools import combinations

from lionagi import Branch, iModel
from lionagi.models import HashableModel
from .models import StrategyCandidate, JudgeScore, PairwiseComparison


class JudgeEngine:
    """Cross-judges for candidate evaluation and pairwise comparison."""
    
    JUDGE_SCORING_PROMPT = """You are an expert plan evaluator with the role of {judge_role}.

Evaluate this software development plan on the following criteria (score 0-10 each):

1. FEASIBILITY: Can this plan realistically be executed?
2. RISK: How well does it manage potential risks and blockers?  
3. COVERAGE: Does it comprehensively address the task requirements?
4. COST_EFFICIENCY: Is the resource allocation reasonable and efficient?
5. COORDINATION_CLARITY: Are agent roles and handoffs clear?
6. TESTABILITY: Can progress and success be measured/validated?

PLAN TO EVALUATE:
{plan_json}

ORIGINAL TASK: {task_description}

Provide scores (0-10) for each criterion and an overall score (0-10).
Include detailed reasoning for your evaluation."""

    PAIRWISE_PROMPT = """You are an expert plan evaluator with the role of {judge_role}.

Compare these two software development plans and determine which is better overall.

PLAN A:
{plan_a_json}

PLAN B: 
{plan_b_json}

ORIGINAL TASK: {task_description}

Evaluation criteria:
- Feasibility and risk management
- Coverage of requirements
- Resource efficiency
- Coordination clarity
- Testability and validation

Which plan is better? Respond with:
- winner: "A" or "B"
- confidence: 0.0-1.0 (how confident are you?)
- reasoning: Detailed comparison explaining your choice

Consider the trade-offs carefully and justify your decision."""

    def __init__(self, config_dict: Dict[str, Any]):
        self.judges_config = config_dict.get("judges", [])
        self.max_concurrency = config_dict.get("budgets", {}).get("max_total_concurrency", 8)
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
    
    async def score_candidates(
        self,
        candidates: List[StrategyCandidate],
        task_description: str
    ) -> List[List[JudgeScore]]:
        """Score all candidates with all judges (rubric-based)."""
        tasks = []
        
        for candidate_idx, candidate in enumerate(candidates):
            for judge_config in self.judges_config:
                task = asyncio.create_task(
                    self._score_single_candidate(
                        candidate=candidate,
                        judge_config=judge_config,
                        task_description=task_description,
                        candidate_id=str(candidate_idx)
                    )
                )
                tasks.append(task)
        
        # Execute scoring tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Organize scores by candidate
        scores_by_candidate = [[] for _ in candidates]
        task_idx = 0
        
        for candidate_idx in range(len(candidates)):
            for judge_idx in range(len(self.judges_config)):
                if task_idx < len(results) and isinstance(results[task_idx], JudgeScore):
                    scores_by_candidate[candidate_idx].append(results[task_idx])
                task_idx += 1
        
        return scores_by_candidate
    
    async def pairwise_comparisons(
        self,
        candidates: List[StrategyCandidate], 
        task_description: str,
        max_pairs: int = 24
    ) -> List[PairwiseComparison]:
        """Generate pairwise comparisons between candidates."""
        # Sample uncertain pairs (all combinations if small, random subset if large)
        all_pairs = list(combinations(range(len(candidates)), 2))
        
        if len(all_pairs) <= max_pairs:
            selected_pairs = all_pairs
        else:
            # Prioritize uncertain pairs (could implement entropy-based selection)
            selected_pairs = random.sample(all_pairs, max_pairs)
        
        tasks = []
        
        for candidate_a_idx, candidate_b_idx in selected_pairs:
            for judge_config in self.judges_config:
                task = asyncio.create_task(
                    self._compare_pair(
                        candidate_a=candidates[candidate_a_idx],
                        candidate_b=candidates[candidate_b_idx],
                        candidate_a_id=str(candidate_a_idx),
                        candidate_b_id=str(candidate_b_idx),
                        judge_config=judge_config,
                        task_description=task_description
                    )
                )
                tasks.append(task)
        
        # Execute comparison tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful comparisons
        comparisons = [
            result for result in results
            if isinstance(result, PairwiseComparison)
        ]
        
        return comparisons
    
    async def _score_single_candidate(
        self,
        candidate: StrategyCandidate,
        judge_config: Dict[str, Any],
        task_description: str,
        candidate_id: str
    ) -> Optional[JudgeScore]:
        """Score a single candidate with one judge."""
        async with self.semaphore:
            try:
                branch = Branch(chat_model=iModel(
                    provider=judge_config["provider"],
                    model=judge_config["model"]
                ))
                
                plan_json = json.dumps([phase.model_dump() for phase in candidate.phases], indent=2)
                
                instruction = self.JUDGE_SCORING_PROMPT.format(
                    judge_role=judge_config["role"],
                    plan_json=plan_json,
                    task_description=task_description
                )
                
                result = await branch.operate(
                    instruction=instruction,
                    response_format=JudgeScore,
                    temperature=0.3  # Low temperature for consistent scoring
                )
                
                # Set judge ID
                result.judge_id = judge_config["role"]
                return result
                
            except Exception as e:
                print(f"Scoring failed for {judge_config['role']}: {e}")
                return None
    
    async def _compare_pair(
        self,
        candidate_a: StrategyCandidate,
        candidate_b: StrategyCandidate,
        candidate_a_id: str,
        candidate_b_id: str,
        judge_config: Dict[str, Any],
        task_description: str
    ) -> Optional[PairwiseComparison]:
        """Compare two candidates pairwise."""
        async with self.semaphore:
            try:
                branch = Branch(chat_model=iModel(
                    provider=judge_config["provider"],
                    model=judge_config["model"]
                ))
                
                plan_a_json = json.dumps([phase.model_dump() for phase in candidate_a.phases], indent=2)
                plan_b_json = json.dumps([phase.model_dump() for phase in candidate_b.phases], indent=2)
                
                instruction = self.PAIRWISE_PROMPT.format(
                    judge_role=judge_config["role"],
                    plan_a_json=plan_a_json,
                    plan_b_json=plan_b_json,
                    task_description=task_description
                )
                
                # Get structured comparison result
                class ComparisonResult(HashableModel):
                    winner: str  # "A" or "B"
                    confidence: float
                    reasoning: str
                
                result = await branch.operate(
                    instruction=instruction,
                    response_format=ComparisonResult,
                    temperature=0.3
                )
                
                # Convert to PairwiseComparison
                winner_id = candidate_a_id if result.winner == "A" else candidate_b_id
                
                return PairwiseComparison(
                    candidate_a_id=candidate_a_id,
                    candidate_b_id=candidate_b_id,
                    winner_id=winner_id,
                    judge_id=judge_config["role"],
                    confidence=result.confidence,
                    reasoning=result.reasoning
                )
                
            except Exception as e:
                print(f"Pairwise comparison failed for {judge_config['role']}: {e}")
                return None


def sample_uncertain_pairs(n_candidates: int, max_pairs: int = 24) -> List[Tuple[int, int]]:
    """
    Sample pairs for pairwise comparison, prioritizing uncertain pairs.
    
    For now, uses simple random sampling. Could be enhanced with entropy-based
    selection from BTL posteriors in future rounds.
    """
    all_pairs = list(combinations(range(n_candidates), 2))
    
    if len(all_pairs) <= max_pairs:
        return all_pairs
    else:
        return random.sample(all_pairs, max_pairs)