import time
import numpy as np
from pyplasmod import (
    PlasmodClient,
)

super_user = "root"
super_password = "Plasmod"

fmt = "\n=== {:30} ===\n"
dim = 8

collection_name = "hello_plasmod"
plasmod_client = PlasmodClient("http://localhost:19530", user=super_user, password=super_password)

plasmod_client.drop_user("user1")
plasmod_client.drop_user("user2")
plasmod_client.drop_user("user3")

plasmod_client.create_user("user1", "password1")
plasmod_client.create_user("user2", "password2")
plasmod_client.create_user("user3", "password3")

users = plasmod_client.list_users()
print("users:", users)

plasmod_client.drop_user("user3")

users = plasmod_client.list_users()
print("after drop opeartion, users:", users)


db_rw_privileges = [
  {"object_type": "Global", "object_name": "*", "privilege": "CreateCollection"},
  {"object_type": "Global", "object_name": "*", "privilege": "DropCollection"},
  {"object_type": "Global", "object_name": "*", "privilege": "DescribeCollection"},
  {"object_type": "Global", "object_name": "*", "privilege": "ShowCollections"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Search"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Query"},
  {"object_type": "Collection", "object_name": "*", "privilege": "CreateIndex"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Load"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Release"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Delete"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Insert"},
]

db_ro_privileges = [
  {"object_type": "Global", "object_name": "*", "privilege": "DescribeCollection"},
  {"object_type": "Global", "object_name": "*", "privilege": "ShowCollections"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Search"},
  {"object_type": "Collection", "object_name": "*", "privilege": "Query"},
]

role_db_rw = "db_rw"
role_db_ro = "db_ro"
role_custom = "custom_role"
role_cluster_admin = "cluster_admin"
role_database_readonly = "database_readonly"
role_collection_readwrite = "collection_readwrite"

current_roles = plasmod_client.list_roles()
print("current roles:", current_roles)

for role in [role_db_rw, role_db_ro]:
    if role in current_roles:
        role_info = plasmod_client.describe_role(role)
        for item in role_info['privileges']:
            plasmod_client.revoke_privilege(role, item["object_type"], item["privilege"], item["object_name"])
        
        plasmod_client.drop_role(role)

# manage custom privilege group and grant it to custom role
privilege_group_name = "custom_privilege_group"
plasmod_client.create_privilege_group(privilege_group_name)
plasmod_client.add_privileges_to_group(privilege_group_name, ["Search", "Query"])
plasmod_client.list_privilege_groups()
plasmod_client.remove_privileges_from_group(privilege_group_name, ["Search"])
plasmod_client.list_privilege_groups()
plasmod_client.create_role(role_custom)
plasmod_client.grant_privilege_v2(role_custom, privilege_group_name, "*")

# grant cluster level built-in privilege group
plasmod_client.create_role(role_cluster_admin)
plasmod_client.grant_privilege_v2(role_cluster_admin, "ClusterAdmin", "*", "*")

# grant database level built-in privilege group
plasmod_client.create_role(role_database_readonly)
plasmod_client.grant_privilege_v2(role_database_readonly, "DatabaseReadOnly", "*", "db1")

# grant collection level built-in privilege group
plasmod_client.create_role(role_collection_readwrite)
plasmod_client.grant_privilege_v2(role_collection_readwrite, "CollectionReadWrite", "col1", "db1")

roles = plasmod_client.list_roles()
print("roles:", roles)

plasmod_client.create_role(role_db_rw)
for item in db_rw_privileges:
    plasmod_client.grant_privilege(role_db_rw, item["object_type"], item["privilege"], item["object_name"])


plasmod_client.create_role(role_db_ro)
for item in db_ro_privileges:
    plasmod_client.grant_privilege(role_db_ro, item["object_type"], item["privilege"], item["object_name"])


roles = plasmod_client.list_roles()
print("roles:", roles)
for role in roles:
    role_info = plasmod_client.describe_role(role)
    print(f"info for {role}:", role_info)


user1_info = plasmod_client.describe_user("user1")
print("user info for user1:", user1_info)
print(f"grant {role_db_rw} to user1")
plasmod_client.grant_role("user1", role_db_rw)
print("user info for user1:", user1_info)
plasmod_client.grant_role("user1", role_collection_readwrite)

plasmod_client.grant_role("user2", role_db_ro)
plasmod_client.grant_role("user2", role_db_rw)
plasmod_client.grant_role("user2", role_database_readonly)
plasmod_client.grant_role("user2", role_cluster_admin)

user2_info = plasmod_client.describe_user("user2")
print("user info for user2:", user2_info)
print(f"revoke {role} from user2")
plasmod_client.revoke_role("user2", role_db_rw)
user2_info = plasmod_client.describe_user("user2")
print("user info for user2:", user2_info)

user3_info = plasmod_client.describe_user("user3")
print("user info for user3:", user3_info)


# revoke all privileges before dropping roles and users
plasmod_client.revoke_privilege_v2(role_cluster_admin, "ClusterAdmin", "*", "*")
plasmod_client.revoke_privilege_v2(role_database_readonly, "DatabaseReadOnly", "*", "db1")
plasmod_client.revoke_privilege_v2(role_collection_readwrite, "CollectionReadWrite", "col1", "db1")
plasmod_client.revoke_privilege_v2(role_custom, privilege_group_name, "*")

plasmod_client.drop_role(role_cluster_admin)
plasmod_client.drop_role(role_database_readonly)
plasmod_client.drop_role(role_collection_readwrite)
plasmod_client.drop_role(role_custom)
plasmod_client.list_roles

plasmod_client.drop_privilege_group(privilege_group_name)

plasmod_client.drop_user("user1")
plasmod_client.drop_user("user2")
plasmod_client.drop_user("user3")    

