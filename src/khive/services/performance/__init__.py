"""Performance benchmarking and analysis service."""

from .analysis import (BottleneckIdentifier, PerformanceAnalyzer,
                       RegressionDetector, TrendAnalyzer)
from .benchmark_framework import (BenchmarkFramework, BenchmarkResult,
                                  BenchmarkSuite, PerformanceMetrics)
from .optimization import OptimizationRecommender, PerformanceTuner
from .reporting import CIIntegration, PerformanceReporter
from .storage import BenchmarkStorage, PerformanceDatabase
from .visualization import DashboardGenerator, PerformanceVisualizer

__all__ = [
    # Core framework
    "BenchmarkFramework",
    "BenchmarkResult",
    "BenchmarkSuite",
    "PerformanceMetrics",
    # Storage
    "BenchmarkStorage",
    "PerformanceDatabase",
    # Analysis
    "PerformanceAnalyzer",
    "TrendAnalyzer",
    "RegressionDetector",
    "BottleneckIdentifier",
    # Visualization
    "PerformanceVisualizer",
    "DashboardGenerator",
    # Optimization
    "OptimizationRecommender",
    "PerformanceTuner",
    # Reporting
    "PerformanceReporter",
    "CIIntegration",
]
