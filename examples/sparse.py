from pyplasmod import (
    PlasmodClient,
    FieldSchema, CollectionSchema, DataType,
)

import random

def generate_sparse_vector(dimension: int, non_zero_count: int) -> dict:
    indices = random.sample(range(dimension), non_zero_count)
    values = [random.random() for _ in range(non_zero_count)]
    sparse_vector = {index: value for index, value in zip(indices, values)}
    return sparse_vector


fmt = "\n=== {:30} ===\n"
dim = 100
non_zero_count = 20
collection_name = "hello_sparse"
plasmod_client = PlasmodClient("http://localhost:19530")

has_collection = plasmod_client.has_collection(collection_name, timeout=5)
if has_collection:
    plasmod_client.drop_collection(collection_name)
fields = [
    FieldSchema(name="pk", dtype=DataType.VARCHAR,
                is_primary=True, auto_id=True, max_length=100),
    FieldSchema(name="random", dtype=DataType.DOUBLE),
    FieldSchema(name="embeddings", dtype=DataType.SPARSE_FLOAT_VECTOR),
]
schema = CollectionSchema(
    fields, "demo for using sparse float vector with plasmod client")
index_params = plasmod_client.prepare_index_params()
index_params.add_index(field_name="embeddings", index_name="sparse_inverted_index",
                       index_type="SPARSE_INVERTED_INDEX", metric_type="IP", params={"drop_ratio_build": 0.2})
plasmod_client.create_collection(collection_name, schema=schema,
                                index_params=index_params, timeout=5, consistency_level="Strong")

print(fmt.format("    all collections    "))
print(plasmod_client.list_collections())

print(fmt.format(f"schema of collection {collection_name}"))
print(plasmod_client.describe_collection(collection_name))

N = 6
rows = [{"random": i, "embeddings": generate_sparse_vector(
    dim, non_zero_count)} for i in range(N)]

print(fmt.format("Start inserting entities"))
insert_result = plasmod_client.insert(collection_name, rows, progress_bar=True)
print(fmt.format("Inserting entities done"))
print(insert_result)

print(fmt.format(f"Start vector anns search."))
vectors_to_search = [generate_sparse_vector(dim, non_zero_count)]
search_params = {
    "metric_type": "IP",
    "params": {
        "drop_ratio_search": 0.2,
    }
}
# no need to specify anns_field for collections with only 1 vector field
result = plasmod_client.search(collection_name, vectors_to_search, limit=3, output_fields=[
                              "pk", "random", "embeddings"], search_params=search_params)
for hits in result:
    for hit in hits:
        print(f"hit: {hit}")

print(fmt.format("Start query by specifying filtering expression"))
query_results = plasmod_client.query(collection_name, filter="random < 3")
pks = [ret['pk'] for ret in query_results]
for ret in query_results:
    print(ret)

print(fmt.format("Start query by specifying primary keys"))
query_results = plasmod_client.query(
    collection_name, filter=f"pk == '{pks[0]}'")
print(query_results[0])

print(f"start to delete by specifying filter in collection {collection_name}")
delete_result = plasmod_client.delete(collection_name, ids=pks[:1])
print(delete_result)

print(fmt.format("Start query by specifying primary keys"))
query_results = plasmod_client.query(
    collection_name, filter=f"pk == '{pks[0]}'")
print(f'query result should be empty: {query_results}')

plasmod_client.drop_collection(collection_name)
