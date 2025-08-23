"""Performance data visualization and dashboard generation."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Import plotly for visualization
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    px = None
    make_subplots = None

from .analysis import (BottleneckIdentifier, PerformanceAnalyzer,
                       RegressionDetector, TrendAnalyzer, TrendDirection)
from .benchmark_framework import BenchmarkResult
from .storage import BenchmarkStorage

logger = logging.getLogger(__name__)


class PerformanceVisualizer:
    """Creates performance visualizations and charts."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage
        self.analyzer = PerformanceAnalyzer(storage)
        self.trend_analyzer = TrendAnalyzer(storage)

        if not PLOTLY_AVAILABLE:
            logger.warning(
                "Plotly not available. Visualization features will be limited."
            )

    def create_performance_timeline(
        self,
        benchmark_name: str,
        operation_type: str | None = None,
        metric_name: str = "duration",
        days_back: int = 30,
        title: str | None = None,
    ) -> str | None:
        """Create a timeline chart of performance metrics."""

        if not PLOTLY_AVAILABLE:
            logger.error("Plotly required for timeline visualization")
            return None

        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, since=since
        )

        if not results:
            logger.warning(f"No results found for {benchmark_name}")
            return None

        # Extract data
        timestamps = []
        values = []

        for result in sorted(results, key=lambda r: r.timestamp):
            value = self.analyzer._extract_metric_value(result, metric_name)
            if value is not None:
                timestamps.append(result.timestamp)
                values.append(value)

        if not values:
            logger.warning(f"No valid {metric_name} values found")
            return None

        # Create timeline plot
        fig = go.Figure()

        # Main timeline
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=values,
                mode="lines+markers",
                name=f"{metric_name.replace('_', ' ').title()}",
                line=dict(color="blue", width=2),
                marker=dict(size=6),
            )
        )

        # Add trend line
        if len(values) > 2:
            trend_analysis = self.trend_analyzer.analyze_trend(
                benchmark_name=benchmark_name,
                operation_type=operation_type or "all",
                metric_name=metric_name,
                days_back=days_back,
            )

            if trend_analysis.correlation != 0:
                # Simple linear trend
                x_values = [
                    (ts - timestamps[0]).total_seconds() / 86400 for ts in timestamps
                ]
                trend_values = [
                    trend_analysis.historical_mean + trend_analysis.slope * x
                    for x in x_values
                ]

                color = (
                    "green"
                    if trend_analysis.direction == TrendDirection.IMPROVING
                    else "red"
                )

                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=trend_values,
                        mode="lines",
                        name=f"Trend ({trend_analysis.direction.value})",
                        line=dict(color=color, width=2, dash="dash"),
                        opacity=0.7,
                    )
                )

        # Add mean line
        mean_value = self.analyzer.analyze_metric(results, metric_name)["mean"]
        fig.add_hline(
            y=mean_value,
            line_dash="dot",
            line_color="gray",
            annotation_text=f"Mean: {mean_value:.3f}",
        )

        # Customize layout
        chart_title = (
            title
            or f"{benchmark_name} - {metric_name.replace('_', ' ').title()} Over Time"
        )
        fig.update_layout(
            title=chart_title,
            xaxis_title="Time",
            yaxis_title=metric_name.replace("_", " ").title(),
            hovermode="x unified",
            template="plotly_white",
        )

        # Return HTML
        return fig.to_html(
            include_plotlyjs=True, div_id=f"timeline_{benchmark_name}_{metric_name}"
        )

    def create_performance_comparison(
        self,
        benchmark_names: list[str],
        metric_name: str = "duration",
        operation_type: str | None = None,
        days_back: int = 30,
        chart_type: str = "box",
    ) -> str | None:
        """Create comparison chart between different benchmarks."""

        if not PLOTLY_AVAILABLE:
            logger.error("Plotly required for comparison visualization")
            return None

        since = datetime.now() - timedelta(days=days_back)
        all_data = []

        for benchmark_name in benchmark_names:
            results = self.storage.get_results(
                benchmark_name=benchmark_name,
                operation_type=operation_type,
                since=since,
            )

            values = []
            for result in results:
                value = self.analyzer._extract_metric_value(result, metric_name)
                if value is not None:
                    values.append(value)

            if values:
                all_data.append({"benchmark": benchmark_name, "values": values})

        if not all_data:
            logger.warning("No data found for comparison")
            return None

        fig = go.Figure()

        if chart_type == "box":
            for data in all_data:
                fig.add_trace(
                    go.Box(
                        y=data["values"], name=data["benchmark"], boxpoints="outliers"
                    )
                )

        elif chart_type == "violin":
            for data in all_data:
                fig.add_trace(
                    go.Violin(
                        y=data["values"], name=data["benchmark"], points="outliers"
                    )
                )

        elif chart_type == "histogram":
            for data in all_data:
                fig.add_trace(
                    go.Histogram(
                        x=data["values"], name=data["benchmark"], opacity=0.7, nbinsx=20
                    )
                )

        else:  # bar chart
            means = [statistics.mean(data["values"]) for data in all_data]
            names = [data["benchmark"] for data in all_data]

            fig.add_trace(go.Bar(x=names, y=means, name="Average"))

        fig.update_layout(
            title=f"Performance Comparison - {metric_name.replace('_', ' ').title()}",
            yaxis_title=metric_name.replace("_", " ").title(),
            template="plotly_white",
        )

        return fig.to_html(
            include_plotlyjs=True, div_id=f"comparison_{metric_name}_{chart_type}"
        )

    def create_resource_utilization_dashboard(
        self,
        benchmark_name: str,
        operation_type: str | None = None,
        days_back: int = 7,
    ) -> str | None:
        """Create comprehensive resource utilization dashboard."""

        if not PLOTLY_AVAILABLE:
            logger.error("Plotly required for dashboard visualization")
            return None

        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, since=since
        )

        if not results:
            logger.warning(f"No results found for {benchmark_name}")
            return None

        # Create subplot dashboard
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "CPU Usage",
                "Memory Usage",
                "I/O Operations",
                "Network Activity",
            ),
            vertical_spacing=0.1,
            horizontal_spacing=0.1,
        )

        timestamps = [r.timestamp for r in sorted(results, key=lambda x: x.timestamp)]

        # CPU Usage
        cpu_values = [
            r.metrics.cpu_percent_peak
            for r in sorted(results, key=lambda x: x.timestamp)
        ]
        fig.add_trace(
            go.Scatter(
                x=timestamps, y=cpu_values, name="CPU %", line=dict(color="red")
            ),
            row=1,
            col=1,
        )

        # Memory Usage
        memory_values = [
            r.metrics.memory_peak_mb for r in sorted(results, key=lambda x: x.timestamp)
        ]
        fig.add_trace(
            go.Scatter(
                x=timestamps, y=memory_values, name="Memory MB", line=dict(color="blue")
            ),
            row=1,
            col=2,
        )

        # I/O Operations
        io_read_values = [
            r.metrics.io_read_bytes for r in sorted(results, key=lambda x: x.timestamp)
        ]
        io_write_values = [
            r.metrics.io_write_bytes for r in sorted(results, key=lambda x: x.timestamp)
        ]

        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=io_read_values,
                name="I/O Read",
                line=dict(color="green"),
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=io_write_values,
                name="I/O Write",
                line=dict(color="orange"),
            ),
            row=2,
            col=1,
        )

        # Network Activity
        network_sent = [
            r.metrics.network_sent_bytes
            for r in sorted(results, key=lambda x: x.timestamp)
        ]
        network_recv = [
            r.metrics.network_recv_bytes
            for r in sorted(results, key=lambda x: x.timestamp)
        ]

        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=network_sent,
                name="Network Sent",
                line=dict(color="purple"),
            ),
            row=2,
            col=2,
        )
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=network_recv,
                name="Network Recv",
                line=dict(color="pink"),
            ),
            row=2,
            col=2,
        )

        fig.update_layout(
            title=f"Resource Utilization Dashboard - {benchmark_name}",
            template="plotly_white",
            height=600,
        )

        return fig.to_html(include_plotlyjs=True, div_id=f"dashboard_{benchmark_name}")

    def create_regression_analysis_chart(
        self,
        benchmark_name: str,
        operation_type: str,
        metric_name: str = "duration",
        days_back: int = 30,
    ) -> str | None:
        """Create regression analysis visualization."""

        if not PLOTLY_AVAILABLE:
            logger.error("Plotly required for regression visualization")
            return None

        # Get recent results and baseline
        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, since=since
        )

        if not results:
            return None

        # Get latest result for regression analysis
        latest_result = max(results, key=lambda r: r.timestamp)

        regression_detector = RegressionDetector(self.storage)
        regression_result = regression_detector.detect_regression(
            current_result=latest_result,
            metric_name=metric_name,
            comparison_days=days_back,
        )

        # Extract historical values
        timestamps = []
        values = []

        for result in sorted(results, key=lambda r: r.timestamp):
            value = self.analyzer._extract_metric_value(result, metric_name)
            if value is not None:
                timestamps.append(result.timestamp)
                values.append(value)

        if not values:
            return None

        fig = go.Figure()

        # Historical data
        fig.add_trace(
            go.Scatter(
                x=timestamps[:-1],  # All except latest
                y=values[:-1],
                mode="lines+markers",
                name="Historical",
                line=dict(color="blue"),
                marker=dict(size=4),
            )
        )

        # Latest point (highlighted)
        fig.add_trace(
            go.Scatter(
                x=[timestamps[-1]],
                y=[values[-1]],
                mode="markers",
                name="Current",
                marker=dict(
                    size=12,
                    color="red" if regression_result.regression_detected else "green",
                    symbol="diamond",
                ),
            )
        )

        # Baseline mean
        fig.add_hline(
            y=regression_result.baseline_mean,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Baseline Mean: {regression_result.baseline_mean:.3f}",
        )

        # Regression threshold
        if regression_result.baseline_mean > 0:
            threshold_value = regression_result.baseline_mean * 1.2  # 20% threshold
            fig.add_hline(
                y=threshold_value,
                line_dash="dot",
                line_color="orange",
                annotation_text=f"Regression Threshold: {threshold_value:.3f}",
            )

        # Add annotations
        annotations = []
        if regression_result.regression_detected:
            annotations.append(
                dict(
                    x=timestamps[-1],
                    y=values[-1],
                    text=f"Regression: {regression_result.relative_change:.1f}x slower",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="red",
                    arrowwidth=2,
                    bgcolor="rgba(255,0,0,0.1)",
                    bordercolor="red",
                )
            )

        fig.update_layout(
            title=f"Regression Analysis - {benchmark_name}.{operation_type}",
            xaxis_title="Time",
            yaxis_title=metric_name.replace("_", " ").title(),
            template="plotly_white",
            annotations=annotations,
        )

        return fig.to_html(
            include_plotlyjs=True,
            div_id=f"regression_{benchmark_name}_{operation_type}",
        )

    def create_bottleneck_analysis_chart(
        self, benchmark_name: str, days_back: int = 7
    ) -> str | None:
        """Create bottleneck analysis visualization."""

        if not PLOTLY_AVAILABLE:
            logger.error("Plotly required for bottleneck visualization")
            return None

        bottleneck_identifier = BottleneckIdentifier(self.storage)
        bottlenecks = bottleneck_identifier.identify_bottlenecks(
            benchmark_name=benchmark_name, days_back=days_back
        )

        if not bottlenecks:
            # Create empty chart with message
            fig = go.Figure()
            fig.add_annotation(
                text="No bottlenecks detected",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=20),
            )
            fig.update_layout(
                title=f"Bottleneck Analysis - {benchmark_name}", template="plotly_white"
            )
            return fig.to_html(include_plotlyjs=True)

        # Create bottleneck severity chart
        bottleneck_types = [b.bottleneck_type for b in bottlenecks]
        performance_impacts = [b.performance_impact for b in bottlenecks]
        confidences = [b.confidence * 100 for b in bottlenecks]  # Convert to percentage

        colors = []
        for bottleneck in bottlenecks:
            if bottleneck.severity == "critical":
                colors.append("red")
            elif bottleneck.severity == "high":
                colors.append("orange")
            elif bottleneck.severity == "medium":
                colors.append("yellow")
            else:
                colors.append("green")

        fig = go.Figure()

        # Performance impact bars
        fig.add_trace(
            go.Bar(
                x=bottleneck_types,
                y=performance_impacts,
                name="Performance Impact (%)",
                marker_color=colors,
                text=[f"{impact:.1f}%" for impact in performance_impacts],
                textposition="auto",
            )
        )

        # Confidence line
        fig.add_trace(
            go.Scatter(
                x=bottleneck_types,
                y=confidences,
                mode="lines+markers",
                name="Confidence (%)",
                yaxis="y2",
                line=dict(color="blue", dash="dash"),
                marker=dict(size=8),
            )
        )

        fig.update_layout(
            title=f"Bottleneck Analysis - {benchmark_name}",
            xaxis_title="Bottleneck Type",
            yaxis_title="Performance Impact (%)",
            yaxis2=dict(
                title="Confidence (%)", overlaying="y", side="right", range=[0, 100]
            ),
            template="plotly_white",
        )

        return fig.to_html(include_plotlyjs=True, div_id=f"bottleneck_{benchmark_name}")


class DashboardGenerator:
    """Generates comprehensive performance dashboards."""

    def __init__(
        self,
        storage: BenchmarkStorage,
        output_path: Path = Path("performance_dashboards"),
    ):
        self.storage = storage
        self.output_path = output_path
        self.output_path.mkdir(exist_ok=True)
        self.visualizer = PerformanceVisualizer(storage)

    def generate_benchmark_dashboard(
        self, benchmark_name: str, days_back: int = 30
    ) -> Path:
        """Generate comprehensive dashboard for a specific benchmark."""

        dashboard_html = self._create_dashboard_template(
            title=f"Performance Dashboard - {benchmark_name}",
            benchmark_name=benchmark_name,
        )

        # Get all operation types for this benchmark
        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(benchmark_name=benchmark_name, since=since)
        operation_types = list(set(r.operation_type for r in results))

        charts = []

        # Timeline charts for each operation type
        for op_type in operation_types:
            timeline_chart = self.visualizer.create_performance_timeline(
                benchmark_name=benchmark_name,
                operation_type=op_type,
                days_back=days_back,
                title=f"{benchmark_name} - {op_type} Timeline",
            )
            if timeline_chart:
                charts.append({
                    "title": f"{op_type} Performance Timeline",
                    "content": timeline_chart,
                })

        # Resource utilization dashboard
        resource_dashboard = self.visualizer.create_resource_utilization_dashboard(
            benchmark_name=benchmark_name, days_back=days_back
        )
        if resource_dashboard:
            charts.append({
                "title": "Resource Utilization",
                "content": resource_dashboard,
            })

        # Bottleneck analysis
        bottleneck_chart = self.visualizer.create_bottleneck_analysis_chart(
            benchmark_name=benchmark_name, days_back=days_back
        )
        if bottleneck_chart:
            charts.append({"title": "Bottleneck Analysis", "content": bottleneck_chart})

        # Regression analysis for each operation type
        regression_detector = RegressionDetector(self.storage)
        for op_type in operation_types:
            regression_chart = self.visualizer.create_regression_analysis_chart(
                benchmark_name=benchmark_name,
                operation_type=op_type,
                days_back=days_back,
            )
            if regression_chart:
                charts.append({
                    "title": f"{op_type} Regression Analysis",
                    "content": regression_chart,
                })

        # Generate summary statistics
        summary = self._generate_summary_stats(benchmark_name, days_back)

        # Combine everything into final HTML
        final_html = self._combine_dashboard_elements(
            template=dashboard_html, charts=charts, summary=summary
        )

        # Save dashboard
        dashboard_file = (
            self.output_path
            / f"{benchmark_name}_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )

        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(final_html)

        logger.info(f"Dashboard generated: {dashboard_file}")
        return dashboard_file

    def generate_system_overview_dashboard(self, days_back: int = 30) -> Path:
        """Generate system-wide performance overview dashboard."""

        # Get all unique benchmarks
        since = datetime.now() - timedelta(days=days_back)
        all_results = self.storage.get_results(since=since)
        benchmark_names = list(set(r.benchmark_name for r in all_results))

        if not benchmark_names:
            logger.warning("No benchmark data found for system overview")
            return None

        dashboard_html = self._create_dashboard_template(
            title="System Performance Overview", benchmark_name="System Overview"
        )

        charts = []

        # Performance comparison across benchmarks
        comparison_chart = self.visualizer.create_performance_comparison(
            benchmark_names=benchmark_names[:10],  # Limit to top 10
            days_back=days_back,
            chart_type="box",
        )
        if comparison_chart:
            charts.append({
                "title": "Performance Comparison Across Benchmarks",
                "content": comparison_chart,
            })

        # System-wide bottleneck analysis
        all_bottlenecks = []
        bottleneck_identifier = BottleneckIdentifier(self.storage)

        for benchmark_name in benchmark_names:
            bottlenecks = bottleneck_identifier.identify_bottlenecks(
                benchmark_name=benchmark_name, days_back=days_back
            )
            all_bottlenecks.extend(bottlenecks)

        if all_bottlenecks:
            bottleneck_summary_chart = self._create_system_bottleneck_chart(
                all_bottlenecks
            )
            if bottleneck_summary_chart:
                charts.append({
                    "title": "System-wide Bottleneck Summary",
                    "content": bottleneck_summary_chart,
                })

        # Generate system summary
        system_summary = self._generate_system_summary(all_results, all_bottlenecks)

        # Combine everything
        final_html = self._combine_dashboard_elements(
            template=dashboard_html, charts=charts, summary=system_summary
        )

        # Save dashboard
        dashboard_file = (
            self.output_path
            / f"system_overview_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )

        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(final_html)

        logger.info(f"System overview dashboard generated: {dashboard_file}")
        return dashboard_file

    def _create_dashboard_template(self, title: str, benchmark_name: str) -> str:
        """Create base HTML template for dashboard."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }}
                .summary {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .chart-container {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .chart-title {{
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #333;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    margin-top: 40px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            
            <div class="summary" id="summary-section">
                <!-- Summary will be inserted here -->
            </div>
            
            <div id="charts-section">
                <!-- Charts will be inserted here -->
            </div>
            
            <div class="footer">
                <p>Khive Performance Monitoring Dashboard</p>
            </div>
        </body>
        </html>
        """

    def _generate_summary_stats(
        self, benchmark_name: str, days_back: int
    ) -> dict[str, Any]:
        """Generate summary statistics for a benchmark."""
        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(benchmark_name=benchmark_name, since=since)

        if not results:
            return {"error": "No data available"}

        # Basic stats
        total_runs = len(results)
        operation_types = list(set(r.operation_type for r in results))
        date_range = (
            min(r.timestamp for r in results),
            max(r.timestamp for r in results),
        )

        # Performance analysis
        analyzer = PerformanceAnalyzer(self.storage)
        duration_analysis = analyzer.analyze_metric(results, "duration")
        success_rates = [
            r.metrics.success_rate for r in results if r.metrics.success_rate >= 0
        ]
        avg_success_rate = statistics.mean(success_rates) if success_rates else 0

        # Resource utilization
        memory_peaks = [
            r.metrics.memory_peak_mb for r in results if r.metrics.memory_peak_mb > 0
        ]
        cpu_peaks = [
            r.metrics.cpu_percent_peak
            for r in results
            if r.metrics.cpu_percent_peak > 0
        ]

        return {
            "benchmark_name": benchmark_name,
            "total_runs": total_runs,
            "operation_types": operation_types,
            "date_range": date_range,
            "avg_duration_ms": duration_analysis.get("mean", 0) * 1000,
            "p95_duration_ms": duration_analysis.get("p95", 0) * 1000,
            "avg_success_rate": avg_success_rate * 100,
            "avg_memory_peak_mb": statistics.mean(memory_peaks) if memory_peaks else 0,
            "avg_cpu_peak_percent": statistics.mean(cpu_peaks) if cpu_peaks else 0,
        }

    def _generate_system_summary(
        self, all_results: list[BenchmarkResult], all_bottlenecks: list
    ) -> dict[str, Any]:
        """Generate system-wide summary statistics."""
        if not all_results:
            return {"error": "No system data available"}

        benchmark_names = list(set(r.benchmark_name for r in all_results))
        operation_types = list(set(r.operation_type for r in all_results))

        # System performance metrics
        all_durations = [
            r.metrics.duration for r in all_results if r.metrics.duration > 0
        ]
        all_success_rates = [
            r.metrics.success_rate for r in all_results if r.metrics.success_rate >= 0
        ]

        # Resource utilization across system
        all_memory = [
            r.metrics.memory_peak_mb
            for r in all_results
            if r.metrics.memory_peak_mb > 0
        ]
        all_cpu = [
            r.metrics.cpu_percent_peak
            for r in all_results
            if r.metrics.cpu_percent_peak > 0
        ]

        # Bottleneck summary
        bottleneck_types = [b.bottleneck_type for b in all_bottlenecks]
        bottleneck_counts = {
            bt: bottleneck_types.count(bt) for bt in set(bottleneck_types)
        }

        return {
            "total_benchmarks": len(benchmark_names),
            "total_operation_types": len(operation_types),
            "total_test_runs": len(all_results),
            "avg_system_duration_ms": statistics.mean(all_durations) * 1000
            if all_durations
            else 0,
            "system_success_rate": statistics.mean(all_success_rates) * 100
            if all_success_rates
            else 0,
            "avg_system_memory_mb": statistics.mean(all_memory) if all_memory else 0,
            "avg_system_cpu_percent": statistics.mean(all_cpu) if all_cpu else 0,
            "bottleneck_summary": bottleneck_counts,
            "date_range": (
                min(r.timestamp for r in all_results),
                max(r.timestamp for r in all_results),
            )
            if all_results
            else None,
        }

    def _create_system_bottleneck_chart(self, all_bottlenecks: list) -> str | None:
        """Create system-wide bottleneck summary chart."""
        if not PLOTLY_AVAILABLE or not all_bottlenecks:
            return None

        # Count bottlenecks by type and severity
        bottleneck_data = {}

        for bottleneck in all_bottlenecks:
            key = f"{bottleneck.bottleneck_type}_{bottleneck.severity}"
            if key not in bottleneck_data:
                bottleneck_data[key] = 0
            bottleneck_data[key] += 1

        # Create stacked bar chart
        bottleneck_types = list(set(b.bottleneck_type for b in all_bottlenecks))
        severities = ["low", "medium", "high", "critical"]

        fig = go.Figure()

        for severity in severities:
            values = []
            for bt in bottleneck_types:
                key = f"{bt}_{severity}"
                values.append(bottleneck_data.get(key, 0))

            color_map = {
                "low": "green",
                "medium": "yellow",
                "high": "orange",
                "critical": "red",
            }

            fig.add_trace(
                go.Bar(
                    name=severity.title(),
                    x=bottleneck_types,
                    y=values,
                    marker_color=color_map[severity],
                )
            )

        fig.update_layout(
            title="System-wide Bottleneck Distribution",
            xaxis_title="Bottleneck Type",
            yaxis_title="Count",
            barmode="stack",
            template="plotly_white",
        )

        return fig.to_html(include_plotlyjs=True, div_id="system_bottlenecks")

    def _combine_dashboard_elements(
        self, template: str, charts: list[dict[str, str]], summary: dict[str, Any]
    ) -> str:
        """Combine template, charts, and summary into final dashboard HTML."""

        # Generate summary HTML
        summary_html = self._generate_summary_html(summary)

        # Generate charts HTML
        charts_html = ""
        for chart in charts:
            charts_html += f"""
            <div class="chart-container">
                <div class="chart-title">{chart["title"]}</div>
                {chart["content"]}
            </div>
            """

        # Insert into template
        final_html = template.replace(
            "<!-- Summary will be inserted here -->", summary_html
        )
        final_html = final_html.replace(
            "<!-- Charts will be inserted here -->", charts_html
        )

        return final_html

    def _generate_summary_html(self, summary: dict[str, Any]) -> str:
        """Generate HTML for summary statistics."""
        if "error" in summary:
            return f'<p style="color: red;">Error: {summary["error"]}</p>'

        if "total_benchmarks" in summary:  # System summary
            return f"""
            <h2>System Overview</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                <div><strong>Total Benchmarks:</strong> {summary["total_benchmarks"]}</div>
                <div><strong>Total Test Runs:</strong> {summary["total_test_runs"]}</div>
                <div><strong>Average Duration:</strong> {summary["avg_system_duration_ms"]:.2f} ms</div>
                <div><strong>System Success Rate:</strong> {summary["system_success_rate"]:.1f}%</div>
                <div><strong>Average Memory:</strong> {summary["avg_system_memory_mb"]:.1f} MB</div>
                <div><strong>Average CPU:</strong> {summary["avg_system_cpu_percent"]:.1f}%</div>
            </div>
            <h3>Bottleneck Summary</h3>
            <div>
                {" | ".join([f"{k}: {v}" for k, v in summary["bottleneck_summary"].items()])}
            </div>
            """
        # Benchmark summary
        return f"""
            <h2>Benchmark Summary: {summary["benchmark_name"]}</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                <div><strong>Total Runs:</strong> {summary["total_runs"]}</div>
                <div><strong>Operation Types:</strong> {len(summary["operation_types"])}</div>
                <div><strong>Average Duration:</strong> {summary["avg_duration_ms"]:.2f} ms</div>
                <div><strong>P95 Duration:</strong> {summary["p95_duration_ms"]:.2f} ms</div>
                <div><strong>Success Rate:</strong> {summary["avg_success_rate"]:.1f}%</div>
                <div><strong>Average Memory Peak:</strong> {summary["avg_memory_peak_mb"]:.1f} MB</div>
                <div><strong>Average CPU Peak:</strong> {summary["avg_cpu_peak_percent"]:.1f}%</div>
            </div>
            <p><strong>Operations:</strong> {", ".join(summary["operation_types"])}</p>
            """
