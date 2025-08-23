# CI/CD Integration Design for Automated Performance Regression Detection

## Experimental Validation Results

### Framework Validation
✅ **Regression Detection Test**: Validated statistical regression detection with configurable thresholds  
✅ **Benchmark Storage Test**: Confirmed JSONL-based historical data storage works correctly  
✅ **Statistical Analysis**: Verified trend analysis and confidence scoring functionality  
✅ **Performance Profiler**: Confirmed comprehensive metrics collection with microsecond precision  

### Integration Architecture Design

## GitHub Actions Workflow Enhancement

### Enhanced Performance CI Pipeline

```yaml
# .github/workflows/performance-regression-detection.yml
name: Performance Regression Detection

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily baseline updates

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  performance-baseline:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    outputs:
      baseline-updated: ${{ steps.baseline.outputs.updated }}
    steps:
      - uses: actions/checkout@v4
      - name: Setup Environment
        uses: ./.github/actions/setup-performance-env
      
      - name: Run Baseline Performance Tests
        id: baseline
        run: |
          uv run pytest tests/performance/ \
            -m "benchmark" \
            --benchmark-report=baseline_report.json \
            --baseline-mode=establish \
            --statistical-samples=10
          
          echo "updated=true" >> $GITHUB_OUTPUT
      
      - name: Store Performance Baseline
        run: |
          python scripts/store_performance_baseline.py \
            --report=baseline_report.json \
            --commit-sha=${{ github.sha }} \
            --branch=${{ github.ref_name }}
      
      - name: Upload Baseline Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: performance-baseline-${{ github.sha }}
          path: |
            baseline_report.json
            .khive/performance/benchmarks/

  performance-regression-detection:
    runs-on: ubuntu-latest
    needs: []  # Can run independently
    strategy:
      fail-fast: false
      matrix:
        test-suite: [
          "orchestration",
          "cache", 
          "session",
          "artifacts",
          "integration"
        ]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need history for comparison
      
      - name: Setup Performance Environment  
        uses: ./.github/actions/setup-performance-env
      
      - name: Download Historical Baselines
        run: |
          python scripts/download_baselines.py \
            --days-back=30 \
            --test-suite=${{ matrix.test-suite }}
      
      - name: Run Performance Tests with Regression Detection
        id: perf-test
        run: |
          uv run pytest tests/performance/test_${{ matrix.test-suite }}_performance.py \
            -m "performance" \
            --benchmark-report=perf_report_${{ matrix.test-suite }}.json \
            --regression-detection=true \
            --threshold-config=performance_thresholds.yaml \
            --statistical-confidence=0.95
        continue-on-error: true
      
      - name: Analyze Performance Regressions
        id: analyze
        run: |
          python scripts/analyze_regressions.py \
            --report=perf_report_${{ matrix.test-suite }}.json \
            --test-suite=${{ matrix.test-suite }} \
            --output=regression_analysis_${{ matrix.test-suite }}.json
        
      - name: Generate Performance Dashboard Data
        run: |
          python scripts/update_dashboard_data.py \
            --test-suite=${{ matrix.test-suite }} \
            --report=perf_report_${{ matrix.test-suite }}.json \
            --analysis=regression_analysis_${{ matrix.test-suite }}.json
      
      - name: Check for Critical Regressions
        id: critical-check  
        run: |
          CRITICAL=$(jq '.regressions[] | select(.regression_details.relative_change > 2.0) | length' regression_analysis_${{ matrix.test-suite }}.json || echo "0")
          echo "critical-count=$CRITICAL" >> $GITHUB_OUTPUT
          
          if [ "$CRITICAL" -gt "0" ]; then
            echo "❌ CRITICAL: $CRITICAL critical performance regressions detected in ${{ matrix.test-suite }}"
            exit 1
          fi
      
      - name: Create Regression Issue
        if: failure() && steps.critical-check.outputs.critical-count > 0
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const analysis = JSON.parse(fs.readFileSync('regression_analysis_${{ matrix.test-suite }}.json', 'utf8'));
            
            const critical = analysis.regressions.filter(r => r.regression_details.relative_change > 2.0);
            const moderate = analysis.regressions.filter(r => r.regression_details.relative_change > 1.5 && r.regression_details.relative_change <= 2.0);
            
            const title = `🚨 Performance Regression in ${{ matrix.test-suite }} (${critical.length} critical, ${moderate.length} moderate)`;
            
            let body = `## Performance Regression Detected\n\n`;
            body += `**Test Suite**: ${{ matrix.test-suite }}\n`;
            body += `**Commit**: ${{ github.sha }}\n`;
            body += `**PR**: #${{ github.event.number || 'N/A' }}\n\n`;
            
            if (critical.length > 0) {
              body += `### 🔴 Critical Regressions (>200% degradation)\n\n`;
              critical.forEach(reg => {
                body += `- **${reg.operation_type}**: ${(reg.regression_details.relative_change * 100).toFixed(1)}% slower\n`;
                body += `  - Current: ${reg.regression_details.current_value.toFixed(6)}s\n`;
                body += `  - Historical: ${reg.regression_details.historical_mean.toFixed(6)}s\n\n`;
              });
            }
            
            body += `### 📊 Performance Analysis\n`;
            body += `See detailed analysis in the [workflow run](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})\n`;
            
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: title,
              body: body,
              labels: ['performance', 'regression', 'priority:high']
            });
      
      - name: Upload Performance Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: performance-report-${{ matrix.test-suite }}-${{ github.run_number }}
          path: |
            perf_report_${{ matrix.test-suite }}.json
            regression_analysis_${{ matrix.test-suite }}.json

  performance-dashboard-update:
    runs-on: ubuntu-latest
    needs: [performance-regression-detection]
    if: always()
    steps:
      - uses: actions/checkout@v4
      
      - name: Download All Performance Reports
        uses: actions/download-artifact@v4
        with:
          pattern: performance-report-*-${{ github.run_number }}
          merge-multiple: true
      
      - name: Update Performance Dashboard
        run: |
          python scripts/consolidate_performance_data.py \
            --reports-dir=. \
            --output=consolidated_performance.json
          
          python scripts/update_performance_dashboard.py \
            --data=consolidated_performance.json \
            --commit-sha=${{ github.sha }} \
            --branch=${{ github.ref_name }}
      
      - name: Deploy Dashboard Update
        run: |
          # Deploy to performance monitoring dashboard
          # This could be Streamlit, Plotly Dash, or static GitHub Pages
          python scripts/deploy_dashboard.py \
            --environment=${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}

  performance-summary:
    runs-on: ubuntu-latest  
    needs: [performance-regression-detection]
    if: always()
    steps:
      - name: Generate Performance Summary
        uses: actions/github-script@v7
        with:
          script: |
            const testSuites = ['orchestration', 'cache', 'session', 'artifacts', 'integration'];
            let summary = '## 📊 Performance Test Summary\n\n';
            
            const jobs = await github.rest.actions.listJobsForWorkflowRun({
              owner: context.repo.owner,
              repo: context.repo.repo, 
              run_id: context.runId
            });
            
            const perfJobs = jobs.data.jobs.filter(job => 
              job.name.includes('performance-regression-detection')
            );
            
            let totalRegressions = 0;
            let criticalRegressions = 0;
            
            testSuites.forEach(suite => {
              const job = perfJobs.find(j => j.name.includes(suite));
              if (job) {
                const status = job.conclusion === 'success' ? '✅' : '❌';
                summary += `- **${suite}**: ${status} ${job.conclusion}\n`;
                if (job.conclusion === 'failure') {
                  criticalRegressions++;
                }
              }
            });
            
            summary += `\n**Status**: ${criticalRegressions === 0 ? '✅ No critical regressions' : `❌ ${criticalRegressions} critical regressions detected`}\n`;
            
            // Add to job summary
            await core.summary
              .addRaw(summary)
              .write();
```

### Performance Threshold Configuration

```yaml
# performance_thresholds.yaml
thresholds:
  orchestration:
    simple_operation_ms: 100
    complex_operation_ms: 1000
    memory_limit_mb: 50
    regression_threshold: 1.2  # 20% degradation
    
  cache:
    cache_get_ms: 5
    cache_set_ms: 10
    throughput_ops_per_sec: 1000
    regression_threshold: 1.15  # 15% degradation (more sensitive)
    
  session:
    session_create_ms: 50
    concurrent_sessions: 100
    memory_per_session_mb: 5
    regression_threshold: 1.3   # 30% degradation (less sensitive)
    
  artifacts:
    file_read_ms: 10
    file_write_ms: 25
    memory_limit_mb: 25
    regression_threshold: 1.25  # 25% degradation
    
  integration:
    end_to_end_workflow_ms: 5000
    cross_service_coordination_ms: 2000
    regression_threshold: 1.4   # 40% degradation (complex workflows)

statistical:
  min_samples: 5
  confidence_level: 0.95
  trend_detection_threshold: 0.3
  
alerts:
  critical_threshold: 2.0     # 200% degradation
  moderate_threshold: 1.5     # 150% degradation
  minor_threshold: 1.2        # 120% degradation
```

## Performance Dashboard Integration

### Streamlit Dashboard Implementation

```python
# scripts/performance_dashboard.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json
from datetime import datetime, timedelta

class PerformanceDashboard:
    def __init__(self):
        self.benchmark_storage = Path(".khive/performance/benchmarks")
        
    def load_performance_data(self, days_back=30):
        """Load performance data from the last N days."""
        cutoff = datetime.now() - timedelta(days=days_back)
        
        benchmarks = []
        if self.benchmark_storage.exists():
            with open(self.benchmark_storage / "benchmarks.jsonl") as f:
                for line in f:
                    data = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(data["timestamp"])
                    if timestamp >= cutoff:
                        benchmarks.append(data)
        
        return benchmarks
    
    def render_performance_trends(self, benchmarks):
        """Render performance trend charts."""
        st.header("📊 Performance Trends")
        
        # Group by test suite
        test_suites = {}
        for b in benchmarks:
            suite = b["test_name"]
            if suite not in test_suites:
                test_suites[suite] = {}
            
            op_type = b["operation_type"] 
            if op_type not in test_suites[suite]:
                test_suites[suite][op_type] = []
                
            test_suites[suite][op_type].append({
                "timestamp": b["timestamp"],
                "avg_operation_time": b["metrics"].get("avg_operation_time", 0),
                "memory_usage": b["metrics"].get("memory_usage", 0)
            })
        
        # Create tabs for each test suite
        tabs = st.tabs(list(test_suites.keys()))
        
        for tab, suite_name in zip(tabs, test_suites.keys()):
            with tab:
                suite_data = test_suites[suite_name]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("⏱️ Response Time Trends")
                    
                    fig = go.Figure()
                    for op_type, data in suite_data.items():
                        timestamps = [d["timestamp"] for d in data]
                        times = [d["avg_operation_time"] * 1000 for d in data]  # Convert to ms
                        
                        fig.add_trace(go.Scatter(
                            x=timestamps,
                            y=times,
                            mode='lines+markers',
                            name=op_type,
                            line=dict(width=2)
                        ))
                    
                    fig.update_layout(
                        title=f"{suite_name} - Response Time Trends",
                        xaxis_title="Time",
                        yaxis_title="Response Time (ms)",
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("🧠 Memory Usage Trends")
                    
                    fig = go.Figure()
                    for op_type, data in suite_data.items():
                        timestamps = [d["timestamp"] for d in data]
                        memory = [d["memory_usage"] for d in data if d["memory_usage"] > 0]
                        
                        if memory:
                            fig.add_trace(go.Scatter(
                                x=timestamps[:len(memory)],
                                y=memory,
                                mode='lines+markers',
                                name=op_type,
                                line=dict(width=2)
                            ))
                    
                    fig.update_layout(
                        title=f"{suite_name} - Memory Usage Trends", 
                        xaxis_title="Time",
                        yaxis_title="Memory Usage (MB)",
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

    def render_regression_alerts(self):
        """Render current regression alerts."""
        st.header("🚨 Regression Alerts")
        
        # Load latest regression analysis results
        reports_dir = Path("performance_reports")
        if reports_dir.exists():
            latest_reports = sorted(reports_dir.glob("regression_analysis_*.json"))
            
            if latest_reports:
                critical_count = 0
                moderate_count = 0
                minor_count = 0
                
                for report_file in latest_reports[-5:]:  # Last 5 reports
                    with open(report_file) as f:
                        analysis = json.load(f)
                    
                    for regression in analysis.get("regressions", []):
                        change = regression["regression_details"]["relative_change"]
                        if change > 2.0:
                            critical_count += 1
                        elif change > 1.5:
                            moderate_count += 1
                        elif change > 1.2:
                            minor_count += 1
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🔴 Critical", critical_count, delta=None)
                with col2:
                    st.metric("🟡 Moderate", moderate_count, delta=None) 
                with col3:
                    st.metric("🟠 Minor", minor_count, delta=None)
                    
                if critical_count == 0 and moderate_count == 0 and minor_count == 0:
                    st.success("✅ No performance regressions detected!")
            else:
                st.info("No regression analysis reports found")
        else:
            st.info("Performance reports directory not found")

def main():
    st.set_page_config(
        page_title="Khive Performance Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Khive Performance Monitoring Dashboard")
    st.markdown("Real-time performance metrics and regression detection for the khive system")
    
    dashboard = PerformanceDashboard()
    
    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Controls")
        days_back = st.slider("Days of history", 7, 90, 30)
        auto_refresh = st.checkbox("Auto-refresh (30s)", False)
    
    # Load and display data
    benchmarks = dashboard.load_performance_data(days_back)
    
    if benchmarks:
        dashboard.render_regression_alerts()
        dashboard.render_performance_trends(benchmarks)
        
        # Performance statistics
        st.header("📈 Performance Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Benchmarks", len(benchmarks))
        with col2:
            unique_tests = len(set(b["test_name"] for b in benchmarks))
            st.metric("Test Suites", unique_tests)
        with col3:
            avg_time = sum(b["metrics"].get("avg_operation_time", 0) for b in benchmarks) / len(benchmarks)
            st.metric("Avg Response Time", f"{avg_time*1000:.2f}ms")
        with col4:
            latest = max(benchmarks, key=lambda x: x["timestamp"])
            st.metric("Last Updated", latest["timestamp"][:19])
    else:
        st.warning("No performance data available for the selected time range")
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()
```

## Deployment Strategy

### GitHub Actions Setup Script

```python
# scripts/setup_performance_ci.py
#!/usr/bin/env python3
"""Setup script for performance CI/CD integration."""

import json
import yaml
from pathlib import Path

def create_github_actions_setup():
    """Create GitHub Actions setup action."""
    
    action_yml = {
        "name": "Setup Performance Testing Environment",
        "description": "Setup environment for performance testing with all dependencies",
        "runs": {
            "using": "composite",
            "steps": [
                {
                    "name": "Install uv",
                    "uses": "astral-sh/setup-uv@v4",
                    "with": {"version": "latest"}
                },
                {
                    "name": "Set up Python",
                    "shell": "bash",
                    "run": "uv python install 3.12"
                },
                {
                    "name": "Install dependencies",
                    "shell": "bash", 
                    "run": "uv sync"
                },
                {
                    "name": "Setup performance directories",
                    "shell": "bash",
                    "run": "mkdir -p .khive/performance/{benchmarks,reports,dashboards}"
                },
                {
                    "name": "Install performance monitoring tools",
                    "shell": "bash",
                    "run": "uv add --dev psutil plotly streamlit"
                }
            ]
        }
    }
    
    action_dir = Path(".github/actions/setup-performance-env")
    action_dir.mkdir(parents=True, exist_ok=True)
    
    with open(action_dir / "action.yml", "w") as f:
        yaml.dump(action_yml, f, default_flow_style=False)
    
    print(f"✅ Created GitHub Actions setup at {action_dir}/action.yml")

def create_performance_scripts():
    """Create performance analysis scripts."""
    
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    # Baseline storage script
    baseline_script = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime
from tests.performance.test_benchmark_regression import BenchmarkStorage, PerformanceBenchmark

def store_baseline(report_path: str, commit_sha: str, branch: str):
    storage = BenchmarkStorage()
    
    with open(report_path) as f:
        report = json.load(f)
    
    for test_name, test_data in report.get("test_results", {}).items():
        for operation_type, metrics in test_data.items():
            benchmark = PerformanceBenchmark(
                test_name=test_name,
                operation_type=operation_type,
                timestamp=datetime.now(),
                metrics=metrics,
                metadata={
                    "commit_sha": commit_sha,
                    "branch": branch,
                    "baseline": True,
                    "ci_run": True
                }
            )
            storage.save_benchmark(benchmark)
    
    print(f"✅ Stored baseline for {len(report.get('test_results', {}))} test suites")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    
    store_baseline(args.report, args.commit_sha, args.branch)
"""
    
    with open(scripts_dir / "store_performance_baseline.py", "w") as f:
        f.write(baseline_script)
    
    # Regression analysis script
    analysis_script = """#!/usr/bin/env python3
import json
from pathlib import Path
from tests.performance.test_benchmark_regression import (
    BenchmarkStorage, RegressionDetector, BenchmarkReporter
)

def analyze_regressions(report_path: str, test_suite: str, output_path: str):
    storage = BenchmarkStorage()
    detector = RegressionDetector(
        regression_threshold=1.2,
        min_samples=5,
        statistical_confidence=0.95
    )
    
    with open(report_path) as f:
        report = json.load(f)
    
    # Analyze each test in the suite
    analysis_results = {
        "test_suite": test_suite,
        "generated_at": datetime.now().isoformat(), 
        "regressions": [],
        "recommendations": []
    }
    
    for test_name, test_metrics in report.get("test_results", {}).items():
        historical_benchmarks = storage.load_benchmarks(
            test_name=test_name, days_back=30
        )
        
        for operation_type, metrics in test_metrics.items():
            regression_result = detector.detect_regression(
                current_metrics=metrics,
                historical_benchmarks=[
                    b for b in historical_benchmarks
                    if b.operation_type == operation_type
                ]
            )
            
            if regression_result["regression_detected"]:
                analysis_results["regressions"].append({
                    "test_name": test_name,
                    "operation_type": operation_type,
                    "regression_details": regression_result
                })
    
    # Generate recommendations
    regression_count = len(analysis_results["regressions"])
    critical_count = len([r for r in analysis_results["regressions"]
                         if r["regression_details"]["relative_change"] > 2.0])
    
    if critical_count > 0:
        analysis_results["recommendations"].append(
            f"CRITICAL: {critical_count} critical performance regressions require immediate attention"
        )
    elif regression_count > 0:
        analysis_results["recommendations"].append(
            f"Monitor: {regression_count} performance regressions detected"
        )
    else:
        analysis_results["recommendations"].append(
            "Performance is stable - no regressions detected"
        )
    
    with open(output_path, "w") as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"✅ Analysis complete: {regression_count} regressions found")
    return analysis_results

if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--test-suite", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    analyze_regressions(args.report, args.test_suite, args.output)
"""
    
    with open(scripts_dir / "analyze_regressions.py", "w") as f:
        f.write(analysis_script)
    
    # Make scripts executable
    for script in scripts_dir.glob("*.py"):
        script.chmod(0o755)
    
    print(f"✅ Created performance analysis scripts in {scripts_dir}")

def main():
    print("🚀 Setting up Performance CI/CD Integration...")
    
    create_github_actions_setup()
    create_performance_scripts()
    
    print("✅ Performance CI/CD integration setup complete!")
    print("\nNext steps:")
    print("1. Commit the new GitHub Actions workflow and scripts")
    print("2. Push to trigger the first baseline establishment")
    print("3. Monitor performance dashboard for regression detection")

if __name__ == "__main__":
    main()
"""
    
    with open("setup_performance_ci.py", "w") as f:
        f.write(setup_script)
    
    Path("setup_performance_ci.py").chmod(0o755)
    print("✅ Created setup_performance_ci.py")

## Summary

This comprehensive CI/CD integration design provides:

1. **Automated Baseline Establishment**: Daily baseline updates on main branch
2. **Statistical Regression Detection**: 95% confidence level with trend analysis
3. **Multi-Suite Testing**: Parallel execution across orchestration, cache, session, artifacts, and integration suites
4. **Intelligent Alerting**: Critical/moderate/minor regression classification with automatic GitHub issue creation
5. **Real-time Dashboard**: Streamlit-based performance monitoring with trend visualization
6. **Threshold Management**: Configurable per-service thresholds with statistical validation

The integration leverages the existing robust performance testing framework while adding comprehensive CI/CD automation for continuous performance monitoring.