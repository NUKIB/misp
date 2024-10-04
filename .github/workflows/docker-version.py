#!/usr/bin/env python3
import sys
import json
import argparse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("ref", default="develop", nargs='?')
args = parser.parse_args()

# Fetch the latest commit for given ref, ref can be branch or tag name
if args.ref[0] == "v":
    tags = urllib.request.urlopen("https://api.github.com/repos/MISP/MISP/tags").read()
    tags = json.loads(tags)

    found_tag = None
    is_latest_tag = False
    for i, tag in enumerate(tags):
        if tag["name"] == args.ref:
            found_tag = tag
            if i == 0:
                is_latest_tag = True
            break
    if found_tag is None:
        print("Tag {} not found, latest tag is {}.".format(args.ref, tags[0]["name"]), file=sys.stderr)
        sys.exit(1)
    last_commit = found_tag["commit"]["sha"]
else:
    commits = urllib.request.urlopen("https://api.github.com/repos/MISP/MISP/commits/{}?per_page=1".format(args.ref)).read()
    last_commit = json.loads(commits)["sha"]

print("Latest commit for {} is {}".format(args.ref, last_commit), file=sys.stderr)

print("MISP_VERSION={}".format(args.ref))
print("MISP_COMMIT={}".format(last_commit))
