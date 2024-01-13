#!/usr/bin/env bash
# Copyright (C) 2024 National Cyber and Information Security Agency of the Czech Republic
set -e

/var/www/MISP/app/Console/cake admin createZmqConfig
exec python3 /var/www/MISP/app/files/scripts/mispzmq/mispzmq.py