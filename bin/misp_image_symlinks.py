#!/usr/bin/env python3
# Copyright (C) 2024 National Cyber and Information Security Agency of the Czech Republic
import sys
from pathlib import Path

DIRS = {
    "/customize/img_orgs/": "/var/www/MISP/app/files/img/orgs/",
    "/customize/img_custom/": "/var/www/MISP/app/files/img/custom/"
}

for source, destination in DIRS.items():
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        continue

    # Remove old symlinks that are not valid anymore
    for item in destination.iterdir():
        if item.is_symlink() and not item.readlink().exists():
            try:
                item.unlink()
                print(f"Remove non existing symlink {item}", file=sys.stderr)
            except Exception as e:
                print(f"Could not remove existing symlink {item}: {e}", file=sys.stderr)

    # Create new symlinks
    for item in source.iterdir():
        if item.is_file() and not destination.joinpath(item.name).exists():
            new_symlink = destination.joinpath(item.name)
            new_symlink.symlink_to(item)
            print(f"Created new symlink to {new_symlink}", file=sys.stderr)