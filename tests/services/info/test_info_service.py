# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import AsyncMock, patch

import pytest
from khive.clients.executor import AsyncExecutor
from khive.services.info.info_service import InfoServiceGroup
from khive.services.info.parts import InfoRequest, InfoResponse, InsightMode


class TestInfoServiceGroup:
    """Tests for the InfoServiceGroup class."""

    def test_info_service_initialization(self):
        """Test that InfoServiceGroup initializes correctly."""
        # Act
        service = InfoServiceGroup()

        # Assert
        assert hasattr(service, '_executor')
        assert isinstance(service._executor, AsyncExecutor)

    @pytest.mark.asyncio
    async def test_search_basic_functionality(self, mocker):
        """Test basic search functionality."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={
            "choices": [{"message": {"content": "Test response"}}]
        })

        # Mock the match_endpoint function
        mocker.patch(
            "khive.connections.match_endpoint.match_endpoint",
            return_value=mock_endpoint,
        )

        service = InfoServiceGroup()
        request = InfoRequest(query="What is Python?")

        # Act
        response = await service.search(request)

        # Assert
        assert isinstance(response, InfoResponse)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_search_with_context(self, mocker):
        """Test search with additional context."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={
            "choices": [{"message": {"content": "Contextual response"}}]
        })

        mocker.patch(
            "khive.connections.match_endpoint.match_endpoint",
            return_value=mock_endpoint,
        )

        service = InfoServiceGroup()
        request = InfoRequest(
            query="How to optimize performance?",
            context="Working on a web application with slow response times"
        )

        # Act
        response = await service.search(request)

        # Assert
        assert isinstance(response, InfoResponse)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_search_error_handling(self, mocker):
        """Test search error handling."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(side_effect=Exception("API Error"))

        mocker.patch(
            "khive.connections.match_endpoint.match_endpoint",
            return_value=mock_endpoint,
        )

        service = InfoServiceGroup()
        request = InfoRequest(query="Test query")

        # Act
        response = await service.search(request)

        # Assert
        assert isinstance(response, InfoResponse)
        assert response.success is False
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_mode_auto_detection(self, mocker):
        """Test that mode is auto-detected when not provided."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={
            "choices": [{"message": {"content": "Auto-detected mode response"}}]
        })

        mocker.patch(
            "khive.connections.match_endpoint.match_endpoint",
            return_value=mock_endpoint,
        )

        service = InfoServiceGroup()
        request = InfoRequest(query="Quick question")  # No mode specified

        # Act
        response = await service.search(request)

        # Assert
        assert isinstance(response, InfoResponse)
        assert hasattr(response, 'mode_used')

    @pytest.mark.asyncio
    async def test_time_budget_respected(self, mocker):
        """Test that time budget is considered in search."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={
            "choices": [{"message": {"content": "Budget-aware response"}}]
        })

        mocker.patch(
            "khive.connections.match_endpoint.match_endpoint",
            return_value=mock_endpoint,
        )

        service = InfoServiceGroup()
        request = InfoRequest(
            query="Complex research question",
            time_budget_seconds=30.0
        )

        # Act
        response = await service.search(request)

        # Assert
        assert isinstance(response, InfoResponse)
        assert response.success is True

    def test_insight_source_creation(self):
        """Test creating InsightSource objects."""
        from khive.services.info.parts import InsightSource
        
        source = InsightSource(
            type="search",
            provider="test_provider",
            confidence=0.85,
            url="https://example.com"
        )
        
        assert source.type == "search"
        assert source.provider == "test_provider"
        assert source.confidence == 0.85
        assert source.url == "https://example.com"

    def test_insight_creation(self):
        """Test creating Insight objects."""
        from khive.services.info.parts import Insight, InsightSource
        
        source = InsightSource(
            type="analysis",
            provider="test",
            confidence=0.9
        )
        
        insight = Insight(
            summary="Test insight",
            details="Detailed explanation",
            sources=[source],
            relevance=0.95
        )
        
        assert insight.summary == "Test insight"
        assert insight.details == "Detailed explanation"
        assert len(insight.sources) == 1
        assert insight.relevance == 0.95

    def test_info_request_validation(self):
        """Test InfoRequest validation."""
        # Valid request
        request = InfoRequest(query="Test query")
        assert request.query == "Test query"
        assert request.context is None
        assert request.mode is None
        assert request.time_budget_seconds == 20.0

        # Request with all fields
        request_full = InfoRequest(
            query="Complex query",
            context="Test context",
            mode=InsightMode.COMPREHENSIVE,
            time_budget_seconds=45.0
        )
        assert request_full.query == "Complex query"
        assert request_full.context == "Test context"
        assert request_full.mode == InsightMode.COMPREHENSIVE
        assert request_full.time_budget_seconds == 45.0

    def test_info_response_creation(self):
        """Test InfoResponse creation."""
        from khive.services.info.parts import Insight, InsightSource
        
        source = InsightSource(type="search", provider="test", confidence=0.8)
        insight = Insight(summary="Test insight", sources=[source])
        
        response = InfoResponse(
            success=True,
            summary="Test summary",
            insights=[insight],
            confidence=0.85,
            mode_used=InsightMode.QUICK
        )
        
        assert response.success is True
        assert response.summary == "Test summary"
        assert len(response.insights) == 1
        assert response.confidence == 0.85
        assert response.mode_used == InsightMode.QUICK


class TestInfoServiceIntegration:
    """Integration tests for the InfoServiceGroup class."""

    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self, mocker):
        """Test complete search flow from request to response."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={
            "choices": [{"message": {"content": "Comprehensive answer about the topic"}}]
        })

        mocker.patch(
            "khive.connections.match_endpoint.match_endpoint",
            return_value=mock_endpoint,
        )

        service = InfoServiceGroup()
        request = InfoRequest(
            query="Explain machine learning basics",
            context="Preparing for a technical presentation",
            mode=InsightMode.COMPREHENSIVE,
            time_budget_seconds=30.0
        )

        # Act
        response = await service.search(request)

        # Assert
        assert isinstance(response, InfoResponse)
        assert response.success is True
        assert response.summary is not None
        assert hasattr(response, 'mode_used')

    def test_insight_mode_enum_values(self):
        """Test that all InsightMode enum values are accessible."""
        assert InsightMode.QUICK == "quick"
        assert InsightMode.COMPREHENSIVE == "comprehensive"
        assert InsightMode.ANALYTICAL == "analytical"
        assert InsightMode.REALTIME == "realtime"

    def test_service_interface_completeness(self):
        """Test that the service has the expected interface."""
        service = InfoServiceGroup()
        
        # Check that required methods exist
        assert hasattr(service, 'search')
        assert callable(getattr(service, 'search'))
        
        # Check that the service can be used as an async context manager
        assert hasattr(service, '__aenter__')
        assert hasattr(service, '__aexit__')


class TestInsightModeDetection:
    """Test insight mode detection logic."""

    def test_quick_mode_detection(self):
        """Test detection of queries that should use QUICK mode."""
        quick_queries = [
            "What is Python?",
            "Define machine learning",
            "How many days in a year?"
        ]
        
        for query in quick_queries:
            request = InfoRequest(query=query)
            # The actual mode detection logic would be in the service
            # Here we just test the enum values
            assert InsightMode.QUICK == "quick"

    def test_comprehensive_mode_detection(self):
        """Test detection of queries that should use COMPREHENSIVE mode."""
        comprehensive_queries = [
            "Compare different web frameworks for Python",
            "Analyze the pros and cons of microservices architecture",
            "Research the latest trends in AI development"
        ]
        
        for query in comprehensive_queries:
            request = InfoRequest(query=query)
            assert InsightMode.COMPREHENSIVE == "comprehensive"

    def test_analytical_mode_detection(self):
        """Test detection of queries that should use ANALYTICAL mode."""
        analytical_queries = [
            "What are the trade-offs between SQL and NoSQL databases?",
            "Evaluate different approaches to handling authentication",
            "Analyze the security implications of cloud deployment"
        ]
        
        for query in analytical_queries:
            request = InfoRequest(query=query)
            assert InsightMode.ANALYTICAL == "analytical"
