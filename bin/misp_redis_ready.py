#!/usr/bin/env python3.11
# Copyright (C) 2024 National Cyber and Information Security Agency of the Czech Republic
import os
import sys
import time
from typing import Optional, Tuple
import redis
import logging


def error(message: str):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def convert_bool(value: str) -> bool:
    value = value.lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off", ""):
        return False

    error(f"Environment variable 'REDIS_USE_TLS' must be boolean (`true`, `1`, `yes`, `false`, `0` or `no`), `{value}` given")


def connect(host: str, password: Optional[str] = None, use_tls: bool = False) -> redis.Redis:
    r = redis.Redis(host=host, port=6379, password=password, ssl=use_tls)
    r.ping()
    return r


def wait_for_connection(host: str, password: Optional[str] = None, use_tls: bool = False) -> redis.Redis:
    logging.info(f"Connecting to Redis server {host}")
    last_exception = None
    for i in range(1, 10):
        try:
            return connect(host, password, use_tls)
        except Exception as e:
            last_exception = e
            logging.info("Waiting for Redis connection...")
            time.sleep(1)
    logging.error(f"Could not connect to Redis server {host}")
    print(last_exception, file=sys.stderr)
    sys.exit(1)


def wait_for_load(connection: redis.Redis):
    data_loaded = False
    for i in range(1, 10):
        try:
            persistence = connection.info("persistence")
        except Exception:
            logging.error(f"Could not get persistence info from Redis server, skipping")
            sys.exit(0)

        if "loading" not in persistence:
            logging.warning("Loading not found in persistence info from Redis, skipping loading check")
            sys.exit(0)

        if persistence["loading"]:
            logging.info("Waiting for Redis to load to memory...")
            time.sleep(1)
        else:
            data_loaded = True

    if data_loaded:
        logging.info("Redis ready")
    else:
        logging.warning("Redis is still loading data to memory, waiting skipped")


def get_connection_info() -> Tuple[str, Optional[str], bool]:
    host = os.environ.get("REDIS_HOST")
    if host is None:
        error("Environment variable 'REDIS_HOST' not set.")

    password = os.environ.get("REDIS_PASSWORD")

    use_tls = os.environ.get("REDIS_USE_TLS")
    use_tls = convert_bool(use_tls) if use_tls else False

    return host, password, use_tls


def main():
    logging.basicConfig(format="%(asctime)s - %(levelname)s: %(message)s", level=logging.DEBUG)

    host, password, use_tls = get_connection_info()
    redis = wait_for_connection(host, password, use_tls)

    info = redis.info("server")
    logging.info(f"Connected to Redis {info['redis_version']}")

    wait_for_load(redis)


if __name__ == "__main__":
    main()
