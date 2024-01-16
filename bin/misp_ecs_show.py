#!/usr/bin/env python3
# Copyright (C) 2023 National Cyber and Information Security Agency of the Czech Republic
import sys
import orjson
import argparse
import subprocess
from typing import Optional
from pprint import pformat

POSSIBLE_DATASETS = (
    "httpd.access", "httpd.error", "php-fpm.access", "php-fpm.error", "jobber.runs", "supervisor.log", "system.logs",
    "application.logs")
POSSIBLE_MODULES = ("httpd", "php-fpm", "jobber", "supervisor", "system", "application")


class CliColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def ecs_is_error(item: dict) -> bool:
    if item["event"]["dataset"] in ("httpd.error", "php-fpm.error"):
        return True

    if "log" in item and "level" in item["log"] and item["log"]["level"] in ("error", "warn", "warning"):
        return True

    return False


def fetch_items():
    vector = subprocess.Popen(["/usr/bin/vector", "--color", "always", "tap", "parse_ecs_*"], stdout=subprocess.PIPE)
    for line in vector.stdout:
        yield orjson.loads(line)


def main(dataset: Optional[list] = None, module: Optional[list] = None, errors_only: bool = False, as_line: bool = False):
    for item in fetch_items():
        if dataset and not item["event"]["dataset"] in dataset:
            continue

        if module and not item["event"]["module"] in module:
            continue

        is_error = ecs_is_error(item)
        if errors_only and not is_error:
            continue

        if "original" in item["event"]:
            del item["event"]["original"]

        # Remove unnecessary metadata
        del item["ecs"]
        if "created" in item["event"]:
            del item["event"]["created"]
        del item["event"]["kind"]  # `event` all the time
        del item["event"]["provider"]  # `misp` all the time

        if as_line:
            if is_error:
                sys.stdout.write(CliColors.WARNING)

            sys.stdout.write(item["@timestamp"])
            sys.stdout.write(f' [{item["event"]["dataset"]}] ')
            if "original" in item["event"]:
                sys.stdout.write(item["event"]["original"])
            elif "message" in item:
                sys.stdout.write(item["message"])
            elif "error" in item and "message" in item["error"]:
                sys.stdout.write(item["error"]["message"])
            else:
                print(item, file=sys.stdout, end="")

            if is_error:
                sys.stdout.write(f"{CliColors.ENDC}\n")
            else:
                sys.stdout.write("\n")
        else:
            formatted = pformat(item, width=160)

            if is_error:
                sys.stdout.write(CliColors.WARNING)
                sys.stdout.write(formatted)
                sys.stdout.write(f"{CliColors.ENDC}\n")
            else:
                sys.stdout.write(formatted)
                sys.stdout.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="misp_ecs_show",
        description="Show current logs collected by Vector",
    )
    parser.add_argument("--dataset", nargs='+', choices=POSSIBLE_DATASETS)
    parser.add_argument("--module", nargs='+', choices=POSSIBLE_MODULES)
    parser.add_argument("--error", action="store_true", help="Show just errors")
    parser.add_argument("--line", action="store_true", help="Show error log as one line")
    parsed = parser.parse_args()

    try:
        main(parsed.dataset, parsed.module, parsed.error, parsed.line)
    except KeyboardInterrupt:
        pass
