from pyplasmod import (
    PlasmodClient,
)

plasmod_client = PlasmodClient("http://localhost:19530")

version = plasmod_client.get_server_version()
print(f"server version: {version}")
