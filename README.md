# MISP Docker image

[MISP](https://github.com/misp/misp/) container (Docker) image focused on high performance and security based on [AlmaLinux 9](https://hub.docker.com/_/almalinux), ready for production.

This image contains the latest version of MISP and the required dependencies. Image is intended as immutable, which means that it is not possible
to update MISP from the user interface and instead, an admin should download a newer image.

> [!IMPORTANT]  
> This container is intended to be used with MISP v2.5. If you want to use older MISP v2.4, please use [`misp-2.4` branch](https://github.com/NUKIB/misp/tree/misp-2.4). 

> [!IMPORTANT]  
> This container is intended to be used with RHEL 9 base image. If you want to use older base image, please use [`el8` branch](https://github.com/NUKIB/misp/tree/el8).

## Key features

* 🎩 Image is based on AlmaLinux, so it perfectly fits your infrastructure if you use CentOS or RHEL as a host system
* ✅ Modern MISP features are enabled by default (like advanced audit log or storing settings in the database)
* 👩‍💻 Integrated support for [OpenID Connect (OIDC) authentication](docs/OIDC.md)
* 🔒️ PHP is by default protected by Snuffleupagus extensions with [rules](snuffleupagus-misp.rules) tailored to MISP
* 🚀 Optional extensions and configurations that will make MISP faster are enabled
* 📓 Integrated support for logging into [ECS format](docs/LOGGING.md), exceptions to Sentry and forwarding logs to syslog server
* 🧪 The final image is automatically tested, so every release should work as expected
* 🏛 Build for amd64 (x86_64) and arm64 (aarch64)

## Usage

First, you have to install Docker. Follow [these manuals](https://docs.docker.com/engine/install/) how to install Docker on your machine. Windows, macOS, or Linux are supported.
For Linux, you also need to install [Docker Compose V2](https://docs.docker.com/compose/cli-command/), on macOS or Windows is already included in Docker itself.
Or you can use Docker Compose V1, but then you have to use all commands with a dash (so `docker-compose` instead of `docker compose`). 

### Usage for testing

Docker Compose file defines MISP itself, [MISP Modules](https://github.com/NUKIB/misp-modules), MariaDB and Redis, so everything you need to run MISP. Just run:

    curl --proto '=https' --tlsv1.2 -O https://raw.githubusercontent.com/NUKIB/misp/main/docker-compose.yml
    docker compose up -d

Then you can access MISP in your browser by accessing `http://localhost:8080`. The default user after installation is `admin@admin.test` with the password `admin`.

To delete all volumes after testing, run:

    docker-compose down -v

### Updating

When a new MISP is released, a new container image is also created. To update MISP and MISP Modules, just run these commands in the folder that contains `docker-compose.yml` file.
These commands will download the latest images and recreate containers. All data will be preserved.

    docker compose pull
    docker compose up -d

### Usage in a production environment

For production usage, please:
* change passwords for MariaDB and Redis,
* modify environment variables to requested values,
* deploy reverse proxy (for example `nginx`) before MISP to handle HTTPS connections.
  * do not forget to send the proper `X-Forwared-For` header

### Usage in air-gapped environment

MISP by default does not require access to Internet. So it is possible to use MISP in air-gapped environment or an environment with blocked outgoing connections. Check [AIR-GAP.md](docs/AIR-GAP.md) for more information.

### Image building

If you don't trust image built by GitHub Actions and stored in GitHub Container Registry or you want to build a different MISP version, you can build this image by yourself:

    docker build --build-arg MISP_VERSION=v2.5.0 -t ghcr.io/nukib/misp https://github.com/NUKIB/misp.git#main

If you don't like AlmaLinux, you can use as a base image different distribution that is compatible with AlmaLinux 9, like [CentOS Stream](https://www.centos.org/centos-stream/) or [Rocky Linux](https://hub.docker.com/r/rockylinux/rockylinux):

    docker build --build-arg BASE_IMAGE=quay.io/centos/centos:stream9 -t ghcr.io/nukib/misp https://github.com/NUKIB/misp.git#main

## Logging

Logging is important to keep your MISP secure and in good condition. [Check detailed manual how to configure logging.](docs/LOGGING.md)

## Environment variables

By changing or defining these container environment variables, you can change container behavior.

### Database connection

MISP requires MySQL or MariaDB database.

* `MYSQL_HOST` (required, string) - hostname or IP address
* `MYSQL_PORT` (optional, int, default `3306`)
* `MYSQL_LOGIN` (required, string) - database user
* `MYSQL_PASSWORD` (optional, string)
* `MYSQL_DATABASE` (required, string) - database name

### Redis

By default, MISP requires Redis. MISP will connect to Redis defined in `REDIS_HOST` variable on port `6379`. Redis alternative [Dragonfly](https://www.dragonflydb.io) is also supported.

* `REDIS_HOST` (required, string) - hostname or IP address
* `REDIS_PASSWORD` (optional, string) - password used to connect password-protected Redis instance
* `REDIS_USE_TLS` (optional, bool) - enable encrypted communication

#### Default Redis databases

* `10` - ZeroMQ connector
* `11` - SimpleBackgroundJobs
* `12` - session data if `PHP_SESSIONS_IN_REDIS` is enabled
* `13` - MISP app

### Application

* `MISP_BASEURL` (required, string) - full URL with https:// or http://
* `MISP_UUID` (required, string) - MISP instance UUID (can be generated by `uuidgen` command)
* `MISP_ORG` (required, string) - MISP default organisation name
* `MISP_HOST_ORG_ID` (optional, int, default `1`) - MISP default organisation ID
* `MISP_MODULE_URL` (optional, string) - full URL to MISP modules
* `MISP_DEBUG` (optional, boolean, default `false`) - enable debug mode (do not enable on production environment)
* `MISP_OUTPUT_COMPRESSION` (optional, boolean, default `true`) - enable or disable gzip or brotli output compression

[Check more variables that allow MISP customization.](docs/CUSTOMIZATION.md)

### Email setting

* `SMTP_HOST` (optional, string) - SMTP server that will be used for sending emails. SMTP server must support STARTTLS.
* `SMTP_PORT` (optional, int, default `25`) - the TCP port for the SMTP host. Must support STARTTLS.
* `SMTP_USERNAME` (optional, string)
* `SMTP_PASSWORD` (optional, string)
* `MISP_EMAIL` (required, string) - the email address that MISP should use for all notifications
* `MISP_EMAIL_REPLY_TO` (optional, string) - the email address that will be used in `Reply-To` header
* `MISP_DEFAULT_PUBLISH_ALERT` (optional, bool, default `false`) - if sending event alert emails should be enabled by default to newly created users
* `SUPPORT_EMAIL` (optional, string) - the email address that will be included in Apache error pages

### PGP for email encryption and signing

* `GNUPG_SIGN` (optional, boolean, default `false`) - sign outgoing emails by PGP
* `GNUPG_PRIVATE_KEY` (optional, string) - private key used to sign emails sent by MISP
* `GNUPG_PRIVATE_KEY_PASSWORD` (optional, string) - password for PGP private key used to sign emails sent by MISP
* `GNUPG_BODY_ONLY_ENCRYPTED` (optional, boolean, default `false`)

Alternatively, if you want to generate new PGP keys for email signing instead of
providing a key using `GNUPG_PRIVATE_KEY`, you can do it by running this command
inside the container:

    gpg --homedir /var/www/MISP/.gnupg --full-generate-key --pinentry-mode=loopback --passphrase "password"

### Security

* `SECURITY_SALT` (required, string) - random string (recommended at least 32 chars) used for salting hashed values (you can use `openssl rand -base64 32` output as value)
* `SECURITY_ADVANCED_AUTHKEYS` (optional, boolean, default `false`) - enable advanced auth keys support
* `SECURITY_HIDE_ORGS` (optional, boolean, default `false`) - hide org names for normal users
* `SECURITY_ENCRYPTION_KEY` (optional, string) - encryption key with at least 32 chars that will be used to encrypt sensitive information stored in database *WARNING:* Never change this value after deployment!
* `SECURITY_CRYPTO_POLICY` (optional, string, default `DEFAULT:NO-SHA1`) - set container wide crypto policies. [More details](https://www.redhat.com/en/blog/consistent-security-crypto-policies-red-hat-enterprise-linux-8). Use an empty string to keep container default value.
* `SECURITY_REST_CLIENT_ENABLE_ARBITRARY_URLS` (optional, boolean, default `false`) - enable to query any arbitrary URL via rest client (required for Workflows Webhook).

### Outgoing proxy

For pulling events from another MISP or fetching feeds MISP requires access to Internet. Set these variables to use HTTP proxy for outgoing connections from MISP.

* `PROXY_HOST` (optional, string) - The hostname of an HTTP proxy for outgoing sync requests. Leave empty to not use a proxy.
* `PROXY_PORT` (optional, int, default `3128`) - The TCP port for the HTTP proxy.
* `PROXY_METHOD` (optional, string) - The authentication method for the HTTP proxy. Currently, supported are Basic or Digest. Leave empty for no proxy authentication.
* `PROXY_USER` (optional, string) - The authentication username for the HTTP proxy.
* `PROXY_PASSWORD` (optional, string) - The authentication password for the HTTP proxy.

### OpenID Connect (OIDC) login

[Check detailed manual how to configure OIDC login](docs/OIDC.md)

### ZeroMQ

* `ZEROMQ_ENABLED` (optional, boolean, default `false`) - enable ZeroMQ integration, server will listen at `*:50000`
* `ZEROMQ_USERNAME` (optional, string) - ZeroMQ server username
* `ZEROMQ_PASSWORD` (optional, string) - ZeroMQ server password

### PHP config

* `PHP_SESSIONS_IN_REDIS` (optional, boolean, default `true`) - when enabled, sessions are stored in Redis. That provides better performance and sessions survive container restart
* `PHP_SESSIONS_COOKIE_SAMESITE` (optional, string, default `Lax`) - sets [session.cookie_samesite](https://www.php.net/manual/en/session.configuration.php#ini.session.cookie-samesite), can be `Strict` or `Lax`.
* `PHP_SNUFFLEUPAGUS` (optional, boolean, default `true`) - enable PHP hardening by using [Snuffleupagus](https://snuffleupagus.readthedocs.io) PHP extension with [rules](snuffleupagus-misp.rules) tailored to MISP (when enabled, PHP JIT will be disabled)
* `PHP_TIMEZONE` (optional, string, default `UTC`) - sets [date.timezone](https://www.php.net/manual/en/datetime.configuration.php#ini.date.timezone)
* `PHP_MEMORY_LIMIT` (optional, string, default `2048M`) - sets [memory_limit](https://www.php.net/manual/en/ini.core.php#ini.memory-limit)
* `PHP_MAX_EXECUTION_TIME` (optional, int, default `300`) - sets [max_execution_time](https://www.php.net/manual/en/info.configuration.php#ini.max-execution-time) (in seconds)
* `PHP_UPLOAD_MAX_FILESIZE` (optional, string, default `50M`) - sets [upload_max_filesize](https://www.php.net/manual/en/ini.core.php#ini.upload-max-filesize) and [post_max_size](https://www.php.net/manual/en/ini.core.php#ini.post-max-size)
* `PHP_XDEBUG_ENABLED` (optional, boolean, default `false`) - enable [Xdebug](https://xdebug.org) PHP extension for debugging purposes (do not enable on production environment)
* `PHP_XDEBUG_PROFILER_TRIGGER` (optional, string) - secret value for `XDEBUG_PROFILE` GET/POST variable that will enable profiling

### Jobber

Automation tasks are run by [jobber](https://github.com/dshearer/jobber) application, which is managed by `supervisor`. Check [`.jobber`](.jobber) file for tasks definition.

You can change default configuration by modifying these environment variables:

* `JOBBER_USER_ID` (optional, int, default `1`) - MISP user ID which is used in scheduled tasks by Jobber (1 is the user ID of the initial created admin@admin.test user)
* `JOBBER_CACHE_FEEDS_TIME` (optional, string, default `0 R0-10 6,8,10,12,14,16,18`) - [Jobber time string][jobber-time-string] for cache feeds task scheduling
* `JOBBER_FETCH_FEEDS_TIME` (optional, string, default `0 R0-10 6,8,10,12,14,16,18`) - [Jobber time string][jobber-time-string] for fetch feeds task scheduling
* `JOBBER_PULL_SERVERS_TIME` (optional, string, default `0 R0-10 6,10,15`) - [Jobber time string][jobber-time-string] for pull servers task scheduling
* `JOBBER_PUSH_SERVERS_TIME` (optional, string) - [Jobber time string][jobber-time-string] for pushing to servers task scheduling
* `JOBBER_CACHE_SERVERS_TIME` (optional, string, default `0 R0-10 6,10,15`) - [Jobber time string][jobber-time-string] for cache servers task scheduling
* `JOBBER_SCAN_ATTACHMENT_TIME` (optional, string, default `0 R0-10 6`) - [Jobber time string][jobber-time-string] for scan attachment task scheduling
* `JOBBER_LOG_ROTATE_TIME` (optional, string, default `0 0 5`) - [Jobber time string][jobber-time-string] for log rotate task scheduling
* `JOBBER_USER_CHECK_VALIDITY_TIME` (optional, string, default `0 0 5`) - [Jobber time string][jobber-time-string] for updating user role and org or blocking invalid users (makes sense only if `OIDC_OFFLINE_ACCESS` and `OIDC_CHECK_USER_VALIDITY` is set)
* `JOBBER_SEND_PERIODIC_SUMMARY` (optional, string, default `0 0 6 * * 1-5`) - [Jobber time string][jobber-time-string]for sending periodic summary for users (must be just once per day)

If provided time string is empty, job will be disabled.

[jobber-time-string]: https://dshearer.github.io/jobber/doc/v1.4/#time-strings

### Supervisor

Supervisor is used to run all processes within the container, you can adjust the amount of workers that should be started by modifying these variables:

* `DEFAULT_WORKERS` (optional, int, default `1`) - number of default workers to start
* `EMAIL_WORKERS` (optional, int, default `3`) - number of email workers to start
* `CACHE_WORKERS` (optional, int, default `1`) - number of cache workers to start
* `PRIO_WORKERS` (optional, int, default `3`) - number of prio workers to start
* `UPDATE_WORKERS` (optional, int, default `1`) - number of update workers to start

If one of the variables is set to `0`, no workers will be started.

### Extra variables

* `ECS_`, `SYSLOG_` and `SENTRY_` are documented in [LOGGING.md](docs/LOGGING.md) 
* `OIDC_` are documented in [OIDC.md](docs/OIDC.md) 
* `S3_` for storing attachments in S3 compatible object storage are documented in [S3_SUPPORT.md](docs/S3_SUPPORT.md) 

## Container volumes

* `/var/www/MISP/app/tmp/logs/` - application logs
* `/var/www/MISP/app/files/certs/` - uploaded certificates used for accessing remote feeds and servers
* `/var/www/MISP/app/attachments/` - uploaded attachments and malware samples
* `/var/www/MISP/.gnupg/` - GPG homedir

## License

This software is licensed under GNU General Public License version 3. MISP is licensed under GNU Affero General Public License version 3.

* Copyright (C) 2022-2024 [National Cyber and Information Security Agency of the Czech Republic (NÚKIB)](https://nukib.gov.cz/en/) 🇨🇿
