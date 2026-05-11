# Copyright (C) 2019-2021 Zilliz. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

"""Tests for batch processing utilities."""

import pytest

from pyplasmod.batch import (
    DEFAULT_BATCH_SIZE,
    MAX_BATCH_VECTORS,
    BatchResult,
    iter_batches,
    validate_batch_size,
)


class TestIterBatches:
    """Tests for iter_batches function."""

    def test_empty_input(self):
        """Empty input should yield no batches."""
        result = list(iter_batches([], batch_size=10))
        assert result == []

    def test_single_batch(self):
        """Input smaller than batch_size should yield single batch."""
        items = [1, 2, 3, 4, 5]
        result = list(iter_batches(items, batch_size=10))
        assert result == [[1, 2, 3, 4, 5]]

    def test_exact_batches(self):
        """Input exactly divisible by batch_size."""
        items = [1, 2, 3, 4, 5, 6]
        result = list(iter_batches(items, batch_size=2))
        assert result == [[1, 2], [3, 4], [5, 6]]

    def test_partial_last_batch(self):
        """Last batch may be smaller than batch_size."""
        items = [1, 2, 3, 4, 5]
        result = list(iter_batches(items, batch_size=2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_batch_size_one(self):
        """batch_size=1 should yield individual items."""
        items = [1, 2, 3]
        result = list(iter_batches(items, batch_size=1))
        assert result == [[1], [2], [3]]

    def test_batch_size_larger_than_input(self):
        """batch_size larger than input should yield single batch."""
        items = [1, 2, 3]
        result = list(iter_batches(items, batch_size=100))
        assert result == [[1, 2, 3]]

    def test_invalid_batch_size_zero(self):
        """batch_size=0 should raise ValueError."""
        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            list(iter_batches([1, 2, 3], batch_size=0))

    def test_invalid_batch_size_negative(self):
        """Negative batch_size should raise ValueError."""
        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            list(iter_batches([1, 2, 3], batch_size=-1))

    def test_default_batch_size(self):
        """Default batch_size should be DEFAULT_BATCH_SIZE."""
        items = list(range(DEFAULT_BATCH_SIZE + 100))
        batches = list(iter_batches(items))
        assert len(batches) == 2
        assert len(batches[0]) == DEFAULT_BATCH_SIZE
        assert len(batches[1]) == 100

    def test_preserves_order(self):
        """Batches should preserve input order."""
        items = list(range(100))
        batches = list(iter_batches(items, batch_size=30))
        flattened = [item for batch in batches for item in batch]
        assert flattened == items

    def test_string_items(self):
        """Should work with string items."""
        items = ["a", "b", "c", "d", "e"]
        result = list(iter_batches(items, batch_size=2))
        assert result == [["a", "b"], ["c", "d"], ["e"]]

    def test_dict_items(self):
        """Should work with dict items."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = list(iter_batches(items, batch_size=2))
        assert result == [[{"id": 1}, {"id": 2}], [{"id": 3}]]


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_default_values(self):
        """Default values should be zeros and empty lists."""
        result = BatchResult()
        assert result.total_count == 0
        assert result.accepted_count == 0
        assert result.failed_count == 0
        assert result.batch_count == 0
        assert result.memory_ids == []
        assert result.errors == []

    def test_success_property_true(self):
        """success should be True when no failures."""
        result = BatchResult(total_count=10, accepted_count=10, failed_count=0)
        assert result.success is True

    def test_success_property_false_with_failures(self):
        """success should be False when there are failures."""
        result = BatchResult(total_count=10, accepted_count=8, failed_count=2)
        assert result.success is False

    def test_success_property_false_with_errors(self):
        """success should be False when there are errors."""
        result = BatchResult(
            total_count=10,
            accepted_count=10,
            failed_count=0,
            errors=[{"error": "test"}],
        )
        assert result.success is False

    def test_merge(self):
        """merge should combine two BatchResults."""
        r1 = BatchResult(
            total_count=10,
            accepted_count=8,
            failed_count=2,
            batch_count=2,
            memory_ids=["a", "b"],
            errors=[{"batch_index": 0, "error": "e1"}],
        )
        r2 = BatchResult(
            total_count=5,
            accepted_count=5,
            failed_count=0,
            batch_count=1,
            memory_ids=["c"],
            errors=[],
        )
        merged = r1.merge(r2)
        assert merged.total_count == 15
        assert merged.accepted_count == 13
        assert merged.failed_count == 2
        assert merged.batch_count == 3
        assert merged.memory_ids == ["a", "b", "c"]
        assert len(merged.errors) == 1

    def test_raise_on_error_no_errors(self):
        """raise_on_error should not raise when no errors."""
        result = BatchResult(total_count=10, accepted_count=10)
        result.raise_on_error()  # Should not raise

    def test_raise_on_error_with_errors(self):
        """raise_on_error should raise PlasmodException when errors exist."""
        from pyplasmod.exceptions import PlasmodException

        result = BatchResult(
            total_count=10,
            accepted_count=8,
            failed_count=2,
            errors=[
                {"batch_index": 0, "error": "connection failed"},
                {"batch_index": 1, "error": "timeout"},
            ],
        )
        with pytest.raises(PlasmodException, match="Batch operation failed"):
            result.raise_on_error()

    def test_raise_on_error_truncates_many_errors(self):
        """raise_on_error should truncate error message for many errors."""
        from pyplasmod.exceptions import PlasmodException

        result = BatchResult(
            total_count=100,
            accepted_count=90,
            failed_count=10,
            errors=[{"batch_index": i, "error": f"error {i}"} for i in range(10)],
        )
        with pytest.raises(PlasmodException, match="and 5 more errors"):
            result.raise_on_error()


class TestValidateBatchSize:
    """Tests for validate_batch_size function."""

    def test_valid_batch_size(self):
        """Valid batch_size should be returned unchanged."""
        assert validate_batch_size(100) == 100
        assert validate_batch_size(1) == 1
        assert validate_batch_size(DEFAULT_BATCH_SIZE) == DEFAULT_BATCH_SIZE

    def test_batch_size_clamped_to_max(self):
        """batch_size exceeding max should be clamped."""
        huge = MAX_BATCH_VECTORS + 1000
        assert validate_batch_size(huge) == MAX_BATCH_VECTORS

    def test_invalid_batch_size_zero(self):
        """batch_size=0 should raise ValueError."""
        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            validate_batch_size(0)

    def test_invalid_batch_size_negative(self):
        """Negative batch_size should raise ValueError."""
        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            validate_batch_size(-5)

    def test_custom_max_allowed(self):
        """Custom max_allowed should be respected."""
        assert validate_batch_size(100, max_allowed=50) == 50
        assert validate_batch_size(30, max_allowed=50) == 30
