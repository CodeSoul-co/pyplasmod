# How to Manage PlasmodClient in PyPlasmod

This guide provides instructions on managing connections with the Plasmod server using the `PlasmodClient` of PyPlasmod. It includes default behavior, advanced usage with aliases, and best practices.

A `PlasmodClient` holds an alias to a Plasmod server connection. This alias represents a connection to a server or a specific database within the server. Let's first take a look at the default behavior.

## Default Behavior

### PlasmodClient Shares Connections

Multiple `PlasmodClient` objects with the same Plasmod **uri** and **authentication** reuse the same connection to the Plasmod server. Each client instance maintains its own database context, so they can operate on different databases while sharing the underlying connection.

The following code snippet demonstrate the reusing of connections in a single thread:
```python
TEST_DB = "test_DB"
URI = "http://localhost:19530"

c = PlasmodClient(uri=URI)

# Multiple PlasmodClient objects reuse the same connection to Plasmod server
c_shared = []
for i in range(10):
    tmp = PlasmodClient(uri=URI)
    c_shared.append(tmp)
    print(f"alias for {i}th PlasmodClient: {tmp._using}, results of list_collections: {tmp.list_collections()}")
```

If you close one of the `PlasmodClient` objects, the others won't work anymore.
```python
c.close() # close one of the PlasmodClient objects
for tmp in c_shared:
    try:
        tmp.list_collections()
    except Exception as ex:
        print("PlasmodClient sharing the same connection will be unable to use, exception: %s", ex)
```

The following code snippet demonstrate the reusing of connections in multiple threads:
```python
def multi_thread_init_plasmod_client():
    """Multiple PlasmodClient objects in multiple threads share the same connection to Plasmod server"""
    threads = []
    thread_count = 10
    for k in range(thread_count):
        x = threading.Thread(target=worker, args=(PlasmodClient(uri=URI),))
        threads.append(x)
        x.start()

    for th in threads:
        th.join()


def multi_thread_copy_plasmod_client():
    """PlasmodClient objects are safe to copy across threads"""
    c_main = PlasmodClient(uri=URI)

    threads = []
    thread_count = 10
    for k in range(thread_count):
        x = threading.Thread(target=worker, args=(c_main,))
        threads.append(x)
        x.start()

    for th in threads:
        th.join()


def worker(c: PlasmodClient):
    got = c.list_collections()
    print(f"Worker, alias to the server connection: {c._using}, results of list_collections: {got}")
```

Whether copy or not, they all share the same connection to Plasmod server underneath.

### PlasmodClient Doesn't Share Connections

**`PlasmodClient` objects with different uri or authentication don't share connections to the Plasmod server by default.**

Note: `PlasmodClient` objects with the same uri and authentication but different `db_name` **will share the same connection**. Each client instance maintains its own database context (`self._db_name`), so they can operate on different databases while sharing the underlying connection.

The following code snippet demonstrate the *c_testdb* and *c* share the same connection but use different databases:
```python
c = PlasmodClient(uri=URI)
c.create_database(TEST_DB)

c_testdb = PlasmodClient(uri=URI, db_name=TEST_DB)

# c and c_testdb share the same connection (same alias), but use different databases
print(f"alias for c:        {c._using}, results of c.list_collections: {c.list_collections()}")
print(f"alias for c_testdb: {c_testdb._using}, results of c_testdb.list_collections: {c_testdb.list_collections()}")

# Both clients share the same connection, so closing one affects the other
c_testdb.close()
try:
    c_testdb.list_collections()
except Exception as ex:
    print(f"c_testdb has been closed, exception: {ex}")

# close of c_testdb affects c because they share the same connection
try:
    print(f"results of c.list_collections: {c.list_collections()}")
except Exception as ex:
    print(f"c is also affected because they share the same connection, exception: {ex}")
```

## Advanced usage: customized aliases

If single connection doesn't meet your performance needs, you can create multiple connections with customized aliases.
The following code snippet demonstrate how to create unique connectionswith "c1-alias" and "c2-alias":

```python
def advanced_unique_connections():
  c1 = PlasmodClient(uri=URI, alias="c1-alias")
  c2 = PlasmodClient(uri=URI, alias="c2-alias")
```
Notes:

- **Avoid Conflict**: Manage alias names carefully to avoid conflicts in connection management.
- **Resource Management**: Ensure to close PlasmodClient of customized aliases when no longer needed to free resources.

### Best Practices

- If you use the default bahavior, that different PlasmodClient might share the same connection to Plasmod server. Always ensure to **never close the PlasmodClient** to avoid influencing shared PlasmodClient.
- If you use customized aliases, be aware to manage them carefully.
    - Ensure PlasmodClient are closed when no longer needed to free resources.
    - Ensure no other clients require the connection before closing the PlasmodClient.
    - Aviod using short-lived connections, reuse them as much as possible.

By following these guidelines, you can effectively manage Plasmod client connections for various application scenarios.
