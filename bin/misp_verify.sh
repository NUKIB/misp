#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
set -e
set -o xtrace

# Check if PHP is properly configured
php -v

# Build test
cd /var/www/MISP/tests/
bash build-test.sh

check_jinja_template () {
  python3 -c 'import sys, jinja2; env = jinja2.Environment(); template = open(sys.argv[1]).read(); env.parse(template); sys.exit(0)' $1
}

check_jinja_template /var/www/MISP/app/Config/config.php
check_jinja_template /var/www/MISP/app/Config/database.php
check_jinja_template /var/www/MISP/app/Config/email.php
check_jinja_template /etc/httpd/conf.d/misp.conf
