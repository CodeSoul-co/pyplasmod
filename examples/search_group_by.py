from pyplasmod.plasmod_client.plasmod_client import PlasmodClient
from pyplasmod import (
    FieldSchema, CollectionSchema, DataType,
)
import numpy as np
from typing import List

collection_name = "test_plasmod_client_iterator"
prepare_new_data = False
clean_exist = False

USER_ID = "id"
AGE = "age"
DEPOSIT = "deposit"
PICTURE = "picture"
DIM = 8
NUM_ENTITIES = 10000
rng = np.random.default_rng(seed=19530)
plasmod_client = PlasmodClient("http://localhost:19530")
if plasmod_client.has_collection(collection_name) and clean_exist:
    plasmod_client.drop_collection(collection_name)
    print(f"dropped existed collection{collection_name}")

if not plasmod_client.has_collection(collection_name):
    fields = [
        FieldSchema(name=USER_ID, dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name=AGE, dtype=DataType.INT64),
        FieldSchema(name=DEPOSIT, dtype=DataType.DOUBLE),
        FieldSchema(name=PICTURE, dtype=DataType.FLOAT_VECTOR, dim=DIM)
    ]
    schema = CollectionSchema(fields)
    plasmod_client.create_collection(collection_name, dimension=DIM, schema=schema)

if prepare_new_data:
    entities = []
    for i in range(NUM_ENTITIES):
        entity = {
            USER_ID: i,
            AGE: (i % 100),
            DEPOSIT: float(i),
            PICTURE: rng.random((1, DIM))[0]
        }
        entities.append(entity)
    plasmod_client.insert(collection_name, entities)
    plasmod_client.flush(collection_name)
    print(f"Finish flush collections:{collection_name}")

index_params = plasmod_client.prepare_index_params()

index_params.add_index(
    field_name=PICTURE,
    index_type='IVF_FLAT',
    metric_type='L2',
    params={"nlist": 1024}
)
plasmod_client.create_index(collection_name, index_params)
plasmod_client.load_collection(collection_name)

nq = 3
def print_res(result: List[List[dict]]):
    for i in range(nq):
        r = result[i]
        print(f"search_group_by_res_i:{i}")
        for e in r:
            print(f"search_entity:{e}")
        print(f"======================================================")


vector_to_search = rng.random((nq, DIM), np.float32)
# just search_group_by, no group_size, only 1 entities per group
res = plasmod_client.search(collection_name, data=vector_to_search, limit=10, anns_field=PICTURE,
                     output_fields=[USER_ID, AGE], group_by_field=AGE)
print_res(res)

# search_group_by, with group_size=3, but not strict_group_size, entity number in per group may be 1~3
res = plasmod_client.search(collection_name, data=vector_to_search, limit=10, anns_field=PICTURE,
                     output_fields=[USER_ID, AGE], group_by_field=AGE, group_size=3)
print_res(res)

# search_group_by, with group_size=3, and strict_group_size=true, entity number
# in per group will be exactly 3 if data's sufficient
res = plasmod_client.search(collection_name, data=vector_to_search, limit=10, anns_field=PICTURE,
                     output_fields=[USER_ID, AGE], group_by_field=AGE, group_size=3, strict_group_size=True)
print_res(res)

