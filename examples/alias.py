import time
import numpy as np
from pyplasmod import (
    PlasmodClient,
)

fmt = "\n=== {:30} ===\n"
dim = 8
collection_name = "hello_plasmod"
plasmod_client = PlasmodClient("http://localhost:19530")
plasmod_client.drop_collection(collection_name)
plasmod_client.create_collection(collection_name, dim, consistency_level="Strong", metric_type="L2", auto_id=True)

collection_name2 = "hello_plasmod2"
plasmod_client.drop_collection(collection_name2)
plasmod_client.create_collection(collection_name2, dim, consistency_level="Strong", metric_type="L2", auto_id=True)


print("collections:", plasmod_client.list_collections())

desc_c1 = plasmod_client.describe_collection(collection_name)
print(f"{collection_name} :", desc_c1)

rng = np.random.default_rng(seed=19530)

rows = [
    {"vector": rng.random((1, dim))[0], "a": 100},
    {"vector": rng.random((1, dim))[0], "b": 200},
    {"vector": rng.random((1, dim))[0], "c": 300},
]

print(fmt.format(f"Start inserting entities to {collection_name}"))
insert_result = plasmod_client.insert(collection_name, rows)
print(insert_result)

rows = [
    {"vector": rng.random((1, dim))[0], "d": 400},
    {"vector": rng.random((1, dim))[0], "e": 500},
    {"vector": rng.random((1, dim))[0], "f": 600},
]

print(fmt.format(f"Start inserting entities to {collection_name2}"))
insert_result2 = plasmod_client.insert(collection_name2, rows)
print(insert_result2)



alias = "alias_hello_plasmod"
plasmod_client.drop_alias(alias)
plasmod_client.create_alias(collection_name, alias)

aliases =  plasmod_client.list_aliases(collection_name)
print(f"aliases of {collection_name} is:", aliases)


alias_info =  plasmod_client.describe_alias(alias)
print(f"info of {alias} is:", alias_info)

assert plasmod_client.describe_collection(alias) == plasmod_client.describe_collection(collection_name)

plasmod_client.alter_alias(collection_name2, alias)
assert plasmod_client.describe_collection(alias) == plasmod_client.describe_collection(collection_name2)

query_results = plasmod_client.query(alias, filter= "f == 600")
print("results of query 'f == 600' is ")
for ret in query_results: 
    print(ret)


plasmod_client.drop_alias(alias)
has_collection = plasmod_client.has_collection(alias)
assert not has_collection
has_collection = plasmod_client.has_collection(collection_name2)
assert has_collection

plasmod_client.drop_collection(collection_name)
plasmod_client.drop_collection(collection_name2)
