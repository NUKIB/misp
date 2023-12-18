#!/usr/bin/env python3
# Copyright (C) 2023 National Cyber and Information Security Agency of the Czech Republic
# This scrips checks if all components running properly
import os
import sys
import json
import logging
import subprocess
import requests


class SubprocessException(Exception):
    def __init__(self, process: subprocess.CompletedProcess):
        self.process = process
        message = "Return code: {}\nSTDERR: {}\nSTDOUT: {}".format(process.returncode, process.stderr, process.stdout)
        super().__init__(message)


s = requests.Session()
# This is a hack how to go through mod_auth_openidc
s.headers["Authorization"] = "dummydummydummydummydummydummydummydummy"


def check_fpm_status() -> dict:
    r = s.get('http://localhost/fpm-status')
    r.raise_for_status()

    output = {}
    for line in r.text.splitlines():
        key, value = line.split(":", 1)
        output[key] = value.strip()
    return output


def check_httpd_status() -> dict:
    r = s.get('http://localhost/server-status?auto')
    r.raise_for_status()

    output = {}
    for line in r.text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            output[key] = value.strip()

    del output["Scoreboard"]
    return output


def check_redis():
    r = subprocess.run(["/var/www/MISP/app/Console/cake", "Admin", "redisReady"], capture_output=True)
    if r.returncode != 0:
        raise SubprocessException(r)


if __name__ == "__main__":
    if os.geteuid() == 0:
        print("This script should not be run under root user", file=sys.stderr)
        sys.exit(255)

    output = {}

    try:
        output["httpd"] = check_httpd_status()
    except Exception:
        logging.exception("Could not check httpd status. Probably Apache is broken.")
        sys.exit(1)

    try:
        output["fpm"] = check_fpm_status()
    except Exception:
        logging.exception("Could not check PHP-FPM status. Probably Apache or PHP-FPM is broken.")
        sys.exit(2)

    try:
        check_redis()
        output["redis"] = True
    except Exception:
        logging.exception("Could not check Redis status. Probably Redis connection is broken.")
        sys.exit(3)

    print(json.dumps(output), file=sys.stderr)
    sys.exit(0)

