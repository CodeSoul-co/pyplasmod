"""
Example: LangChain integration with Plasmod.

This example demonstrates how to use Plasmod as a LangChain VectorStore
for document storage and similarity search.

Requirements:
    pip install langchain-core langchain-openai

Requires a running Plasmod server at http://127.0.0.1:8080
"""

from __future__ import annotations

import os
from typing import List

# Check for required dependencies
try:
    from langchain_core.documents import Document
except ImportError:
    print("Error: langchain-core is required.")
    print("Install with: pip install langchain-core")
    exit(1)

from pyplasmod import PlasmodClient
from pyplasmod.langchain import PlasmodVectorStore


class SimpleEmbeddings:
    """
    Simple mock embeddings for demonstration.

    In production, use a real embedding model like:
    - langchain_openai.OpenAIEmbeddings
    - langchain_huggingface.HuggingFaceEmbeddings
    - langchain_community.embeddings.OllamaEmbeddings
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        # Simple hash-based embedding for demo purposes
        embeddings = []
        for text in texts:
            # Create a deterministic embedding based on text hash
            hash_val = hash(text)
            embedding = [
                ((hash_val >> i) & 0xFF) / 255.0
                for i in range(0, self.dim * 8, 8)
            ][:self.dim]
            # Pad if needed
            while len(embedding) < self.dim:
                embedding.append(0.0)
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        return self.embed_documents([text])[0]


def example_basic_usage():
    """Basic usage: add texts and search."""
    print("=" * 60)
    print("Example: Basic LangChain VectorStore Usage")
    print("=" * 60)

    # Create Plasmod client
    client = PlasmodClient(base_url="http://127.0.0.1:8080")

    # Create embeddings (use OpenAIEmbeddings in production)
    embeddings = SimpleEmbeddings(dim=128)

    # Create vector store
    vectorstore = PlasmodVectorStore(
        client=client,
        embedding=embeddings,
        segment_id="warm.default",
        batch_size=100,
    )

    # Add texts
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a subset of artificial intelligence.",
        "Python is a popular programming language.",
        "Vector databases store and search embeddings efficiently.",
        "LangChain helps build LLM applications.",
    ]

    print(f"Adding {len(texts)} texts...")
    ids = vectorstore.add_texts(texts)
    print(f"Added texts with IDs: {ids}")

    # Search
    print("\nSearching for 'artificial intelligence'...")
    results = vectorstore.similarity_search("artificial intelligence", k=3)

    print(f"Found {len(results)} results:")
    for i, doc in enumerate(results):
        print(f"  {i+1}. {doc.page_content[:50]}...")


def example_with_metadata():
    """Add documents with metadata."""
    print("\n" + "=" * 60)
    print("Example: Documents with Metadata")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")
    embeddings = SimpleEmbeddings(dim=128)

    vectorstore = PlasmodVectorStore(
        client=client,
        embedding=embeddings,
    )

    # Add texts with metadata
    texts = [
        "Introduction to machine learning",
        "Advanced deep learning techniques",
        "Natural language processing basics",
    ]
    metadatas = [
        {"source": "textbook", "chapter": 1, "difficulty": "beginner"},
        {"source": "paper", "chapter": 5, "difficulty": "advanced"},
        {"source": "tutorial", "chapter": 2, "difficulty": "intermediate"},
    ]

    print("Adding texts with metadata...")
    ids = vectorstore.add_texts(texts, metadatas=metadatas)
    print(f"Added {len(ids)} documents")

    # Search with scores
    print("\nSearching with scores...")
    results = vectorstore.similarity_search_with_score("deep learning", k=2)

    for doc, score in results:
        print(f"  Score: {score:.3f}")
        print(f"  Content: {doc.page_content}")
        print(f"  Metadata: {doc.metadata}")
        print()


def example_add_documents():
    """Add LangChain Document objects."""
    print("=" * 60)
    print("Example: Add LangChain Documents")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")
    embeddings = SimpleEmbeddings(dim=128)

    vectorstore = PlasmodVectorStore(
        client=client,
        embedding=embeddings,
    )

    # Create Document objects
    documents = [
        Document(
            page_content="Plasmod is an agent-native database.",
            metadata={"source": "docs", "topic": "database"},
        ),
        Document(
            page_content="LangChain provides tools for LLM applications.",
            metadata={"source": "docs", "topic": "framework"},
        ),
        Document(
            page_content="Vector search enables semantic similarity.",
            metadata={"source": "tutorial", "topic": "search"},
        ),
    ]

    print(f"Adding {len(documents)} documents...")
    ids = vectorstore.add_documents(documents)
    print(f"Document IDs: {ids}")


def example_batch_processing():
    """Demonstrate batch processing for large datasets."""
    print("\n" + "=" * 60)
    print("Example: Batch Processing Large Dataset")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")
    embeddings = SimpleEmbeddings(dim=128)

    vectorstore = PlasmodVectorStore(
        client=client,
        embedding=embeddings,
        batch_size=50,  # Process 50 documents at a time
    )

    # Generate a larger dataset
    texts = [f"Document number {i} with some content about topic {i % 10}." for i in range(200)]

    print(f"Adding {len(texts)} texts with batch_size=50...")
    ids = vectorstore.add_texts(texts, batch_size=50)
    print(f"Added {len(ids)} documents")


def example_from_texts():
    """Create vector store from texts in one step."""
    print("\n" + "=" * 60)
    print("Example: Create VectorStore from Texts")
    print("=" * 60)

    embeddings = SimpleEmbeddings(dim=128)

    texts = [
        "First document",
        "Second document",
        "Third document",
    ]

    print("Creating vector store from texts...")
    vectorstore = PlasmodVectorStore.from_texts(
        texts=texts,
        embedding=embeddings,
        base_url="http://127.0.0.1:8080",
        segment_id="warm.default",
    )

    print("Vector store created and populated!")

    # Search
    results = vectorstore.similarity_search("document", k=2)
    print(f"Search results: {len(results)} documents found")


def example_as_retriever():
    """Use as a LangChain Retriever."""
    print("\n" + "=" * 60)
    print("Example: Use as LangChain Retriever")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")
    embeddings = SimpleEmbeddings(dim=128)

    vectorstore = PlasmodVectorStore(
        client=client,
        embedding=embeddings,
    )

    # Add some documents
    vectorstore.add_texts([
        "The capital of France is Paris.",
        "The capital of Germany is Berlin.",
        "The capital of Italy is Rome.",
    ])

    # Get retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    print("Retriever created!")
    print(f"Retriever type: {type(retriever).__name__}")

    # Use retriever (in a real app, this would be part of a chain)
    # docs = retriever.invoke("What is the capital of France?")


def example_error_handling():
    """Demonstrate error handling for unsupported operations."""
    print("\n" + "=" * 60)
    print("Example: Error Handling")
    print("=" * 60)

    client = PlasmodClient(base_url="http://127.0.0.1:8080")
    embeddings = SimpleEmbeddings(dim=128)

    vectorstore = PlasmodVectorStore(
        client=client,
        embedding=embeddings,
    )

    # Try delete (not supported)
    print("Attempting delete operation...")
    try:
        vectorstore.delete(ids=["id1", "id2"])
    except NotImplementedError as e:
        print(f"  NotImplementedError: {e}")

    # Try MMR search (not supported)
    print("\nAttempting MMR search...")
    try:
        vectorstore.max_marginal_relevance_search("query", k=5)
    except NotImplementedError as e:
        print(f"  NotImplementedError: {e}")


def main():
    """Run all examples."""
    print("Plasmod LangChain Integration Examples")
    print("======================================\n")
    print("Note: These examples require:")
    print("  1. A running Plasmod server at http://127.0.0.1:8080")
    print("  2. langchain-core installed (pip install langchain-core)")
    print()

    try:
        example_basic_usage()
        example_with_metadata()
        example_add_documents()
        example_batch_processing()
        example_from_texts()
        example_as_retriever()
        example_error_handling()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure Plasmod server is running at http://127.0.0.1:8080")


if __name__ == "__main__":
    main()
