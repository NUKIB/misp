#!/usr/bin/env python3.12
# Copyright (C) 2026 National Cyber and Information Security Agency of the Czech Republic
import os.path
import subprocess
from pathlib import Path
from itertools import chain


p = Path("/var/www/MISP/app/webroot/")
files_to_compress = []
for file in (chain(p.glob('css/*.css'), p.glob('js/*.js'))):
    if file.stat().st_size <= 4096:
        continue # do not compress small files

    if os.path.exists(str(file) + ".br"):
        continue # compressed variant already exists

    files_to_compress.append(str(file))

if files_to_compress:
    subprocess.run(["brotli"] + files_to_compress, check=True)