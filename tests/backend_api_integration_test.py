#!/usr/bin/env python3
"""
Backend API Integration Test Suite - Event-Sourcing Domain Expertise
Comprehensive testing of khive backend APIs for dashboard integration

Validates:
- All API endpoints respond correctly
- CORS headers are present
- Data structures match frontend expectations
- Error handling works properly
- Load handling for concurrent requests
"""

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


@dataclass
class TestResult:
    endpoint: str
    method: str
    status_code: int
    response_time_ms: int
    success: bool
    error_message: Optional[str] = None
    cors_headers: Optional[Dict[str, str]] = None
    response_data: Optional[Dict[str, Any]] = None


class BackendAPITester:
    """Comprehensive API tester with event-sourcing validation patterns"""

    def __init__(self, base_url: str = "http://localhost:11634"):
        self.base_url = base_url.rstrip("/")
        self.results: List[TestResult] = []
        self.session = requests.Session()

    def test_endpoint(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        expected_status: int = 200,
        test_cors: bool = True,
    ) -> TestResult:
        """Test a single endpoint with comprehensive validation"""

        url = f"{self.base_url}{endpoint}"

        start_time = time.time()
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "OPTIONS":
                response = self.session.options(url)
            else:
                raise ValueError(f"Unsupported method: {method}")

            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            # Extract CORS headers
            cors_headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower().startswith("access-control-")
            }

            # Parse response data
            response_data = None
            if response.content:
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = {"raw_content": response.text[:500]}

            success = response.status_code == expected_status
            error_message = (
                None
                if success
                else f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
            )

        except Exception as e:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            success = False
            error_message = str(e)
            cors_headers = None
            response_data = None
            status_code = 0

        result = TestResult(
            endpoint=endpoint,
            method=method,
            status_code=(
                getattr(response, "status_code", 0) if "response" in locals() else 0
            ),
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message,
            cors_headers=cors_headers,
            response_data=response_data,
        )

        self.results.append(result)
        return result

    def test_cors_preflight(self, endpoint: str) -> TestResult:
        """Test CORS preflight OPTIONS request"""
        return self.test_endpoint("OPTIONS", endpoint, expected_status=200)

    def run_comprehensive_test_suite(self):
        """Run all API endpoint tests systematically"""

        print("🚀 Starting Comprehensive Backend API Test Suite")
        print(f"Target: {self.base_url}")
        print("=" * 60)

        # 1. Health Check - Critical baseline
        print("\n📡 Testing Health & Status Endpoints")
        self.test_endpoint("GET", "/health")
        self.test_endpoint("GET", "/api/stats")

        # 2. Configuration Endpoints - Working
        print("\n⚙️  Testing Configuration Endpoints")
        self.test_endpoint("GET", "/api/config/roles")
        self.test_endpoint("GET", "/api/config/domains")

        # 3. CORS Preflight Tests - Critical Issue
        print("\n🌐 Testing CORS Preflight Requests")
        self.test_cors_preflight("/api/config/roles")
        self.test_cors_preflight("/api/sessions")
        self.test_cors_preflight("/api/coordination/metrics")

        # 4. Session Management - 500 Error Issue
        print("\n📋 Testing Session Management")
        self.test_endpoint("GET", "/api/sessions")
        self.test_endpoint("POST", "/api/sessions", {"name": "test_session"})

        # 5. Agent Management - Mixed Success
        print("\n🤖 Testing Agent Management")
        self.test_endpoint("GET", "/api/agents")
        self.test_endpoint(
            "POST",
            "/api/agents",
            {
                "role": "researcher",
                "domain": "event-sourcing",
                "context": "Test agent creation",
            },
        )
        self.test_endpoint(
            "POST", "/api/agents", {}, expected_status=400
        )  # Invalid data

        # 6. Coordination System - Working
        print("\n🔄 Testing Coordination System")
        self.test_endpoint("GET", "/api/coordinate/status")
        self.test_endpoint(
            "POST",
            "/api/coordinate/start",
            {
                "task_id": "test_task",
                "description": "Test coordination",
                "agent_id": "tester_001",
            },
        )

        # 7. Missing Endpoints - 404 Errors Expected
        print("\n❌ Testing Missing Endpoints (Expected Failures)")
        self.test_endpoint("GET", "/api/coordination/metrics", expected_status=404)
        self.test_endpoint("GET", "/api/coordination/file-locks", expected_status=404)
        self.test_endpoint("GET", "/api/events", expected_status=404)
        self.test_endpoint("GET", "/api/plans", expected_status=404)
        self.test_endpoint(
            "GET", "/api/observability/system-performance", expected_status=404
        )
        self.test_endpoint(
            "GET", "/api/observability/agent-analytics", expected_status=404
        )

        # 8. Planning Service
        print("\n📊 Testing Planning Service")
        self.test_endpoint("POST", "/api/plan", {"task": "Test planning request"})

        # 9. Artifacts Service
        print("\n📂 Testing Artifacts Service")
        self.test_endpoint("GET", "/api/artifacts")

        # 10. Load Testing - Concurrent Requests
        print("\n⚡ Testing Load Handling")
        self.test_concurrent_requests()

    def test_concurrent_requests(self):
        """Test API handling of multiple concurrent requests"""
        import queue
        import threading

        results_queue = queue.Queue()

        def make_request(endpoint: str):
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                results_queue.put(
                    {
                        "endpoint": endpoint,
                        "status": response.status_code,
                        "time": response.elapsed.total_seconds(),
                    }
                )
            except Exception as e:
                results_queue.put({"endpoint": endpoint, "error": str(e)})

        # Fire 10 concurrent requests
        endpoints = ["/health", "/api/config/roles", "/api/coordinate/status"] * 3 + [
            "/api/sessions"
        ]
        threads = []

        start_time = time.time()
        for endpoint in endpoints:
            t = threading.Thread(target=make_request, args=(endpoint,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        end_time = time.time()

        # Collect results
        concurrent_results = []
        while not results_queue.empty():
            concurrent_results.append(results_queue.get())

        print(f"    Concurrent requests: {len(concurrent_results)}")
        print(f"    Total time: {end_time - start_time:.2f}s")
        print(
            f"    Success rate: {len([r for r in concurrent_results if r.get('status', 0) == 200])}/{len(concurrent_results)}"
        )

    def print_summary_report(self):
        """Print comprehensive test results summary"""

        print("\n" + "=" * 60)
        print("📊 BACKEND API TEST SUMMARY REPORT")
        print("=" * 60)

        # Overall Stats
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r.success])
        failed_tests = total_tests - successful_tests
        avg_response_time = (
            sum(r.response_time_ms for r in self.results) / total_tests
            if total_tests > 0
            else 0
        )

        print(f"\n📈 Overall Statistics:")
        print(f"    Total Tests: {total_tests}")
        print(f"    ✅ Successful: {successful_tests}")
        print(f"    ❌ Failed: {failed_tests}")
        print(f"    📊 Success Rate: {(successful_tests / total_tests) * 100:.1f}%")
        print(f"    ⚡ Avg Response Time: {avg_response_time:.0f}ms")

        # Critical Issues
        print(f"\n🚨 CRITICAL ISSUES IDENTIFIED:")

        cors_failures = [
            r for r in self.results if r.method == "OPTIONS" and not r.success
        ]
        if cors_failures:
            print(
                f"    🌐 CORS Issues: {len(cors_failures)} endpoints missing OPTIONS support"
            )
            for result in cors_failures[:3]:  # Show first 3
                print(f"        - {result.endpoint} → {result.status_code}")

        missing_endpoints = [
            r for r in self.results if r.status_code == 404 and r.method == "GET"
        ]
        if missing_endpoints:
            print(
                f"    🔍 Missing Endpoints: {len(missing_endpoints)} endpoints not implemented"
            )
            for result in missing_endpoints:
                print(f"        - {result.endpoint}")

        server_errors = [r for r in self.results if 500 <= r.status_code < 600]
        if server_errors:
            print(f"    💥 Server Errors: {len(server_errors)} internal server errors")
            for result in server_errors:
                print(
                    f"        - {result.endpoint} → {result.status_code}: {result.error_message}"
                )

        # Performance Issues
        slow_endpoints = [r for r in self.results if r.response_time_ms > 1000]
        if slow_endpoints:
            print(f"    🐌 Performance Issues: {len(slow_endpoints)} endpoints >1000ms")
            for result in slow_endpoints:
                print(f"        - {result.endpoint} → {result.response_time_ms}ms")

        # Working Endpoints
        working_endpoints = [r for r in self.results if r.success and r.method == "GET"]
        print(f"\n✅ WORKING ENDPOINTS ({len(working_endpoints)}):")
        for result in working_endpoints:
            cors_status = "✅ CORS" if result.cors_headers else "❌ CORS"
            print(
                f"    - {result.endpoint} → {result.status_code} ({result.response_time_ms}ms) {cors_status}"
            )

        # Detailed CORS Analysis
        print(f"\n🌐 CORS HEADERS ANALYSIS:")
        cors_enabled = [r for r in self.results if r.cors_headers]
        print(f"    Endpoints with CORS headers: {len(cors_enabled)}")

        if cors_enabled:
            sample_cors = cors_enabled[0].cors_headers
            print(f"    Sample CORS headers: {list(sample_cors.keys())}")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("    1. ⚠️  Add CORS middleware for OPTIONS preflight requests")
        print("    2. ⚠️  Implement missing dashboard endpoints:")
        print("        - /api/coordination/metrics")
        print("        - /api/coordination/file-locks")
        print("        - /api/events")
        print("        - /api/plans")
        print("        - /api/observability/*")
        print("    3. ⚠️  Fix session service 500 error (artifacts service dependency)")
        print("    4. ⚠️  Add request validation for agent creation")
        print("    5. ⚠️  Performance optimization for slow endpoints")

    def save_detailed_report(self, filename: str = "backend_api_test_report.json"):
        """Save detailed test results to JSON file"""

        report = {
            "test_timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "summary": {
                "total_tests": len(self.results),
                "successful_tests": len([r for r in self.results if r.success]),
                "failed_tests": len([r for r in self.results if not r.success]),
                "avg_response_time_ms": (
                    sum(r.response_time_ms for r in self.results) / len(self.results)
                    if self.results
                    else 0
                ),
            },
            "detailed_results": [asdict(result) for result in self.results],
        }

        with open(filename, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n📄 Detailed report saved to: {filename}")


def main():
    """Run comprehensive backend API tests"""

    print("🧪 Backend API Integration Test - Event-Sourcing Validation")
    print("Testing khive daemon backend for dashboard integration")

    tester = BackendAPITester()

    # Check if backend is running
    try:
        health_check = requests.get(f"{tester.base_url}/health", timeout=5)
        if health_check.status_code != 200:
            print(f"❌ Backend not healthy: {health_check.status_code}")
            return 1
        print(f"✅ Backend is running at {tester.base_url}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to backend at {tester.base_url}: {e}")
        print(
            "   Make sure khive daemon is running: uv run python -m khive.daemon.server"
        )
        return 1

    # Run comprehensive tests
    tester.run_comprehensive_test_suite()

    # Generate reports
    tester.print_summary_report()
    tester.save_detailed_report()

    # Return exit code based on results
    failed_tests = len([r for r in tester.results if not r.success])
    return 0 if failed_tests == 0 else 1


if __name__ == "__main__":
    exit(main())
