# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Batch processing utilities for Plasmod SDK.

This module provides utilities for splitting large data into smaller batches
to avoid memory issues when ingesting large amounts of data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Sequence, TypeVar

T = TypeVar("T")

# Default batch size for vector ingestion (conservative to avoid memory issues)
DEFAULT_BATCH_SIZE = 500

# Maximum batch size allowed by the server (from binary.py _MAX_BATCH_VECTORS)
MAX_BATCH_VECTORS = 1 << 22  # 4,194,304


def iter_batches(items: Sequence[T], batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[List[T]]:
    """
    Split a sequence into batches of specified size.

    This is a memory-efficient generator that yields batches without
    creating a full copy of the input data.

    Args:
        items: The sequence to split into batches.
        batch_size: Maximum number of items per batch. Defaults to 500.

    Yields:
        Lists of items, each containing at most ``batch_size`` items.

    Raises:
        ValueError: If batch_size is less than 1.

    Examples:
        >>> list(iter_batches([1, 2, 3, 4, 5], batch_size=2))
        [[1, 2], [3, 4], [5]]
        >>> list(iter_batches([], batch_size=10))
        []
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    n = len(items)
    if n == 0:
        return

    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        yield list(items[start:end])


@dataclass
class BatchResult:
    """
    Result of a batched operation.

    Attributes:
        total_count: Total number of items processed.
        accepted_count: Number of items successfully accepted.
        failed_count: Number of items that failed.
        batch_count: Number of batches sent.
        memory_ids: List of memory IDs returned by successful batches.
        errors: List of error information for failed batches.
    """

    total_count: int = 0
    accepted_count: int = 0
    failed_count: int = 0
    batch_count: int = 0
    memory_ids: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def merge(self, other: "BatchResult") -> "BatchResult":
        """Merge another BatchResult into this one."""
        return BatchResult(
            total_count=self.total_count + other.total_count,
            accepted_count=self.accepted_count + other.accepted_count,
            failed_count=self.failed_count + other.failed_count,
            batch_count=self.batch_count + other.batch_count,
            memory_ids=self.memory_ids + other.memory_ids,
            errors=self.errors + other.errors,
        )

    @property
    def success(self) -> bool:
        """Return True if all items were accepted without errors."""
        return self.failed_count == 0 and len(self.errors) == 0

    def raise_on_error(self) -> None:
        """Raise an exception if any errors occurred."""
        if self.errors:
            from pyplasmod.exceptions import PlasmodException

            error_summary = "; ".join(
                f"batch {e.get('batch_index', '?')}: {e.get('error', 'unknown')}"
                for e in self.errors[:5]
            )
            if len(self.errors) > 5:
                error_summary += f" ... and {len(self.errors) - 5} more errors"
            raise PlasmodException(
                f"Batch operation failed: {self.failed_count} items failed across "
                f"{len(self.errors)} batches. Errors: {error_summary}"
            )


def validate_batch_size(batch_size: int, max_allowed: int = MAX_BATCH_VECTORS) -> int:
    """
    Validate and normalize batch size.

    Args:
        batch_size: Requested batch size.
        max_allowed: Maximum allowed batch size.

    Returns:
        Validated batch size (clamped to max_allowed if necessary).

    Raises:
        ValueError: If batch_size is less than 1.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    return min(batch_size, max_allowed)


__all__ = [
    "BatchResult",
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_VECTORS",
    "iter_batches",
    "validate_batch_size",
]
