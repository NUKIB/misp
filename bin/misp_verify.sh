#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
set -e
set -o xtrace

# Check if PHP is properly configured
php -v

# Build test
# TODO: Temporary disable, because LIEF is broken in arm
#cd /var/www/MISP/tests/
#bash build-test.sh

misp_create_configs.py validate
