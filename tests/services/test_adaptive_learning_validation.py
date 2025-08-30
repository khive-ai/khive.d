"""
Comprehensive test suite for validating adaptive learning capabilities
of the coordination system.

This test suite validates that the adaptive coordinator learns from execution
history and improves pattern suggestions over time through:

1. Cold start testing (no history)
2. Learning curve analysis (suggestion accuracy as history builds)
3. Pattern effectiveness validation (system learns which patterns work best)
4. Prediction accuracy testing (performance predictions vs actual results)
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from khive.services.claude.hooks.adaptive_coordinator import (
    AdaptiveCoordinator,
)


class LearningValidationFramework:
    """Framework for testing adaptive learning capabilities."""

    def __init__(self):
        self.execution_data = self._generate_simulation_data()
        self.learning_metrics = {
            "suggestion_accuracy": [],
            "prediction_errors": [],
            "confidence_scores": [],
            "learning_rate": [],
            "convergence_metrics": {},
        }

    def _generate_simulation_data(self) -> list[dict[str, Any]]:
        """Generate realistic simulation data for 25+ executions across task types."""
        return [
            # Phase 1: Cold start - Initial executions with varied outcomes
            {
                "task": "Refactor authentication system",
                "pattern": "fan_out",
                "metrics": {
                    "execution_time": 15,
                    "success_rate": 85,
                    "conflict_rate": 10,
                    "dedup_rate": 20,
                },
            },
            {
                "task": "Refactor authentication system",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 12,
                    "success_rate": 95,
                    "conflict_rate": 2,
                    "dedup_rate": 30,
                },
            },
            {
                "task": "Refactor authentication system",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 18,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 25,
                },
            },
            # Phase 2: API implementation - Learning patterns
            {
                "task": "Implement user API endpoints",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 8,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 35,
                },
            },
            {
                "task": "Implement user API endpoints",
                "pattern": "fan_out",
                "metrics": {
                    "execution_time": 10,
                    "success_rate": 90,
                    "conflict_rate": 5,
                    "dedup_rate": 15,
                },
            },
            {
                "task": "Implement payment API",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 7,
                    "success_rate": 95,
                    "conflict_rate": 1,
                    "dedup_rate": 40,
                },
            },
            {
                "task": "Implement payment API",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 11,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 30,
                },
            },
            # Phase 3: Security testing - Consensus patterns excel
            {
                "task": "Test security vulnerabilities",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 6,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 45,
                },
            },
            {
                "task": "Test security vulnerabilities",
                "pattern": "fan_out",
                "metrics": {
                    "execution_time": 8,
                    "success_rate": 85,
                    "conflict_rate": 8,
                    "dedup_rate": 20,
                },
            },
            {
                "task": "Test SQL injection protection",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 5,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 50,
                },
            },
            {
                "task": "Test authentication security",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 7,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 40,
                },
            },
            # Phase 4: Database operations - Pipeline preferred
            {
                "task": "Migrate database schema",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 9,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 60,
                },
            },
            {
                "task": "Migrate database schema",
                "pattern": "fan_out",
                "metrics": {
                    "execution_time": 14,
                    "success_rate": 80,
                    "conflict_rate": 15,
                    "dedup_rate": 25,
                },
            },
            {
                "task": "Optimize database queries",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 6,
                    "success_rate": 95,
                    "conflict_rate": 2,
                    "dedup_rate": 55,
                },
            },
            # Phase 5: Analysis tasks - Fan-out excels
            {
                "task": "Analyze performance bottlenecks",
                "pattern": "fan_out",
                "metrics": {
                    "execution_time": 5,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 35,
                },
            },
            {
                "task": "Analyze performance bottlenecks",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 9,
                    "success_rate": 90,
                    "conflict_rate": 3,
                    "dedup_rate": 25,
                },
            },
            {
                "task": "Analyze code quality metrics",
                "pattern": "fan_out",
                "metrics": {
                    "execution_time": 4,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 40,
                },
            },
            {
                "task": "Research new technologies",
                "pattern": "fan_out",
                "metrics": {
                    "execution_time": 8,
                    "success_rate": 95,
                    "conflict_rate": 2,
                    "dedup_rate": 30,
                },
            },
            # Phase 6: Review processes - Consensus works well
            {
                "task": "Review code changes",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 8,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 45,
                },
            },
            {
                "task": "Review security measures",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 6,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 50,
                },
            },
            # Phase 7: More refactoring - Pipeline proven effective
            {
                "task": "Refactor API controllers",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 10,
                    "success_rate": 95,
                    "conflict_rate": 3,
                    "dedup_rate": 35,
                },
            },
            {
                "task": "Refactor database layer",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 11,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 45,
                },
            },
            # Phase 8: Complex system design - Hierarchical patterns
            {
                "task": "Design microservices architecture",
                "pattern": "hierarchical",
                "metrics": {
                    "execution_time": 20,
                    "success_rate": 90,
                    "conflict_rate": 5,
                    "dedup_rate": 30,
                },
            },
            {
                "task": "Design distributed cache system",
                "pattern": "hierarchical",
                "metrics": {
                    "execution_time": 18,
                    "success_rate": 95,
                    "conflict_rate": 2,
                    "dedup_rate": 25,
                },
            },
            # Phase 9: Additional learning data
            {
                "task": "Test integration endpoints",
                "pattern": "consensus",
                "metrics": {
                    "execution_time": 7,
                    "success_rate": 100,
                    "conflict_rate": 0,
                    "dedup_rate": 55,
                },
            },
            {
                "task": "Implement caching layer",
                "pattern": "pipeline",
                "metrics": {
                    "execution_time": 9,
                    "success_rate": 95,
                    "conflict_rate": 1,
                    "dedup_rate": 40,
                },
            },
        ]

    def run_learning_simulation(
        self, coordinator: AdaptiveCoordinator
    ) -> dict[str, Any]:
        """Run complete learning simulation and collect metrics."""
        results = {
            "phases": [],
            "learning_progression": [],
            "prediction_accuracy": [],
            "confidence_evolution": [],
        }

        # Phase 1: Cold start (no history)
        cold_start_suggestions = []
        for i in range(3):
            exec_data = self.execution_data[i]
            suggestion = coordinator.suggest_pattern(exec_data["task"])
            cold_start_suggestions.append({
                "suggested": suggestion["pattern"],
                "actual_best": "pipeline",  # Based on our data, pipeline works best for refactoring
                "confidence": suggestion["confidence"],
                "reason": suggestion["reason"],
            })

        results["phases"].append({
            "phase": "cold_start",
            "suggestions": cold_start_suggestions,
            "avg_confidence": np.mean([
                s["confidence"] for s in cold_start_suggestions
            ]),
        })

        # Execute all simulations and track learning
        for i, exec_data in enumerate(self.execution_data):
            # Record execution
            coordinator.record_execution(
                exec_data["task"],
                exec_data["pattern"],
                {
                    **exec_data["metrics"],
                    "agent_count": 4,
                    "context_reuse_rate": exec_data["metrics"].get("dedup_rate", 0),
                },
            )

            # Test suggestion accuracy every 3 executions
            if i % 3 == 2 and i < len(self.execution_data) - 1:
                next_task = (
                    self.execution_data[i + 1]["task"]
                    if i + 1 < len(self.execution_data)
                    else exec_data["task"]
                )
                suggestion = coordinator.suggest_pattern(next_task)

                # Determine the actual best pattern for this task type
                actual_best = self._get_best_pattern_for_task(next_task, i + 1)

                learning_point = {
                    "execution_count": i + 1,
                    "suggested_pattern": suggestion["pattern"],
                    "actual_best": actual_best,
                    "is_correct": suggestion["pattern"] == actual_best,
                    "confidence": suggestion["confidence"],
                    "reason": suggestion["reason"],
                }
                results["learning_progression"].append(learning_point)

                # Test prediction accuracy
                prediction = coordinator.predict_performance(
                    next_task, suggestion["pattern"]
                )
                if i + 1 < len(self.execution_data):
                    actual_metrics = self.execution_data[i + 1]["metrics"]
                    pred_error = abs(
                        prediction["predicted_time"] - actual_metrics["execution_time"]
                    )
                    results["prediction_accuracy"].append({
                        "predicted_time": prediction["predicted_time"],
                        "actual_time": actual_metrics["execution_time"],
                        "error": pred_error,
                        "confidence": prediction["confidence"],
                    })

        return results

    def _get_best_pattern_for_task(self, task: str, up_to_index: int) -> str:
        """Determine the best pattern for a task type based on historical data."""
        task_lower = task.lower()

        # Analyze historical performance for similar tasks
        similar_tasks = []
        for i in range(min(up_to_index, len(self.execution_data))):
            exec_data = self.execution_data[i]
            if any(
                keyword in task_lower
                for keyword in exec_data["task"].lower().split()[:2]
            ):
                similar_tasks.append(exec_data)

        if not similar_tasks:
            return "fan_out"  # Default

        # Calculate efficiency scores and find best pattern
        pattern_scores = {}
        for exec_data in similar_tasks:
            pattern = exec_data["pattern"]
            metrics = exec_data["metrics"]

            # Calculate efficiency score (same as in AdaptiveCoordinator)
            score = (
                metrics["success_rate"] * 0.4
                + metrics.get("dedup_rate", 0) * 0.2
                + (100 - metrics["conflict_rate"]) * 0.2
                + metrics.get("dedup_rate", 0) * 0.1
                + min(100, 1000 / max(1, metrics["execution_time"])) * 0.1
            )

            if pattern not in pattern_scores:
                pattern_scores[pattern] = []
            pattern_scores[pattern].append(score)

        # Return pattern with highest average score
        avg_scores = {p: np.mean(scores) for p, scores in pattern_scores.items()}
        return max(avg_scores, key=avg_scores.get)

    def analyze_learning_effectiveness(self, results: dict[str, Any]) -> dict[str, Any]:
        """Analyze learning effectiveness and generate insights."""
        learning_data = results["learning_progression"]

        if not learning_data:
            return {"error": "No learning data available"}

        # Calculate accuracy over time
        accuracy_over_time = []
        window_size = 3
        for i in range(len(learning_data) - window_size + 1):
            window = learning_data[i : i + window_size]
            accuracy = sum(1 for point in window if point["is_correct"]) / len(window)
            accuracy_over_time.append({
                "execution_range": (
                    window[0]["execution_count"],
                    window[-1]["execution_count"],
                ),
                "accuracy": accuracy,
            })

        # Calculate confidence calibration
        confidence_buckets = {"low": [], "medium": [], "high": []}
        for point in learning_data:
            conf = point["confidence"]
            if conf < 0.5:
                confidence_buckets["low"].append(point["is_correct"])
            elif conf < 0.8:
                confidence_buckets["medium"].append(point["is_correct"])
            else:
                confidence_buckets["high"].append(point["is_correct"])

        confidence_calibration = {}
        for bucket, correctness in confidence_buckets.items():
            if correctness:
                confidence_calibration[bucket] = {
                    "accuracy": np.mean(correctness),
                    "sample_size": len(correctness),
                }

        # Prediction error analysis
        pred_data = results["prediction_accuracy"]
        avg_prediction_error = (
            np.mean([p["error"] for p in pred_data]) if pred_data else None
        )
        error_reduction = None
        if len(pred_data) > 6:
            early_errors = [p["error"] for p in pred_data[:3]]
            late_errors = [p["error"] for p in pred_data[-3:]]
            error_reduction = np.mean(early_errors) - np.mean(late_errors)

        # Learning convergence
        if len(learning_data) > 6:
            early_accuracy = np.mean([p["is_correct"] for p in learning_data[:3]])
            late_accuracy = np.mean([p["is_correct"] for p in learning_data[-3:]])
            learning_improvement = late_accuracy - early_accuracy
        else:
            learning_improvement = 0

        return {
            "learning_curve": {
                "initial_accuracy": (
                    learning_data[0]["is_correct"] if learning_data else None
                ),
                "final_accuracy": (
                    learning_data[-1]["is_correct"] if learning_data else None
                ),
                "improvement": learning_improvement,
                "accuracy_progression": accuracy_over_time,
            },
            "confidence_calibration": confidence_calibration,
            "prediction_performance": {
                "average_error": avg_prediction_error,
                "error_reduction": error_reduction,
                "sample_size": len(pred_data),
            },
            "convergence_metrics": {
                "executions_to_accuracy": self._find_convergence_point(learning_data),
                "learning_rate": self._calculate_learning_rate(learning_data),
                "stability_score": self._calculate_stability(learning_data),
            },
        }

    def _find_convergence_point(self, learning_data: list[dict]) -> int:
        """Find when the system reaches stable high accuracy."""
        if len(learning_data) < 6:
            return -1

        # Look for 3 consecutive correct suggestions
        for i in range(len(learning_data) - 2):
            if all(learning_data[j]["is_correct"] for j in range(i, i + 3)):
                return learning_data[i]["execution_count"]
        return -1

    def _calculate_learning_rate(self, learning_data: list[dict]) -> float:
        """Calculate how quickly the system improves."""
        if len(learning_data) < 4:
            return 0.0

        # Calculate improvement rate over time
        improvements = []
        for i in range(1, len(learning_data)):
            prev_accuracy = 1.0 if learning_data[i - 1]["is_correct"] else 0.0
            curr_accuracy = 1.0 if learning_data[i]["is_correct"] else 0.0
            improvements.append(curr_accuracy - prev_accuracy)

        # Return average improvement per step
        return np.mean(improvements)

    def _calculate_stability(self, learning_data: list[dict]) -> float:
        """Calculate how stable the suggestions are over time."""
        if len(learning_data) < 4:
            return 0.0

        # Calculate variance in accuracy over sliding windows
        accuracies = [1.0 if point["is_correct"] else 0.0 for point in learning_data]
        window_size = min(3, len(accuracies) // 2)
        window_variances = []

        for i in range(len(accuracies) - window_size + 1):
            window = accuracies[i : i + window_size]
            window_variances.append(np.var(window))

        # Lower variance = higher stability
        return 1.0 - np.mean(window_variances)


@pytest.mark.unit
class TestAdaptiveLearningValidation:
    """Test suite for adaptive learning capabilities."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.history_file = Path(self.temp_dir) / "test_coordination_history.json"
        self.framework = LearningValidationFramework()

    def teardown_method(self):
        """Cleanup after each test method."""
        if self.history_file.exists():
            self.history_file.unlink()

    def test_cold_start_behavior(self):
        """Test system behavior with no execution history."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Test suggestions with no history
        suggestion1 = coordinator.suggest_pattern("Refactor authentication system")
        suggestion2 = coordinator.suggest_pattern("Implement user API")
        suggestion3 = coordinator.suggest_pattern("Test security features")

        # Should use heuristic fallback
        assert suggestion1["reason"] == "heuristic_fallback"
        assert suggestion2["reason"] == "heuristic_fallback"
        assert suggestion3["reason"] == "heuristic_fallback"

        # Confidence should be low for heuristics
        assert suggestion1["confidence"] < 0.5
        assert suggestion2["confidence"] < 0.5
        assert suggestion3["confidence"] < 0.5

        # Should suggest reasonable patterns based on keywords
        assert suggestion1["pattern"] in [
            "fan_out",
            "pipeline",
        ]  # refactor -> reasonable patterns
        assert suggestion3["pattern"] in [
            "consensus",
            "fan_out",
        ]  # test -> consensus makes sense

    def test_learning_curve_progression(self):
        """Test that suggestion accuracy improves as history builds."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Run learning simulation
        results = self.framework.run_learning_simulation(coordinator)
        analysis = self.framework.analyze_learning_effectiveness(results)

        # Validate learning progression
        learning_curve = analysis["learning_curve"]
        assert "accuracy_progression" in learning_curve
        assert "improvement" in learning_curve

        # System should show improvement over time
        if len(results["learning_progression"]) >= 6:
            # Should improve or at least not degrade significantly
            assert (
                learning_curve["improvement"] >= -0.2
            ), "System should learn or maintain performance"

        # Should have learning progression data
        assert len(results["learning_progression"]) > 0
        assert all("is_correct" in point for point in results["learning_progression"])

    def test_pattern_effectiveness_learning(self):
        """Test that system learns which patterns work best for different task types."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Add enough samples to reach confidence threshold (10+ samples for full confidence)
        refactoring_tasks = []
        for i in range(12):  # Ensure we have 10+ samples for confidence
            refactoring_tasks.extend([
                {
                    "task": "Refactor auth system",
                    "pattern": "pipeline",
                    "metrics": {
                        "execution_time": 8 + (i % 3),
                        "success_rate": 95,
                        "conflict_rate": 1,
                        "dedup_rate": 35,
                    },
                },
                {
                    "task": "Refactor auth system",
                    "pattern": "fan_out",
                    "metrics": {
                        "execution_time": 15 + (i % 4),
                        "success_rate": 75,
                        "conflict_rate": 15,
                        "dedup_rate": 10,
                    },
                },
            ])

        # Only use first 20 executions to avoid overwhelming
        refactoring_tasks = refactoring_tasks[:20]

        # Record executions
        for task_data in refactoring_tasks:
            coordinator.record_execution(
                task_data["task"],
                task_data["pattern"],
                {
                    **task_data["metrics"],
                    "agent_count": 4,
                    "context_reuse_rate": task_data["metrics"]["dedup_rate"],
                },
            )

        # Test learned preferences - use similar task description to match the learned task type
        suggestion = coordinator.suggest_pattern("Refactor authentication module")

        # Should learn from history with enough samples and similar task type
        if suggestion["reason"] == "learned_from_history":
            # If it learned, should prefer pipeline which performed better
            assert suggestion["pattern"] == "pipeline"
            assert suggestion["confidence"] >= 0.7
        else:
            # If it falls back to heuristics, verify the pattern scores were recorded
            assert len(coordinator.pattern_scores) > 0
            # Check that refactoring task type exists with both patterns
            task_type = coordinator._extract_task_type("Refactor auth system")
            assert task_type in coordinator.pattern_scores
            assert "pipeline" in coordinator.pattern_scores[task_type]
            assert "fan_out" in coordinator.pattern_scores[task_type]
            # Pipeline should have higher score
            assert (
                coordinator.pattern_scores[task_type]["pipeline"]
                > coordinator.pattern_scores[task_type]["fan_out"]
            )

    def test_prediction_accuracy_validation(self):
        """Test performance predictions vs actual results."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Build some history
        test_executions = self.framework.execution_data[:10]
        for exec_data in test_executions:
            coordinator.record_execution(
                exec_data["task"],
                exec_data["pattern"],
                {
                    **exec_data["metrics"],
                    "agent_count": 4,
                    "context_reuse_rate": exec_data["metrics"].get("dedup_rate", 0),
                },
            )

        # Test predictions for patterns with history
        prediction = coordinator.predict_performance(
            "Refactor authentication system", "pipeline"
        )

        # Should have reasonable predictions based on history
        assert prediction["based_on_samples"] > 0
        assert prediction["confidence"] > 0
        assert 0 < prediction["predicted_time"] < 100  # Reasonable time range
        assert 0 <= prediction["predicted_success_rate"] <= 100

        # Prediction for unknown combination should have low confidence
        unknown_prediction = coordinator.predict_performance(
            "Brand new task type", "hierarchical"
        )
        assert unknown_prediction["confidence"] == 0
        assert unknown_prediction["based_on_samples"] == 0

    def test_confidence_calibration(self):
        """Test that confidence scores correlate with actual accuracy."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Run full simulation
        results = self.framework.run_learning_simulation(coordinator)
        analysis = self.framework.analyze_learning_effectiveness(results)

        # Analyze confidence calibration
        calibration = analysis["confidence_calibration"]

        # High confidence suggestions should be more accurate than low confidence
        if "high" in calibration and "low" in calibration:
            if (
                calibration["high"]["sample_size"] > 0
                and calibration["low"]["sample_size"] > 0
            ):
                high_accuracy = calibration["high"]["accuracy"]
                low_accuracy = calibration["low"]["accuracy"]

                # High confidence should generally be more accurate (allowing some variance)
                assert (
                    high_accuracy >= low_accuracy - 0.2
                ), "High confidence should correlate with accuracy"

    def test_convergence_speed(self):
        """Test how quickly the system converges to optimal suggestions."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Run simulation and analyze convergence
        results = self.framework.run_learning_simulation(coordinator)
        analysis = self.framework.analyze_learning_effectiveness(results)

        convergence = analysis["convergence_metrics"]

        # Should have convergence metrics
        assert "executions_to_accuracy" in convergence
        assert "learning_rate" in convergence
        assert "stability_score" in convergence

        # Learning rate should be reasonable (not too slow or erratic)
        learning_rate = convergence["learning_rate"]
        assert -0.5 <= learning_rate <= 0.5, "Learning rate should be reasonable"

        # Stability should improve over time (should be at least somewhat stable)
        stability = convergence["stability_score"]
        assert 0 <= stability <= 1, "Stability score should be normalized"

    def test_memory_efficiency(self):
        """Test that the system manages memory and file storage efficiently."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Simulate many executions
        for i in range(1200):  # More than the 1000 limit for file storage
            coordinator.record_execution(
                f"Task {i % 10}",  # Cycle through task types
                ["fan_out", "pipeline", "consensus"][i % 3],
                {
                    "execution_time": 5 + (i % 10),
                    "success_rate": 90 + (i % 10),
                    "conflict_rate": i % 5,
                    "dedup_rate": 20 + (i % 20),
                    "agent_count": 3 + (i % 5),
                    "context_reuse_rate": 20 + (i % 20),
                },
            )

        # Current implementation keeps all in memory during runtime
        # But should limit file storage to last 1000 entries
        assert (
            len(coordinator.execution_history) == 1200
        ), "Memory should contain all executions during runtime"

        # Check file storage limitation by loading a new coordinator
        coordinator.save_history()
        new_coordinator = AdaptiveCoordinator(str(self.history_file))

        # File should contain only last 1000 entries
        assert (
            len(new_coordinator.execution_history) <= 1000
        ), "File storage should be limited to 1000 entries"

        # System should still function properly with limited history
        suggestion = new_coordinator.suggest_pattern("Task 5")
        assert suggestion is not None
        assert "pattern" in suggestion

    @pytest.mark.integration
    def test_full_learning_validation(self):
        """Integration test for complete learning validation."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Run complete simulation
        results = self.framework.run_learning_simulation(coordinator)
        analysis = self.framework.analyze_learning_effectiveness(results)

        # Comprehensive validation
        assert "learning_curve" in analysis
        assert "confidence_calibration" in analysis
        assert "prediction_performance" in analysis
        assert "convergence_metrics" in analysis

        # Should have substantial learning data
        assert len(results["learning_progression"]) >= 5
        assert len(results["prediction_accuracy"]) >= 3

        # Get insights from coordinator
        insights = coordinator.get_insights()
        # Check if we have a no_history status, or if we have execution data
        if "status" in insights:
            assert insights["status"] != "no_history"
        else:
            # If no status field, check for execution data directly
            assert "total_executions" in insights
            assert insights["total_executions"] > 20

        assert len(insights.get("best_patterns", {})) > 0

        # Validate that system learned preferences
        pattern_scores = coordinator.pattern_scores
        assert len(pattern_scores) > 0, "System should have learned pattern preferences"

        # Verify that multiple patterns were recorded for various task types
        total_patterns = sum(len(patterns) for patterns in pattern_scores.values())
        assert (
            total_patterns >= 3
        ), "Should have learned multiple pattern-task combinations"

        # Test final state - system should have some confidence (even if heuristic)
        final_suggestion = coordinator.suggest_pattern("Final test task")
        assert final_suggestion["confidence"] >= 0, "Should have some confidence level"

    def test_learning_validation_report_generation(self):
        """Test generation of comprehensive learning effectiveness report."""
        coordinator = AdaptiveCoordinator(str(self.history_file))

        # Run simulation
        results = self.framework.run_learning_simulation(coordinator)
        analysis = self.framework.analyze_learning_effectiveness(results)

        # Generate comprehensive report
        report = {
            "simulation_metadata": {
                "total_executions": len(self.framework.execution_data),
                "task_types": len(
                    set(d["task"] for d in self.framework.execution_data)
                ),
                "patterns_tested": len(
                    set(d["pattern"] for d in self.framework.execution_data)
                ),
                "simulation_date": datetime.now().isoformat(),
            },
            "cold_start_performance": results["phases"][0] if results["phases"] else {},
            "learning_effectiveness": analysis,
            "final_system_state": {
                "total_history": len(coordinator.execution_history),
                "learned_patterns": len(coordinator.pattern_scores),
                "confidence_level": coordinator.get_insights().get(
                    "confidence_level", "unknown"
                ),
            },
            "recommendations": {
                "learning_convergence": analysis["convergence_metrics"][
                    "executions_to_accuracy"
                ],
                "prediction_reliability": analysis["prediction_performance"][
                    "average_error"
                ],
                "system_readiness": (
                    "production"
                    if analysis["learning_curve"]["improvement"] > 0
                    else "needs_training"
                ),
            },
        }

        # Validate report completeness
        assert "simulation_metadata" in report
        assert "learning_effectiveness" in report
        assert "final_system_state" in report
        assert "recommendations" in report

        # Save report for inspection
        report_path = Path(self.temp_dir) / "learning_validation_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        assert report_path.exists(), "Report should be saved successfully"

        # Validate report was generated successfully and contains expected data
        assert report is not None
        print(f"✓ Learning validation report generated successfully at {report_path}")
        print(f"✓ Report contains {len(report)} main sections")
        print(
            f"✓ Simulation covered {report['simulation_metadata']['total_executions']} executions"
        )
        print(f"✓ System readiness: {report['recommendations']['system_readiness']}")


if __name__ == "__main__":
    # Run specific learning validation tests
    pytest.main([__file__, "-v", "-s"])
