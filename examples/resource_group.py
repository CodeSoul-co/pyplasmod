from pyplasmod import (
    PlasmodClient,
    DataType,
)
from pyplasmod.client.constants import DEFAULT_RESOURCE_GROUP

from pyplasmod.client.types import (
    ResourceGroupConfig,
)

fmt = "\n=== {:30} ===\n"
dim = 8
collection_name = "hello_plasmod"
plasmod_client = PlasmodClient("http://localhost:19530")


## create collection and load collection
print("create collection and load collection")
collection_name = "hello_plasmod"
has_collection = plasmod_client.has_collection(collection_name, timeout=5)
if has_collection:
    plasmod_client.drop_collection(collection_name)

schema = plasmod_client.create_schema(enable_dynamic_field=True)
schema.add_field("id", DataType.INT64, is_primary=True)
schema.add_field("embeddings", DataType.FLOAT_VECTOR, dim=dim)
schema.add_field("title", DataType.VARCHAR, max_length=64)
plasmod_client.create_collection(collection_name, schema=schema, consistency_level="Strong")
index_params = plasmod_client.prepare_index_params()
index_params.add_index(field_name = "embeddings", metric_type="L2")
index_params.add_index(field_name = "title", index_type = "Trie", index_name="my_trie")
plasmod_client.create_index(collection_name, index_params)
plasmod_client.load_collection(collection_name)


## create resource group
print("create resource group")
plasmod_client.create_resource_group("rg1")
plasmod_client.create_resource_group("rg2")

## update resource group
configs = {
            "rg1": ResourceGroupConfig(
                requests={"node_num": 1},
                limits={"node_num": 5},
                transfer_from=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
                transfer_to=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
            ),
            "rg2": ResourceGroupConfig(
                requests={"node_num": 4},
                limits={"node_num": 4},
                transfer_from=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
                transfer_to=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
            ),
        }
plasmod_client.update_resource_groups(configs)

## describe resource group
print("describe rg1")
result = plasmod_client.describe_resource_group("rg1")
print(result)

print("describe rg2")
result = plasmod_client.describe_resource_group("rg2")
print(result)

## list resource group
print("list resource group")
result = plasmod_client.list_resource_groups()
print(result)

## transfer replica
print("transfer replica to rg1")
plasmod_client.transfer_replica(DEFAULT_RESOURCE_GROUP, "rg1", collection_name, 1)
print("describe rg1 after transfer replica in")
result = plasmod_client.describe_resource_group("rg1")
print(result)

plasmod_client.transfer_replica("rg1", DEFAULT_RESOURCE_GROUP, collection_name, 1)
print("describe rg1 after transfer replica out")
result = plasmod_client.describe_resource_group("rg1")
print(result)

## drop resource group
print("drop resource group")
# create resource group
configs = {
            "rg1": ResourceGroupConfig(
                requests={"node_num": 0},
                limits={"node_num": 0},
                transfer_from=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
                transfer_to=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
            ),
            "rg2": ResourceGroupConfig(
                requests={"node_num": 0},
                limits={"node_num": 0},
                transfer_from=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
                transfer_to=[{"resource_group": DEFAULT_RESOURCE_GROUP}],
            ),
        }
plasmod_client.update_resource_groups(configs)
plasmod_client.drop_resource_group("rg1")
plasmod_client.drop_resource_group("rg2")


