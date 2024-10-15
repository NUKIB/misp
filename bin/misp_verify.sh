#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
set -e
set -o xtrace

# Check if PHP is properly configured
php -v
php-fpm --test

# Check if PHP extensions are properly built
misp_verify.php

# Build test
# Temporary disable for aarch64, because LIEF is broken in arm
if [[ "$(uname -m)" != "aarch64" ]]; then
  cd /var/www/MISP/tests/
  bash build-test.sh
fi

misp_create_configs.py validate

httpd_ecs_log.py test

cd /var/www/MISP/
git status