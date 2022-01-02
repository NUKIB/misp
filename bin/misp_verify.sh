#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
set -e
set -o xtrace

# Check if PHP is properly configured
php -v

# Build test
cd /var/www/MISP/tests/
bash build-test.sh

# Validate syntax of config.php template
python3 -c 'import sys, jinja2; env = jinja2.Environment(); template = open("/var/www/MISP/app/Config/config.php"); env.parse(template.read()); sys.exit(0)'

# Validate syntax of Apache config template
python3 -c 'import sys, jinja2; env = jinja2.Environment(); template = open("/etc/httpd/conf.d/misp.conf"); env.parse(template.read()); sys.exit(0)'

# Check installed Python packages for vulnerabilities
safety check --full-report || true # ignore output for now
