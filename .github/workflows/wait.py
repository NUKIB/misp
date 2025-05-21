#!/usr/bin/env python3
import sys
import time
import argparse
import urllib.request
import urllib.error

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("--ignore-http-error", action="store_true")
args = parser.parse_args()

max_tries = 30
while True:
    try:
        try:
            urllib.request.urlopen(args.url, timeout=1)
        except urllib.error.HTTPError:
            if args.ignore_http_error:
                break
            raise
        break
    except Exception as e:
        max_tries -= 1
        if max_tries == 0:
            print("Could not connect to {}: {}".format(args.url, e), file=sys.stderr)
            sys.exit(1)
        else:
            time.sleep(1)

