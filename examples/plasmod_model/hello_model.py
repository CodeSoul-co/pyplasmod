# Demonstrates dense / sparse / hybrid embedding helpers from the optional embedding SDK (namespace loaded at runtime).
import importlib
import time

from pyplasmod._interop_names import embedding_sdk_namespace

_ns = embedding_sdk_namespace()
_dense = importlib.import_module(_ns + ".model.dense")
_hybrid = importlib.import_module(_ns + ".model.hybrid")
_sparse = importlib.import_module(_ns + ".model.sparse")

OpenAIEmbeddingFunction = _dense.OpenAIEmbeddingFunction
SentenceTransformerEmbeddingFunction = _dense.SentenceTransformerEmbeddingFunction
BGEM3EmbeddingFunction = _hybrid.BGEM3EmbeddingFunction
BM25EmbeddingFunction = _sparse.BM25EmbeddingFunction
SpladeEmbeddingFunction = _sparse.SpladeEmbeddingFunction

fmt = "=== {:30} ==="


def log(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " " + msg)


# OpenAIEmbeddingFunction usage
docs = [
    "Artificial intelligence was founded as an academic discipline in 1956.",
    "Alan Turing was the first person to conduct substantial research in AI.",
    "Born in Maida Vale, London, Turing was raised in southern England.",
]


def main():
    log(fmt.format("OpenAIEmbeddingFunction"))
    try:
        open_ai_ef = OpenAIEmbeddingFunction(
            model_name="text-embedding-3-small",
            dimensions=256,
        )
        vectors = open_ai_ef.encode_documents(docs)
        log(f"Encoded {len(vectors)} dense vectors")
    except Exception as exc:
        log(f"OpenAI demo skipped: {exc}")

    log(fmt.format("SentenceTransformerEmbeddingFunction"))
    try:
        sentence_transformer_ef = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
        )
        vectors = sentence_transformer_ef.encode_documents(docs)
        log(f"Encoded {len(vectors)} dense vectors")
    except Exception as exc:
        log(f"SentenceTransformer demo skipped: {exc}")

    log(fmt.format("BM25EmbeddingFunction"))
    try:
        bm25_ef = BM25EmbeddingFunction()
        bm25_ef.fit([docs])
        vectors = bm25_ef.encode_documents(docs)
        log(f"Encoded {len(vectors)} sparse vectors")
    except Exception as exc:
        log(f"BM25 demo skipped: {exc}")

    log(fmt.format("SpladeEmbeddingFunction"))
    try:
        splade_ef = SpladeEmbeddingFunction()
        vectors = splade_ef.encode_documents(docs)
        log(f"Encoded {len(vectors)} sparse vectors")
    except Exception as exc:
        log(f"Splade demo skipped: {exc}")

    log(fmt.format("BGEM3EmbeddingFunction"))
    try:
        bgem3_ef = BGEM3EmbeddingFunction()
        bgem3_ef.fit([docs])
        dense_vectors, sparse_vectors = bgem3_ef.encode_documents(docs)
        log(f"Encoded hybrid dense={len(dense_vectors)} sparse={len(sparse_vectors)}")
    except Exception as exc:
        log(f"BGEM3 demo skipped: {exc}")


if __name__ == "__main__":
    main()
