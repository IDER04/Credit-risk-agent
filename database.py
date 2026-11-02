from contextlib import contextmanager #open/close connection w database
import mysql.connector
from config import DB_CONFIG


class DatabaseError(Exception):
    """Any problem talking to MySQL, with a readable message."""


@contextmanager
def get_connection():
    """Open a connection, hand it out, and always close it afterwards."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=5)
    except mysql.connector.Error as e:
        raise DatabaseError(f"Cannot connect to MySQL: {e}") from e
    try:
        yield conn
    finally:
        conn.close()


def query(sql, params=None):
    """Run a SELECT and return a list of dicts (one per row)."""
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params or ())
            return cur.fetchall()
        except mysql.connector.Error as e:
            raise DatabaseError(f"SQL error: {e}") from e
        finally:
            cur.close()
def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE as one transaction. Returns (rowcount, lastrowid)."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql, params or ())
            conn.commit()
            return cur.rowcount, cur.lastrowid
        except mysql.connector.Error as e:
            conn.rollback()
            raise DatabaseError(f"SQL error: {e}") from e
        finally:
            cur.close()