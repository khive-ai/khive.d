"""Integration tests for khive services.

This module contains comprehensive integration tests that validate cross-system
functionality, external service integration, and end-to-end workflows.

Test Categories:
- Artifacts Service Integration: File system operations, session management
- Cache Service Integration: Redis connectivity and operations
- Planning Service Integration: OpenAI API integration and workflows
- Orchestration Integration: LionAGI workflows and multi-agent coordination
- CLI Integration: End-to-end command execution
- Cross-Service Workflows: Service coordination scenarios
- Error Recovery: Failure handling and recovery paths
- Performance Integration: Load testing and concurrency validation

All integration tests are marked with @pytest.mark.integration and can be run with:
    pytest -m integration

External dependencies (Redis, PostgreSQL) are handled via test fixtures that
provide both real connections for full integration testing and mocks for
isolated testing scenarios.
"""
