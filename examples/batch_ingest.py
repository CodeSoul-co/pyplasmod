"""
Example: Batch ingestion with automatic splitting.

This example demonstrates how to use the batch ingestion methods
to efficiently ingest large amounts of data without memory issues.

Requires a running Plasmod server at http://127.0.0.1:8080
"""

from __future__ import annotations

import random
from typing import List

from pyplasmod import PlasmodClient, BatchResult


def generate_random_vectors(count: int, dim: int = 128) -> List[List[float]]:
    """Generate random vectors for testing."""
    return [[random.random() for _ in range(dim)] for _ in range(count)]


def example_ingest_batch():
    """Example: Ingest vectors in batches."""
    print("=" * 60)
    print("Example: ingest_batch with automatic splitting")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")

    # Generate 2500 vectors (will be split into batches)
    vectors = generate_random_vectors(2500, dim=128)
    object_ids = [f"vec_{i}" for i in range(len(vectors))]

    print(f"Ingesting {len(vectors)} vectors...")

    # Ingest with automatic batching (default batch_size=500)
    result: BatchResult = client.ingest_batch(
        segment_id="warm.default",
        vectors=vectors,
        object_ids=object_ids,
        batch_size=500,  # 2500 / 500 = 5 batches
    )

    print(f"Total count: {result.total_count}")
    print(f"Accepted count: {result.accepted_count}")
    print(f"Failed count: {result.failed_count}")
    print(f"Batch count: {result.batch_count}")
    print(f"Success: {result.success}")

    if result.errors:
        print(f"Errors: {result.errors}")


def example_add_vectors():
    """Example: Simplified add_vectors interface."""
    print("\n" + "=" * 60)
    print("Example: add_vectors (simplified interface)")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")

    vectors = generate_random_vectors(100, dim=128)

    result = client.add_vectors(
        vectors,
        segment_id="warm.default",
        batch_size=50,
    )

    print(f"Added {result.accepted_count} vectors in {result.batch_count} batches")


def example_ingest_events():
    """Example: Ingest events in batches."""
    print("\n" + "=" * 60)
    print("Example: ingest_events with batching")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")

    # Create sample events
    events = [
        {
            "event_id": f"event_{i}",
            "agent_id": "agent_1",
            "session_id": "session_1",
            "event_type": "observation",
            "payload": {
                "content": f"This is observation {i}",
                "timestamp": f"2024-01-01T00:00:{i:02d}Z",
            },
        }
        for i in range(50)
    ]

    print(f"Ingesting {len(events)} events...")

    result = client.ingest_events(
        events,
        batch_size=10,
        raise_on_error=False,  # Continue on errors
    )

    print(f"Accepted: {result.accepted_count}/{result.total_count}")
    print(f"Batches: {result.batch_count}")

    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors[:3]:
            print(f"  - Event {error.get('event_index')}: {error.get('error')}")


def example_batch_query():
    """Example: Execute multiple queries in batches."""
    print("\n" + "=" * 60)
    print("Example: batch_query")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")

    # Create multiple queries
    queries = [
        {"query_text": f"query {i}", "top_k": 5}
        for i in range(10)
    ]

    print(f"Executing {len(queries)} queries...")

    results = client.batch_query(queries, batch_size=3)

    print(f"Got {len(results)} results")
    for i, result in enumerate(results[:3]):
        objects = result.get("objects", []) if isinstance(result, dict) else []
        print(f"  Query {i}: {len(objects)} results")


def example_error_handling():
    """Example: Handling batch errors."""
    print("\n" + "=" * 60)
    print("Example: Error handling with raise_on_error=False")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")

    vectors = generate_random_vectors(100, dim=128)

    # With raise_on_error=False, errors are collected instead of raised
    result = client.ingest_batch(
        segment_id="warm.default",
        vectors=vectors,
        batch_size=20,
        raise_on_error=False,
    )

    if result.success:
        print("All batches succeeded!")
    else:
        print(f"Some batches failed: {result.failed_count} items failed")
        print(f"Errors: {result.errors}")

        # You can still raise an exception if needed
        # result.raise_on_error()


def main():
    """Run all examples."""
    print("Plasmod Batch Ingestion Examples")
    print("================================\n")
    print("Note: These examples require a running Plasmod server.\n")

    try:
        example_ingest_batch()
        example_add_vectors()
        example_ingest_events()
        example_batch_query()
        example_error_handling()
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure Plasmod server is running at http://127.0.0.1:8080")


if __name__ == "__main__":
    main()
