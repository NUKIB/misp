#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
PHP_INI=/etc/php.ini

set -e
set -o xtrace

# PHP custom build extensions configuration
echo 'extension = brotli.so' > /etc/php.d/40-brotli.ini
echo 'extension = zstd.so' > /etc/php.d/40-zstd.ini
echo 'extension = igbinary.so' > /etc/php.d/40-igbinary.ini
echo 'extension = ssdeep.so' > /etc/php.d/40-ssdeep.ini
echo 'extension = simdjson.so' > /etc/php.d/40-simdjson.ini
echo "extension = redis.so

redis.session.locking_enabled = 1
redis.session.lock_expire = 30
redis.session.lock_wait_time = 50000
redis.session.lock_retries = 100" > /etc/php.d/50-redis.ini

# PHP-FPM config
echo 'pm.status_path = /fpm-status' >> /etc/php-fpm.d/www.conf # enable PHP-FPM status page
echo 'listen.acl_users = apache' >> /etc/php-fpm.d/www.conf # `nginx` user doesn't exists
echo 'access.log = /var/log/php-fpm/$pool.access.log' >> /etc/php-fpm.d/www.conf # enable PHP-FPM access log
echo 'access.format = "%R %{HTTP_X_REQUEST_ID}e - %u %t \"%m %r%Q%q\" %s %{mili}d %{kilo}M %C%%"' >> /etc/php-fpm.d/www.conf # change log format

# PHP config
sed -e 's/allow_url_fopen = On/allow_url_fopen = Off/' -i ${PHP_INI}
sed -e 's/;assert.active = On/assert.active = Off/' -i ${PHP_INI}
sed -e 's/expose_php = On/expose_php = Off/' -i ${PHP_INI}
sed -e 's/session.sid_length = 26/session.sid_length = 32/' -i ${PHP_INI}
sed -e 's/session.use_strict_mode = 0/session.use_strict_mode = 1/' -i ${PHP_INI}
sed -e 's/pcre.jit=0/pcre.jit=1/' -i ${PHP_INI}
sed -e 's/opcache.enable_cli=1/opcache.enable_cli=0/' -i /etc/php.d/10-opcache.ini
# use igbinary serializer for apcu and sessions
sed -e 's/session.serialize_handler = php/session.serialize_handler = igbinary/' -i ${PHP_INI}
sed -e "s/;apc.serializer='php'/apc.serializer='igbinary'/" -i /etc/php.d/40-apcu.ini
# Disable modules that are not required by MISP to reduce attack potential
rm /etc/php.d/{20-ftp.ini,20-shmop.ini,20-sysvmsg.ini,20-sysvsem.ini,20-sysvshm.ini,20-exif.ini,20-xsl.ini,30-mysqli.ini,20-calendar.ini}
rm /etc/php.d/15-xdebug.ini # disable xdebug by default

# Apache config
chmod o+r /etc/httpd/conf.d/misp.conf
# Remove unnecessary configs
rm -f /etc/httpd/conf.d/userdir.conf /etc/httpd/conf.d/welcome.conf
# Remove unnecessary modules
rm -f /etc/httpd/conf.modules.d/{00-dav.conf,01-cgi.conf,00-systemd.conf,00-lua.conf}
# Keep enabled just proxy and fcgi module, others are not necessary and generate errors to logs
echo "LoadModule proxy_module modules/mod_proxy.so
LoadModule proxy_fcgi_module modules/mod_proxy_fcgi.so" > /etc/httpd/conf.modules.d/00-proxy.conf

# Download MISP
mkdir /var/www/MISP
chown apache:apache /var/www/MISP
git config --system http.sslVersion tlsv1.3 # Always use TLSv1.3 or better for git operations
git config --system --add safe.directory '*' # Fix fatal error `detected dubious ownership` in new git
su-exec apache git clone --branch "$MISP_VERSION" --depth 1 https://github.com/MISP/MISP.git /var/www/MISP

cd /var/www/MISP/
su-exec apache git config core.filemode false

# Clone just submodules under app, we don't need the rest
cd /var/www/MISP/app/
su-exec apache git submodule update --depth 1 --jobs 4 --init --recursive .

# Install Python dependencies as system package
cd /var/www/MISP/app/files/
pip3 install scripts/mixbox scripts/misp-stix scripts/python-maec scripts/python-stix scripts/python-cybox

# Install MISP composer dependencies
cd /var/www/MISP/app/
# Remove unused packages
su-exec apache php composer.phar --no-cache remove --update-no-dev iglocska/cake-resque
su-exec apache php composer.phar --no-cache require --update-no-dev sentry/sdk jakub-onderka/openid-connect-php:1.1.0 aws/aws-sdk-php

# Create attachments folder and set correct owner
mkdir /var/www/MISP/app/attachments
chown apache:apache /var/www/MISP/app/attachments

# File permission
chown -R root:apache /var/www/MISP
find /var/www/MISP -type d -print0 | xargs -0 chmod g=rx
chmod -R g+r,o= /var/www/MISP
chown apache:apache /var/www/MISP/app/files/scripts/tmp
chown -R apache:apache /var/www/MISP/app/tmp
chown -R apache:apache /var/www/MISP/app/files/img/orgs
chown -R apache:apache /var/www/MISP/app/files/img/custom

# Create customisations folders and copy default content
mkdir -p /customize/img_orgs/ /customize/img_custom/
cp /var/www/MISP/app/files/img/orgs/* /customize/img_orgs/
chmod 644 /customize/img_orgs/*

# Create alias to cake console command
echo 'alias cake="su-exec apache /var/www/MISP/app/Console/cake"' >> /root/.bashrc
