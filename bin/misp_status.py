#!/usr/bin/env python3
# Copyright (C) 2023 National Cyber and Information Security Agency of the Czech Republic
# This scrips checks if all components running properly
import os
import sys
import json
import http.client
import socket
import xmlrpc.client
import logging
import subprocess
import requests


class UnixStreamHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM
        )
        self.sock.connect(self.host)


class UnixStreamTransport(xmlrpc.client.Transport, object):
    def __init__(self, socket_path):
        self.socket_path = socket_path
        super().__init__()

    def make_connection(self, host):
        return UnixStreamHTTPConnection(self.socket_path)


class UnixStreamXMLRPCClient(xmlrpc.client.ServerProxy):
    def __init__(self, addr, **kwargs):
        transport = UnixStreamTransport(addr)
        super().__init__(
            "http://", transport=transport, **kwargs
        )


class SubprocessException(Exception):
    def __init__(self, process: subprocess.CompletedProcess):
        self.process = process
        message = "Return code: {}\nSTDERR: {}\nSTDOUT: {}".format(process.returncode, process.stderr, process.stdout)
        super().__init__(message)


s = requests.Session()
supervisor_api = UnixStreamXMLRPCClient("/run/supervisor/supervisor.sock")


def check_supervisor():
    state = supervisor_api.supervisor.getState()
    if state["statecode"] != 1:
        raise Exception(f"Unexpected state code {state['statecode']} received from supervisor, expected 1")


def check_supervisor_process(process_name: str) -> bool:
    try:
        process_info = supervisor_api.supervisor.getProcessInfo(process_name)
    except xmlrpc.client.Fault as e:
        if e.faultCode == 10:  # BAD_NAME
            return False  # process is not enabled
        raise

    if process_info["state"] != 20:
        raise Exception(f"Invalid process state {process_info['statename']}, expected RUNNING")

    return True


def check_fpm_status() -> dict:
    r = s.get('http://127.0.0.2/fpm-status')
    r.raise_for_status()

    output = {}
    for line in r.text.splitlines():
        key, value = line.split(":", 1)
        output[key] = value.strip()
    return output


def check_httpd_status() -> dict:
    r = s.get('http://127.0.0.2/server-status?auto')
    r.raise_for_status()

    output = {}
    for line in r.text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            output[key] = value.strip()

    del output["Scoreboard"]
    return output


def check_vector():
    if not check_supervisor_process("vector"):
        return False

    r = s.get('http://127.0.0.1:8686/health')
    r.raise_for_status()
    if not r.json()["ok"]:
        raise Exception(f"Invalid status ({r.text}) received from vector API")

    return True


def check_zeromq():
    return check_supervisor_process("zeromq")


def check_redis():
    r = subprocess.run(["/var/www/MISP/app/Console/cake", "Admin", "redisReady"], capture_output=True)
    if r.returncode != 0:
        raise SubprocessException(r)


def main() -> dict:
    output = {
        "supervisor": False,
        "httpd": False,
        "php-fpm": False,
        "redis": False,
    }

    try:
        check_supervisor()
        output["supervisor"] = True
    except Exception:
        logging.exception("Could not check supervisor status")

    try:
        check_httpd_status()
        output["httpd"] = True
    except Exception:
        logging.exception("Could not check httpd status. Probably Apache is broken.")

    try:
        check_fpm_status()
        output["php-fpm"] = True
    except Exception:
        logging.exception("Could not check PHP-FPM status. Probably Apache or PHP-FPM is broken.")

    try:
        check_redis()
        output["redis"] = True
    except Exception:
        logging.exception("Could not check Redis status. Probably Redis connection is broken.")

    try:
        if check_vector():
            output["vector"] = True
    except Exception:
        output["vector"] = False
        logging.exception("Could not check vector status")

    try:
        if check_zeromq():
            output["zeromq"] = True
    except Exception:
        output["zeromq"] = False
        logging.exception("Could not check zeromq status")

    return output


if __name__ == "__main__":
    if os.geteuid() == 0:
        print("This script should not be run under root user", file=sys.stderr)
        sys.exit(255)

    output = main()
    sys.stdout.write(json.dumps(output, separators=(",", ":")))

    for value in output.values():
        if value is False:
            sys.exit(1)

    sys.exit(0)

