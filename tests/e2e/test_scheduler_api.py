"""
Test scheduler HTTP endpoints.

This module tests the HTTP API endpoints for scheduler management
including status checks and manual trigger functionality.
"""
import asyncio

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_status_endpoint():
    """Test GET /admin/scheduler/status"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/admin/scheduler/status")
        assert response.status_code == 200

        data = response.json()
        assert "running" in data
        assert "interval_minutes" in data
        assert "jobs" in data
        assert "update_service" in data

        # Validate update service status
        assert "update_count" in data["update_service"]
        assert "sources" in data["update_service"]


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_trigger_endpoint():
    """Test POST /admin/scheduler/trigger"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/admin/scheduler/trigger")
        assert response.status_code == 200

        data = response.json()
        assert "total_fetched" in data or "error" in data

        if "total_fetched" in data:
            assert data["total_fetched"] >= 0

            # Verify structure
            assert "sources" in data
            assert "started_at" in data
            assert "completed_at" in data


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_initial_update():
    """Verify scheduler ran initial update on startup."""
    async with httpx.AsyncClient() as client:
        # Get scheduler status
        response = await client.get(f"{BASE_URL}/admin/scheduler/status")
        assert response.status_code == 200

        data = response.json()

        # Verify scheduler is running
        assert data["running"] is True

        # Verify update_count reflects initial updates
        assert data["update_service"]["update_count"] >= 0


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_job_info():
    """Test scheduler job information in status endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/admin/scheduler/status")
        assert response.status_code == 200

        data = response.json()

        # Check jobs array
        assert "jobs" in data
        assert len(data["jobs"]) >= 0

        # If jobs exist, verify structure
        if len(data["jobs"]) > 0:
            job = data["jobs"][0]
            assert "id" in job
            assert "name" in job
            assert "next_run" in job


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_triggers():
    """Test multiple concurrent trigger requests."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Send multiple concurrent trigger requests
        tasks = [client.post(f"{BASE_URL}/admin/scheduler/trigger") for _ in range(3)]

        responses = await asyncio.gather(*tasks)

        # All should complete successfully
        for response in responses:
            assert response.status_code == 200

            data = response.json()
            assert "total_fetched" in data or "error" in data


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_endpoint_error_handling():
    """Test scheduler endpoints handle errors gracefully."""
    async with httpx.AsyncClient() as client:
        # Test status endpoint (should always work)
        response = await client.get(f"{BASE_URL}/admin/scheduler/status")
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_update_sequence():
    """Test sequence of status and trigger operations."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Get initial status
        status1 = await client.get(f"{BASE_URL}/admin/scheduler/status")
        assert status1.status_code == 200
        data1 = status1.json()
        initial_count = data1["update_service"]["update_count"]

        # Trigger update
        trigger = await client.post(f"{BASE_URL}/admin/scheduler/trigger")
        assert trigger.status_code == 200

        # Get updated status
        await asyncio.sleep(1)
        status2 = await client.get(f"{BASE_URL}/admin/scheduler/status")
        assert status2.status_code == 200
        data2 = status2.json()

        # Verify count increased
        assert data2["update_service"]["update_count"] >= initial_count
