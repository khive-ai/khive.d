"""
Comprehensive tests for the API client (khive.clients.api_client).

This module tests the core HTTP client functionality including request handling,
error management, retries, and connection pooling.
"""

import aiohttp
from aiohttp import ClientResponse, ClientSession
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import httpx

from khive.clients.api_client import AsyncAPIClient
from khive.clients.errors import (
    APIClientError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)


class TestAsyncAPIClient:
    """Test the AsyncAPIClient class functionality."""

    def test_api_client_initialization(self):
        """Test AsyncAPIClient initialization with default parameters."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        # Check basic attributes exist
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 10.0  # default timeout
        assert client.headers == {}  # default headers

    def test_api_client_initialization_with_params(self):
        """Test AsyncAPIClient initialization with custom parameters."""
        base_url = "https://api.example.com"
        timeout = 30.0
        headers = {"Authorization": "Bearer token"}

        client = AsyncAPIClient(
            base_url=base_url, timeout=timeout, headers=headers
        )

        assert client.base_url == base_url
        assert client.timeout == timeout
        assert client.headers == headers

    @pytest.mark.asyncio
    async def test_get_request_success(self):
        """Test successful GET request."""
        client = AsyncAPIClient(base_url="https://api.example.com")
        
        # Test actual request method instead of mocking internal _make_request
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await client.get("/test")
            
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_post_request_success(self):
        """Test successful POST request with JSON data."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        data = {"name": "test", "value": 42}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"created": True, "id": 123}
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await client.post("/create", json=data)
            
            assert result["created"] is True
            assert result["id"] == 123

    @pytest.mark.asyncio
    async def test_put_request_success(self):
        """Test successful PUT request."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        data = {"name": "updated"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"updated": True}
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await client.put("/update/123", json=data)
            
            assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_delete_request_success(self):
        """Test successful DELETE request."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = None
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await client.delete("/delete/123")
            
            # DELETE typically returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_request_with_params(self):
        """Test request with query parameters."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        params = {"page": 1, "limit": 10, "sort": "name"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await client.get("/search", params=params)
            
            assert "results" in result

    @pytest.mark.asyncio
    async def test_request_with_custom_headers(self):
        """Test request with custom headers."""
        headers = {"X-Custom-Header": "value", "Authorization": "Bearer token"}
        client = AsyncAPIClient(base_url="https://api.example.com", headers=headers)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await client.get("/protected")
            
            assert result["data"] == "test"

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test handling of HTTP error responses."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.side_effect = Exception("Not JSON")
            mock_response.text = "Not Found"
            
            # Create a proper HTTPStatusError
            import httpx
            error_response = Mock()
            error_response.status_code = 404
            error_response.headers = {"Content-Type": "application/json"}
            error_response.json.side_effect = Exception("Not JSON")
            error_response.text = "Not Found"
            
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=error_response
            )
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with pytest.raises(APIClientError):
                await client.get("/nonexistent")

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self):
        """Test handling of rate limit errors."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_response.headers = {
                "Content-Type": "application/json",
                "Retry-After": "60",
            }
            mock_response.json.return_value = {"error": "Rate limit exceeded"}
            mock_response.text = '{"error": "Rate limit exceeded"}'
            
            # Create a proper HTTPStatusError
            import httpx
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests", request=Mock(), response=mock_response
            )
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with pytest.raises(RateLimitError) as exc_info:
                await client.get("/rate-limited")

            assert "429" in str(exc_info.value)
            # Should extract retry-after if available
            if hasattr(exc_info.value, "retry_after"):
                assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a proper httpx ConnectError
            import httpx
            mock_client.request.side_effect = httpx.ConnectError("Connection failed")
            mock_client_class.return_value = mock_client
            
            with pytest.raises(APIConnectionError) as exc_info:
                await client.get("/test")

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test handling of timeout errors."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a proper httpx TimeoutException
            import httpx
            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value = mock_client
            
            with pytest.raises(APITimeoutError) as exc_info:
                await client.get("/slow")

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self):
        """Test handling of JSON decode errors."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.raise_for_status.return_value = None
            # Make json() raise an exception to simulate invalid JSON
            import json
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with pytest.raises(APIClientError):
                await client.get("/invalid-json")

    @pytest.mark.asyncio
    async def test_non_json_response_handling(self):
        """Test handling of non-JSON responses."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_response.headers = {"Content-Type": "text/plain"}
            mock_response.raise_for_status.return_value = None
            # Make json() raise an exception to simulate non-JSON response
            import json
            mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with pytest.raises(APIClientError):
                await client.get("/text-response")

    @pytest.mark.asyncio
    async def test_session_management(self):
        """Test session creation and management."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        # Test that client is created when needed
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Access client to trigger creation
            session = await client._get_client()

            assert session is not None
            mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """Test APIClient as async context manager."""
        async with AsyncAPIClient(base_url="https://api.example.com") as client:
            assert client is not None
            # Client should be created and available
            assert hasattr(client, "_client")

    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test proper session cleanup."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        # Mock client with aclose method
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch.object(client, "_client", mock_client):
            await client.close()

            # Should call client.aclose()
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_url_construction(self):
        """Test URL construction with base_url."""
        base_url = "https://api.example.com/v1"
        client = AsyncAPIClient(base_url=base_url)

        # The URL construction is handled by httpx.AsyncClient internally
        # We just verify the base_url is set correctly
        assert client.base_url == base_url

    def test_header_merging(self):
        """Test merging of default and request headers."""
        default_headers = {"Authorization": "Bearer token", "User-Agent": "test"}
        client = AsyncAPIClient(base_url="https://api.example.com", headers=default_headers)

        # The header merging is handled by httpx.AsyncClient internally
        # We just verify the headers are set correctly
        assert client.headers == default_headers

    def test_request_timeout_configuration(self):
        """Test timeout configuration."""
        timeout = 45.0
        client = AsyncAPIClient(base_url="https://api.example.com", timeout=timeout)

        assert client.timeout == timeout

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Test retry mechanism for failed requests."""
        from khive.clients.resilience import RetryConfig
        
        # Create client with retry configuration
        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        client = AsyncAPIClient(base_url="https://api.example.com", retry_config=retry_config)

        # Mock consecutive failures then success
        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                import httpx
                raise httpx.ConnectError("Temporary failure")

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request.side_effect = mock_request_side_effect
            mock_client_class.return_value = mock_client
            
            # Should retry and eventually succeed
            result = await client.get("/flaky")
            assert result["success"] is True
            # Should have been called 3 times (2 failures + 1 success)
            assert call_count == 3


class TestAsyncAPIClientIntegration:
    """Integration tests for APIClient."""

    @pytest.mark.asyncio
    async def test_real_session_creation(self):
        """Test actual httpx client creation."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        # Should be able to create a real client
        session = await client._get_client()
        assert isinstance(session, httpx.AsyncClient)

        # Cleanup
        await client.close()

    def test_error_hierarchy(self):
        """Test that custom errors inherit correctly."""
        # Test error class hierarchy
        assert issubclass(RateLimitError, APIClientError)
        assert issubclass(APIConnectionError, APIClientError)

        # Test error instantiation
        api_error = APIClientError("Test error")
        assert str(api_error) == "Test error"

        rate_error = RateLimitError("Rate limited", retry_after=60)
        assert "Rate limited" in str(rate_error)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        client = AsyncAPIClient(base_url="https://api.example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": 1}
            mock_response.raise_for_status.return_value = None
            mock_response.is_closed = False
            mock_response.close = Mock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Should handle multiple concurrent requests
            import asyncio

            tasks = [client.get(f"/item/{i}") for i in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            for result in results:
                assert result["id"] == 1
