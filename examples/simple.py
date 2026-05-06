import time
import numpy as np
from pyplasmod import (
    PlasmodClient,
)

fmt = "\n=== {:30} ===\n"
dim = 8
collection_name = "hello_plasmod"
plasmod_client = PlasmodClient("http://localhost:19530")

has_collection = plasmod_client.has_collection(collection_name, timeout=5)
if has_collection:
    plasmod_client.drop_collection(collection_name)
plasmod_client.create_collection(collection_name, dim, consistency_level="Strong", metric_type="L2")

print(fmt.format("    all collections    "))
print(plasmod_client.list_collections())

print(fmt.format(f"schema of collection {collection_name}"))
print(plasmod_client.describe_collection(collection_name))

rng = np.random.default_rng(seed=19530)
rows = [
        {"id": 1, "vector": rng.random((1, dim))[0], "a": 100},
        {"id": 2, "vector": rng.random((1, dim))[0], "b": 200},
        {"id": 3, "vector": rng.random((1, dim))[0], "c": 300},
        {"id": 4, "vector": rng.random((1, dim))[0], "d": 400},
        {"id": 5, "vector": rng.random((1, dim))[0], "e": 500},
        {"id": 6, "vector": rng.random((1, dim))[0], "f": 600},
]

print(fmt.format("Start inserting entities"))
insert_result = plasmod_client.insert(collection_name, rows, progress_bar=True)
print(fmt.format("Inserting entities done"))
print(insert_result)

print(fmt.format("Start query by specifying primary keys"))
query_results = plasmod_client.query(collection_name, ids=[2])
print(query_results[0])

upsert_ret = plasmod_client.upsert(collection_name, {"id": 2 , "vector": rng.random((1, dim))[0], "g": 100})
print(upsert_ret)

print(fmt.format("Start query by specifying primary keys"))
query_results = plasmod_client.query(collection_name, ids=[2])
print(query_results[0])


print(fmt.format("Start query by specifying filtering expression"))
query_results = plasmod_client.query(collection_name, filter= "f == 600")
for ret in query_results:
    print(ret)


print(f"start to delete by specifying filter in collection {collection_name}")
delete_result = plasmod_client.delete(collection_name, ids=[6])
print(delete_result)

print(fmt.format("Start query by specifying filtering expression"))
query_results = plasmod_client.query(collection_name, filter= "f == 600")
assert len(query_results) == 0

rng = np.random.default_rng(seed=19530)
vectors_to_search = rng.random((1, dim))

print(fmt.format(f"Start search with retrieve several fields."))
result = plasmod_client.search(collection_name, vectors_to_search, limit=3, output_fields=["pk", "a", "b"])
for hits in result:
    for hit in hits:
        print(f"hit: {hit}")

plasmod_client.drop_collection(collection_name)
