#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
set -e

if [ "$1" = 'supervisord' ]; then
    echo "======================================"
    echo "MISP $MISP_VERSION container image provided by National Cyber and Information Security Agency of the Czech Republic"
    echo "In case of any problem with this image, please fill issue at https://github.com/NUKIB/misp/issues"
    echo "======================================"

    misp_create_configs.py

    update-crypto-policies

    # Make config files not readable by others
    chown root:apache /var/www/MISP/app/Config/{config.php,database.php,email.php}
    chmod 440 /var/www/MISP/app/Config/{config.php,database.php,email.php}

    # Check syntax errors in generated config files
    su-exec apache php -l /var/www/MISP/app/Config/config.php
    su-exec apache php -l /var/www/MISP/app/Config/database.php
    su-exec apache php -l /var/www/MISP/app/Config/email.php

    # Check if all permissions are OK
    su-exec apache misp_check_permissions.py

    # Check syntax of Apache2 configs
    httpd -t

    # Check syntax of PHP-FPM config
    php-fpm --test

    # Create database schema
    su-exec apache misp_create_database.py $MYSQL_HOST $MYSQL_LOGIN $MYSQL_DATABASE /var/www/MISP/INSTALL/MYSQL.sql

    # Update database to latest version
    su-exec apache /var/www/MISP/app/Console/cake Admin runUpdates || true

    # Update all data stored in JSONs like objects, warninglists etc.
    nice su-exec apache /var/www/MISP/app/Console/cake Admin updateJSON &

    # Check if redis is listening and running
    su-exec apache /var/www/MISP/app/Console/cake Admin redisReady
fi

# unset sensitive env variables
unset MYSQL_PASSWORD
unset REDIS_PASSWORD
unset SECURITY_SALT
unset SECURITY_ENCRYPTION_KEY
unset OIDC_CLIENT_SECRET_INNER
unset OIDC_CLIENT_SECRET
unset OIDC_CLIENT_CRYPTO_PASS

# Create GPG homedir under apache user
chown -R apache:apache /var/www/MISP/.gnupg
chmod 700 /var/www/MISP/.gnupg
su-exec apache gpg --homedir /var/www/MISP/.gnupg --list-keys

if [ -n "${GNUPG_PRIVATE_KEY}" -a -n "${GNUPG_PRIVATE_KEY_PASSWORD}" ]; then
    # Import private key
    su-exec apache gpg --homedir /var/www/MISP/.gnupg --import --batch \
        --passphrase "${GNUPG_PRIVATE_KEY_PASSWORD}" <<< "${GNUPG_PRIVATE_KEY}"
fi
unset GNUPG_PRIVATE_KEY
unset GNUPG_PRIVATE_KEY_PASSWORD

# Change volumes permission to apache user
chown apache:apache /var/www/MISP/app/attachments
chown apache:apache /var/www/MISP/app/tmp/logs
chown apache:apache /var/www/MISP/app/files/certs

# Remove possible exists PID files
rm -f /var/run/httpd/httpd.pid
rm -f /var/run/syslogd.pid

exec "$@"
