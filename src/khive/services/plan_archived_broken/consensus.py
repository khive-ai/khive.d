"""
Consensus algorithms for multi-agent orchestration.

Based on ChatGPT's detailed consensus toolbox implementation.
Provides various consensus methods for different task types.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import numpy as np
from collections import defaultdict


@dataclass
class JudgeWeight:
    """Weight tracking for judge reliability."""
    w: float = 1.0  # multiplicative weight (Hedge)
    mistakes: int = 0


@dataclass
class PairwiseResult:
    """Results from pairwise comparisons."""
    outcomes: Dict[Tuple[int, int], int]  # outcomes[i][j] = votes preferring i over j


@dataclass
class BTLParams:
    """Bradley-Terry-Luce model parameters."""
    scores: np.ndarray  # utility/skill estimates per candidate


def hedge_update(
    weights: Dict[str, JudgeWeight], 
    judge_losses: Dict[str, float], 
    eta: float = 0.5
) -> Dict[str, JudgeWeight]:
    """
    Multiplicative weights update (Hedge algorithm).
    Updates judge weights based on their performance.
    
    Theory: Multiplicative weights / Hedge for online learning.
    """
    for j, loss in judge_losses.items():
        if j not in weights:
            weights[j] = JudgeWeight()
        w = weights[j].w * math.exp(-eta * float(loss))
        weights[j].w = max(1e-6, w)
        weights[j].mistakes += (loss > 0.5)
    
    # Normalize to sum=1 for convenience
    Z = sum(jw.w for jw in weights.values())
    if Z > 0:
        for jw in weights.values():
            jw.w /= Z
    
    return weights


def robust_mean(xs: List[float], trim: float = 0.1) -> float:
    """
    Robust mean estimation with trimming and Huber fallback.
    Reduces outlier impact for numeric aggregation.
    """
    if not xs:
        return 0.0
    
    xs_sorted = sorted(xs)
    k = int(len(xs) * trim)
    core = xs_sorted[k:len(xs)-k] if len(xs) > 2*k else xs_sorted
    mu = float(np.mean(core))
    
    # One Huber reweight with c≈1.345 * std of core
    s = float(np.std(core)) if len(core) > 1 else 1.0
    c = 1.345 * s
    
    def psi(r):
        return max(-c, min(c, r))
    
    num, den = 0.0, 0.0
    for x in xs:
        r = x - mu
        num += mu + psi(r)
        den += 1.0
    
    return num / den if den > 0 else mu


def schulze_winner(n: int, pairwins: np.ndarray) -> List[int]:
    """
    Schulze method (Condorcet completion) for ranking candidates.
    
    Uses beatpath computation to find the Condorcet winner or
    resolve cycles in pairwise preferences.
    
    Args:
        n: Number of candidates
        pairwins: Matrix where pairwins[i,j] = votes preferring i over j
        
    Returns:
        List of candidate indices sorted by beatpath strength
    """
    # Initialize path strengths
    p = np.zeros((n, n), dtype=int)
    
    for i in range(n):
        for j in range(n):
            if i != j:
                if pairwins[i, j] > pairwins[j, i]:
                    p[i, j] = pairwins[i, j] - pairwins[j, i]
                else:
                    p[i, j] = 0
    
    # Find strongest paths (Floyd-Warshall variant)
    for k in range(n):
        for i in range(n):
            if i == k:
                continue
            for j in range(n):
                if j == k or j == i:
                    continue
                p[i, j] = max(p[i, j], min(p[i, k], p[k, j]))
    
    # Rank by how many others each candidate beats
    score = []
    for i in range(n):
        wins = sum(p[i, j] >= p[j, i] for j in range(n) if j != i)
        score.append((i, wins))
    
    return [i for i, _ in sorted(score, key=lambda t: (-t[1], t[0]))]


def rank_centrality(
    n: int, 
    pairwins: np.ndarray, 
    alpha: float = 0.5
) -> np.ndarray:
    """
    Rank-Centrality (spectral method) for cardinal strength scores.
    
    Builds a Markov chain from pairwise wins and finds stationary distribution.
    Gives calibrated strength scores under Bradley-Terry-Luce model.
    
    Args:
        n: Number of candidates
        pairwins: Matrix of pairwise preferences
        alpha: Teleportation probability for ergodicity
        
    Returns:
        Cardinal strength scores for each candidate
    """
    P = np.zeros((n, n), dtype=float)
    
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            w_ij = pairwins[i, j]
            w_ji = pairwins[j, i]
            denom = w_ij + w_ji
            
            # Probability of transitioning from i to j
            p = (w_ji / denom) if denom > 0 else 0.5
            P[i, j] = p
        
        P[i, i] = 0.0
        row_sum = P[i].sum()
        
        # Add teleportation for ergodicity
        if row_sum > 0:
            P[i] = (1 - alpha) * (P[i] / row_sum) + alpha * (1.0 / n)
        else:
            P[i] = np.ones(n) / n
    
    # Power iteration to find stationary distribution
    v = np.ones(n) / n
    for _ in range(200):
        v_next = v @ P
        if np.linalg.norm(v_next - v, 1) < 1e-9:
            break
        v = v_next
    
    return v / v.sum()


def dawid_skene(
    labels: List[List[int]], 
    n_classes: int, 
    iters: int = 20
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Dawid-Skene EM algorithm for noisy label aggregation.
    
    Learns judge confusion matrices and infers true labels from
    noisy judgments. Robust to varying judge quality.
    
    Args:
        labels: labels[rater][item] ∈ {0..n_classes-1} or -1 if missing
        n_classes: Number of label classes
        iters: EM iterations
        
    Returns:
        - Posterior probabilities over classes per item
        - Confusion matrices per rater
    """
    R, I = len(labels), len(labels[0]) if labels else 0
    if R == 0 or I == 0:
        return np.ones((I, n_classes)) / n_classes, np.ones((R, n_classes, n_classes))
    
    # Initialize with majority vote
    post = np.ones((I, n_classes)) / n_classes
    for i in range(I):
        counts = np.zeros(n_classes)
        for r in range(R):
            if i < len(labels[r]):
                y = labels[r][i]
                if y >= 0:
                    counts[y] += 1
        if counts.sum() > 0:
            post[i] = counts / counts.sum()
    
    # Initialize confusion matrices with Laplace prior
    C = np.ones((R, n_classes, n_classes))
    
    for _ in range(iters):
        # M-step: Update confusion matrices
        C[:] = 1.0  # Reset with prior
        for r in range(R):
            for i in range(min(I, len(labels[r]))):
                y = labels[r][i]
                if y >= 0:
                    C[r, y] += post[i]
        
        # Normalize confusion matrices
        C /= C.sum(axis=2, keepdims=True)
        
        # E-step: Update posteriors
        for i in range(I):
            logp = np.zeros(n_classes)
            for r in range(R):
                if i < len(labels[r]):
                    y = labels[r][i]
                    if y >= 0:
                        logp += np.log(C[r, y] + 1e-12)
            
            p = np.exp(logp - logp.max())
            post[i] = p / p.sum()
    
    return post, C


class UCB1:
    """
    Upper Confidence Bound algorithm for multi-armed bandits.
    
    Used for routing expensive evaluations to promising candidates.
    Achieves logarithmic regret for bounded rewards.
    """
    
    def __init__(self, k: int):
        """Initialize UCB1 with k arms."""
        self.n = [0] * k  # Number of pulls per arm
        self.r = [0.0] * k  # Total reward per arm
        self.t = 0  # Total time steps
        self.k = k
    
    def select(self) -> int:
        """Select next arm to pull using UCB1 strategy."""
        self.t += 1
        
        # Pull each arm at least once
        for i in range(self.k):
            if self.n[i] == 0:
                return i
        
        # Calculate UCB values
        ucb = []
        for i in range(self.k):
            avg_reward = self.r[i] / self.n[i]
            bonus = math.sqrt(2 * math.log(self.t) / self.n[i])
            ucb.append(avg_reward + bonus)
        
        return int(np.argmax(ucb))
    
    def update(self, i: int, reward: float):
        """Update statistics after pulling arm i."""
        if 0 <= i < self.k:
            self.n[i] += 1
            self.r[i] += reward


class ThompsonSampling:
    """
    Thompson Sampling for multi-armed bandits.
    
    Bayesian approach that maintains Beta distributions for each arm.
    """
    
    def __init__(self, k: int):
        """Initialize Thompson Sampling with k arms."""
        self.k = k
        self.alpha = np.ones(k)  # Success counts + 1
        self.beta = np.ones(k)   # Failure counts + 1
    
    def select(self) -> int:
        """Select next arm by sampling from Beta distributions."""
        samples = np.random.beta(self.alpha, self.beta)
        return int(np.argmax(samples))
    
    def update(self, i: int, reward: float):
        """Update Beta parameters after pulling arm i."""
        if 0 <= i < self.k:
            # Assume Bernoulli rewards
            if reward > 0.5:
                self.alpha[i] += 1
            else:
                self.beta[i] += 1


def majority_judgment(grades: List[List[int]], n_grades: int = 5) -> List[float]:
    """
    Majority Judgment aggregation for graded evaluations.
    
    Median-based aggregation that's robust to tactical extremes.
    
    Args:
        grades: grades[judge][candidate] ∈ {0..n_grades-1}
        n_grades: Number of grade levels (e.g., 5 for Bad..Excellent)
        
    Returns:
        Aggregated scores per candidate
    """
    if not grades or not grades[0]:
        return []
    
    n_candidates = len(grades[0])
    scores = []
    
    for c in range(n_candidates):
        candidate_grades = []
        for judge_grades in grades:
            if c < len(judge_grades) and judge_grades[c] >= 0:
                candidate_grades.append(judge_grades[c])
        
        if candidate_grades:
            # Use median grade as the score
            scores.append(float(np.median(candidate_grades)))
        else:
            # No grades for this candidate
            scores.append(n_grades / 2.0)
    
    return scores


def borda_count(rankings: List[List[int]]) -> List[float]:
    """
    Borda count for simple rank aggregation.
    
    Fast but manipulable - use only for initial triage.
    
    Args:
        rankings: rankings[judge] = list of candidate indices in preference order
        
    Returns:
        Borda scores per candidate
    """
    if not rankings:
        return []
    
    # Find all candidates
    all_candidates = set()
    for ranking in rankings:
        all_candidates.update(ranking)
    
    n_candidates = len(all_candidates)
    candidate_list = sorted(all_candidates)
    candidate_idx = {c: i for i, c in enumerate(candidate_list)}
    
    scores = np.zeros(n_candidates)
    
    for ranking in rankings:
        n_ranked = len(ranking)
        for pos, candidate in enumerate(ranking):
            if candidate in candidate_idx:
                # Higher position = more points
                points = n_ranked - pos - 1
                scores[candidate_idx[candidate]] += points
    
    return scores.tolist()


def two_phase_commit(
    participants: List[str],
    votes: Dict[str, bool],
    required_quorum: float = 1.0
) -> Tuple[bool, str]:
    """
    Two-Phase Commit protocol for atomic multi-agent operations.
    
    Args:
        participants: List of participant IDs
        votes: Prepare votes from participants
        required_quorum: Fraction of participants that must vote yes
        
    Returns:
        - Whether to commit
        - Reason for decision
    """
    if not participants:
        return False, "No participants"
    
    yes_votes = sum(1 for p in participants if votes.get(p, False))
    quorum_size = math.ceil(len(participants) * required_quorum)
    
    if yes_votes >= quorum_size:
        return True, f"Commit: {yes_votes}/{len(participants)} votes"
    else:
        return False, f"Abort: Only {yes_votes}/{len(participants)} votes (need {quorum_size})"


class ConsensusEngine:
    """
    Main consensus engine combining multiple algorithms.
    
    Selects appropriate consensus method based on task type and data.
    """
    
    def __init__(self):
        self.judge_weights: Dict[str, JudgeWeight] = {}
        self.ucb_bandits: Dict[str, UCB1] = {}
        self.thompson_samplers: Dict[str, ThompsonSampling] = {}
    
    def select_consensus_method(
        self,
        task_type: str,
        data_type: str
    ) -> str:
        """
        Select appropriate consensus algorithm based on task and data.
        
        Based on ChatGPT's selection matrix.
        """
        selection_matrix = {
            ("rank", "pairwise"): "schulze",
            ("rank", "scores"): "rank_centrality",
            ("classify", "labels"): "dawid_skene",
            ("score", "numeric"): "robust_mean",
            ("grade", "ordinal"): "majority_judgment",
            ("triage", "rankings"): "borda",
            ("commit", "votes"): "two_phase_commit",
            ("route", "rewards"): "ucb1",
        }
        
        key = (task_type, data_type)
        return selection_matrix.get(key, "robust_mean")
    
    def aggregate(
        self,
        task_type: str,
        data_type: str,
        data: any,
        **kwargs
    ) -> any:
        """
        Main aggregation method that routes to appropriate algorithm.
        """
        method = self.select_consensus_method(task_type, data_type)
        
        if method == "schulze":
            return self._aggregate_schulze(data)
        elif method == "rank_centrality":
            return self._aggregate_rank_centrality(data)
        elif method == "dawid_skene":
            return self._aggregate_dawid_skene(data, **kwargs)
        elif method == "robust_mean":
            return robust_mean(data, **kwargs)
        elif method == "majority_judgment":
            return majority_judgment(data, **kwargs)
        elif method == "borda":
            return borda_count(data)
        elif method == "two_phase_commit":
            return two_phase_commit(**data)
        elif method == "ucb1":
            return self._route_ucb1(data, **kwargs)
        else:
            return robust_mean(data) if isinstance(data, list) else data
    
    def _aggregate_schulze(self, pairwins: np.ndarray) -> List[int]:
        """Apply Schulze method to pairwise preferences."""
        n = pairwins.shape[0]
        return schulze_winner(n, pairwins)
    
    def _aggregate_rank_centrality(self, pairwins: np.ndarray) -> np.ndarray:
        """Apply Rank-Centrality to get cardinal scores."""
        n = pairwins.shape[0]
        return rank_centrality(n, pairwins)
    
    def _aggregate_dawid_skene(
        self,
        labels: List[List[int]],
        n_classes: int = 2
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply Dawid-Skene for noisy label aggregation."""
        return dawid_skene(labels, n_classes)
    
    def _route_ucb1(self, task_id: str, k: int) -> int:
        """Route evaluation using UCB1 bandit."""
        if task_id not in self.ucb_bandits:
            self.ucb_bandits[task_id] = UCB1(k)
        return self.ucb_bandits[task_id].select()
    
    def update_judge_weights(self, judge_losses: Dict[str, float], eta: float = 0.5):
        """Update judge weights using Hedge algorithm."""
        self.judge_weights = hedge_update(self.judge_weights, judge_losses, eta)
    
    def get_weighted_aggregation(
        self,
        judge_votes: Dict[str, float]
    ) -> float:
        """
        Aggregate votes weighted by judge reliability.
        """
        if not self.judge_weights:
            # Initialize equal weights
            for judge in judge_votes:
                self.judge_weights[judge] = JudgeWeight()
        
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for judge, vote in judge_votes.items():
            weight = self.judge_weights.get(judge, JudgeWeight()).w
            weighted_sum += vote * weight
            weight_sum += weight
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0