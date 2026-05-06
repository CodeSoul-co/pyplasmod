import sys

import numpy as np
import pytest
from pyplasmod._interop_names import lite_embedding_package
from pyplasmod.plasmod_client import PlasmodClient

pytest.importorskip(lite_embedding_package(), reason="optional local embedded engine not installed")


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="local embedded engine not supported on Windows"
)
class TestLocalEmbeddedEngine:
    def test_plasmod_client_with_local_db_path(self, tmp_path):
        """PlasmodClient(.db path) should connect via optional embedded server."""
        db_file = tmp_path / "test.db"
        client = PlasmodClient(db_file.as_posix(), timeout=10)
        try:
            collections = client.list_collections()
            assert isinstance(collections, list)
        finally:
            client.close()

    def test_local_engine_insert_search(self, tmp_path):
        """End-to-end: create collection, insert, search, query, delete."""
        db_file = tmp_path / "test.db"
        client = PlasmodClient(db_file.as_posix(), timeout=10)
        try:
            client.create_collection(collection_name="demo_collection", dimension=3)

            rng = np.random.default_rng(seed=19530)
            vectors = [[rng.uniform(-1, 1) for _ in range(3)] for _ in range(3)]
            data = [
                {"id": i, "vector": vectors[i], "text": f"doc_{i}", "subject": "history"}
                for i in range(len(vectors))
            ]
            res = client.insert(collection_name="demo_collection", data=data)
            assert res["insert_count"] == 3

            res = client.search(
                collection_name="demo_collection",
                data=[vectors[0]],
                filter="subject == 'history'",
                limit=2,
                output_fields=["text", "subject"],
            )
            assert len(res[0]) == 2

            res = client.query(
                collection_name="demo_collection",
                filter="subject == 'history'",
                output_fields=["text", "subject"],
            )
            assert len(res) == 3

            res = client.delete(
                collection_name="demo_collection",
                filter="subject == 'history'",
            )
            assert len(res) == 3
        finally:
            client.close()

    def test_local_engine_multiple_clients_same_db(self, tmp_path):
        """Two clients sharing the same .db file should work."""
        db_file = tmp_path / "shared.db"
        client1 = PlasmodClient(db_file.as_posix(), timeout=10)
        try:
            client1.create_collection(collection_name="col1", dimension=3)
            assert "col1" in client1.list_collections()

            client2 = PlasmodClient(db_file.as_posix(), timeout=10)
            try:
                assert "col1" in client2.list_collections()
            finally:
                client2.close()
        finally:
            client1.close()
