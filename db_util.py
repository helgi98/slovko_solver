import sqlite3
from sqlite3 import Error


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


def execute_query(conn, query, params=()):
    cur = conn.cursor()

    cur.execute(query, params)

    return cur.fetchall()