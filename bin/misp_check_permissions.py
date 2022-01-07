#!/usr/bin/env python3
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
import os
import sys
import getpass

FILES_THAT_SHOULD_NOT_BE_WRITABLE = (
    "/etc/supervisord.d/misp.ini",
    "/etc/rsyslog.conf",
    "/etc/httpd/conf.d/misp.conf",
    "/etc/php.d/snuffleupagus-misp.rules",
    "/root/.jobber",
)

fail = False
for file in FILES_THAT_SHOULD_NOT_BE_WRITABLE:
    if not os.path.exists(file):
        continue  # skip non existing files

    if os.stat(file).st_uid == os.getuid():
        fail = True
        print("File `{}` should not be owned by {} user.".format(file, getpass.getuser()), file=sys.stderr)
        continue

    if os.access(file, os.W_OK):
        fail = True
        print("File `{}` should not be writable for {} user.".format(file, getpass.getuser()), file=sys.stderr)

if fail:
    print("ERROR: Some files are writable that should not, stopping.", file=sys.stderr)

sys.exit(1 if fail else 0)
