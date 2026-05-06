""" Before running this example, you need to start Plasmod server first. """

import logging
import threading

from pyplasmod import PlasmodClient

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s (%(lineno)s) (%(threadName)s)')

URI = "http://localhost:19530"
TEST_DB = "test_db"

def worker(c: PlasmodClient):
    LOGGER.info(f"Worker, alias to the server connection: {c._using}, results of list_collections: {c.list_collections()}")

def multi_thread_init_plasmod_client():
    """Multiple PlasmodClient objects in multiple threads share the same connection to Plasmod server"""
    LOGGER.info("Multiple PlasmodClient objects in multiple threads share the same connection to Plasmod server")
    threads = []
    thread_count = 10
    for k in range(thread_count):
        x = threading.Thread(target=worker, args=(PlasmodClient(uri=URI),))
        threads.append(x)
        x.start()
        LOGGER.debug(f"Thread-{k} '{x.name}' started")

    for th in threads:
        th.join()
        LOGGER.debug(f"Thread '{th.name}' finished")


def multi_thread_copy_plasmod_client():
    """PlasmodClient objects are safe to copy across threads"""
    LOGGER.info("Multiple PlasmodClient objects are safe to copy across threads, they all shared the same connection to Plasmod server")
    c_main = PlasmodClient(uri=URI)

    threads = []
    thread_count = 10
    for k in range(thread_count):
        x = threading.Thread(target=worker, args=(c_main,))
        threads.append(x)
        x.start()
        LOGGER.debug(f"Thread-{k} '{x.name}' started")

    for th in threads:
        th.join()
        LOGGER.debug(f"Thread '{th.name}' finished")


def shared_connections():
    # A PlasmodClient holds an alias to a Plasmod server connection
    c = PlasmodClient(uri=URI)
    LOGGER.info(f"Alias to the server connection: {c._using}, results of list_collections: {c.list_collections()}")
    if TEST_DB not in c.list_databases():
        c.create_database(TEST_DB)

    # Multiple PlasmodClient objects reuse the same connection to Plasmod server
    LOGGER.info("By default, multiple PlasmodClient objects reuse the same connection to Plasmod server")
    c_shared = []
    for i in range(10):
        tmp = PlasmodClient(uri=URI)
        c_shared.append(tmp)
        LOGGER.info(f"  {i}th PlasmodClient, alias to the server connection: {tmp._using}, results of list_collections: {tmp.list_collections()}")

    # PlasmodClient with different database but same uri and authentication
    # will share the same connection, but each client maintains its own database context
    LOGGER.info("=============================")
    c_testdb = PlasmodClient(uri=URI, db_name=TEST_DB)
    LOGGER.info(
        f"PlasmodClient to test_db, alias to the server connection: {c_testdb._using}, "
        f"results of list_collections: {c_testdb.list_collections()}"
    )
    LOGGER.info(
        f"Note: c and c_testdb share the same connection (alias: {c._using} == {c_testdb._using}), "
        f"but use different databases (default vs {TEST_DB})"
    )

    # PlasmodClient object is safe to copy across threads
    LOGGER.info("=============================")
    multi_thread_copy_plasmod_client()

    # PlasmodClient in multiple threads share the same connection to Plasmod server
    LOGGER.info("=============================")
    multi_thread_init_plasmod_client()

    # Never close a client if you're absolutely sure no one else is using it.
    # Close of one PlasmodClient closes all other PlasmodClient's access to PlasmodServer
    LOGGER.info("=============================")
    c.close()
    LOGGER.info("Closed PlasmodClient c, all PlasmodClient sharing the same connection will be unable to use")
    for tmp in c_shared:
        try:
            tmp.list_collections()
        except Exception as ex:
            LOGGER.warning("    PlasmodClient sharing the same connection will be unable to use, exception: %s", ex)


def advanced_unique_connections():
    # Use different alias to create PlasmodClient doesn't share the connection to Plasmod server
    LOGGER.info("=============================")
    LOGGER.info("Use different alias to create PlasmodClient doesn't share the connection to Plasmod server")
    c1 = PlasmodClient(uri=URI, alias="c1-alias")
    LOGGER.info(f"Alias of c1 to the server connection: {c1._using}, results of c1.list_collections: {c1.list_collections()}")
    c2 = PlasmodClient(uri=URI, alias="c2-alias")
    LOGGER.info(f"Alias of c2 to the server connection: {c2._using}, results of c2.list_collections: {c2.list_collections()}")

    c1.close()
    LOGGER.info("Closed PlasmodClient c1, c1 cannot use")
    try:
        c1.list_collections()
    except Exception as ex:
        LOGGER.warning("Closed PlasmodClient c1, it cannot use, exception: %s", ex)
    LOGGER.info(f"Closed PlasmodClient c1, c2 can still use PlasmodServer, results of c2.list_collections: {c2.list_collections()}")

    LOGGER.info("Be sure to manage your own alias's PlasmodClient, close it when you're done")
    c2.close()


if __name__ == "__main__":
    shared_connections()
    advanced_unique_connections()
