import mysql.connector

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "unlistings",
    "charset": "utf8mb4",
}


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)
