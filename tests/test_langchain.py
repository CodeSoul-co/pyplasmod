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

"""Tests for LangChain integration."""

from unittest.mock import MagicMock, patch
import pytest

# Check if langchain-core is available
try:
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from pyplasmod import PlasmodClient


# Skip all tests if langchain-core is not installed
pytestmark = pytest.mark.skipif(
    not LANGCHAIN_AVAILABLE,
    reason="langchain-core not installed",
)


class MockEmbeddings:
    """Mock embeddings for testing."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed_documents(self, texts):
        """Return mock embeddings for documents."""
        return [[float(i % 10) / 10.0] * self.dim for i, _ in enumerate(texts)]

    def embed_query(self, text):
        """Return mock embedding for query."""
        return [0.5] * self.dim


@pytest.fixture
def mock_client():
    """Create a mock PlasmodClient."""
    client = MagicMock(spec=PlasmodClient)
    client.rpc_ingest_batch = MagicMock(return_value={"ok": True})
    client.ingest_event = MagicMock(return_value={"memory_id": "test"})
    client.query = MagicMock(return_value={"objects": []})
    client.rpc_query_warm = MagicMock(return_value=["id1", "id2"])
    return client


@pytest.fixture
def mock_embeddings():
    """Create mock embeddings."""
    return MockEmbeddings(dim=128)


class TestPlasmodVectorStore:
    """Tests for PlasmodVectorStore."""

    def test_import(self):
        """PlasmodVectorStore should be importable."""
        from pyplasmod.langchain import PlasmodVectorStore

        assert PlasmodVectorStore is not None

    def test_init(self, mock_client, mock_embeddings):
        """Should initialize with client and embeddings."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(
            client=mock_client,
            embedding=mock_embeddings,
            segment_id="test.segment",
            workspace_id="ws1",
            batch_size=100,
        )

        assert store._client is mock_client
        assert store._embedding is mock_embeddings
        assert store._segment_id == "test.segment"
        assert store._workspace_id == "ws1"
        assert store._batch_size == 100

    def test_embeddings_property(self, mock_client, mock_embeddings):
        """embeddings property should return the embedding model."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        assert store.embeddings is mock_embeddings

    def test_add_texts_empty(self, mock_client, mock_embeddings):
        """add_texts with empty input should return empty list."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        result = store.add_texts([])
        assert result == []

    def test_add_texts_generates_ids(self, mock_client, mock_embeddings):
        """add_texts should generate UUIDs if ids not provided."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        result = store.add_texts(["hello", "world"])

        assert len(result) == 2
        # IDs should be UUID-like strings
        for id_ in result:
            assert isinstance(id_, str)
            assert len(id_) == 36  # UUID format

    def test_add_texts_uses_provided_ids(self, mock_client, mock_embeddings):
        """add_texts should use provided ids."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        result = store.add_texts(["hello", "world"], ids=["id1", "id2"])

        assert result == ["id1", "id2"]

    def test_add_texts_mismatched_ids_raises(self, mock_client, mock_embeddings):
        """add_texts should raise if ids length doesn't match."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)

        with pytest.raises(ValueError, match="ids length must match"):
            store.add_texts(["hello", "world"], ids=["id1"])

    def test_add_texts_mismatched_metadatas_raises(self, mock_client, mock_embeddings):
        """add_texts should raise if metadatas length doesn't match."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)

        with pytest.raises(ValueError, match="metadatas length must match"):
            store.add_texts(["hello", "world"], metadatas=[{"key": "value"}])

    def test_add_texts_calls_rpc_ingest_batch(self, mock_client, mock_embeddings):
        """add_texts should call rpc_ingest_batch with vectors."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(
            client=mock_client,
            embedding=mock_embeddings,
            segment_id="test.seg",
        )
        store.add_texts(["hello", "world"], ids=["id1", "id2"])

        mock_client.rpc_ingest_batch.assert_called()
        call_args = mock_client.rpc_ingest_batch.call_args
        assert call_args[0][0] == "test.seg"  # segment_id
        assert len(call_args[0][1]) == 2  # vectors
        assert call_args[0][2] == ["id1", "id2"]  # object_ids

    def test_add_texts_batches_large_input(self, mock_client, mock_embeddings):
        """add_texts should batch large inputs."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(
            client=mock_client,
            embedding=mock_embeddings,
            batch_size=2,
        )
        store.add_texts(["a", "b", "c", "d", "e"])

        # 5 texts / 2 per batch = 3 batches
        assert mock_client.rpc_ingest_batch.call_count == 3

    def test_add_documents(self, mock_client, mock_embeddings):
        """add_documents should extract text and metadata from Documents."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)

        docs = [
            Document(page_content="hello", metadata={"source": "test1"}),
            Document(page_content="world", metadata={"source": "test2"}),
        ]
        result = store.add_documents(docs)

        assert len(result) == 2
        mock_client.rpc_ingest_batch.assert_called()

    def test_similarity_search(self, mock_client, mock_embeddings):
        """similarity_search should return Documents."""
        from pyplasmod.langchain import PlasmodVectorStore

        mock_client.query.return_value = {
            "objects": [
                {
                    "object_id": "id1",
                    "score": 0.9,
                    "payload": {"page_content": "hello", "metadata": {"key": "val"}},
                },
                {
                    "object_id": "id2",
                    "score": 0.8,
                    "payload": {"page_content": "world", "metadata": {}},
                },
            ]
        }

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        results = store.similarity_search("test query", k=5)

        assert len(results) == 2
        assert isinstance(results[0], Document)
        assert results[0].page_content == "hello"
        assert results[0].metadata["key"] == "val"
        assert results[0].metadata["id"] == "id1"

    def test_similarity_search_with_score(self, mock_client, mock_embeddings):
        """similarity_search_with_score should return (Document, score) tuples."""
        from pyplasmod.langchain import PlasmodVectorStore

        mock_client.query.return_value = {
            "objects": [
                {"object_id": "id1", "score": 0.9, "payload": {"page_content": "hello"}},
            ]
        }

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        results = store.similarity_search_with_score("test", k=5)

        assert len(results) == 1
        doc, score = results[0]
        assert isinstance(doc, Document)
        assert score == 0.9

    def test_similarity_search_by_vector(self, mock_client, mock_embeddings):
        """similarity_search_by_vector should search using provided vector."""
        from pyplasmod.langchain import PlasmodVectorStore

        mock_client.query.return_value = {"objects": []}

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        query_vector = [0.1] * 128
        store.similarity_search_by_vector(query_vector, k=10)

        mock_client.query.assert_called_once()
        call_args = mock_client.query.call_args[0][0]
        assert call_args["query_vector"] == query_vector
        assert call_args["top_k"] == 10

    def test_similarity_search_fallback_to_rpc(self, mock_client, mock_embeddings):
        """Should fallback to rpc_query_warm if JSON query fails."""
        from pyplasmod.langchain import PlasmodVectorStore

        mock_client.query.side_effect = Exception("JSON query not supported")
        mock_client.rpc_query_warm.return_value = ["id1", "id2"]

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        results = store.similarity_search("test", k=5)

        mock_client.rpc_query_warm.assert_called()
        assert len(results) == 2

    def test_delete_raises_not_implemented(self, mock_client, mock_embeddings):
        """delete should raise NotImplementedError."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)

        with pytest.raises(NotImplementedError, match="not supported"):
            store.delete(ids=["id1"])

    def test_mmr_raises_not_implemented(self, mock_client, mock_embeddings):
        """max_marginal_relevance_search should raise NotImplementedError."""
        from pyplasmod.langchain import PlasmodVectorStore

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)

        with pytest.raises(NotImplementedError, match="MMR"):
            store.max_marginal_relevance_search("test", k=5)

    def test_from_texts(self, mock_embeddings):
        """from_texts should create store and add texts."""
        from pyplasmod.langchain import PlasmodVectorStore

        with patch.object(PlasmodVectorStore, "add_texts", return_value=["id1", "id2"]):
            with patch("pyplasmod.langchain.vectorstore.PlasmodHttpClient") as MockClient:
                mock_instance = MagicMock()
                MockClient.return_value = mock_instance

                store = PlasmodVectorStore.from_texts(
                    texts=["hello", "world"],
                    embedding=mock_embeddings,
                    base_url="http://test:8080",
                )

                assert isinstance(store, PlasmodVectorStore)

    def test_from_documents(self, mock_embeddings):
        """from_documents should create store and add documents."""
        from pyplasmod.langchain import PlasmodVectorStore

        docs = [
            Document(page_content="hello"),
            Document(page_content="world"),
        ]

        with patch.object(PlasmodVectorStore, "from_texts") as mock_from_texts:
            mock_from_texts.return_value = MagicMock(spec=PlasmodVectorStore)

            PlasmodVectorStore.from_documents(
                documents=docs,
                embedding=mock_embeddings,
            )

            mock_from_texts.assert_called_once()
            call_args = mock_from_texts.call_args
            assert call_args[0][0] == ["hello", "world"]

    def test_as_retriever(self, mock_client, mock_embeddings):
        """as_retriever should return a VectorStoreRetriever."""
        from pyplasmod.langchain import PlasmodVectorStore
        from langchain_core.vectorstores import VectorStoreRetriever

        store = PlasmodVectorStore(client=mock_client, embedding=mock_embeddings)
        retriever = store.as_retriever()

        assert isinstance(retriever, VectorStoreRetriever)
        assert retriever.vectorstore is store


class TestLangChainNotInstalled:
    """Tests for behavior when langchain-core is not installed."""

    def test_import_error_message(self):
        """Should provide helpful error message when langchain not installed."""
        from pyplasmod.langchain.vectorstore import _check_langchain_installed, LANGCHAIN_AVAILABLE

        if LANGCHAIN_AVAILABLE:
            # If langchain is installed, this should not raise
            _check_langchain_installed()
        # If not installed, the test would be skipped anyway
