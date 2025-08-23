#!/usr/bin/env python3
"""
Demo script showing the khive performance monitoring infrastructure.
This demonstrates the key features without platform-specific issues.
"""

from datetime import datetime
from pathlib import Path

from src.khive.services.performance import (BenchmarkResult, BenchmarkStorage,
                                            PerformanceAnalyzer,
                                            PerformanceMetrics,
                                            PerformanceReporter)


def create_sample_benchmarks(storage: BenchmarkStorage) -> None:
    """Create sample benchmark results for demonstration."""

    print("📊 Creating sample benchmark data...")

    # Simulate different types of operations with varying performance
    test_scenarios = [
        ("cache_operations", "read", 0.005, 1000, 995),  # Fast cache reads
        ("cache_operations", "write", 0.008, 500, 495),  # Cache writes
        ("database_query", "simple", 0.025, 200, 200),  # Simple DB queries
        ("database_query", "complex", 0.150, 50, 48),  # Complex queries
        ("file_processing", "small", 0.012, 300, 298),  # Small files
        ("file_processing", "large", 0.095, 25, 24),  # Large files
        ("api_calls", "internal", 0.018, 150, 148),  # Internal APIs
        ("api_calls", "external", 0.250, 40, 35),  # External APIs
    ]

    for name, op_type, avg_duration, ops_count, success_count in test_scenarios:
        # Create metrics with realistic variation
        import random

        duration_variation = random.uniform(0.8, 1.2)
        actual_duration = avg_duration * duration_variation

        # Add some memory usage patterns
        base_memory = 50.0
        memory_usage = base_memory + random.uniform(5, 25)

        metrics = PerformanceMetrics(
            duration=actual_duration,
            operations_count=ops_count,
            success_count=success_count,
            error_count=ops_count - success_count,
            memory_start_mb=base_memory,
            memory_peak_mb=memory_usage,
            memory_end_mb=base_memory + 2.0,
            memory_delta_mb=2.0,
            cpu_percent_avg=random.uniform(15, 45),
            cpu_percent_peak=random.uniform(50, 85),
        )

        # Create benchmark result
        result = BenchmarkResult(
            benchmark_name=name,
            operation_type=op_type,
            timestamp=datetime.now(),
            metrics=metrics,
            tags=[name.split("_")[0], op_type],
            metadata={
                "test_run": True,
                "complexity": "high" if avg_duration > 0.1 else "low",
                "priority": "critical" if "database" in name else "normal",
            },
            environment={
                "python_version": "3.10",
                "platform": "demo",
                "memory_total_gb": 16.0,
            },
        )

        # Store the result
        storage_id = storage.store_result(result)
        print(
            f"  ✅ Stored {name}.{op_type}: {storage_id} "
            f"({ops_count} ops, {actual_duration:.3f}s, "
            f"{metrics.success_rate:.1%} success)"
        )


def demonstrate_analysis(storage: BenchmarkStorage) -> None:
    """Demonstrate performance analysis capabilities."""

    print("\n🔍 Performance Analysis:")

    analyzer = PerformanceAnalyzer(storage)

    # Get all results for analysis
    all_results = storage.get_results()
    print(f"  📈 Total benchmark results: {len(all_results)}")

    # Analyze duration metric
    if all_results:
        duration_analysis = analyzer.analyze_metric(
            results=all_results, metric_name="duration"
        )

        if "error" not in duration_analysis:
            print("  ⏱️  Duration Analysis:")
            print(f"     • Mean: {duration_analysis['mean']:.3f}s")
            print(f"     • Median: {duration_analysis['median']:.3f}s")
            print(
                f"     • Range: {duration_analysis['min']:.3f}s - {duration_analysis['max']:.3f}s"
            )
            print(f"     • Sample size: {duration_analysis['sample_size']}")

        # Analyze memory usage
        memory_analysis = analyzer.analyze_metric(
            results=all_results, metric_name="memory_peak_mb"
        )

        if "error" not in memory_analysis:
            print("  💾 Memory Analysis:")
            print(f"     • Peak memory - Mean: {memory_analysis['mean']:.1f}MB")
            print(f"     • Peak memory - Max: {memory_analysis['max']:.1f}MB")

    # Get storage summary
    summary = storage.get_summary()
    print("  📊 Storage Summary:")
    print(f"     • Unique benchmarks: {summary['total_benchmarks']}")

    if summary.get("summaries"):
        for bench_summary in summary["summaries"][:3]:  # Show top 3
            print(
                f"     • {bench_summary['benchmark_name']}.{bench_summary['operation_type']}: "
                f"avg {bench_summary['avg_duration']:.3f}s "
                f"({bench_summary['result_count']} runs)"
            )


def demonstrate_reporting(storage: BenchmarkStorage) -> None:
    """Demonstrate performance reporting capabilities."""

    print("\n📋 Performance Reporting:")

    reporter = PerformanceReporter(storage)

    try:
        # Generate comprehensive report
        report_path = reporter.generate_comprehensive_report(
            report_name="khive_demo_performance",
            days_back=1,
            include_recommendations=True,
        )

        print(f"  ✅ Generated comprehensive report: {report_path}")

        # Show report file size
        if Path(report_path).exists():
            size_kb = Path(report_path).stat().st_size / 1024
            print(f"     • Report size: {size_kb:.1f} KB")

    except Exception as e:
        print(f"  ⚠️  Report generation: {e}")


def demonstrate_storage_features(storage: BenchmarkStorage) -> None:
    """Demonstrate storage and retrieval features."""

    print("\n💾 Storage Features:")

    # Get storage information
    info = storage.get_storage_info()
    print("  📁 Storage Info:")
    print(f"     • Total results: {info['total_results']}")
    print(f"     • Unique benchmarks: {info['unique_benchmarks']}")
    print(f"     • Database size: {info['database_size_mb']:.2f} MB")
    print(f"     • Storage path: {info['storage_path']}")

    # Test baseline retrieval
    baseline = storage.get_baseline("cache_operations", "read")
    if baseline:
        print("  🎯 Latest cache_operations.read baseline:")
        print(f"     • Duration: {baseline.metrics.duration:.3f}s")
        print(
            f"     • Throughput: {baseline.metrics.throughput_ops_per_sec:.1f} ops/sec"
        )
        print(f"     • Success rate: {baseline.metrics.success_rate:.1%}")

    # Test filtered retrieval
    cache_results = storage.get_results(benchmark_name="cache_operations")
    print(f"  🔍 Cache operations results: {len(cache_results)} found")


def main():
    """Main demonstration function."""

    print("🚀 khive Performance Monitoring Infrastructure Demo")
    print("=" * 60)

    # Set up storage in temporary location
    demo_storage_path = Path(".khive/performance/demo")
    storage = BenchmarkStorage(demo_storage_path)

    try:
        # 1. Create sample data
        create_sample_benchmarks(storage)

        # 2. Demonstrate analysis
        demonstrate_analysis(storage)

        # 3. Demonstrate storage features
        demonstrate_storage_features(storage)

        # 4. Demonstrate reporting
        demonstrate_reporting(storage)

        print("\n✨ Demo completed successfully!")
        print(f"📁 Demo data stored in: {demo_storage_path}")
        print(f"🧹 You can clean up with: rm -rf {demo_storage_path}")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
