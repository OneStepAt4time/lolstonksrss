"""
GitHub workflow dispatcher for triggering GitHub Actions workflows.

This module provides a client for triggering GitHub Actions workflows
via the GitHub REST API, enabling automatic GitHub Pages updates.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GitHubWorkflowDispatcher:
    """Client for triggering GitHub Actions workflows via API."""

    def __init__(self, token: str, repository: str) -> None:
        """
        Initialize GitHub workflow dispatcher.

        Args:
            token: GitHub Personal Access Token (PAT) with workflow scope
            repository: Repository in format "owner/repo"
        """
        self.token = token
        self.repository = repository
        self.base_url = "https://api.github.com"

    def _mask_token(self, token: str) -> str:
        """
        Mask token for safe logging.

        Args:
            token: GitHub token to mask

        Returns:
            Masked token showing only first 4 characters
        """
        if len(token) <= 4:
            return "****"
        return f"{token[:4]}****"

    async def trigger_workflow(
        self,
        workflow_file: str,
        ref: str = "main",
        inputs: dict[str, str] | None = None,
    ) -> bool:
        """
        Trigger a GitHub Actions workflow.

        Implementation details:
        - Uses GitHub REST API workflow_dispatch endpoint
        - Includes exponential backoff retry logic for 5xx errors
        - Handles authentication and rate limiting gracefully
        - Logs all errors with masked tokens for security

        Args:
            workflow_file: Workflow file name (e.g., "publish-news.yml")
            ref: Git ref to run workflow on (default: "main")
            inputs: Optional workflow input parameters

        Returns:
            True if workflow triggered successfully, False otherwise
        """
        url = (
            f"{self.base_url}/repos/{self.repository}/actions/"
            f"workflows/{workflow_file}/dispatches"
        )

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        payload: dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs

        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff in seconds

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    logger.debug(
                        f"Triggering workflow {workflow_file} on {self.repository}",
                        extra={
                            "workflow": workflow_file,
                            "repository": self.repository,
                            "ref": ref,
                            "attempt": attempt + 1,
                        },
                    )

                    response = await client.post(url, json=payload, headers=headers)

                    # Success case (204 No Content)
                    if response.status_code == 204:
                        logger.info(
                            f"Successfully triggered workflow {workflow_file}",
                            extra={
                                "workflow": workflow_file,
                                "repository": self.repository,
                                "ref": ref,
                                "inputs": inputs,
                            },
                        )
                        return True

                    # Authentication failure
                    if response.status_code == 401:
                        logger.error(
                            "GitHub API authentication failed - invalid or expired token",
                            extra={
                                "status_code": 401,
                                "token_prefix": self._mask_token(self.token),
                                "repository": self.repository,
                            },
                        )
                        return False

                    # Forbidden or rate limited (don't retry)
                    if response.status_code in (403, 429):
                        logger.warning(
                            f"GitHub API rate limit or permission denied (status {response.status_code})",
                            extra={
                                "status_code": response.status_code,
                                "repository": self.repository,
                                "token_prefix": self._mask_token(self.token),
                                "response_text": response.text[:200],
                            },
                        )
                        return False

                    # Not found (workflow or repo doesn't exist)
                    if response.status_code == 404:
                        logger.error(
                            f"Workflow or repository not found: {workflow_file}",
                            extra={
                                "status_code": 404,
                                "workflow": workflow_file,
                                "repository": self.repository,
                            },
                        )
                        return False

                    # Server error (retry with exponential backoff)
                    if response.status_code >= 500:
                        if attempt < max_retries - 1:
                            delay = retry_delays[attempt]
                            logger.warning(
                                f"GitHub API server error (status {response.status_code}), "
                                f"retrying in {delay}s",
                                extra={
                                    "status_code": response.status_code,
                                    "attempt": attempt + 1,
                                    "max_retries": max_retries,
                                    "retry_delay": delay,
                                },
                            )
                            # Use asyncio.sleep for async context
                            import asyncio

                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"GitHub API server error after {max_retries} attempts",
                                extra={
                                    "status_code": response.status_code,
                                    "attempts": max_retries,
                                    "response_text": response.text[:200],
                                },
                            )
                            return False

                    # Unexpected status code
                    logger.error(
                        f"Unexpected GitHub API response: {response.status_code}",
                        extra={
                            "status_code": response.status_code,
                            "workflow": workflow_file,
                            "response_text": response.text[:200],
                        },
                    )
                    return False

            except httpx.TimeoutException as e:
                logger.error(
                    f"GitHub API request timeout (attempt {attempt + 1}/{max_retries})",
                    extra={
                        "error": str(e),
                        "attempt": attempt + 1,
                        "workflow": workflow_file,
                    },
                )
                if attempt == max_retries - 1:
                    return False

            except httpx.HTTPError as e:
                logger.error(
                    "GitHub API HTTP error",
                    extra={
                        "error": str(e),
                        "workflow": workflow_file,
                        "token_prefix": self._mask_token(self.token),
                    },
                    exc_info=True,
                )
                return False

            except Exception as e:
                logger.error(
                    "Unexpected error triggering GitHub workflow",
                    extra={
                        "error": str(e),
                        "workflow": workflow_file,
                        "token_prefix": self._mask_token(self.token),
                    },
                    exc_info=True,
                )
                return False

        return False
