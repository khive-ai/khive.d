"""
Adaptive coordination system that learns from execution patterns.

This module implements machine learning-like capabilities for the coordination
system to improve over time based on successful patterns.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExecutionPattern:
    """Represents a successful execution pattern."""

    task_type: str
    pattern_used: str
    agent_count: int
    execution_time: float
    success_rate: float
    context_reuse_rate: float
    conflict_rate: float
    dedup_rate: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def efficiency_score(self) -> float:
        """Calculate overall efficiency score."""
        return (
            self.success_rate * 0.4
            + self.context_reuse_rate * 0.2
            + (100 - self.conflict_rate) * 0.2
            + self.dedup_rate * 0.1
            + min(100, 1000 / max(1, self.execution_time)) * 0.1  # Speed bonus
        )


class AdaptiveCoordinator:
    """Learns and adapts coordination strategies based on historical performance."""

    def __init__(self, history_file: str = "coordination_history.json"):
        """Initialize adaptive coordinator with optional history file."""
        self.history_file = Path(history_file)
        self.execution_history: list[ExecutionPattern] = []
        self.pattern_scores: dict[str, dict[str, float]] = {}
        self.task_type_patterns: dict[str, list[str]] = {}
        self.confidence_threshold = 0.7

        # Load historical data if exists
        self.load_history()

    def load_history(self):
        """Load execution history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    data = json.load(f)
                    self.execution_history = [
                        ExecutionPattern(**pattern)
                        for pattern in data.get("history", [])
                    ]
                    self.pattern_scores = data.get("pattern_scores", {})
                    self.task_type_patterns = data.get("task_type_patterns", {})
                    self._recalculate_scores()
            except Exception as e:
                print(f"Error loading history: {e}")

    def save_history(self):
        """Save execution history to file."""
        try:
            data = {
                "history": [
                    asdict(p) for p in self.execution_history[-1000:]
                ],  # Keep last 1000
                "pattern_scores": self.pattern_scores,
                "task_type_patterns": self.task_type_patterns,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def _recalculate_scores(self):
        """Recalculate pattern scores from history."""
        # Group by task type and pattern
        pattern_groups = {}

        for execution in self.execution_history:
            key = f"{execution.task_type}:{execution.pattern_used}"
            if key not in pattern_groups:
                pattern_groups[key] = []
            pattern_groups[key].append(execution.efficiency_score)

        # Calculate average scores
        self.pattern_scores = {}
        for key, scores in pattern_groups.items():
            task_type, pattern = key.split(":", 1)
            if task_type not in self.pattern_scores:
                self.pattern_scores[task_type] = {}
            self.pattern_scores[task_type][pattern] = sum(scores) / len(scores)

    def record_execution(
        self, task_description: str, pattern_used: str, metrics: dict[str, Any]
    ):
        """Record a new execution pattern and learn from it."""
        # Extract task type from description
        task_type = self._extract_task_type(task_description)

        # Create execution pattern
        execution = ExecutionPattern(
            task_type=task_type,
            pattern_used=pattern_used,
            agent_count=metrics.get("agent_count", 0),
            execution_time=metrics.get("execution_time", 0),
            success_rate=metrics.get("success_rate", 100),
            context_reuse_rate=metrics.get("context_reuse_rate", 0),
            conflict_rate=metrics.get("conflict_rate", 0),
            dedup_rate=metrics.get("dedup_rate", 0),
        )

        # Add to history
        self.execution_history.append(execution)

        # Update pattern scores
        if task_type not in self.pattern_scores:
            self.pattern_scores[task_type] = {}

        # Update with exponential moving average
        alpha = 0.3  # Learning rate
        old_score = self.pattern_scores[task_type].get(pattern_used, 50)
        new_score = execution.efficiency_score
        self.pattern_scores[task_type][pattern_used] = (
            alpha * new_score + (1 - alpha) * old_score
        )

        # Track successful patterns for task types
        if execution.efficiency_score > 70:
            if task_type not in self.task_type_patterns:
                self.task_type_patterns[task_type] = []
            if pattern_used not in self.task_type_patterns[task_type]:
                self.task_type_patterns[task_type].append(pattern_used)

        # Save updated history
        self.save_history()

    def suggest_pattern(
        self, task_description: str, available_agents: int = 0
    ) -> dict[str, Any]:
        """Suggest the best coordination pattern based on learned history."""
        task_type = self._extract_task_type(task_description)

        # Check if we have history for this task type
        if self.pattern_scores.get(task_type):
            # Find best pattern from history
            best_pattern = max(
                self.pattern_scores[task_type].items(), key=lambda x: x[1]
            )

            # Calculate confidence based on sample size
            sample_size = sum(
                1
                for e in self.execution_history
                if e.task_type == task_type and e.pattern_used == best_pattern[0]
            )
            confidence = min(1.0, sample_size / 10)  # Full confidence at 10+ samples

            if confidence >= self.confidence_threshold:
                return {
                    "pattern": best_pattern[0],
                    "expected_score": best_pattern[1],
                    "confidence": confidence,
                    "reason": "learned_from_history",
                    "sample_size": sample_size,
                }

        # Fallback to heuristics if no confident history
        return self._heuristic_suggestion(task_description, available_agents)

    def _extract_task_type(self, description: str) -> str:
        """Extract task type from description."""
        desc_lower = description.lower()

        # Common task type keywords
        task_types = {
            "refactor": "refactoring",
            "implement": "implementation",
            "test": "testing",
            "debug": "debugging",
            "analyze": "analysis",
            "review": "review",
            "optimize": "optimization",
            "migrate": "migration",
            "deploy": "deployment",
            "document": "documentation",
        }

        for keyword, task_type in task_types.items():
            if keyword in desc_lower:
                return task_type

        # Default to first significant word
        words = desc_lower.split()
        return words[0] if words else "general"

    def _heuristic_suggestion(
        self, task_description: str, available_agents: int
    ) -> dict[str, Any]:
        """Fallback heuristic-based pattern suggestion."""
        desc_lower = task_description.lower()

        # Simple heuristics
        if any(word in desc_lower for word in ["analyze", "research", "explore"]):
            pattern = "fan_out"
        elif any(word in desc_lower for word in ["implement", "build", "create"]):
            pattern = "pipeline"
        elif any(word in desc_lower for word in ["verify", "validate", "test"]):
            pattern = "consensus"
        elif available_agents > 5:
            pattern = "hierarchical"
        else:
            pattern = "fan_out"

        return {
            "pattern": pattern,
            "expected_score": 50,  # Neutral score for heuristics
            "confidence": 0.3,
            "reason": "heuristic_fallback",
            "sample_size": 0,
        }

    def get_insights(self) -> dict[str, Any]:
        """Get learning insights and recommendations."""
        if not self.execution_history:
            return {"status": "no_history", "message": "No execution history available"}

        # Calculate overall statistics
        recent_executions = self.execution_history[-100:]  # Last 100 executions
        avg_efficiency = sum(e.efficiency_score for e in recent_executions) / len(
            recent_executions
        )

        # Find best patterns per task type
        best_patterns = {}
        for task_type, patterns in self.pattern_scores.items():
            if patterns:
                best = max(patterns.items(), key=lambda x: x[1])
                best_patterns[task_type] = {"pattern": best[0], "score": best[1]}

        # Identify improving vs declining patterns
        improving_patterns = []
        declining_patterns = []

        for task_type in self.pattern_scores:
            recent = [e for e in recent_executions if e.task_type == task_type]
            older = [
                e for e in self.execution_history[:-100] if e.task_type == task_type
            ]

            if recent and older:
                recent_avg = sum(e.efficiency_score for e in recent) / len(recent)
                older_avg = sum(e.efficiency_score for e in older) / len(older)

                if recent_avg > older_avg + 5:
                    improving_patterns.append(task_type)
                elif recent_avg < older_avg - 5:
                    declining_patterns.append(task_type)

        return {
            "total_executions": len(self.execution_history),
            "recent_avg_efficiency": avg_efficiency,
            "best_patterns": best_patterns,
            "improving": improving_patterns,
            "declining": declining_patterns,
            "unique_task_types": len(self.pattern_scores),
            "confidence_level": (
                "high"
                if len(self.execution_history) > 100
                else "medium"
                if len(self.execution_history) > 50
                else "low"
            ),
        }

    def predict_performance(
        self, task_description: str, pattern: str
    ) -> dict[str, Any]:
        """Predict performance for a given task and pattern combination."""
        task_type = self._extract_task_type(task_description)

        # Check historical performance
        if (
            task_type in self.pattern_scores
            and pattern in self.pattern_scores[task_type]
        ):
            score = self.pattern_scores[task_type][pattern]

            # Find similar executions
            similar = [
                e
                for e in self.execution_history
                if e.task_type == task_type and e.pattern_used == pattern
            ]

            if similar:
                avg_time = sum(e.execution_time for e in similar) / len(similar)
                avg_success = sum(e.success_rate for e in similar) / len(similar)

                return {
                    "predicted_score": score,
                    "predicted_time": avg_time,
                    "predicted_success_rate": avg_success,
                    "confidence": min(1.0, len(similar) / 10),
                    "based_on_samples": len(similar),
                }

        # No history - return neutral prediction
        return {
            "predicted_score": 50,
            "predicted_time": 10,
            "predicted_success_rate": 80,
            "confidence": 0,
            "based_on_samples": 0,
        }


# Global instance
_adaptive_coordinator = AdaptiveCoordinator()


def get_adaptive_coordinator() -> AdaptiveCoordinator:
    """Get the global adaptive coordinator instance."""
    return _adaptive_coordinator


def record_coordination_execution(task: str, pattern: str, metrics: dict[str, Any]):
    """Record an execution for learning."""
    _adaptive_coordinator.record_execution(task, pattern, metrics)


def suggest_best_pattern(task: str, agents: int = 0) -> dict[str, Any]:
    """Get the best pattern suggestion based on learning."""
    return _adaptive_coordinator.suggest_pattern(task, agents)


def get_coordination_insights() -> dict[str, Any]:
    """Get insights from the adaptive coordinator."""
    return _adaptive_coordinator.get_insights()
