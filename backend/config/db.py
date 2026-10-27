"""MySQL connection pool (mysql-connector-python)."""
import os
from mysql.connector import pooling, Error as MySQLError

_pool = None


def init_pool():
    """Create the connection pool once at startup and verify connectivity."""
    global _pool
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="ai_interview_pool",
            pool_size=10,
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "ai_interview_db"),
        )
        # Quick ping to confirm real connectivity, not just pool creation.
        conn = _pool.get_connection()
        conn.ping(reconnect=True)
        conn.close()
        print("[DB] MySQL connection OK")
    except MySQLError as err:
        print(f"[DB] Could not connect to MySQL: {err}")
        print("[DB] Check your .env DB_HOST/DB_USER/DB_PASSWORD/DB_NAME values, and that MySQL is running.")


def get_connection():
    """Get a connection from the pool. Raises if the pool failed to initialize."""
    global _pool
    if _pool is None:
        init_pool()
    if _pool is None:
        raise RuntimeError("Database pool was not initialized. Check MySQL connection settings in .env.")
    return _pool.get_connection()
