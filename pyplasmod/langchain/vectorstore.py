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

"""
LangChain VectorStore adapter for Plasmod.

This module provides a LangChain-compatible VectorStore interface for Plasmod,
allowing seamless integration with LangChain workflows.

Note: This adapter requires langchain-core to be installed:
    pip install langchain-core

Example:
    >>> from langchain_openai import OpenAIEmbeddings
    >>> from pyplasmod.langchain import PlasmodVectorStore
    >>> from pyplasmod import PlasmodClient
    >>>
    >>> client = PlasmodClient(base_url="http://localhost:8080")
    >>> embeddings = OpenAIEmbeddings()
    >>> vectorstore = PlasmodVectorStore(client=client, embedding=embeddings)
    >>>
    >>> # Add documents
    >>> vectorstore.add_texts(["Hello world", "Goodbye world"])
    >>>
    >>> # Search
    >>> results = vectorstore.similarity_search("Hello", k=5)
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar

from pyplasmod.batch import DEFAULT_BATCH_SIZE, BatchResult, iter_batches, validate_batch_size
from pyplasmod.http.client import PlasmodHttpClient

# Type variable for VectorStore
VST = TypeVar("VST", bound="PlasmodVectorStore")

# Try to import LangChain types - they are optional dependencies
try:
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Define stub classes for type hints when langchain is not installed
    Document = Any  # type: ignore
    Embeddings = Any  # type: ignore
    VectorStore = object  # type: ignore


def _check_langchain_installed() -> None:
    """Raise ImportError if langchain-core is not installed."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "langchain-core is required for LangChain integration. "
            "Install it with: pip install langchain-core"
        )


class PlasmodVectorStore(VectorStore if LANGCHAIN_AVAILABLE else object):  # type: ignore
    """
    LangChain VectorStore implementation for Plasmod.

    This class provides a LangChain-compatible interface for storing and
    retrieving documents using Plasmod as the backend vector store.

    Plasmod Concepts vs LangChain:
        - LangChain Document ≈ Plasmod Event/Memory
        - LangChain metadata ≈ Plasmod payload/attributes
        - LangChain page_content ≈ Plasmod event content/text
        - LangChain id ≈ Plasmod memory_id/event_id

    Attributes:
        client: PlasmodHttpClient instance for API communication.
        embedding: Embeddings model for text vectorization.
        segment_id: Plasmod segment identifier for vector storage.
        workspace_id: Optional workspace identifier for isolation.
        batch_size: Default batch size for bulk operations.

    Supported Operations:
        - add_texts: Add text documents with automatic embedding
        - add_documents: Add LangChain Document objects
        - similarity_search: Find similar documents by text query
        - similarity_search_with_score: Search with relevance scores
        - similarity_search_by_vector: Search using pre-computed vectors

    Not Supported (raises NotImplementedError):
        - delete: Document deletion
        - update: Document updates
        - max_marginal_relevance_search: MMR search
        - Complex metadata filtering (partial support via Plasmod query)
    """

    def __init__(
        self,
        client: PlasmodHttpClient,
        embedding: "Embeddings",
        *,
        segment_id: str = "warm.default",
        workspace_id: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        """
        Initialize PlasmodVectorStore.

        Args:
            client: PlasmodHttpClient instance.
            embedding: LangChain Embeddings model for text vectorization.
            segment_id: Plasmod segment identifier. Defaults to "warm.default".
            workspace_id: Optional workspace ID for data isolation.
            batch_size: Default batch size for bulk operations.

        Raises:
            ImportError: If langchain-core is not installed.
        """
        _check_langchain_installed()

        self._client = client
        self._embedding = embedding
        self._segment_id = segment_id
        self._workspace_id = workspace_id
        self._batch_size = validate_batch_size(batch_size)

    @property
    def embeddings(self) -> Optional["Embeddings"]:
        """Return the embedding model."""
        return self._embedding

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        *,
        ids: Optional[List[str]] = None,
        batch_size: Optional[int] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Add texts to the vector store with automatic embedding.

        This method embeds the texts using the configured embedding model
        and stores them in Plasmod. Large inputs are automatically split
        into batches to avoid memory issues.

        Args:
            texts: Iterable of text strings to add.
            metadatas: Optional list of metadata dicts for each text.
            ids: Optional list of IDs for each text. Auto-generated if not provided.
            batch_size: Override default batch size for this operation.
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            List of IDs for the added texts.

        Raises:
            ValueError: If metadatas or ids length doesn't match texts length.
        """
        texts_list = list(texts)
        n = len(texts_list)

        if n == 0:
            return []

        if metadatas is not None and len(metadatas) != n:
            raise ValueError("metadatas length must match texts length")

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(n)]
        elif len(ids) != n:
            raise ValueError("ids length must match texts length")

        effective_batch_size = batch_size if batch_size is not None else self._batch_size
        effective_batch_size = validate_batch_size(effective_batch_size)

        all_ids: List[str] = []

        for batch_idx, batch_texts in enumerate(iter_batches(texts_list, effective_batch_size)):
            batch_start = batch_idx * effective_batch_size
            batch_end = batch_start + len(batch_texts)

            # Get IDs for this batch
            batch_ids = ids[batch_start:batch_end]

            # Get metadata for this batch
            batch_metadatas: Optional[List[Dict[str, Any]]] = None
            if metadatas is not None:
                batch_metadatas = metadatas[batch_start:batch_end]

            # Embed texts in this batch
            batch_vectors = self._embedding.embed_documents(batch_texts)

            # Ingest vectors
            self._client.rpc_ingest_batch(
                self._segment_id,
                batch_vectors,
                batch_ids,
            )

            # Also ingest as events to preserve text content and metadata
            for i, (text, doc_id) in enumerate(zip(batch_texts, batch_ids)):
                event: Dict[str, Any] = {
                    "event_id": doc_id,
                    "event_type": "document",
                    "payload": {
                        "page_content": text,
                    },
                }

                if self._workspace_id:
                    event["workspace_id"] = self._workspace_id

                if batch_metadatas is not None:
                    event["payload"]["metadata"] = batch_metadatas[i]

                try:
                    self._client.ingest_event(event)
                except Exception:
                    # Event ingestion is best-effort for metadata storage
                    # Vector is already stored, so we continue
                    pass

            all_ids.extend(batch_ids)

        return all_ids

    def add_documents(
        self,
        documents: List["Document"],
        *,
        ids: Optional[List[str]] = None,
        batch_size: Optional[int] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Add LangChain Document objects to the vector store.

        Args:
            documents: List of LangChain Document objects.
            ids: Optional list of IDs. Auto-generated if not provided.
            batch_size: Override default batch size for this operation.
            **kwargs: Additional arguments passed to add_texts.

        Returns:
            List of IDs for the added documents.
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        # Use document IDs if available and ids not explicitly provided
        if ids is None:
            ids = []
            for doc in documents:
                if hasattr(doc, "id") and doc.id is not None:
                    ids.append(doc.id)
                else:
                    ids.append(str(uuid.uuid4()))

        return self.add_texts(
            texts,
            metadatas=metadatas,
            ids=ids,
            batch_size=batch_size,
            **kwargs,
        )

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> List["Document"]:
        """
        Search for documents similar to the query text.

        Args:
            query: Query text to search for.
            k: Number of results to return. Defaults to 4.
            **kwargs: Additional arguments passed to the query.

        Returns:
            List of LangChain Document objects most similar to the query.
        """
        docs_and_scores = self.similarity_search_with_score(query, k=k, **kwargs)
        return [doc for doc, _ in docs_and_scores]

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> List[Tuple["Document", float]]:
        """
        Search for documents similar to the query text, with relevance scores.

        Args:
            query: Query text to search for.
            k: Number of results to return. Defaults to 4.
            **kwargs: Additional arguments passed to the query.

        Returns:
            List of (Document, score) tuples, sorted by relevance.
        """
        # Embed the query
        query_vector = self._embedding.embed_query(query)

        return self.similarity_search_by_vector_with_score(
            query_vector,
            k=k,
            **kwargs,
        )

    def similarity_search_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        **kwargs: Any,
    ) -> List["Document"]:
        """
        Search for documents similar to the given embedding vector.

        Args:
            embedding: Query embedding vector.
            k: Number of results to return. Defaults to 4.
            **kwargs: Additional arguments passed to the query.

        Returns:
            List of LangChain Document objects most similar to the embedding.
        """
        docs_and_scores = self.similarity_search_by_vector_with_score(
            embedding,
            k=k,
            **kwargs,
        )
        return [doc for doc, _ in docs_and_scores]

    def similarity_search_by_vector_with_score(
        self,
        embedding: List[float],
        k: int = 4,
        **kwargs: Any,
    ) -> List[Tuple["Document", float]]:
        """
        Search for documents similar to the given embedding vector, with scores.

        Args:
            embedding: Query embedding vector.
            k: Number of results to return. Defaults to 4.
            **kwargs: Additional arguments passed to the query.

        Returns:
            List of (Document, score) tuples, sorted by relevance.
        """
        _check_langchain_installed()
        from langchain_core.documents import Document

        # Build Plasmod query
        query_body: Dict[str, Any] = {
            "query_vector": embedding,
            "top_k": k,
        }

        if self._workspace_id:
            query_body["workspace_id"] = self._workspace_id

        # Add any additional query parameters
        for key in ["relation_constraints", "filters", "include_payload"]:
            if key in kwargs:
                query_body[key] = kwargs[key]

        # Execute query
        try:
            response = self._client.query(query_body)
        except Exception:
            # Fallback to RPC query if JSON query fails
            try:
                object_ids = self._client.rpc_query_warm(
                    self._segment_id,
                    k,
                    embedding,
                )
                # Convert to document format
                results: List[Tuple[Document, float]] = []
                for i, obj_id in enumerate(object_ids):
                    doc = Document(
                        page_content="",  # Content not available from RPC query
                        metadata={"id": obj_id},
                    )
                    # Score is position-based (lower is better)
                    score = 1.0 - (i / max(len(object_ids), 1))
                    results.append((doc, score))
                return results
            except Exception:
                return []

        # Parse response
        results: List[Tuple[Document, float]] = []

        objects = response.get("objects", []) if isinstance(response, dict) else []
        for obj in objects:
            # Extract content and metadata
            page_content = ""
            metadata: Dict[str, Any] = {}

            if isinstance(obj, dict):
                # Try to get page_content from various fields
                payload = obj.get("payload", {})
                if isinstance(payload, dict):
                    page_content = payload.get("page_content", "")
                    metadata = payload.get("metadata", {})

                # Add object ID to metadata
                if "object_id" in obj:
                    metadata["id"] = obj["object_id"]
                elif "memory_id" in obj:
                    metadata["id"] = obj["memory_id"]
                elif "event_id" in obj:
                    metadata["id"] = obj["event_id"]

                # Get score
                score = obj.get("score", obj.get("distance", 0.0))
            else:
                # Simple string ID
                metadata["id"] = str(obj)
                score = 0.0

            doc = Document(page_content=page_content, metadata=metadata)
            results.append((doc, float(score)))

        return results

    @classmethod
    def from_texts(
        cls: Type[VST],
        texts: List[str],
        embedding: "Embeddings",
        metadatas: Optional[List[Dict[str, Any]]] = None,
        *,
        client: Optional[PlasmodHttpClient] = None,
        base_url: str = "http://127.0.0.1:8080",
        segment_id: str = "warm.default",
        batch_size: int = DEFAULT_BATCH_SIZE,
        **kwargs: Any,
    ) -> VST:
        """
        Create a PlasmodVectorStore from a list of texts.

        This is a convenience method that creates a new vector store and
        adds the provided texts in one step.

        Args:
            texts: List of texts to add.
            embedding: Embeddings model for text vectorization.
            metadatas: Optional list of metadata dicts.
            client: Optional PlasmodHttpClient. Created if not provided.
            base_url: Plasmod server URL (used if client not provided).
            segment_id: Plasmod segment identifier.
            batch_size: Batch size for bulk operations.
            **kwargs: Additional arguments.

        Returns:
            PlasmodVectorStore instance with texts added.
        """
        if client is None:
            client = PlasmodHttpClient(base_url=base_url)

        store = cls(
            client=client,
            embedding=embedding,
            segment_id=segment_id,
            batch_size=batch_size,
        )

        store.add_texts(texts, metadatas=metadatas, batch_size=batch_size)

        return store

    @classmethod
    def from_documents(
        cls: Type[VST],
        documents: List["Document"],
        embedding: "Embeddings",
        *,
        client: Optional[PlasmodHttpClient] = None,
        base_url: str = "http://127.0.0.1:8080",
        segment_id: str = "warm.default",
        batch_size: int = DEFAULT_BATCH_SIZE,
        **kwargs: Any,
    ) -> VST:
        """
        Create a PlasmodVectorStore from a list of Documents.

        Args:
            documents: List of LangChain Document objects.
            embedding: Embeddings model for text vectorization.
            client: Optional PlasmodHttpClient.
            base_url: Plasmod server URL (used if client not provided).
            segment_id: Plasmod segment identifier.
            batch_size: Batch size for bulk operations.
            **kwargs: Additional arguments.

        Returns:
            PlasmodVectorStore instance with documents added.
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        return cls.from_texts(
            texts,
            embedding,
            metadatas=metadatas,
            client=client,
            base_url=base_url,
            segment_id=segment_id,
            batch_size=batch_size,
            **kwargs,
        )

    def delete(
        self,
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Optional[bool]:
        """
        Delete documents by ID.

        Note: This operation is NOT currently supported by Plasmod.
        Plasmod is designed as an append-only event store with provenance tracking.

        Args:
            ids: List of document IDs to delete.
            **kwargs: Additional arguments.

        Raises:
            NotImplementedError: Always raised as deletion is not supported.
        """
        raise NotImplementedError(
            "Document deletion is not supported by Plasmod. "
            "Plasmod is designed as an append-only event store with provenance tracking. "
            "Consider using workspace isolation or event expiration policies instead."
        )

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        **kwargs: Any,
    ) -> List["Document"]:
        """
        Maximum Marginal Relevance search.

        Note: MMR is NOT currently supported by Plasmod.

        Args:
            query: Query text.
            k: Number of results to return.
            fetch_k: Number of candidates to fetch.
            lambda_mult: Diversity parameter.
            **kwargs: Additional arguments.

        Raises:
            NotImplementedError: Always raised as MMR is not supported.
        """
        raise NotImplementedError(
            "Maximum Marginal Relevance (MMR) search is not currently supported by Plasmod. "
            "Use similarity_search instead."
        )

    def as_retriever(self, **kwargs: Any) -> Any:
        """
        Return a LangChain Retriever interface for this vector store.

        Args:
            **kwargs: Arguments passed to VectorStoreRetriever.

        Returns:
            VectorStoreRetriever instance.

        Raises:
            ImportError: If langchain-core is not installed.
        """
        _check_langchain_installed()
        from langchain_core.vectorstores import VectorStoreRetriever

        return VectorStoreRetriever(vectorstore=self, **kwargs)
