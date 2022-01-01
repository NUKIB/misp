#!/usr/bin/env python3
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
import os
import sys
import time
import argparse
import pymysql.cursors
from pymysql.constants import CLIENT
from pymysql.connections import Connection
from typing import Optional


def connect(host: str, user: str, password: Optional[str]) -> pymysql.connections.Connection:
    connection = pymysql.connect(host=host, user=user, password=password, connect_timeout=1, client_flag=CLIENT.MULTI_STATEMENTS)
    connection.ping()
    return connection


def wait_for_connection(host: str, user: str, password: Optional[str]) -> Connection:
    last_exception = None
    for i in range(1, 10):
        try:
            return connect(host, user, password)
        except Exception as e:
            last_exception = e
            print("Waiting for database connection...", file=sys.stderr)
            time.sleep(1)
    print("ERROR: Could not connect to database", file=sys.stderr)
    print(last_exception, file=sys.stderr)
    sys.exit(1)


def is_schema_created(connection: Connection, database: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from information_schema.tables where table_schema=%s and table_name='admin_settings'", database)
        return bool(cursor.fetchone()[0])


def create_schema(connection: Connection, file):
    with connection.cursor() as cursor:
        cursor.execute(file.read())
    connection.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("database")
    parser.add_argument("schema_file", type=argparse.FileType("r"))
    args = parser.parse_args()

    password = os.environ.get("MYSQL_PASSWORD")

    connection = wait_for_connection(args.host, args.user, password)

    if is_schema_created(connection, args.database):
        print("Database schema is already created.", file=sys.stderr)
        connection.close()
        sys.exit(0)

    try:
        connection.select_db(args.database)
    except Exception as e:
        print("ERROR: Could not connect to database", file=sys.stderr)
        print(e, file=sys.stderr)
        connection.close()
        sys.exit(1)

    print("Creating database schema...", file=sys.stderr)
    create_schema(connection, args.schema_file)
    print("Database schema created.", file=sys.stderr)

    connection.close()

    sys.exit(0)


if __name__ == "__main__":
    main()
