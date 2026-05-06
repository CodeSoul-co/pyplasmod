import numpy as np
from pyplasmod import (
    PlasmodClient,
    DataType,
    AnnSearchRequest, RRFRanker, WeightedRanker,
)

fmt = "\n=== {:30} ===\n"
search_latency_fmt = "search latency = {:.4f}s"
num_entities, dim = 3000, 8

collection_name = "hello_plasmod"
plasmod_client = PlasmodClient("http://localhost:19530")

has_collection = plasmod_client.has_collection(collection_name, timeout=5)
if has_collection:
    plasmod_client.drop_collection(collection_name)

schema = plasmod_client.create_schema(auto_id=False, description="hello_plasmod is the simplest demo to introduce the APIs")
schema.add_field("pk", DataType.VARCHAR, is_primary=True, max_length=100)
schema.add_field("random", DataType.DOUBLE)
schema.add_field("embeddings", DataType.FLOAT_VECTOR, dim=dim)
schema.add_field("embeddings2", DataType.FLOAT_VECTOR, dim=dim)

index_params = plasmod_client.prepare_index_params()
index_params.add_index(field_name = "embeddings", index_type = "IVF_FLAT", metric_type="L2", nlist=128)
index_params.add_index(field_name = "embeddings2",index_type = "IVF_FLAT", metric_type="L2", nlist=128)

print(fmt.format("Create collection `hello_plasmod`"))

plasmod_client.create_collection(collection_name, schema=schema, index_params=index_params, consistency_level="Strong")

print(fmt.format("Start inserting entities"))
rng = np.random.default_rng(seed=19530)
entities = [
    # provide the pk field because `auto_id` is set to False
    [str(i) for i in range(num_entities)],
    rng.random(num_entities).tolist(),  # field random, only supports list
    rng.random((num_entities, dim)),    # field embeddings, supports numpy.ndarray and list
    rng.random((num_entities, dim)),    # field embeddings2, supports numpy.ndarray and list
]

rows = [ {"pk": entities[0][i], "random": entities[1][i], "embeddings": entities[2][i], "embeddings2": entities[3][i]} for i in range (num_entities)]

insert_result = plasmod_client.insert(collection_name, rows)


print(fmt.format("Start loading"))
plasmod_client.load_collection(collection_name)

field_names = ["embeddings", "embeddings2"]

req_list = []
nq = 1
default_limit = 5
vectors_to_search = []

for i in range(len(field_names)):
    # 4. generate search data
    vectors_to_search = rng.random((nq, dim))
    search_param = {
        "data": vectors_to_search,
        "anns_field": field_names[i],
        "param": {"metric_type": "L2"},
        "limit": default_limit,
        "expr": "random > 0.5"}
    req = AnnSearchRequest(**search_param)
    req_list.append(req)

print(fmt.format("rank by RRFRanker"))
hybrid_res = plasmod_client.hybrid_search(collection_name, req_list, RRFRanker(), default_limit, output_fields=["random"])
for hits in hybrid_res:
    for hit in hits:
        print(f" hybrid search hit: {hit}")

req_list = []
for i in range(len(field_names)):
    # 4. generate search data
    vectors_to_search = rng.random((nq, dim))
    search_param = {
        "data": vectors_to_search,
        "anns_field": field_names[i],
        "param": {"metric_type": "L2"},
        "limit": default_limit,
        "expr": "random > {radius}",
        "expr_params": {"radius": 0.5}}
    req = AnnSearchRequest(**search_param)
    req_list.append(req)

print(fmt.format("rank by RRFRanker with expression template"))
hybrid_res = plasmod_client.hybrid_search(collection_name, req_list, RRFRanker(), default_limit, output_fields=["random"])
for hits in hybrid_res:
    for hit in hits:
        print(f" hybrid search hit: {hit}")
