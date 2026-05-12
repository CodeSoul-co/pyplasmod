# Milvus to Plasmod Migration Guide

This document provides a mapping between Milvus and Plasmod concepts, helping users understand how to migrate from Milvus to Plasmod or use both systems effectively.

## Overview

**Milvus** is a vector database focused on similarity search with traditional database concepts (collections, schemas, indexes).

**Plasmod** is an agent-native database designed for multi-agent systems, focusing on cognitive object storage, event-driven materialization, and structured evidence retrieval with provenance tracking.

> **Important**: Plasmod is NOT a drop-in replacement for Milvus. They serve different use cases and have different design philosophies.

## Concept Mapping

| Milvus Concept | Plasmod Equivalent | Notes |
|----------------|-------------------|-------|
| Collection | Workspace / Namespace | Not a direct equivalent. Plasmod workspaces provide isolation but don't require explicit schema definition. |
| Schema | N/A (Schema-less) | Plasmod uses flexible event/memory structures without predefined schemas. |
| Primary Key | `memory_id` / `event_id` | Plasmod auto-generates IDs or accepts user-provided IDs. |
| Vector Field | Embedded in Event/Memory | Vectors are part of the event payload or ingested separately. |
| Scalar Fields | `payload` / `attributes` | Arbitrary JSON payload attached to events/memories. |
| Partition | Session / Agent scope | Plasmod uses session_id and agent_id for logical partitioning. |
| Index | Warm Segment | Plasmod manages indexing internally via warm segments. |
| Metric Type | Configured server-side | Distance metrics are configured at the Plasmod server level. |

## API Mapping

### Supported Operations

| Milvus API | Plasmod API | Status |
|------------|-------------|--------|
| `insert()` | `ingest_event()` / `ingest_batch()` | ✅ Supported |
| `search()` | `query()` / `rpc_query_warm()` | ✅ Supported |
| `query()` (filter) | `query()` with constraints | ✅ Partial support |
| Batch insert | `ingest_batch()` with `batch_size` | ✅ Supported |
| Top-K search | `query()` with `top_k` | ✅ Supported |

### Not Supported (By Design)

| Milvus API | Plasmod Status | Reason |
|------------|----------------|--------|
| `create_collection()` | ❌ Not applicable | Plasmod is schema-less; workspaces are created implicitly. |
| `drop_collection()` | ❌ Not supported | Plasmod is append-only with provenance tracking. Use `dataset_purge()` for admin cleanup. |
| `create_index()` | ❌ Not applicable | Indexing is managed internally by Plasmod. |
| `load_collection()` | ❌ Not applicable | Plasmod manages memory automatically. |
| `release_collection()` | ❌ Not applicable | Plasmod manages memory automatically. |
| `delete()` | ❌ Not supported | Append-only design. Use event expiration or workspace isolation. |
| `upsert()` | ❌ Not supported | Append-only design. Ingest new events instead. |
| `create_partition()` | ❌ Not applicable | Use `session_id` / `agent_id` for logical partitioning. |
| Complex metadata filters | ⚠️ Limited | Plasmod supports `relation_constraints` but not full SQL-like filtering. |

### Should Not Be Implemented

These Milvus features conflict with Plasmod's design goals:

1. **Schema Management**: Plasmod's flexibility comes from being schema-less.
2. **Explicit Index Control**: Plasmod optimizes indexing automatically.
3. **Delete/Update Operations**: Plasmod maintains provenance and audit trails.
4. **Collection Lifecycle**: Plasmod workspaces are lightweight and implicit.

## Migration Guide

### From Milvus Insert to Plasmod Ingest

**Milvus:**
```python
from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")
client.insert(
    collection_name="my_collection",
    data=[
        {"id": 1, "vector": [0.1, 0.2, ...], "text": "hello"},
        {"id": 2, "vector": [0.3, 0.4, ...], "text": "world"},
    ]
)
```

**Plasmod:**
```python
from pyplasmod import PlasmodClient

client = PlasmodClient(base_url="http://localhost:8080")

# Option 1: Ingest as events (preserves metadata)
for item in data:
    client.ingest_event({
        "event_id": str(item["id"]),
        "event_type": "document",
        "payload": {"text": item["text"]},
    })

# Option 2: Batch ingest vectors (high performance)
vectors = [item["vector"] for item in data]
object_ids = [str(item["id"]) for item in data]
result = client.ingest_batch(
    segment_id="warm.default",
    vectors=vectors,
    object_ids=object_ids,
    batch_size=500,  # Automatic batching
)
print(f"Ingested {result.accepted_count} vectors in {result.batch_count} batches")
```

### From Milvus Search to Plasmod Query

**Milvus:**
```python
results = client.search(
    collection_name="my_collection",
    data=[[0.1, 0.2, ...]],
    limit=10,
    output_fields=["text"],
)
```

**Plasmod:**
```python
# Option 1: JSON query (with metadata)
results = client.query({
    "query_vector": [0.1, 0.2, ...],
    "top_k": 10,
})

# Option 2: Binary RPC query (high performance)
object_ids = client.rpc_query_warm(
    segment_id="warm.default",
    top_k=10,
    vector=[0.1, 0.2, ...],
)
```

### Using LangChain Adapter

For LangChain users, Plasmod provides a VectorStore adapter:

```python
from langchain_openai import OpenAIEmbeddings
from pyplasmod import PlasmodClient
from pyplasmod.langchain import PlasmodVectorStore

client = PlasmodClient(base_url="http://localhost:8080")
embeddings = OpenAIEmbeddings()

vectorstore = PlasmodVectorStore(
    client=client,
    embedding=embeddings,
    batch_size=500,
)

# Add documents (automatically batched)
vectorstore.add_texts(["Hello world", "Goodbye world"])

# Search
docs = vectorstore.similarity_search("Hello", k=5)
```

## Capability Matrix

| Capability | Milvus | Plasmod | Notes |
|------------|--------|---------|-------|
| Vector similarity search | ✅ | ✅ | Core feature in both |
| Batch ingestion | ✅ | ✅ | Plasmod auto-batches large inputs |
| Metadata storage | ✅ | ✅ | Via `payload` in Plasmod |
| Top-K queries | ✅ | ✅ | |
| Workspace isolation | ✅ (collections) | ✅ (workspaces) | |
| Schema definition | ✅ Required | ❌ Schema-less | |
| Index management | ✅ Manual | ✅ Automatic | |
| Delete operations | ✅ | ❌ | Plasmod is append-only |
| Update operations | ✅ | ❌ | Plasmod is append-only |
| Provenance tracking | ❌ | ✅ | Plasmod tracks event lineage |
| Multi-agent support | ❌ | ✅ | Core Plasmod feature |
| Session management | ❌ | ✅ | Core Plasmod feature |
| LangChain integration | ✅ | ✅ | Via `PlasmodVectorStore` |

## When to Use Which

### Use Milvus When:
- You need traditional database operations (CRUD)
- You require explicit schema control
- You need complex metadata filtering
- You're building a general-purpose vector search application

### Use Plasmod When:
- You're building multi-agent AI systems
- You need provenance and audit trails
- You want event-driven architecture
- You need session/agent-scoped data isolation
- You prefer schema-less flexibility

## Error Handling

When migrating, be aware that some Milvus operations will raise `NotImplementedError` in Plasmod:

```python
from pyplasmod.langchain import PlasmodVectorStore

vectorstore = PlasmodVectorStore(...)

# This will raise NotImplementedError
try:
    vectorstore.delete(ids=["id1", "id2"])
except NotImplementedError as e:
    print(f"Not supported: {e}")
    # Alternative: Use workspace isolation or event expiration
```

## Questions?

For more information:
- Plasmod documentation: See `docs/sdk/README.md` in the Plasmod repository
- pyplasmod SDK: See `README.md` in this repository
- LangChain integration: See `pyplasmod/langchain/vectorstore.py`
