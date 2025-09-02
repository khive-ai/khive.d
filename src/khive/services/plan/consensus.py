"""
Multi-round consensus algorithms for plan ranking.
Implements BTL, RankCentrality, and Schulze methods as described by ChatGPT.
"""
from __future__ import annotations
import math
import numpy as np
from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum


class ConsensusMethod(str, Enum):
    BTL = "bradley_terry_luce"
    RANK_CENTRALITY = "rank_centrality"  
    SCHULZE = "schulze"


@dataclass
class Pairwise:
    """Pairwise comparison data structure."""
    wins: Dict[Tuple[int, int], int]  # (i,j) -> count where i beats j
    n: int  # number of candidates


class ConsensusAlgorithms:
    """Multi-method consensus ranking algorithms."""
    
    @staticmethod
    def btl_rank(pairwise: Pairwise, iters: int = 200, eps: float = 1e-6) -> np.ndarray:
        """
        Bradley-Terry with MM updates; returns skill vector s (sum=1).
        
        References:
        - https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model
        - https://web.stanford.edu/class/archive/stats/stats200/stats200.1172/Lecture24.pdf
        """
        n = pairwise.n
        s = np.ones(n) / n  # Initialize uniform
        
        for iteration in range(iters):
            s_old = s.copy()
            denom = np.zeros(n)
            numer = np.zeros(n)
            
            for (i, j), w_ij in pairwise.wins.items():
                w_ji = pairwise.wins.get((j, i), 0)
                pij = s[i] / (s[i] + s[j] + 1e-12)  # P(i beats j)
                pji = 1.0 - pij
                
                numer[i] += w_ij
                numer[j] += w_ji
                denom[i] += w_ij / pij + w_ji / pji
                denom[j] += w_ji / pji + w_ij / pij
            
            # MM update
            s = np.clip(numer / np.maximum(denom, 1e-12), 1e-9, None)
            s = s / s.sum()  # Normalize
            
            # Check convergence
            if np.linalg.norm(s - s_old, 1) < eps:
                break
                
        return s
    
    @staticmethod
    def rank_centrality(pairwise: Pairwise, eps: float = 1e-12) -> np.ndarray:
        """
        Spectral ranking via stationary distribution over comparison graph.
        
        References:
        - https://arxiv.org/abs/1209.1688 "Rank Centrality: Ranking from Pair-wise Comparisons"
        """
        n = pairwise.n
        P = np.zeros((n, n))
        
        # Build transition matrix
        for (i, j), w_ij in pairwise.wins.items():
            w_ji = pairwise.wins.get((j, i), 0)
            total = w_ij + w_ji
            if total > 0:
                P[i, j] = w_ij / total
                P[j, i] = w_ji / total
        
        # Normalize rows to make P stochastic
        for i in range(n):
            row_sum = P[i, :].sum()
            if row_sum > 0:
                P[i, :] /= row_sum
            else:
                P[i, i] = 1.0  # Self-loop for isolated nodes
        
        # Power method to find stationary distribution
        v = np.ones(n) / n
        for _ in range(200):
            v_new = v @ P
            if np.linalg.norm(v_new - v, 1) < eps:
                break
            v = v_new
        
        return v / v.sum()
    
    @staticmethod
    def schulze_method(pairwise: Pairwise) -> List[int]:
        """
        Schulze method for Condorcet completion when you have ranked ballots.
        
        References:
        - https://en.wikipedia.org/wiki/Schulze_method
        - https://www.ourcommons.ca/content/Committee/421/ERRE/Brief/BR8397842/br-external/SchulzeMarkus-e.pdf
        """
        n = pairwise.n
        
        # Build pairwise preference matrix
        d = np.zeros((n, n))
        for (i, j), w_ij in pairwise.wins.items():
            w_ji = pairwise.wins.get((j, i), 0)
            if w_ij > w_ji:
                d[i, j] = w_ij - w_ji
        
        # Compute strongest paths using Floyd-Warshall
        p = d.copy()
        for i in range(n):
            for j in range(n):
                if i != j:
                    for k in range(n):
                        if k != i and k != j:
                            p[j, k] = max(p[j, k], min(p[j, i], p[i, k]))
        
        # Determine Schulze ranking
        defeated = [False] * n
        ranking = []
        
        for _ in range(n):
            # Find undefeated candidate with highest total strength
            best_candidate = -1
            best_strength = -1
            
            for i in range(n):
                if defeated[i]:
                    continue
                    
                # Check if i is undefeated by any remaining candidate
                is_defeated = False
                for j in range(n):
                    if not defeated[j] and j != i and p[j, i] > p[i, j]:
                        is_defeated = True
                        break
                
                if not is_defeated:
                    strength = sum(p[i, j] for j in range(n) if not defeated[j] and j != i)
                    if strength > best_strength:
                        best_candidate = i
                        best_strength = strength
            
            if best_candidate >= 0:
                ranking.append(best_candidate)
                defeated[best_candidate] = True
            else:
                # Handle ties by adding remaining candidates
                remaining = [i for i in range(n) if not defeated[i]]
                ranking.extend(remaining)
                break
        
        return ranking


class JudgeReliability:
    """
    Dawid-Skene EM algorithm for judge reliability estimation.
    
    References:
    - https://crowdsourcing-class.org/readings/downloads/ml/EM.pdf
    - https://www.jstor.org/stable/2346806
    """
    
    def __init__(self, num_judges: int, num_classes: int = 2):
        self.num_judges = num_judges
        self.num_classes = num_classes
        self.judge_accuracies = np.ones(num_judges) * 0.8  # Prior belief
        self.confusion_matrices = np.array([
            np.eye(num_classes) * 0.9 + (1 - np.eye(num_classes)) * 0.1
            for _ in range(num_judges)
        ])
    
    def update_reliability(self, judgments: List[Tuple[int, int, int]]) -> None:
        """
        Update judge reliability using EM algorithm.
        
        Args:
            judgments: List of (judge_id, item_id, label) tuples
        """
        if not judgments:
            return
        
        # Group judgments by item
        items = defaultdict(list)
        for judge_id, item_id, label in judgments:
            items[item_id].append((judge_id, label))
        
        # EM iterations
        for _ in range(10):  # Usually converges quickly
            # E-step: estimate true labels
            true_labels = {}
            for item_id, item_judgments in items.items():
                # Majority vote weighted by reliability
                votes = defaultdict(float)
                for judge_id, label in item_judgments:
                    votes[label] += self.judge_accuracies[judge_id]
                true_labels[item_id] = max(votes, key=votes.get)
            
            # M-step: update judge accuracies
            new_accuracies = np.zeros(self.num_judges)
            judge_counts = np.zeros(self.num_judges)
            
            for item_id, item_judgments in items.items():
                true_label = true_labels[item_id]
                for judge_id, given_label in item_judgments:
                    if given_label == true_label:
                        new_accuracies[judge_id] += 1
                    judge_counts[judge_id] += 1
            
            # Update accuracies with smoothing
            for j in range(self.num_judges):
                if judge_counts[j] > 0:
                    self.judge_accuracies[j] = (new_accuracies[j] + 1) / (judge_counts[j] + 2)


class MultiRoundConsensus:
    """Multi-round consensus orchestrator."""
    
    def __init__(self, method: ConsensusMethod = ConsensusMethod.BTL):
        self.method = method
        self.judge_reliability = JudgeReliability(num_judges=10)  # Will resize dynamically
        self.algorithms = ConsensusAlgorithms()
    
    def rank_candidates(
        self,
        comparisons: List[Tuple[int, int, int]],  # (winner_id, loser_id, judge_id)
        candidate_ids: List[str]
    ) -> Tuple[List[str], Dict[str, float], float]:
        """
        Rank candidates using selected consensus method.
        
        Returns:
            (ranked_candidate_ids, scores, top_margin)
        """
        n = len(candidate_ids)
        if n <= 1:
            return candidate_ids, {cid: 1.0 for cid in candidate_ids}, 1.0
        
        # Build pairwise comparison matrix
        wins = defaultdict(int)
        for winner_idx, loser_idx, judge_id in comparisons:
            if 0 <= winner_idx < n and 0 <= loser_idx < n:
                wins[(winner_idx, loser_idx)] += 1
        
        pairwise = Pairwise(wins=dict(wins), n=n)
        
        # Apply selected algorithm
        if self.method == ConsensusMethod.BTL:
            scores_array = self.algorithms.btl_rank(pairwise)
        elif self.method == ConsensusMethod.RANK_CENTRALITY:
            scores_array = self.algorithms.rank_centrality(pairwise)
        elif self.method == ConsensusMethod.SCHULZE:
            ranking = self.algorithms.schulze_method(pairwise)
            scores_array = np.zeros(n)
            for i, candidate_idx in enumerate(ranking):
                scores_array[candidate_idx] = (n - i) / n  # Convert rank to score
        else:
            raise ValueError(f"Unknown consensus method: {self.method}")
        
        # Convert to candidate IDs with scores
        id_score_pairs = [(candidate_ids[i], float(scores_array[i])) for i in range(n)]
        id_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        ranked_ids = [pair[0] for pair in id_score_pairs]
        scores = {pair[0]: pair[1] for pair in id_score_pairs}
        
        # Calculate margin between top 2
        sorted_scores = sorted(scores_array, reverse=True)
        margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 1.0
        
        return ranked_ids, scores, float(margin)
    
    def should_converge(self, margin: float, threshold: float = 0.15) -> bool:
        """Check if consensus has converged based on top margin."""
        return margin >= threshold