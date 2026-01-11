#!/usr/bin/env python3.12
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
import base64
import misp_redis_ready


class UnixStreamHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM
        )
        self.sock.connect(self.host)


class UnixStreamTransport(xmlrpc.client.Transport, object):
    def __init__(self, socket_path, username=None, password=None):
        self.socket_path = socket_path
        self.username = username
        self.password = password
        self.verbose = False
        super().__init__()

    def make_connection(self, host):
        return UnixStreamHTTPConnection(self.socket_path)

    def request(self, host, handler, request_body, verbose=False):
        # Build connection and headers similar to xmlrpc.client.Transport.request
        conn = self.make_connection(host)
        if verbose:
            conn.set_debuglevel(1)

        headers = {
            "Content-Type": "text/xml",
            "User-Agent": self.user_agent,
            "Content-Length": str(len(request_body)),
        }

        if self.username and self.password:
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
            logging.debug(f"[Supervisor] Sending auth header: Authorization: Basic {credentials[:20]}...")
        else:
            logging.debug("[Supervisor] No credentials configured")

        logging.debug(f"[Supervisor] Headers: {headers}")
        conn.request("POST", handler, request_body, headers)
        response = conn.getresponse()

        logging.debug(f"[Supervisor] Response status: {response.status} {response.reason}")
        logging.debug(f"[Supervisor] Response headers: {response.getheaders()}")

        if response.status != 200:
            # Match xmlrpc.client.Transport.request behavior by raising ProtocolError
            raise xmlrpc.client.ProtocolError(host + handler, response.status, response.reason, response.getheaders())

        return self.parse_response(response)


class SubprocessException(Exception):
    def __init__(self, process: subprocess.CompletedProcess):
        self.process = process
        message = "Return code: {}\nSTDERR: {}\nSTDOUT: {}".format(process.returncode, process.stderr, process.stdout)
        super().__init__(message)


s = requests.Session()

# Get supervisor credentials from environment
SUPERVISOR_USERNAME = os.environ.get('SUPERVISOR_USERNAME', 'supervisor')
SUPERVISOR_PASSWORD = os.environ.get('SUPERVISOR_PASSWORD', 'changeme')
SUPERVISOR_SOCKET = "/run/supervisor/supervisor.sock"

# Create transport with authentication
transport = UnixStreamTransport(SUPERVISOR_SOCKET, SUPERVISOR_USERNAME, SUPERVISOR_PASSWORD)
supervisor_api = xmlrpc.client.ServerProxy("http://", transport=transport)


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
    host, port, password, use_tls = misp_redis_ready.get_connection_info()
    misp_redis_ready.connect(host, port, password, use_tls)


def main() -> dict:
    # Enable DEBUG logging only when MISP_DEBUG is set to a truthy value
    misp_debug = os.environ.get("MISP_DEBUG", "").lower()
    debug_enabled = misp_debug in ("1", "true", "yes", "on")
    level = logging.DEBUG if debug_enabled else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s:%(name)s:%(message)s')

    # Reduce noisy library logs when not debugging
    if not debug_enabled:
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('xmlrpc').setLevel(logging.WARNING)

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

