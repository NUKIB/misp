#!/usr/bin/env python3
import sys
import time
import argparse
import urllib.request
from http.client import HTTPResponse

parser = argparse.ArgumentParser()
parser.add_argument("url")
args = parser.parse_args()

max_tries = 30
while True:
    try:
        resp: HTTPResponse = urllib.request.urlopen(args.url, timeout=1)
        if 200 <= resp.getcode() < 300:
            break
        else:
            raise Exception("Invalid response code {}".format(resp.getcode()))
    except Exception as e:
        max_tries -= 1
        if max_tries == 0:
            print("Could not connect to {}: {}".format(args.url, e), file=sys.stderr)
            sys.exit(1)
        else:
            time.sleep(1)

