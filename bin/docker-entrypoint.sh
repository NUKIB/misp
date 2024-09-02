#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
set -e

# usage: file_env VAR [DEFAULT]
#    ie: file_env 'XYZ_DB_PASSWORD' 'example'
# (will allow for "$XYZ_DB_PASSWORD_FILE" to fill in the value of
#  "$XYZ_DB_PASSWORD" from a file, especially for Docker's secrets feature)
file_env() {
	local var="$1"
	local fileVar="${var}_FILE"
	local def="${2:-}"
	if [ "${!var:-}" ] && [ "${!fileVar:-}" ]; then
		printf >&2 'error: both %s and %s are set (but are exclusive)\n' "$var" "$fileVar"
		exit 1
	fi
	local val="$def"
	if [ "${!var:-}" ]; then
		val="${!var}"
	elif [ "${!fileVar:-}" ]; then
		val="$(< "${!fileVar}")"
	fi
	export "$var"="$val"
	unset "$fileVar"
}

# Initialize values that might be stored in a file

file_env 'MYSQL_DATABASE'
file_env 'MYSQL_LOGIN'
file_env 'MYSQL_PASSWORD'
file_env 'REDIS_PASSWORD'
file_env 'GNUPG_PRIVATE_KEY'
file_env 'GNUPG_PRIVATE_KEY_PASSWORD'
file_env 'SECURITY_SALT'
file_env 'SECURITY_ENCRYPTION_KEY'
file_env 'PROXY_USER'
file_env 'PROXY_PASSWORD'
file_env 'ZEROMQ_USERNAME'
file_env 'ZEROMQ_PASSWORD'

# Change volumes permission to apache user
chown apache:apache /var/www/MISP/app/{attachments,tmp/logs,files/certs,files/img/orgs,files/img/custom}

if [ "$1" = 'supervisord' ]; then
    echo "======================================"
    echo "MISP $MISP_VERSION container image provided by National Cyber and Information Security Agency of the Czech Republic"
    echo "In case of any problem with this image, please fill issue at https://github.com/NUKIB/misp/issues"
    echo "======================================"

    misp_create_configs.py

    update-crypto-policies

    # Create tmp directory for cake cache
    mkdir -p -m 770 /tmp/cake/
    chown apache:apache /tmp/cake/

    # Make config files not readable by others
    chown root:apache /var/www/MISP/app/Config/{config.php,database.php,email.php}
    chmod 440 /var/www/MISP/app/Config/{config.php,database.php,email.php}

    # Check syntax errors in generated config files
    su-exec apache php -n -l /var/www/MISP/app/Config/config.php
    su-exec apache php -n -l /var/www/MISP/app/Config/database.php
    su-exec apache php -n -l /var/www/MISP/app/Config/email.php

    # Create symlinks to images from customisation
    su-exec apache misp_image_symlinks.py

    # Check if all permissions are OK
    su-exec apache misp_check_permissions.py

    # Check syntax of Apache2 configs
    httpd -t

    # Check syntax of PHP-FPM config
    php-fpm --test

    # Create database schema and check if database is ready
    su-exec apache misp_create_database.py "$MYSQL_HOST" "$MYSQL_LOGIN" "$MYSQL_DATABASE" /var/www/MISP/INSTALL/MYSQL.sql

    # Check if redis is listening and running
    su-exec apache misp_redis_ready.py

    # Update database to latest version
    su-exec apache /var/www/MISP/app/Console/cake Admin runUpdates || true

    # Checks if encryption key is valid if set, but continue even if not valid
    if [[ -n $SECURITY_ENCRYPTION_KEY ]]; then
      su-exec apache /var/www/MISP/app/Console/cake Admin isEncryptionKeyValid || true
    fi

    # Precompress some CSS and JavaScript files by brotli
    brotli -f /var/www/MISP/app/webroot/css/{bootstrap,bootstrap-datepicker,bootstrap-colorpicker,font-awesome,chosen.min,main}.css
    brotli -f /var/www/MISP/app/webroot/js/{jquery,jquery-ui.min,chosen.jquery.min,bootstrap,bootstrap-datepicker,misp,vis}.js

    # Update all data stored in JSONs like objects, warninglists etc.
    nice su-exec apache /var/www/MISP/app/Console/cake Admin updateJSON &
fi

# Create GPG homedir under apache user
chown -R apache:apache /var/www/MISP/.gnupg
chmod 700 /var/www/MISP/.gnupg
su-exec apache gpg --homedir /var/www/MISP/.gnupg --list-keys

if [ -n "${GNUPG_PRIVATE_KEY}" -a -n "${GNUPG_PRIVATE_KEY_PASSWORD}" ]; then
    # Import private key
    su-exec apache gpg --homedir /var/www/MISP/.gnupg --import --batch \
        --passphrase "${GNUPG_PRIVATE_KEY_PASSWORD}" <<< "${GNUPG_PRIVATE_KEY}"
fi

# unset sensitive env variables
for variable_name in $(misp_create_configs.py sensitive-variables)
do
  unset "$variable_name"
done

# Remove possible exists PID and socket files
rm -f /run/httpd/httpd.pid
rm -f /run/syslogd.pid
rm -f /run/vector

exec "$@"
