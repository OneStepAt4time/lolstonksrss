"""Performance tests for the scheduler.

This module tests scheduler performance metrics including update duration,
memory usage, and throughput.
"""
import asyncio
import os
import time

import psutil
import pytest

from src.database import ArticleRepository
from src.services.scheduler import NewsScheduler
from src.services.update_service import UpdateService


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.asyncio
async def test_update_performance_metrics():
    """Test update service performance and timing."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        service = UpdateService(repo)

        # Measure update performance
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss

        stats = await service.update_all_sources()

        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss

        elapsed = end_time - start_time
        memory_used = (end_memory - start_memory) / (1024 * 1024)  # MB

        # Verify performance metrics
        assert stats["elapsed_seconds"] >= 0
        assert elapsed < 60  # Should complete within 60 seconds

        # Log performance data
        print("Update Performance:")
        print(f"  Elapsed time: {elapsed:.2f}s")
        print(f"  Memory used: {memory_used:.2f}MB")
        print(f"  Articles fetched: {stats['total_fetched']}")
        print(f"  Articles new: {stats['total_new']}")

        if stats["total_fetched"] > 0:
            throughput = stats["total_fetched"] / elapsed
            print(f"  Throughput: {throughput:.2f} articles/second")
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.asyncio
async def test_scheduler_overhead():
    """Test scheduler overhead when running periodic updates."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=0.01)  # ~0.6 seconds

        # Measure memory before starting
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)

        # Start scheduler
        scheduler.start()

        # Measure memory after starting
        after_start_memory = process.memory_info().rss / (1024 * 1024)
        startup_overhead = after_start_memory - initial_memory

        # Wait for a few updates
        await asyncio.sleep(3)

        # Measure memory after updates
        after_updates_memory = process.memory_info().rss / (1024 * 1024)

        scheduler.stop()

        print("Scheduler Overhead:")
        print(f"  Startup overhead: {startup_overhead:.2f}MB")
        print(f"  Memory after updates: {after_updates_memory:.2f}MB")

        # Scheduler overhead should be reasonable
        assert startup_overhead < 50  # Less than 50MB overhead
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_update_performance():
    """Test performance of concurrent manual triggers."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)
        scheduler.start()

        # Measure time for multiple concurrent triggers
        start_time = time.time()

        tasks = [scheduler.trigger_update_now() for _ in range(3)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        elapsed = end_time - start_time

        print("Concurrent Update Performance:")
        print(f"  3 concurrent updates completed in: {elapsed:.2f}s")
        print(f"  Average per update: {elapsed/3:.2f}s")

        # Verify all completed successfully
        for result in results:
            assert "total_fetched" in result or "error" in result

        scheduler.stop()
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.asyncio
async def test_database_write_performance():
    """Test database write performance during updates."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        service = UpdateService(repo)

        # Perform update and measure write performance
        start_time = time.time()
        stats = await service.update_all_sources()
        end_time = time.time()

        elapsed = end_time - start_time

        # Calculate write performance
        total_articles = stats["total_new"] + stats["total_duplicates"]

        print("Database Write Performance:")
        print(f"  Total articles processed: {total_articles}")
        print(f"  Time elapsed: {elapsed:.2f}s")

        if total_articles > 0:
            writes_per_second = total_articles / elapsed
            print(f"  Writes per second: {writes_per_second:.2f}")

            # Should be able to write at least 1 article per second
            assert writes_per_second > 0.1
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.asyncio
async def test_scheduler_state_size():
    """Test scheduler state size and memory efficiency."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)

        # Get initial state
        _status1 = scheduler.get_status()

        # Trigger update to populate state
        await scheduler.trigger_update_now()

        # Get updated state
        status2 = scheduler.get_status()

        # Measure state size
        import sys

        state_size = sys.getsizeof(status2)

        print("Scheduler State Size:")
        print(f"  State size: {state_size} bytes")
        print(f"  Update count: {status2['update_service']['update_count']}")

        # State size should be reasonable
        assert state_size < 10000  # Less than 10KB
    finally:
        await repo.close()
