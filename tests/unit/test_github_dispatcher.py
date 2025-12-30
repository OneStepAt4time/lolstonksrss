"""
Unit tests for GitHub workflow dispatcher.

This module tests the GitHub Actions workflow triggering functionality
including authentication, error handling, retry logic, and token masking.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.integrations.github_dispatcher import GitHubWorkflowDispatcher


@pytest.fixture
def dispatcher() -> GitHubWorkflowDispatcher:
    """Create a GitHubWorkflowDispatcher instance for testing."""
    return GitHubWorkflowDispatcher(token="ghp_test1234567890abcdef", repository="owner/repo")


@pytest.mark.asyncio
async def test_trigger_workflow_success(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test successful workflow trigger."""
    # Mock successful response (204 No Content)
    mock_response = Mock()
    mock_response.status_code = 204

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await dispatcher.trigger_workflow(
            workflow_file="publish-news.yml", ref="main", inputs={"test": "value"}
        )

        assert result is True
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_workflow_auth_failure(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test authentication failure (401)."""
    # Mock 401 unauthorized response
    mock_response = Mock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        assert result is False


@pytest.mark.asyncio
async def test_trigger_workflow_rate_limit(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test rate limiting (429)."""
    # Mock 429 rate limit response
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.text = "API rate limit exceeded"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        assert result is False


@pytest.mark.asyncio
async def test_trigger_workflow_forbidden(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test forbidden access (403)."""
    # Mock 403 forbidden response
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        assert result is False


@pytest.mark.asyncio
async def test_trigger_workflow_not_found(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test workflow not found (404)."""
    # Mock 404 not found response
    mock_response = Mock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await dispatcher.trigger_workflow(workflow_file="nonexistent.yml")

        assert result is False


@pytest.mark.asyncio
async def test_trigger_workflow_server_error_retry_success(
    dispatcher: GitHubWorkflowDispatcher,
) -> None:
    """Test server error with successful retry."""
    # Mock first call returns 500, second call returns 204
    mock_response_500 = Mock()
    mock_response_500.status_code = 500

    mock_response_204 = Mock()
    mock_response_204.status_code = 204

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=[mock_response_500, mock_response_204]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

            assert result is True
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 2


@pytest.mark.asyncio
async def test_trigger_workflow_server_error_max_retries(
    dispatcher: GitHubWorkflowDispatcher,
) -> None:
    """Test server error exhausting max retries."""
    # Mock all retries return 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

            assert result is False
            # Should try 3 times
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 3


@pytest.mark.asyncio
async def test_trigger_workflow_timeout(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test timeout handling."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        assert result is False


@pytest.mark.asyncio
async def test_trigger_workflow_http_error(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test HTTP error handling."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.HTTPError("Connection error")
        )

        result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        assert result is False


@pytest.mark.asyncio
async def test_trigger_workflow_unexpected_error(
    dispatcher: GitHubWorkflowDispatcher,
) -> None:
    """Test unexpected error handling."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        assert result is False


@pytest.mark.asyncio
async def test_token_masking_in_logs(
    dispatcher: GitHubWorkflowDispatcher, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that token is never logged in full."""
    import logging

    caplog.set_level(logging.ERROR)

    # Trigger error that would log token
    mock_response = Mock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        # Check that full token is never in logs or records
        full_log_output = caplog.text
        for record in caplog.records:
            if hasattr(record, "token_prefix"):
                full_log_output += str(record.token_prefix)

        assert "ghp_test1234567890abcdef" not in full_log_output

        # Verify error was logged
        assert len(caplog.records) > 0
        assert any("authentication failed" in record.message.lower() for record in caplog.records)


def test_mask_token(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test token masking function."""
    # Test normal token
    masked = dispatcher._mask_token("ghp_test1234567890abcdef")
    assert masked == "ghp_****"

    # Test short token
    masked_short = dispatcher._mask_token("abc")
    assert masked_short == "****"

    # Test very short token
    masked_very_short = dispatcher._mask_token("ab")
    assert masked_very_short == "****"

    # Test empty token
    masked_empty = dispatcher._mask_token("")
    assert masked_empty == "****"


@pytest.mark.asyncio
async def test_trigger_workflow_with_inputs(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test workflow trigger with custom inputs."""
    mock_response = Mock()
    mock_response.status_code = 204

    inputs = {"triggered_by": "windows-app", "reason": "new-articles-found-5"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await dispatcher.trigger_workflow(
            workflow_file="publish-news.yml", ref="main", inputs=inputs
        )

        assert result is True

        # Verify inputs were passed in payload
        call_args = mock_post.call_args
        assert call_args is not None
        payload = call_args.kwargs["json"]
        assert payload["ref"] == "main"
        assert payload["inputs"] == inputs


@pytest.mark.asyncio
async def test_trigger_workflow_custom_ref(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test workflow trigger with custom git ref."""
    mock_response = Mock()
    mock_response.status_code = 204

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml", ref="develop")

        assert result is True

        # Verify custom ref was used
        call_args = mock_post.call_args
        assert call_args is not None
        payload = call_args.kwargs["json"]
        assert payload["ref"] == "develop"


@pytest.mark.asyncio
async def test_trigger_workflow_headers(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test that correct headers are sent."""
    mock_response = Mock()
    mock_response.status_code = 204

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        # Verify headers
        call_args = mock_post.call_args
        assert call_args is not None
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "token ghp_test1234567890abcdef"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"


@pytest.mark.asyncio
async def test_trigger_workflow_url_construction(
    dispatcher: GitHubWorkflowDispatcher,
) -> None:
    """Test that API URL is constructed correctly."""
    mock_response = Mock()
    mock_response.status_code = 204

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

        # Verify URL
        call_args = mock_post.call_args
        assert call_args is not None
        url = call_args.args[0]
        expected_url = (
            "https://api.github.com/repos/owner/repo/actions/"
            "workflows/publish-news.yml/dispatches"
        )
        assert url == expected_url


@pytest.mark.asyncio
async def test_exponential_backoff_delays(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test that exponential backoff uses correct delays."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server Error"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

            # Should sleep with delays: 1s, 2s (fails on 3rd attempt without sleep)
            assert mock_sleep.call_count == 2
            sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
            assert sleep_calls == [1, 2]


@pytest.mark.asyncio
async def test_unexpected_status_code(dispatcher: GitHubWorkflowDispatcher) -> None:
    """Test handling of unexpected status codes."""
    # Test with various unexpected codes
    unexpected_codes = [400, 418, 422, 502, 503]

    for code in unexpected_codes:
        mock_response = Mock()
        mock_response.status_code = code
        mock_response.text = f"Error {code}"

        with patch("httpx.AsyncClient") as mock_client:
            if code >= 500:
                # Server errors should retry
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")
            else:
                # Client errors should not retry
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                result = await dispatcher.trigger_workflow(workflow_file="publish-news.yml")

            assert result is False
