import numpy as np
from pyplasmod import (
    PlasmodClient,
    DataType
)

plasmod_client = PlasmodClient("http://localhost:19530")

db1Name = "db1"
# create db1
if db1Name not in plasmod_client.list_databases():
    print("\ncreate database: db1")
    plasmod_client.create_database(db_name=db1Name, properties={"key1":"value1"})
    db_info = plasmod_client.describe_database(db_name=db1Name)
    print(db_info)


# alter_database_properties of db1
db_info = plasmod_client.describe_database(db_name=db1Name)
print(db_info)
print("\nalter database properties of db1:")
plasmod_client.alter_database_properties(db_name=db1Name, properties={"key": "value"})
db_info = plasmod_client.describe_database(db_name=db1Name)
print(db_info)

print("\ndrop database properties of db1")
plasmod_client.drop_database_properties(db_name=db1Name, property_keys=["key"])
db_info = plasmod_client.describe_database(db_name=db1Name)
print(db_info)

# list database
print("\nlist databases:")
print(plasmod_client.list_databases())