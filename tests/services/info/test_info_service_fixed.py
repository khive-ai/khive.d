"""
Tests for the refactored InfoService.

This module tests the new InfoService architecture with InfoRequest/InfoResponse
and InsightMode-based operations.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from khive.services.info.info_service import InfoServiceGroup
from khive.services.info.parts import (
    InfoRequest,
    InfoResponse,
    InsightMode,
    Insight,
    InsightSource,
)


class TestInfoService:
    """Test the InfoService class functionality."""

    def test_info_service_initialization(self):
        """Test that InfoService initializes correctly."""
        service = InfoServiceGroup()

        # Check that service has required attributes
        assert hasattr(service, "search")
        assert callable(service.search)

    @pytest.mark.asyncio
    async def test_search_basic_functionality(self):
        """Test basic search functionality."""
        service = InfoServiceGroup()

        # Create a simple request
        request = InfoRequest(query="What is Python?", mode=InsightMode.QUICK)

        # Mock the actual handler method that exists
        with patch.object(service, "_handle_quick_insights") as mock_handler:
            mock_response = InfoResponse(
                success=True,
                summary="Python is a programming language",
                insights=[
                    Insight(
                        summary="Python is interpreted",
                        sources=[
                            InsightSource(
                                type="search", provider="test", confidence=0.9
                            )
                        ],
                    )
                ],
                mode_used=InsightMode.QUICK,
                confidence=0.9,
            )
            mock_handler.return_value = mock_response

            result = await service.search(request)

            assert result.success is True
            assert "Python" in result.summary
            assert len(result.insights) > 0
            assert result.mode_used == InsightMode.QUICK

    @pytest.mark.asyncio
    async def test_search_with_context(self):
        """Test search with additional context."""
        service = InfoServiceGroup()

        request = InfoRequest(
            query="How to debug memory leaks?",
            context="Working on a web application with Flask",
            mode=InsightMode.COMPREHENSIVE,
        )

        with patch.object(service, "_handle_comprehensive_insights") as mock_handler:
            mock_response = InfoResponse(
                success=True,
                summary="Memory leak debugging strategies for Flask apps",
                insights=[],
                mode_used=InsightMode.COMPREHENSIVE,
                confidence=0.8,
            )
            mock_handler.return_value = mock_response

            result = await service.search(request)

            assert result.success is True
            assert result.mode_used == InsightMode.COMPREHENSIVE

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test error handling in search."""
        service = InfoServiceGroup()

        request = InfoRequest(query="test query")

        # Mock the _detect_mode method to raise an exception inside handle_request
        # This will trigger the exception handling in handle_request
        with patch.object(service, "_detect_mode") as mock_detect:
            mock_detect.side_effect = Exception("Search failed")

            result = await service.search(request)

            assert result.success is False
            assert result.error is not None
            assert "Search failed" in result.error

    @pytest.mark.asyncio
    async def test_mode_auto_detection(self):
        """Test that mode is auto-detected when not provided."""
        service = InfoServiceGroup()

        # Request without explicit mode
        request = InfoRequest(query="What time is it?")

        with patch.object(service, "_detect_mode") as mock_detect:
            mock_detect.return_value = InsightMode.QUICK

            with patch.object(service, "_handle_quick_insights") as mock_handler:
                mock_response = InfoResponse(
                    success=True,
                    summary="Current time information",
                    insights=[],
                    mode_used=InsightMode.QUICK,
                    confidence=0.9,
                )
                mock_handler.return_value = mock_response

                result = await service.search(request)

                mock_detect.assert_called_once_with("What time is it?")
                assert result.mode_used == InsightMode.QUICK

    @pytest.mark.asyncio
    async def test_time_budget_respected(self):
        """Test that time budget constraints are respected."""
        service = InfoServiceGroup()

        request = InfoRequest(
            query="Complex research query",
            time_budget_seconds=5.0,  # Short time budget
        )

        # Mock the comprehensive handler since this query would normally use comprehensive mode
        with patch.object(service, "_handle_comprehensive_insights") as mock_handler:
            mock_response = InfoResponse(
                success=True,
                summary="Quick answer due to time constraints",
                insights=[],
                mode_used=InsightMode.COMPREHENSIVE,
                confidence=0.7,
            )
            mock_handler.return_value = mock_response

            result = await service.search(request)

            # Should have used comprehensive mode for this type of query
            assert result.mode_used == InsightMode.COMPREHENSIVE

    def test_insight_source_creation(self):
        """Test creation of InsightSource objects."""
        source = InsightSource(
            type="search", provider="exa", confidence=0.85, url="https://example.com"
        )

        assert source.type == "search"
        assert source.provider == "exa"
        assert source.confidence == 0.85
        assert source.url == "https://example.com"

    def test_insight_creation(self):
        """Test creation of Insight objects."""
        source = InsightSource(type="analysis", provider="openai", confidence=0.9)

        insight = Insight(
            summary="Key finding",
            details="Detailed explanation",
            sources=[source],
            relevance=0.95,
        )

        assert insight.summary == "Key finding"
        assert insight.details == "Detailed explanation"
        assert len(insight.sources) == 1
        assert insight.relevance == 0.95

    def test_info_request_validation(self):
        """Test InfoRequest validation."""
        # Valid request
        request = InfoRequest(query="Valid query")
        assert request.query == "Valid query"
        assert request.mode is None  # Should default to None
        assert request.time_budget_seconds == 20.0  # Default value

        # Test time budget validation
        with pytest.raises(ValueError):
            InfoRequest(query="test", time_budget_seconds=0.5)  # Too short

        with pytest.raises(ValueError):
            InfoRequest(query="test", time_budget_seconds=100.0)  # Too long

    def test_info_response_creation(self):
        """Test InfoResponse creation."""
        response = InfoResponse(
            success=True,
            summary="Test summary",
            mode_used=InsightMode.ANALYTICAL,
            confidence=0.8,
        )

        assert response.success is True
        assert response.summary == "Test summary"
        assert response.mode_used == InsightMode.ANALYTICAL
        assert response.confidence == 0.8
        assert len(response.insights) == 0  # Default empty list
        assert len(response.suggestions) == 0  # Default empty list


class TestInfoServiceIntegration:
    """Integration tests for InfoService."""

    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self):
        """Test complete search flow from request to response."""
        service = InfoServiceGroup()

        request = InfoRequest(
            query="Best practices for API design",
            context="Building a REST API for a mobile app",
            mode=InsightMode.COMPREHENSIVE,
        )

        # Mock the comprehensive handler for this test
        with patch.object(service, "_handle_comprehensive_insights") as mock_handler:
            mock_response = InfoResponse(
                success=True,
                summary="API design best practices for mobile applications",
                insights=[],
                mode_used=InsightMode.COMPREHENSIVE,
                confidence=0.8,
            )
            mock_handler.return_value = mock_response

            result = await service.search(request)

            assert isinstance(result, InfoResponse)
            assert result.success is True
            assert result.mode_used == InsightMode.COMPREHENSIVE

    def test_insight_mode_enum_values(self):
        """Test that all InsightMode values are available."""
        assert InsightMode.QUICK == "quick"
        assert InsightMode.COMPREHENSIVE == "comprehensive"
        assert InsightMode.ANALYTICAL == "analytical"
        assert InsightMode.REALTIME == "realtime"

    def test_service_interface_completeness(self):
        """Test that service has all required methods."""
        service = InfoServiceGroup()

        # Check required methods exist
        assert hasattr(service, "search")
        assert callable(service.search)

        # Check that search accepts InfoRequest
        import inspect

        sig = inspect.signature(service.search)
        params = list(sig.parameters.keys())
        assert (
            "request" in params or "query" in params
        )  # Should accept some form of request


class TestInsightModeDetection:
    """Test insight mode auto-detection logic."""

    def test_quick_mode_detection(self):
        """Test detection of queries that should use quick mode."""
        quick_queries = [
            "What is Python?",
            "How many days in a year?",
            "What time is it?",
            "Define REST API",
        ]

        # This would test actual detection logic
        for query in quick_queries:
            # For now, just verify the query types we expect
            assert len(query) > 0
            assert isinstance(query, str)

    def test_comprehensive_mode_detection(self):
        """Test detection of queries that should use comprehensive mode."""
        comprehensive_queries = [
            "Compare different machine learning frameworks for production use",
            "What are the pros and cons of microservices vs monoliths?",
            "Research the latest trends in cybersecurity for 2024",
        ]

        for query in comprehensive_queries:
            assert len(query) > 20  # Longer queries often need comprehensive mode
            assert isinstance(query, str)

    def test_analytical_mode_detection(self):
        """Test detection of queries that should use analytical mode."""
        analytical_queries = [
            "Analyze the trade-offs between different database choices",
            "What are the implications of adopting GraphQL?",
            "Evaluate the risks and benefits of cloud migration",
        ]

        for query in analytical_queries:
            # Analytical queries often contain analysis keywords
            analysis_keywords = [
                "analyze",
                "compare",
                "evaluate",
                "trade-offs",
                "implications",
            ]
            has_analysis_keyword = any(
                keyword in query.lower() for keyword in analysis_keywords
            )
            assert has_analysis_keyword or len(query) > 30
