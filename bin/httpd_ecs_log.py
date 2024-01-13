#!/usr/bin/env python3
# This script converts Apache logs from custom defined format to JSON
# Generating JSON directly by setting ErrorLogFormat is problematic because of JSON escaping
import sys
import socket
import argparse
import logging
import datetime

try:
    import orjson as json

    def jsonl_serialize(value) -> bytes:
        # orjson is faster alternative of standard json library that supports serializing datetime.datetime by default
        return json.dumps(value, option=json.OPT_UTC_Z | json.OPT_APPEND_NEWLINE)

except ModuleNotFoundError:
    import json

    def json_serializer(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def jsonl_serialize(value) -> bytes:
        output = json.dumps(value, default=json_serializer, separators=(',', ':'))
        output += "\n"
        return output.encode("utf-8")


ECS_VERSION = "8.11"


def now():
    return datetime.datetime.now(datetime.timezone.utc)


class EcsLogger:
    _sock = None
    _message_buffer = []
    _exception_logged = False

    def __init__(self, socket_path: str):
        self._socket_path = socket_path

    def _connect(self):
        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.connect(self._socket_path)
        except FileNotFoundError:
            if not self._exception_logged:
                logging.warning(f"Could not connect to logger socket {self._socket_path} – file not found")
                self._exception_logged = True
            self._sock = None
            return

        self._exception_logged = False
        logging.info(f"Connected to logger socket {self._socket_path}, sending {len(self._message_buffer)} messages from buffer")

        # Send messages in buffer that was not send before
        for message in self._message_buffer:
            self._sock.sendall(message)
        self._message_buffer = []

    def send(self, log: dict):
        message = jsonl_serialize(log)

        if not self._sock:
            self._connect()

        if self._sock:
            try:
                self._sock.sendall(message)
                return
            except BrokenPipeError:
                logging.warning(f"Could not send log to logger – broken pipe, trying reconnect")
                self._connect()
                if self._sock:
                    self._sock.sendall(message)
                    return

        self._message_buffer.append(message)


def create_generic_error(message: str) -> dict:
    return {
        "@timestamp": now(),
        "ecs": {
            "version": ECS_VERSION,
        },
        "event": {
            "category": "web",
            "type": "error",
            "kind": "event",
            "provider": "misp",
            "module": "httpd",
            "dataset": "httpd.error",
        },
        "message": message,
    }


def access_log(logger: EcsLogger):
    for line in sys.stdin.buffer:
        line = line.rstrip(b"\n")
        try:
            log = json.loads(line)
        except json.JSONDecodeError:
            logger.send(create_generic_error(f"Invalid JSON access log received from httpd: {line}"))
            continue

        # Normalize log by removing dash that indicates empty value from log messages
        for field in ("log_id", "request_id", "http_x_forwarded_for", "user", "http_referer", "upstream_status", "user_email"):
            if field in log and log[field] == "-":
                log[field] = None

        # Normalize integer values
        for field in ("pid", "remote_port", "server_port", "bytes_sent", "body_bytes_sent", "status"):
            if field in log and log[field] == "-":
                log[field] = None
            else:
                try:
                    log[field] = int(log[field])
                except ValueError:
                    log[field] = None
                    logger.send(create_generic_error(f"Could not convert {field} field value {log[field]} to integer"))

        http_version = None
        if log["server_protocol"][0:5] == "HTTP/":
            http_version = log["server_protocol"][5:]

        client = {
            "ip": log["remote_addr"],
            "port": log["remote_port"],
        }

        # If HTTP header X-Forwarded-For is present, use it as real IP and hide proxy IP in nat section
        # X-Forwarded-For can contain multiple values, see https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
        if log["http_x_forwarded_for"]:
            forwarded_for = [value.strip() for value in log["http_x_forwarded_for"].split(",")]
            forwarded_for.append(log["remote_addr"])

            client = {
                "address": forwarded_for,
                "ip": forwarded_for[0],
                "nat": client,
            }
        else:
            client["address"] = (log["remote_addr"], )

        output = {
            "@timestamp": log["@timestamp"],
            "ecs": {
                "version": ECS_VERSION,
            },
            "event": {
                "category": "web",
                "type": "access",
                "kind": "event",
                "provider": "misp",
                "module": "httpd",
                "dataset": "httpd.access",
                "duration": log["duration"] * 1000,  # in nanoseconds
            },
            "process": {
                "pid": log["pid"],
            },
            "client": client,
            "server": {
                "domain": log["server_name"],
                "port": log["server_port"],
            },
            "http": {
                "version": http_version,
                "request": {
                    "id": log["request_id"],
                    "x_forwarded_for": log["http_x_forwarded_for"],  # custom field
                    "method": log["request_method"],
                    "referer": log["http_referer"],
                },
                "response": {
                    "status_code": log["status"],
                    "bytes": log["bytes_sent"],
                    "body": {
                        "bytes": log["body_bytes_sent"],
                    },
                },
            },
            "url": {
                "path": log["request_uri"],
            },
            "user_agent": {
                "original": log["http_user_agent"],
            },
            "file": {
                "path": log["file"],
            }
        }

        if log["host"]:
            if ":" in log["host"]:
                domain, port = log["host"].split(":", 1)
                output["url"]["domain"] = domain
                output["url"]["port"] = int(port)
            else:
                output["url"]["domain"] = log["host"]

        if log["args"]:
            # According to ECS spec, remove ? from query string
            output["url"]["query"] = log["args"].lstrip("?")

        if log["user"] or log["user_email"]:
            output["user"] = {}

            if log["user"]:
                if "@" in log["user"]:
                    user_id, domain = log["user"].split("@", 1)
                    output["user"]["id"] = user_id
                    output["user"]["domain"] = domain
                else:
                    output["user"]["id"] = log["user"]

            if log["user_email"]:
                output["user"]["email"] = log["user_email"]

        if log["log_id"]:
            output["error"] = {
                "id": log["log_id"],
            }

        logger.send(output)


def error_message_extract_code(message: str):
    if len(message) > 6 and message[0] == 'A' and message[7] == ':':
        return message[0:7]
    return None


def parse_error_log(line: str) -> dict:
    parts = line.split(";", 7)
    if len(parts) != 8:
        output = create_generic_error(line)
        error_code = error_message_extract_code(line)
        if error_code:
            output["error"] = {"code": error_code}
    else:
        timestamp, logger, level, pid, tid, client, log_id, message = parts

        output = {
            "@timestamp": timestamp.replace(" ", "T") + "Z",
            "ecs": {
                "version": ECS_VERSION,
            },
            "event": {
                "category": "web",
                "type": "error",
                "kind": "event",
                "provider": "misp",
                "module": "httpd",
                "dataset": "httpd.error",
            },
            "error": {
                "id": log_id,
            },
            "process": {
                "pid": int(pid),
                "thread": {
                    "id": int(tid),
                },
            },
            "log": {
                "logger": logger,
                "level": level,
            },
            "message": message,
        }

        error_code = error_message_extract_code(message)
        if error_code:
            output["error"]["code"] = error_code

        if client:
            ip, port = client.split(":")
            output["client"] = {
                "ip": ip,
                "port": int(port),
            }
    return output


def error_log(logger: EcsLogger):
    for line in sys.stdin:
        line = line.rstrip("\n")
        try:
            output = parse_error_log(line)
        except Exception as e:
            output = create_generic_error(f"Could not parse error log line '{line}': {str(e)}")
        logger.send(output)


def main():
    logging.basicConfig(format='%(asctime)s [PID %(process)d] %(message)s', level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog="httpd_ecs_log",
        description="Converts httpd logs to ECS JSON and send them to socket",
    )
    parser.add_argument("type", choices=("error_log", "access_log"))
    parser.add_argument("socket", nargs="?", default="/run/vector")
    parsed = parser.parse_args()

    logger = EcsLogger(parsed.socket)

    if parsed.type == "error_log":
        error_log(logger)
    else:
        access_log(logger)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
