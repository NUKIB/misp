#!/usr/bin/env python3
import sys
import time
import argparse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("url")
args = parser.parse_args()

max_tries = 20
while True:
    try:
        urllib.request.urlopen(args.url)
        break
    except Exception as e:
        max_tries -= 1
        if max_tries == 0:
            print("Could not connect to {}: {}".format(args.url, e), file=sys.stderr)
            sys.exit(1)
        else:
            time.sleep(1)

