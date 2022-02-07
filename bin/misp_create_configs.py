#!/usr/bin/env python3
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
import hashlib
import os
import sys
import glob
import uuid
from urllib.parse import urlparse
from typing import Optional
from jinja2 import Environment

required_variables = (
    "MYSQL_HOST", "MYSQL_LOGIN", "MYSQL_DATABASE", "MISP_BASEURL", "SECURITY_SALT", "REDIS_HOST",
    "MISP_ORG", "MISP_EMAIL", "MISP_UUID"
)
optional_variables = (
    "REDIS_PASSWORD", "MYSQL_PASSWORD", "PHP_XDEBUG_ENABLED", "PHP_XDEBUG_PROFILER_TRIGGER", "PHP_SESSIONS_IN_REDIS",
    "GNUPG_PRIVATE_KEY_PASSWORD", "GNUPG_BODY_ONLY_ENCRYPTED", "PROXY_HOST", "PROXY_PORT", "PROXY_METHOD", "PROXY_USER",
    "PROXY_PASSWORD", "MISP_HOST_ORG_ID", "SECURITY_COOKIE_NAME", "ZEROMQ_ENABLED", "OIDC_LOGIN", "OIDC_PROVIDER", "OIDC_PROVIDER_INNER",
    "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET", "OIDC_CLIENT_ID_INNER", "OIDC_CLIENT_SECRET_INNER", "OIDC_PASSWORD_RESET",
    "OIDC_CLIENT_CRYPTO_PASS", "SYSLOG_TARGET", "SYSLOG_PORT", "SYSLOG_PROTOCOL", "MISP_EMAIL_REPLY_TO", "GNUPG_SIGN",
    "ZEROMQ_USERNAME", "ZEROMQ_PASSWORD", "SENTRY_DSN", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD",
    "MISP_MODULE_URL", "MISP_ATTACHMENT_SCAN_MODULE", "SECURITY_ADVANCED_AUTHKEYS", "SECURITY_HIDE_ORGS",
    "OIDC_DEFAULT_ORG", "SENTRY_ENVIRONMENT", "MISP_DEBUG", "SUPPORT_EMAIL", "PHP_SNUFFLEUPAGUS",
    "SECURITY_ENCRYPTION_KEY", "PHP_TIMEZONE", "PHP_MEMORY_LIMIT", "PHP_MAX_EXECUTION_TIME", "PHP_UPLOAD_MAX_FILESIZE",
    "MYSQL_PORT", "SECURITY_CRYPTO_POLICY", "MISP_TERMS_FILE", "MISP_HOME_LOGO", "MISP_FOOTER_LOGO", "MISP_CUSTOM_CSS",
    "OIDC_AUTHENTICATION_METHOD", "OIDC_AUTHENTICATION_METHOD_INNER",
    "JOBBER_USER_ID", "JOBBER_CACHE_FEEDS_TIME", "JOBBER_FETCH_FEEDS_TIME", "JOBBER_PULL_SERVERS_TIME",
    "JOBBER_SCAN_ATTACHMENT_TIME", "JOBBER_LOG_ROTATE_TIME", "PHP_SESSIONS_COOKIE_SAMESITE", "OIDC_CODE_CHALLENGE_METHOD",
    "OIDC_CODE_CHALLENGE_METHOD_INNER",
)
bool_variables = (
    "PHP_XDEBUG_ENABLED", "PHP_SESSIONS_IN_REDIS", "ZEROMQ_ENABLED", "OIDC_LOGIN",
    "GNUPG_BODY_ONLY_ENCRYPTED", "GNUPG_SIGN", "SECURITY_ADVANCED_AUTHKEYS", "SECURITY_HIDE_ORGS",
    "OIDC_DEFAULT_ORG", "MISP_DEBUG",  "PHP_SNUFFLEUPAGUS"
)
default_values = {
    "PHP_SESSIONS_IN_REDIS": "true",
    "PHP_SNUFFLEUPAGUS": "true",
    "PHP_TIMEZONE": "UTC",
    "MISP_HOST_ORG_ID": 1,
    "PHP_MEMORY_LIMIT": "2048M",
    "PHP_MAX_EXECUTION_TIME": 300,
    "PHP_UPLOAD_MAX_FILESIZE": "50M",
    "PROXY_PORT": 3128,
    "MYSQL_PORT": 3306,
    "SYSLOG_PORT": 601,
    "SYSLOG_PROTOCOL": "tcp",
    "SECURITY_CRYPTO_POLICY": "DEFAULT:NO-SHA1",
    "OIDC_AUTHENTICATION_METHOD": "client_secret_basic",
    "JOBBER_USER_ID": "1",
    "JOBBER_CACHE_FEEDS_TIME": "0 R0-10 6,8,10,12,14,16,18",
    "JOBBER_FETCH_FEEDS_TIME": "0 R0-10 6,8,10,12,14,16,18",
    "JOBBER_PULL_SERVERS_TIME": "0 R0-10 6,10,15",
    "JOBBER_SCAN_ATTACHMENT_TIME": "0 R0-10 6",
    "JOBBER_LOG_ROTATE_TIME": "0 0 5",
}


def str_filter(value: Optional[str]) -> str:
    if value is None:
        return 'null'
    return "'" + value.replace("'", "\\'") + "'"


jinja_env = Environment(trim_blocks=True, lstrip_blocks=True)
jinja_env.filters["str"] = str_filter
jinja_env.filters["bool"] = lambda x: 'true' if x else 'false'


def error(message: str):
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(1)


def collect() -> dict:
    variables = {}

    for variable in required_variables:
        if variable not in os.environ:
            error("Environment variable '{}' is required, but not set".format(variable))

        variables[variable] = os.environ.get(variable)

    for variable in optional_variables:
        if variable in os.environ:
            variables[variable] = os.environ.get(variable)
        else:
            variables[variable] = default_values[variable] if variable in default_values else None

    for bool_variable in bool_variables:
        variables[bool_variable] = convert_bool(bool_variable, variables[bool_variable])

    for int_variable in ("MISP_HOST_ORG_ID", "PHP_MAX_EXECUTION_TIME", "MYSQL_PORT", "SYSLOG_PORT", "PROXY_PORT", "JOBBER_USER_ID"):
        variables[int_variable] = convert_int(int_variable, variables[int_variable])

    return variables


def convert_int(variable_name: str, value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        error("Environment variable '{}' must be integer, `{}` given".format(variable_name, value))


def convert_bool(variable_name: str, value: Optional[str]) -> bool:
    if value is None:
        return False

    value = value.lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off", ""):
        return False

    error("Environment variable '{}' must be boolean (`true`, `1`, `yes`, `false`, `0` or `no`), `{}` given".format(variable_name, value))


def check_is_url(variable_name: str, value: Optional[str]):
    if value and not (value.startswith("http://") or value.startswith("https://")):
        error("Environment variable '{}' must start with 'http://' or 'https://'".format(variable_name))


def render_jinja_template(path: str, variables: dict):
    template = jinja_env.from_string(open(path, "r").read())
    template = template.render(variables)
    open(path, "w").write(template)


def generate_apache_config(variables: dict):
    render_jinja_template("/etc/httpd/conf.d/misp.conf", variables)


def generate_jobber_config(variables: dict):
    render_jinja_template("/root/.jobber", variables)


def generate_xdebug_config(enabled: bool, profiler_trigger: str):
    xdebug_config_path = "/etc/php.d/15-xdebug.ini"

    if enabled:
        xdebug_config_template = """
zend_extension=xdebug.so

xdebug.profiler_enable_trigger={profiler_enabled}
xdebug.profiler_enable_trigger_value="{profiler_trigger}"
xdebug.remote_enable=1
"""
        xdebug_config = xdebug_config_template.format(profiler_enabled=1 if profiler_trigger else 0,
                                                      profiler_trigger=profiler_trigger)

        open(xdebug_config_path, "w").write(xdebug_config)


def generate_snuffleupagus_config(enabled: bool):
    if enabled:
        config = """
; Enable 'snuffleupagus' extension module
extension = snuffleupagus.so

; Path to rules configuration files, glob or comma separated list
sp.configuration_file = '/etc/php.d/snuffleupagus-*.rules'
        """
        open("/etc/php.d/40-snuffleupagus.ini", "w").write(config)


def generate_sessions_in_redis_config(enabled: bool, redis_host: str, redis_password: Optional[str] = None):
    if not enabled:
        return

    redis_path = "tcp://{redis_host}:6379?database=12".format(redis_host=redis_host)
    if redis_password:
        redis_path += "&auth={redis_password}".format(redis_password=redis_password)

    config_path = "/etc/php-fpm.d/sessions.conf"
    config_template = """
[www]
php_value[session.save_handler] = redis
php_value[session.save_path]    = "{redis_path}"
"""
    config = config_template.format(redis_path=redis_path)
    open(config_path, "w").write(config)


def generate_rsyslog_config(syslog_target: Optional[str], syslog_port: int, syslog_protocol: str):
    if not syslog_target:
        return

    # Recommended setting from https://github.com/grafana/loki/blob/master/docs/clients/promtail/scraping.md#rsyslog-output-configuration
    config_template = """
action(type="omfwd" target="{syslog_target}" port="{syslog_port}" protocol="{syslog_protocol}"
    Template="RSYSLOG_SyslogProtocol23Format" TCP_Framing="octet-counted"
    action.resumeRetryCount="100"
    queue.type="linkedList" queue.size="10000")
"""
    config = config_template.format(syslog_target=syslog_target, syslog_port=syslog_port,
                                    syslog_protocol=syslog_protocol)
    open("/etc/rsyslog.d/forward.conf", "w+").write(config)


def generate_error_messages(email: str):
    for path in glob.glob('/var/www/html/*.html'):
        render_jinja_template(path, {"SUPPORT_EMAIL": email})


def generate_php_config(variables: dict):
    template = "; Do not edit this file directly! It is automatically generated after every container start.\n" \
               "date.timezone = '{timezone}'\n" \
               "memory_limit = {memory_limit}\n" \
               "max_execution_time = {max_execution_time}\n" \
               "upload_max_filesize = {upload_max_filesize}\n" \
               "post_max_size = {upload_max_filesize}\n" \
               "session.cookie_samesite = '{session_cookie_samesite}'\n"

    template = template.format(
        timezone=variables["PHP_TIMEZONE"],
        memory_limit=variables["PHP_MEMORY_LIMIT"],
        max_execution_time=variables["PHP_MAX_EXECUTION_TIME"],
        upload_max_filesize=variables["PHP_UPLOAD_MAX_FILESIZE"],
        session_cookie_samesite=variables["PHP_SESSIONS_COOKIE_SAMESITE"],
    )
    open("/etc/php.d/99-misp.ini", "w").write(template)


def generate_crypto_policies(crypto_policy: Optional[str]):
    if crypto_policy:
        open("/etc/crypto-policies/config", "w").write(crypto_policy)


def main():
    variables = collect()

    baseurl = urlparse(variables["MISP_BASEURL"])
    if baseurl.scheme not in ("http", "https"):
        error("Environment variable 'MISP_BASEURL' must start with 'http://' or 'https://'")

    if not baseurl.netloc:
        error("Environment variable 'MISP_BASEURL' must be valid URL")

    variables["SERVER_NAME"] = baseurl.netloc

    check_is_url("MISP_MODULE_URL", variables["MISP_MODULE_URL"])

    if len(variables["SECURITY_SALT"]) < 32:
        print("Warning: 'SECURITY_SALT' environment variable should be at least 32 chars long", file=sys.stderr)

    # if security cookie name is not set, generate it by using SECURITY_SALT and MISP_UUID, so it will survive container restart
    if not variables["SECURITY_COOKIE_NAME"]:
        uniq = hashlib.sha256("{}|{}".format(variables["SECURITY_SALT"], variables["MISP_UUID"]).encode()).hexdigest()
        variables["SECURITY_COOKIE_NAME"] = "MISP-session-{}".format(uniq[0:5])

    try:
        uuid.UUID(variables["MISP_UUID"])
    except TypeError:
        error("Environment variable 'MISP_UUID' is not valid UUID.")

    if variables["PHP_SESSIONS_COOKIE_SAMESITE"] not in ("Strict", "Lax", None):
        error("Environment variable 'PHP_SESSIONS_COOKIE_SAMESITE' must be 'Strict', 'Lax' or not set")

    if variables["PHP_SESSIONS_COOKIE_SAMESITE"] is None:
        is_localhost = variables["MISP_BASEURL"].startswith("http://localhost")
        variables["PHP_SESSIONS_COOKIE_SAMESITE"] = "Lax" if is_localhost else "Strict"

    variables["MISP_UUID"] = variables["MISP_UUID"].lower()

    for var in ("OIDC_PROVIDER_INNER", "OIDC_CLIENT_ID_INNER", "OIDC_CLIENT_SECRET_INNER", "OIDC_AUTHENTICATION_METHOD_INNER", "OIDC_CODE_CHALLENGE_METHOD_INNER"):
        if not variables[var]:
            variables[var] = variables[var.replace("_INNER", "")]

    if variables["OIDC_LOGIN"]:
        for var in ("OIDC_PROVIDER", "OIDC_CLIENT_CRYPTO_PASS", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET"):
            if not variables[var]:
                error("OIDC login is enabled, but '{}' environment variable is not set".format(var))
        check_is_url("OIDC_PROVIDER", variables["OIDC_PROVIDER"])
        check_is_url("OIDC_PROVIDER_INNER", variables["OIDC_PROVIDER_INNER"])

        for var in ("OIDC_CODE_CHALLENGE_METHOD", "OIDC_CODE_CHALLENGE_METHOD_INNER"):
            if variables[var] not in ("S256", "plain", "", None):
                error("Environment variable '{}' value is not valid".format(var))

        # mod_auth_openidc require full URL to metadata
        if "/.well-known/openid-configuration" not in variables["OIDC_PROVIDER"]:
            variables["OIDC_PROVIDER"] = variables["OIDC_PROVIDER"].rstrip("/") + "/.well-known/openid-configuration"

    for template_name in ("database.php", "config.php", "email.php"):
        path = "/var/www/MISP/app/Config/{}".format(template_name)
        render_jinja_template(path, variables)

    generate_xdebug_config(variables["PHP_XDEBUG_ENABLED"], variables["PHP_XDEBUG_PROFILER_TRIGGER"])
    generate_snuffleupagus_config(variables['PHP_SNUFFLEUPAGUS'])
    generate_sessions_in_redis_config(variables["PHP_SESSIONS_IN_REDIS"], variables["REDIS_HOST"], variables["REDIS_PASSWORD"])
    generate_apache_config(variables)
    generate_rsyslog_config(variables["SYSLOG_TARGET"], variables["SYSLOG_PORT"], variables["SYSLOG_PROTOCOL"])
    generate_error_messages(variables["SUPPORT_EMAIL"])
    generate_php_config(variables)
    generate_crypto_policies(variables["SECURITY_CRYPTO_POLICY"])
    generate_jobber_config(variables)


if __name__ == "__main__":
    main()
