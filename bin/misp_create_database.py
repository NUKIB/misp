#!/usr/bin/env python3.11
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
import os
import sys
import time
import logging
import argparse
import pymysql.cursors
from pymysql.constants import CLIENT
from pymysql.connections import Connection
from typing import Optional, TextIO


def connect(host: str, port: int, user: str, password: Optional[str]) -> pymysql.connections.Connection:
    connection = pymysql.connect(host=host, port=port, user=user, password=password, connect_timeout=1, client_flag=CLIENT.MULTI_STATEMENTS)
    connection.ping()
    return connection


def wait_for_connection(host: str, port: int, user: str, password: Optional[str]) -> Connection:
    logging.info(f"Connecting to MySQL server {host}:{port}")
    last_exception = None
    for i in range(1, 10):
        try:
            return connect(host, port, user, password)
        except Exception as e:
            last_exception = e            
            logging.info("Waiting for database connection...")            
            logging.info(e)
            time.sleep(1)
    logging.error(f"Could not connect to database server {host}:{port}")
    print(last_exception, file=sys.stderr)
    sys.exit(1)


def is_schema_created(connection: Connection, database: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from information_schema.tables where table_schema=%s and table_name='admin_settings'", database)
        return bool(cursor.fetchone()[0])


def create_schema(connection: Connection, schema_file: TextIO):
    schema = schema_file.read()
    with connection.cursor() as cursor:
        cursor.execute(schema)
    connection.commit()


def main():
    logging.basicConfig(format="%(asctime)s - %(levelname)s: %(message)s", level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("database")
    parser.add_argument("schema_file", type=argparse.FileType("r"))
    args = parser.parse_args()

    password = os.environ.get("MYSQL_PASSWORD")
    port = os.environ.get("MYSQL_PORT")
    port = 3306 if port is None else int(port)

    connection = wait_for_connection(args.host, port, args.user, password)

    if is_schema_created(connection, args.database):
        logging.info("Database schema is already created.")
        connection.close()
        sys.exit(0)

    try:
        connection.select_db(args.database)
    except Exception as e:
        logging.error(f"Could not select database {args.database}")
        print(e, file=sys.stderr)
        connection.close()
        sys.exit(1)

    logging.info("Creating database schema...")
    create_schema(connection, args.schema_file)
    logging.info("Database schema created.")

    connection.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
