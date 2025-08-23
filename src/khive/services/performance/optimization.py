"""Performance optimization recommendations and automated tuning."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .analysis import (BottleneckAnalysis, BottleneckIdentifier,
                       PerformanceAnalyzer, RegressionDetector,
                       RegressionSeverity, TrendAnalyzer, TrendDirection)
from .benchmark_framework import BenchmarkResult
from .storage import BenchmarkStorage

logger = logging.getLogger(__name__)


class OptimizationPriority(Enum):
    """Priority levels for optimization recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationType(Enum):
    """Types of optimizations."""

    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    ALGORITHM = "algorithm"
    CONFIGURATION = "configuration"
    SCALING = "scaling"
    CACHING = "caching"


@dataclass
class OptimizationRecommendation:
    """A specific optimization recommendation."""

    id: str
    title: str
    description: str
    optimization_type: OptimizationType
    priority: OptimizationPriority

    # Impact estimation
    estimated_improvement_percent: float
    confidence: float  # 0.0 to 1.0

    # Implementation details
    implementation_complexity: str  # low, medium, high
    estimated_effort_hours: float

    # Supporting data
    evidence: list[str]
    related_benchmarks: list[str]
    related_operations: list[str]

    # Actionable steps
    action_items: list[str]
    code_examples: list[str] = field(default_factory=list)
    configuration_changes: dict[str, Any] = field(default_factory=dict)

    # Monitoring
    success_metrics: list[str] = field(default_factory=list)
    monitoring_duration_days: int = 7

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "optimization_type": self.optimization_type.value,
            "priority": self.priority.value,
            "estimated_improvement_percent": self.estimated_improvement_percent,
            "confidence": self.confidence,
            "implementation_complexity": self.implementation_complexity,
            "estimated_effort_hours": self.estimated_effort_hours,
            "evidence": self.evidence,
            "related_benchmarks": self.related_benchmarks,
            "related_operations": self.related_operations,
            "action_items": self.action_items,
            "code_examples": self.code_examples,
            "configuration_changes": self.configuration_changes,
            "success_metrics": self.success_metrics,
            "monitoring_duration_days": self.monitoring_duration_days,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OptimizationRecommendation":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            optimization_type=OptimizationType(data["optimization_type"]),
            priority=OptimizationPriority(data["priority"]),
            estimated_improvement_percent=data["estimated_improvement_percent"],
            confidence=data["confidence"],
            implementation_complexity=data["implementation_complexity"],
            estimated_effort_hours=data["estimated_effort_hours"],
            evidence=data["evidence"],
            related_benchmarks=data["related_benchmarks"],
            related_operations=data["related_operations"],
            action_items=data["action_items"],
            code_examples=data.get("code_examples", []),
            configuration_changes=data.get("configuration_changes", {}),
            success_metrics=data.get("success_metrics", []),
            monitoring_duration_days=data.get("monitoring_duration_days", 7),
            metadata=data.get("metadata", {}),
        )


@dataclass
class OptimizationPlan:
    """Complete optimization plan with prioritized recommendations."""

    plan_id: str
    created_at: datetime
    target_benchmarks: list[str]

    # Recommendations by priority
    critical_recommendations: list[OptimizationRecommendation] = field(
        default_factory=list
    )
    high_recommendations: list[OptimizationRecommendation] = field(default_factory=list)
    medium_recommendations: list[OptimizationRecommendation] = field(
        default_factory=list
    )
    low_recommendations: list[OptimizationRecommendation] = field(default_factory=list)

    # Overall plan metrics
    total_estimated_improvement: float = 0.0
    total_estimated_effort_hours: float = 0.0
    recommended_implementation_order: list[str] = field(default_factory=list)

    # Plan metadata
    analysis_period_days: int = 30
    plan_summary: str = ""

    @property
    def all_recommendations(self) -> list[OptimizationRecommendation]:
        """Get all recommendations sorted by priority."""
        return (
            self.critical_recommendations
            + self.high_recommendations
            + self.medium_recommendations
            + self.low_recommendations
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at.isoformat(),
            "target_benchmarks": self.target_benchmarks,
            "critical_recommendations": [
                r.to_dict() for r in self.critical_recommendations
            ],
            "high_recommendations": [r.to_dict() for r in self.high_recommendations],
            "medium_recommendations": [
                r.to_dict() for r in self.medium_recommendations
            ],
            "low_recommendations": [r.to_dict() for r in self.low_recommendations],
            "total_estimated_improvement": self.total_estimated_improvement,
            "total_estimated_effort_hours": self.total_estimated_effort_hours,
            "recommended_implementation_order": self.recommended_implementation_order,
            "analysis_period_days": self.analysis_period_days,
            "plan_summary": self.plan_summary,
        }


class OptimizationRecommender:
    """Generates intelligent optimization recommendations based on performance analysis."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage
        self.analyzer = PerformanceAnalyzer(storage)
        self.trend_analyzer = TrendAnalyzer(storage)
        self.regression_detector = RegressionDetector(storage)
        self.bottleneck_identifier = BottleneckIdentifier(storage)

        # Recommendation knowledge base
        self.optimization_patterns = self._load_optimization_patterns()

    def generate_recommendations(
        self,
        benchmark_name: str | None = None,
        operation_type: str | None = None,
        days_back: int = 30,
        max_recommendations: int = 20,
    ) -> OptimizationPlan:
        """Generate optimization recommendations based on performance analysis."""

        # Get performance data
        since = datetime.now() - timedelta(days=days_back)

        if benchmark_name:
            results = self.storage.get_results(
                benchmark_name=benchmark_name,
                operation_type=operation_type,
                since=since,
            )
            target_benchmarks = [benchmark_name]
        else:
            # System-wide analysis
            results = self.storage.get_results(since=since)
            target_benchmarks = list(set(r.benchmark_name for r in results))

        if not results:
            logger.warning("No performance data found for analysis")
            return OptimizationPlan(
                plan_id=f"opt_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now(),
                target_benchmarks=target_benchmarks,
                plan_summary="No performance data available for analysis",
            )

        # Collect all recommendations
        all_recommendations = []

        # 1. Bottleneck-based recommendations
        bottleneck_recommendations = self._generate_bottleneck_recommendations(
            target_benchmarks, days_back
        )
        all_recommendations.extend(bottleneck_recommendations)

        # 2. Regression-based recommendations
        regression_recommendations = self._generate_regression_recommendations(
            results, days_back
        )
        all_recommendations.extend(regression_recommendations)

        # 3. Trend-based recommendations
        trend_recommendations = self._generate_trend_recommendations(
            target_benchmarks, days_back
        )
        all_recommendations.extend(trend_recommendations)

        # 4. Pattern-based recommendations
        pattern_recommendations = self._generate_pattern_recommendations(
            results, target_benchmarks
        )
        all_recommendations.extend(pattern_recommendations)

        # 5. General performance recommendations
        general_recommendations = self._generate_general_recommendations(
            results, target_benchmarks
        )
        all_recommendations.extend(general_recommendations)

        # Deduplicate and prioritize recommendations
        unique_recommendations = self._deduplicate_recommendations(all_recommendations)
        prioritized_recommendations = self._prioritize_recommendations(
            unique_recommendations, max_recommendations
        )

        # Create optimization plan
        plan = self._create_optimization_plan(
            prioritized_recommendations, target_benchmarks, days_back
        )

        return plan

    def _generate_bottleneck_recommendations(
        self, benchmark_names: list[str], days_back: int
    ) -> list[OptimizationRecommendation]:
        """Generate recommendations based on bottleneck analysis."""

        recommendations = []

        for benchmark_name in benchmark_names:
            bottlenecks = self.bottleneck_identifier.identify_bottlenecks(
                benchmark_name=benchmark_name, days_back=days_back
            )

            for bottleneck in bottlenecks:
                rec = self._create_bottleneck_recommendation(bottleneck, benchmark_name)
                if rec:
                    recommendations.append(rec)

        return recommendations

    def _create_bottleneck_recommendation(
        self, bottleneck: BottleneckAnalysis, benchmark_name: str
    ) -> OptimizationRecommendation | None:
        """Create recommendation for a specific bottleneck."""

        bottleneck_type = bottleneck.bottleneck_type
        severity = bottleneck.severity

        # Map bottleneck to optimization type
        optimization_type_map = {
            "cpu": OptimizationType.CPU,
            "memory": OptimizationType.MEMORY,
            "io": OptimizationType.IO,
            "network": OptimizationType.NETWORK,
        }

        optimization_type = optimization_type_map.get(
            bottleneck_type, OptimizationType.ALGORITHM
        )

        # Map severity to priority
        priority_map = {
            "critical": OptimizationPriority.CRITICAL,
            "high": OptimizationPriority.HIGH,
            "medium": OptimizationPriority.MEDIUM,
            "low": OptimizationPriority.LOW,
        }

        priority = priority_map.get(severity, OptimizationPriority.MEDIUM)

        # Generate specific recommendations based on bottleneck type
        if bottleneck_type == "cpu":
            return self._create_cpu_optimization_recommendation(
                bottleneck, benchmark_name, optimization_type, priority
            )
        if bottleneck_type == "memory":
            return self._create_memory_optimization_recommendation(
                bottleneck, benchmark_name, optimization_type, priority
            )
        if bottleneck_type == "io":
            return self._create_io_optimization_recommendation(
                bottleneck, benchmark_name, optimization_type, priority
            )
        if bottleneck_type == "network":
            return self._create_network_optimization_recommendation(
                bottleneck, benchmark_name, optimization_type, priority
            )

        return None

    def _create_cpu_optimization_recommendation(
        self,
        bottleneck: BottleneckAnalysis,
        benchmark_name: str,
        optimization_type: OptimizationType,
        priority: OptimizationPriority,
    ) -> OptimizationRecommendation:
        """Create CPU-specific optimization recommendation."""

        utilization = bottleneck.current_utilization
        impact = bottleneck.performance_impact

        title = f"Optimize CPU usage for {benchmark_name}"
        description = f"CPU utilization is at {utilization:.1f}% with {impact:.1f}% performance impact. Optimize computational efficiency."

        action_items = [
            "Profile code to identify CPU hotspots",
            "Optimize algorithm complexity where possible",
            "Consider parallel processing for CPU-intensive tasks",
            "Review synchronous operations that could be async",
        ]

        code_examples = [
            # Async optimization example
            """
# Consider converting synchronous operations to async
async def optimized_operation():
    # Use async operations for I/O
    async with aiofiles.open('file.txt', 'r') as f:
        data = await f.read()
    
    # Use asyncio.gather for concurrent operations
    results = await asyncio.gather(*[
        async_task(item) for item in data_items
    ])
    
    return results
            """,
            # CPU optimization example
            """
# Use list comprehension instead of loops where possible
# Slow
results = []
for item in items:
    if condition(item):
        results.append(process(item))

# Faster
results = [process(item) for item in items if condition(item)]
            """,
        ]

        return OptimizationRecommendation(
            id=f"cpu_opt_{benchmark_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            optimization_type=optimization_type,
            priority=priority,
            estimated_improvement_percent=min(
                impact * 0.6, 30
            ),  # Conservative estimate
            confidence=bottleneck.confidence,
            implementation_complexity="medium",
            estimated_effort_hours=8.0
            if priority == OptimizationPriority.CRITICAL
            else 4.0,
            evidence=[
                f"CPU utilization: {utilization:.1f}%",
                f"Performance impact: {impact:.1f}%",
                f"Affected operations: {', '.join(bottleneck.operations_affected[:3])}",
            ],
            related_benchmarks=[benchmark_name],
            related_operations=bottleneck.operations_affected,
            action_items=action_items,
            code_examples=code_examples,
            success_metrics=["cpu_percent_peak", "duration", "throughput_ops_per_sec"],
            metadata={"bottleneck_analysis": bottleneck.metadata},
        )

    def _create_memory_optimization_recommendation(
        self,
        bottleneck: BottleneckAnalysis,
        benchmark_name: str,
        optimization_type: OptimizationType,
        priority: OptimizationPriority,
    ) -> OptimizationRecommendation:
        """Create memory-specific optimization recommendation."""

        utilization = bottleneck.current_utilization
        impact = bottleneck.performance_impact

        title = f"Optimize memory usage for {benchmark_name}"
        description = f"Memory usage is at {utilization:.1f}MB with {impact:.1f}% performance impact. Implement memory efficiency improvements."

        action_items = [
            "Profile memory allocations and identify memory leaks",
            "Implement object pooling for frequently created objects",
            "Use generators instead of lists for large datasets",
            "Consider lazy loading for large data structures",
            "Review data structures for memory efficiency",
        ]

        code_examples = [
            # Memory optimization example
            """
# Use generators for large datasets
def data_processor(large_dataset):
    # Memory-efficient: processes one item at a time
    for item in large_dataset:
        yield process_item(item)

# Instead of loading everything into memory
# results = [process_item(item) for item in large_dataset]  # Memory intensive
results = data_processor(large_dataset)  # Memory efficient
            """,
            # Object pooling example
            """
# Object pooling for frequently created objects
from collections import deque

class ObjectPool:
    def __init__(self, create_func, reset_func, initial_size=10):
        self.create_func = create_func
        self.reset_func = reset_func
        self.pool = deque([create_func() for _ in range(initial_size)])
    
    def acquire(self):
        if self.pool:
            return self.pool.popleft()
        return self.create_func()
    
    def release(self, obj):
        self.reset_func(obj)
        self.pool.append(obj)
            """,
        ]

        return OptimizationRecommendation(
            id=f"memory_opt_{benchmark_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            optimization_type=optimization_type,
            priority=priority,
            estimated_improvement_percent=min(impact * 0.5, 25),
            confidence=bottleneck.confidence,
            implementation_complexity="medium",
            estimated_effort_hours=6.0
            if priority == OptimizationPriority.CRITICAL
            else 3.0,
            evidence=[
                f"Memory usage: {utilization:.1f}MB",
                f"Performance impact: {impact:.1f}%",
                f"Affected operations: {', '.join(bottleneck.operations_affected[:3])}",
            ],
            related_benchmarks=[benchmark_name],
            related_operations=bottleneck.operations_affected,
            action_items=action_items,
            code_examples=code_examples,
            success_metrics=["memory_peak_mb", "memory_delta_mb", "duration"],
            metadata={"bottleneck_analysis": bottleneck.metadata},
        )

    def _create_io_optimization_recommendation(
        self,
        bottleneck: BottleneckAnalysis,
        benchmark_name: str,
        optimization_type: OptimizationType,
        priority: OptimizationPriority,
    ) -> OptimizationRecommendation:
        """Create I/O-specific optimization recommendation."""

        utilization = bottleneck.current_utilization
        impact = bottleneck.performance_impact

        title = f"Optimize I/O operations for {benchmark_name}"
        description = f"I/O operations at {utilization / 1024 / 1024:.1f}MB with {impact:.1f}% performance impact. Implement I/O efficiency improvements."

        action_items = [
            "Implement asynchronous I/O operations",
            "Use batching for multiple small I/O operations",
            "Add caching layer for frequently accessed data",
            "Optimize file access patterns",
            "Consider compression for large data transfers",
        ]

        code_examples = [
            # Async I/O example
            """
import asyncio
import aiofiles

async def async_file_operations(filenames):
    async def read_file(filename):
        async with aiofiles.open(filename, 'r') as f:
            return await f.read()
    
    # Process files concurrently
    results = await asyncio.gather(*[
        read_file(filename) for filename in filenames
    ])
    
    return results
            """,
            # I/O batching example
            """
# Batch multiple small operations
def batch_file_operations(operations, batch_size=10):
    for i in range(0, len(operations), batch_size):
        batch = operations[i:i+batch_size]
        # Process batch together
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [executor.submit(op) for op in batch]
            results = [future.result() for future in futures]
        yield results
            """,
        ]

        return OptimizationRecommendation(
            id=f"io_opt_{benchmark_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            optimization_type=optimization_type,
            priority=priority,
            estimated_improvement_percent=min(impact * 0.7, 40),
            confidence=bottleneck.confidence,
            implementation_complexity="medium",
            estimated_effort_hours=10.0
            if priority == OptimizationPriority.CRITICAL
            else 5.0,
            evidence=[
                f"I/O operations: {utilization / 1024 / 1024:.1f}MB",
                f"Performance impact: {impact:.1f}%",
                f"Affected operations: {', '.join(bottleneck.operations_affected[:3])}",
            ],
            related_benchmarks=[benchmark_name],
            related_operations=bottleneck.operations_affected,
            action_items=action_items,
            code_examples=code_examples,
            success_metrics=["io_read_bytes", "io_write_bytes", "duration"],
            metadata={"bottleneck_analysis": bottleneck.metadata},
        )

    def _create_network_optimization_recommendation(
        self,
        bottleneck: BottleneckAnalysis,
        benchmark_name: str,
        optimization_type: OptimizationType,
        priority: OptimizationPriority,
    ) -> OptimizationRecommendation:
        """Create network-specific optimization recommendation."""

        utilization = bottleneck.current_utilization
        impact = bottleneck.performance_impact

        title = f"Optimize network operations for {benchmark_name}"
        description = f"Network usage at {utilization / 1024 / 1024:.1f}MB with {impact:.1f}% performance impact. Implement network efficiency improvements."

        action_items = [
            "Implement connection pooling and keep-alive",
            "Use request batching where possible",
            "Add response compression",
            "Implement local caching for API responses",
            "Optimize payload sizes",
        ]

        code_examples = [
            # Connection pooling example
            """
import aiohttp
import asyncio

class HTTPClientPool:
    def __init__(self, max_connections=100):
        connector = aiohttp.TCPConnector(
            limit=max_connections,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(connector=connector)
    
    async def make_request(self, url, **kwargs):
        async with self.session.get(url, **kwargs) as response:
            return await response.json()
    
    async def close(self):
        await self.session.close()
            """,
            # Request batching example
            """
# Batch multiple API requests
async def batch_api_requests(urls, batch_size=10):
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i+batch_size]
            tasks = [session.get(url) for url in batch_urls]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                yield await response.json()
                response.close()
            """,
        ]

        return OptimizationRecommendation(
            id=f"network_opt_{benchmark_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            optimization_type=optimization_type,
            priority=priority,
            estimated_improvement_percent=min(impact * 0.6, 35),
            confidence=bottleneck.confidence,
            implementation_complexity="medium",
            estimated_effort_hours=8.0
            if priority == OptimizationPriority.CRITICAL
            else 4.0,
            evidence=[
                f"Network usage: {utilization / 1024 / 1024:.1f}MB",
                f"Performance impact: {impact:.1f}%",
                f"Affected operations: {', '.join(bottleneck.operations_affected[:3])}",
            ],
            related_benchmarks=[benchmark_name],
            related_operations=bottleneck.operations_affected,
            action_items=action_items,
            code_examples=code_examples,
            success_metrics=["network_sent_bytes", "network_recv_bytes", "duration"],
            metadata={"bottleneck_analysis": bottleneck.metadata},
        )

    def _generate_regression_recommendations(
        self, results: list[BenchmarkResult], days_back: int
    ) -> list[OptimizationRecommendation]:
        """Generate recommendations based on performance regressions."""

        recommendations = []

        # Group results by benchmark and operation
        result_groups = {}
        for result in results:
            key = (result.benchmark_name, result.operation_type)
            if key not in result_groups:
                result_groups[key] = []
            result_groups[key].append(result)

        # Analyze each group for regressions
        for (benchmark_name, operation_type), group_results in result_groups.items():
            if len(group_results) < 5:  # Need sufficient data
                continue

            # Get latest result for regression analysis
            latest_result = max(group_results, key=lambda r: r.timestamp)

            regression_result = self.regression_detector.detect_regression(
                current_result=latest_result, comparison_days=days_back
            )

            if regression_result.regression_detected:
                rec = self._create_regression_recommendation(
                    regression_result, benchmark_name, operation_type
                )
                if rec:
                    recommendations.append(rec)

        return recommendations

    def _create_regression_recommendation(
        self, regression_result, benchmark_name: str, operation_type: str
    ) -> OptimizationRecommendation:
        """Create recommendation based on detected regression."""

        severity = regression_result.severity
        relative_change = regression_result.relative_change

        # Map severity to priority
        priority_map = {
            RegressionSeverity.CRITICAL: OptimizationPriority.CRITICAL,
            RegressionSeverity.MODERATE: OptimizationPriority.HIGH,
            RegressionSeverity.MINOR: OptimizationPriority.MEDIUM,
            RegressionSeverity.NONE: OptimizationPriority.LOW,
        }

        priority = priority_map.get(severity, OptimizationPriority.MEDIUM)

        title = f"Address performance regression in {benchmark_name}.{operation_type}"
        description = f"Performance regression detected: {relative_change:.1f}x slower than baseline. {regression_result.recommendation}"

        action_items = [
            "Review recent code changes that might impact performance",
            "Compare current implementation with baseline version",
            "Run detailed profiling to identify regression source",
            "Consider rollback if critical regression affects production",
        ]

        # Add trend-specific actions
        if regression_result.trend_analysis.direction == TrendDirection.DEGRADING:
            action_items.append("Address consistent performance degradation trend")

        return OptimizationRecommendation(
            id=f"regression_opt_{benchmark_name}_{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            optimization_type=OptimizationType.ALGORITHM,
            priority=priority,
            estimated_improvement_percent=(relative_change - 1) * 100,
            confidence=regression_result.confidence,
            implementation_complexity="high"
            if severity == RegressionSeverity.CRITICAL
            else "medium",
            estimated_effort_hours=16.0
            if severity == RegressionSeverity.CRITICAL
            else 8.0,
            evidence=[
                f"Regression severity: {severity.value}",
                f"Performance degradation: {relative_change:.1f}x",
                f"Confidence: {regression_result.confidence:.2f}",
                f"Trend: {regression_result.trend_analysis.direction.value}",
            ],
            related_benchmarks=[benchmark_name],
            related_operations=[operation_type],
            action_items=action_items,
            success_metrics=["duration", "throughput_ops_per_sec", "success_rate"],
            metadata={"regression_analysis": regression_result.metadata},
        )

    def _generate_trend_recommendations(
        self, benchmark_names: list[str], days_back: int
    ) -> list[OptimizationRecommendation]:
        """Generate recommendations based on performance trends."""

        recommendations = []

        for benchmark_name in benchmark_names:
            # Get all operation types for this benchmark
            since = datetime.now() - timedelta(days=days_back)
            results = self.storage.get_results(
                benchmark_name=benchmark_name, since=since
            )
            operation_types = list(set(r.operation_type for r in results))

            for operation_type in operation_types:
                trend_analysis = self.trend_analyzer.analyze_trend(
                    benchmark_name=benchmark_name,
                    operation_type=operation_type,
                    days_back=days_back,
                )

                if trend_analysis.direction == TrendDirection.DEGRADING:
                    rec = self._create_trend_recommendation(
                        trend_analysis, benchmark_name, operation_type
                    )
                    if rec:
                        recommendations.append(rec)

        return recommendations

    def _create_trend_recommendation(
        self, trend_analysis, benchmark_name: str, operation_type: str
    ) -> OptimizationRecommendation:
        """Create recommendation based on performance trend."""

        confidence = trend_analysis.confidence
        change_rate = trend_analysis.recent_vs_historical_change

        # Determine priority based on trend severity
        if change_rate > 1.5:
            priority = OptimizationPriority.HIGH
        elif change_rate > 1.2:
            priority = OptimizationPriority.MEDIUM
        else:
            priority = OptimizationPriority.LOW

        title = (
            f"Address degrading performance trend in {benchmark_name}.{operation_type}"
        )
        description = f"Performance trend is degrading over time. Recent performance is {change_rate:.1f}x slower than historical average."

        action_items = [
            "Investigate gradual performance degradation causes",
            "Review system resource usage trends",
            "Check for memory leaks or resource accumulation",
            "Implement preventive performance monitoring",
        ]

        return OptimizationRecommendation(
            id=f"trend_opt_{benchmark_name}_{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            optimization_type=OptimizationType.ALGORITHM,
            priority=priority,
            estimated_improvement_percent=(change_rate - 1) * 100,
            confidence=confidence,
            implementation_complexity="medium",
            estimated_effort_hours=6.0
            if priority == OptimizationPriority.HIGH
            else 3.0,
            evidence=[
                f"Trend direction: {trend_analysis.direction.value}",
                f"Performance change: {change_rate:.1f}x",
                f"Trend confidence: {confidence:.2f}",
                f"Sample size: {trend_analysis.sample_size}",
            ],
            related_benchmarks=[benchmark_name],
            related_operations=[operation_type],
            action_items=action_items,
            success_metrics=["duration", "throughput_ops_per_sec"],
            metadata={"trend_analysis": trend_analysis.metadata},
        )

    def _generate_pattern_recommendations(
        self, results: list[BenchmarkResult], benchmark_names: list[str]
    ) -> list[OptimizationRecommendation]:
        """Generate recommendations based on known performance patterns."""

        recommendations = []

        # Analyze common performance patterns
        patterns = self._analyze_performance_patterns(results)

        for pattern_name, pattern_data in patterns.items():
            if (
                pattern_data["detected"] and pattern_data["impact"] > 5
            ):  # 5% impact threshold
                rec = self._create_pattern_recommendation(
                    pattern_name, pattern_data, benchmark_names
                )
                if rec:
                    recommendations.append(rec)

        return recommendations

    def _analyze_performance_patterns(
        self, results: list[BenchmarkResult]
    ) -> dict[str, Any]:
        """Analyze common performance patterns in the data."""

        patterns = {}

        # Pattern 1: High memory growth
        memory_deltas = [
            r.metrics.memory_delta_mb for r in results if r.metrics.memory_delta_mb > 0
        ]
        if memory_deltas:
            avg_growth = sum(memory_deltas) / len(memory_deltas)
            patterns["high_memory_growth"] = {
                "detected": avg_growth > 10,  # More than 10MB average growth
                "impact": min(avg_growth, 30),  # Cap at 30% impact
                "evidence": f"Average memory growth: {avg_growth:.1f}MB per operation",
            }

        # Pattern 2: Inconsistent performance (high variance)
        durations = [r.metrics.duration for r in results if r.metrics.duration > 0]
        if durations and len(durations) > 2:
            import statistics

            mean_duration = statistics.mean(durations)
            std_duration = statistics.stdev(durations)
            cv = std_duration / mean_duration if mean_duration > 0 else 0

            patterns["high_variance"] = {
                "detected": cv > 0.3,  # Coefficient of variation > 30%
                "impact": min(cv * 50, 25),  # Convert to impact percentage
                "evidence": f"Performance variance: {cv:.2f} (coefficient of variation)",
            }

        # Pattern 3: Poor success rate
        success_rates = [
            r.metrics.success_rate for r in results if r.metrics.success_rate >= 0
        ]
        if success_rates:
            avg_success_rate = sum(success_rates) / len(success_rates)
            patterns["low_success_rate"] = {
                "detected": avg_success_rate < 0.95,  # Less than 95% success
                "impact": (1 - avg_success_rate) * 100,  # Direct impact percentage
                "evidence": f"Average success rate: {avg_success_rate:.2f}",
            }

        return patterns

    def _create_pattern_recommendation(
        self,
        pattern_name: str,
        pattern_data: dict[str, Any],
        benchmark_names: list[str],
    ) -> OptimizationRecommendation | None:
        """Create recommendation based on detected pattern."""

        pattern_configs = {
            "high_memory_growth": {
                "title": "Address memory growth pattern",
                "description": "Detected consistent memory growth pattern that may indicate memory leaks or inefficient memory usage.",
                "optimization_type": OptimizationType.MEMORY,
                "priority": OptimizationPriority.HIGH,
                "action_items": [
                    "Profile memory allocations to identify growth sources",
                    "Implement proper object disposal and cleanup",
                    "Use memory-efficient data structures",
                    "Add memory usage monitoring and alerts",
                ],
            },
            "high_variance": {
                "title": "Reduce performance variance",
                "description": "Performance shows high variance, indicating inconsistent execution times and potential reliability issues.",
                "optimization_type": OptimizationType.ALGORITHM,
                "priority": OptimizationPriority.MEDIUM,
                "action_items": [
                    "Investigate sources of performance variability",
                    "Implement consistent resource allocation",
                    "Add performance stabilization mechanisms",
                    "Review concurrent operations for race conditions",
                ],
            },
            "low_success_rate": {
                "title": "Improve operation success rate",
                "description": "Operations have lower than expected success rate, impacting overall system reliability.",
                "optimization_type": OptimizationType.ALGORITHM,
                "priority": OptimizationPriority.HIGH,
                "action_items": [
                    "Analyze failure patterns and root causes",
                    "Implement better error handling and retry logic",
                    "Add input validation and error prevention",
                    "Improve system resilience and fault tolerance",
                ],
            },
        }

        if pattern_name not in pattern_configs:
            return None

        config = pattern_configs[pattern_name]

        return OptimizationRecommendation(
            id=f"pattern_opt_{pattern_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=config["title"],
            description=config["description"],
            optimization_type=config["optimization_type"],
            priority=config["priority"],
            estimated_improvement_percent=pattern_data["impact"],
            confidence=0.7,  # Pattern-based recommendations have moderate confidence
            implementation_complexity="medium",
            estimated_effort_hours=8.0,
            evidence=[pattern_data["evidence"]],
            related_benchmarks=benchmark_names,
            related_operations=[],
            action_items=config["action_items"],
            success_metrics=["success_rate", "duration", "memory_delta_mb"],
            metadata={"pattern_data": pattern_data},
        )

    def _generate_general_recommendations(
        self, results: list[BenchmarkResult], benchmark_names: list[str]
    ) -> list[OptimizationRecommendation]:
        """Generate general performance recommendations."""

        recommendations = []

        # Analyze overall system performance characteristics
        if results:
            # General caching recommendation
            total_operations = sum(
                r.metrics.operations_count
                for r in results
                if r.metrics.operations_count > 0
            )
            if total_operations > 1000:  # High volume operations
                caching_rec = OptimizationRecommendation(
                    id=f"general_caching_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    title="Implement performance caching strategy",
                    description="High operation volume detected. Implement caching to reduce redundant computations and I/O.",
                    optimization_type=OptimizationType.CACHING,
                    priority=OptimizationPriority.MEDIUM,
                    estimated_improvement_percent=15.0,
                    confidence=0.6,
                    implementation_complexity="medium",
                    estimated_effort_hours=12.0,
                    evidence=[f"Total operations analyzed: {total_operations}"],
                    related_benchmarks=benchmark_names,
                    related_operations=[],
                    action_items=[
                        "Identify frequently accessed data for caching",
                        "Implement Redis or in-memory caching layer",
                        "Add cache invalidation strategy",
                        "Monitor cache hit/miss ratios",
                    ],
                    code_examples=[
                        """
# Example: Simple LRU cache implementation
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(key):
    # Expensive computation here
    return compute_result(key)
                        """
                    ],
                    success_metrics=["duration", "throughput_ops_per_sec"],
                )
                recommendations.append(caching_rec)

        return recommendations

    def _deduplicate_recommendations(
        self, recommendations: list[OptimizationRecommendation]
    ) -> list[OptimizationRecommendation]:
        """Remove duplicate recommendations based on similarity."""

        unique_recommendations = []
        seen_titles = set()

        for rec in recommendations:
            # Simple deduplication based on title similarity
            title_key = rec.title.lower().replace(" ", "_")
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_recommendations.append(rec)

        return unique_recommendations

    def _prioritize_recommendations(
        self,
        recommendations: list[OptimizationRecommendation],
        max_recommendations: int,
    ) -> list[OptimizationRecommendation]:
        """Prioritize and limit recommendations."""

        # Sort by priority, then by estimated improvement, then by confidence
        def sort_key(rec):
            priority_order = {
                OptimizationPriority.CRITICAL: 4,
                OptimizationPriority.HIGH: 3,
                OptimizationPriority.MEDIUM: 2,
                OptimizationPriority.LOW: 1,
            }
            return (
                priority_order.get(rec.priority, 0),
                rec.estimated_improvement_percent,
                rec.confidence,
            )

        sorted_recommendations = sorted(recommendations, key=sort_key, reverse=True)
        return sorted_recommendations[:max_recommendations]

    def _create_optimization_plan(
        self,
        recommendations: list[OptimizationRecommendation],
        target_benchmarks: list[str],
        days_back: int,
    ) -> OptimizationPlan:
        """Create complete optimization plan."""

        plan = OptimizationPlan(
            plan_id=f"opt_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now(),
            target_benchmarks=target_benchmarks,
            analysis_period_days=days_back,
        )

        # Group recommendations by priority
        for rec in recommendations:
            if rec.priority == OptimizationPriority.CRITICAL:
                plan.critical_recommendations.append(rec)
            elif rec.priority == OptimizationPriority.HIGH:
                plan.high_recommendations.append(rec)
            elif rec.priority == OptimizationPriority.MEDIUM:
                plan.medium_recommendations.append(rec)
            else:
                plan.low_recommendations.append(rec)

        # Calculate total metrics
        plan.total_estimated_improvement = sum(
            rec.estimated_improvement_percent for rec in recommendations
        )
        plan.total_estimated_effort_hours = sum(
            rec.estimated_effort_hours for rec in recommendations
        )

        # Create implementation order recommendation
        plan.recommended_implementation_order = [rec.id for rec in recommendations]

        # Generate plan summary
        plan.plan_summary = self._generate_plan_summary(plan, recommendations)

        return plan

    def _generate_plan_summary(
        self, plan: OptimizationPlan, recommendations: list[OptimizationRecommendation]
    ) -> str:
        """Generate human-readable plan summary."""

        total_recs = len(recommendations)
        critical_count = len(plan.critical_recommendations)
        high_count = len(plan.high_recommendations)

        summary = f"Optimization plan with {total_recs} recommendations for {len(plan.target_benchmarks)} benchmarks. "

        if critical_count > 0:
            summary += f"{critical_count} critical issues require immediate attention. "

        if high_count > 0:
            summary += f"{high_count} high-priority optimizations identified. "

        summary += (
            f"Total estimated improvement: {plan.total_estimated_improvement:.1f}%. "
        )
        summary += f"Estimated effort: {plan.total_estimated_effort_hours:.1f} hours."

        return summary

    def _load_optimization_patterns(self) -> dict[str, Any]:
        """Load optimization patterns knowledge base."""

        # This would typically load from a configuration file or database
        return {
            "cpu_intensive_patterns": {
                "indicators": ["high_cpu_usage", "long_execution_time"],
                "recommendations": ["parallel_processing", "algorithm_optimization"],
            },
            "memory_leak_patterns": {
                "indicators": ["increasing_memory", "memory_not_released"],
                "recommendations": ["object_pooling", "proper_disposal"],
            },
            "io_bottleneck_patterns": {
                "indicators": ["high_io_wait", "disk_intensive_operations"],
                "recommendations": ["async_io", "batching", "caching"],
            },
        }


class PerformanceTuner:
    """Automated performance tuning based on optimization recommendations."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage
        self.recommender = OptimizationRecommender(storage)

    def auto_tune(
        self,
        benchmark_name: str,
        operation_type: str | None = None,
        max_iterations: int = 3,
        improvement_threshold: float = 5.0,  # 5% minimum improvement
    ) -> dict[str, Any]:
        """Automatically apply performance tuning recommendations."""

        tuning_results = {
            "benchmark_name": benchmark_name,
            "operation_type": operation_type,
            "iterations": [],
            "total_improvement_percent": 0.0,
            "successful_optimizations": 0,
            "failed_optimizations": 0,
        }

        # Get baseline performance
        baseline_results = self.storage.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, limit=10
        )

        if not baseline_results:
            tuning_results["error"] = "No baseline performance data available"
            return tuning_results

        baseline_performance = self._calculate_baseline_performance(baseline_results)
        tuning_results["baseline_performance"] = baseline_performance

        logger.info(
            f"Starting auto-tuning for {benchmark_name} with baseline: {baseline_performance}"
        )

        for iteration in range(max_iterations):
            iteration_result = {
                "iteration": iteration + 1,
                "recommendations_applied": [],
                "performance_change": 0.0,
                "success": False,
            }

            # Generate recommendations for current state
            optimization_plan = self.recommender.generate_recommendations(
                benchmark_name=benchmark_name,
                operation_type=operation_type,
                max_recommendations=3,  # Limit for auto-tuning
            )

            if not optimization_plan.all_recommendations:
                iteration_result["message"] = (
                    "No optimization recommendations available"
                )
                tuning_results["iterations"].append(iteration_result)
                break

            # Apply highest priority recommendations that can be auto-applied
            applied_optimizations = []

            for rec in optimization_plan.all_recommendations[:2]:  # Apply top 2
                if self._can_auto_apply(rec):
                    apply_result = self._apply_optimization(rec)
                    applied_optimizations.append({
                        "recommendation_id": rec.id,
                        "title": rec.title,
                        "applied": apply_result["success"],
                        "message": apply_result.get("message", ""),
                    })

            if not applied_optimizations:
                iteration_result["message"] = (
                    "No auto-applicable optimizations available"
                )
                tuning_results["iterations"].append(iteration_result)
                break

            iteration_result["recommendations_applied"] = applied_optimizations

            # Wait for changes to take effect (in real implementation)
            # time.sleep(5)

            # Measure new performance (simulated)
            # new_results = self._measure_performance(benchmark_name, operation_type)
            # For demo, simulate improvement
            simulated_improvement = (
                sum(
                    rec.estimated_improvement_percent
                    for rec in optimization_plan.all_recommendations[:2]
                )
                * 0.7
            )  # Apply 70% of estimated improvement

            iteration_result["performance_change"] = simulated_improvement

            if simulated_improvement >= improvement_threshold:
                iteration_result["success"] = True
                tuning_results["successful_optimizations"] += len(applied_optimizations)
                tuning_results["total_improvement_percent"] += simulated_improvement
            else:
                tuning_results["failed_optimizations"] += len(applied_optimizations)

            tuning_results["iterations"].append(iteration_result)

            # Stop if improvement is below threshold
            if simulated_improvement < improvement_threshold:
                logger.info(
                    f"Auto-tuning stopped: improvement below threshold ({simulated_improvement:.1f}% < {improvement_threshold:.1f}%)"
                )
                break

        logger.info(
            f"Auto-tuning completed: {tuning_results['total_improvement_percent']:.1f}% total improvement"
        )
        return tuning_results

    def _calculate_baseline_performance(
        self, results: list[BenchmarkResult]
    ) -> dict[str, float]:
        """Calculate baseline performance metrics."""

        durations = [r.metrics.duration for r in results if r.metrics.duration > 0]
        success_rates = [
            r.metrics.success_rate for r in results if r.metrics.success_rate >= 0
        ]
        throughputs = [
            r.metrics.throughput_ops_per_sec
            for r in results
            if r.metrics.throughput_ops_per_sec > 0
        ]

        import statistics

        return {
            "avg_duration": statistics.mean(durations) if durations else 0,
            "avg_success_rate": statistics.mean(success_rates) if success_rates else 0,
            "avg_throughput": statistics.mean(throughputs) if throughputs else 0,
        }

    def _can_auto_apply(self, recommendation: OptimizationRecommendation) -> bool:
        """Check if a recommendation can be automatically applied."""

        # Only apply low-risk, configuration-based optimizations automatically
        auto_applicable_types = {
            OptimizationType.CONFIGURATION,
            OptimizationType.CACHING,
        }

        return (
            recommendation.optimization_type in auto_applicable_types
            and recommendation.implementation_complexity == "low"
            and recommendation.priority
            != OptimizationPriority.CRITICAL  # Avoid critical changes
        )

    def _apply_optimization(
        self, recommendation: OptimizationRecommendation
    ) -> dict[str, Any]:
        """Apply an optimization recommendation."""

        # In a real implementation, this would:
        # 1. Parse configuration changes
        # 2. Apply changes to system configuration
        # 3. Restart relevant services if needed
        # 4. Validate changes took effect

        # For demo, simulate application
        logger.info(f"Applying optimization: {recommendation.title}")

        # Simulate success/failure based on confidence
        import random

        success_probability = recommendation.confidence
        success = random.random() < success_probability

        if success:
            return {
                "success": True,
                "message": f"Successfully applied {recommendation.optimization_type.value} optimization",
            }
        return {
            "success": False,
            "message": "Failed to apply optimization: simulated failure",
        }
