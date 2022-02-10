#!/usr/bin/env python3
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
import hashlib
import os
import sys
import glob
import uuid
from urllib.parse import urlparse
from typing import Optional, Type
from jinja2 import Environment


class Option:
    def __init__(self, required: bool = False, typ: Type = str, default=None):
        self.required = required
        self.typ = typ
        self.default = default


VARIABLES = {
    # MySQL
    "MYSQL_HOST": Option(required=True),
    "MYSQL_PORT": Option(typ=int, default=3306),
    "MYSQL_LOGIN": Option(required=True),
    "MYSQL_PASSWORD": Option(),
    "MYSQL_DATABASE": Option(required=True),
    # Redis
    "REDIS_HOST": Option(required=True),
    "REDIS_PASSWORD": Option(),
    # Proxy
    "PROXY_HOST": Option(),
    "PROXY_PORT": Option(typ=int, default=3128),
    "PROXY_METHOD": Option(),
    "PROXY_USER": Option(),
    "PROXY_PASSWORD": Option(),
    # OIDC
    "OIDC_LOGIN": Option(typ=bool),
    "OIDC_PROVIDER": Option(),
    "OIDC_PROVIDER_INNER": Option(),
    "OIDC_CLIENT_ID": Option(),
    "OIDC_CLIENT_ID_INNER": Option(),
    "OIDC_CLIENT_SECRET": Option(),
    "OIDC_CLIENT_SECRET_INNER": Option(),
    "OIDC_CODE_CHALLENGE_METHOD": Option(),
    "OIDC_CODE_CHALLENGE_METHOD_INNER": Option(),
    "OIDC_AUTHENTICATION_METHOD": Option(default="client_secret_basic"),
    "OIDC_AUTHENTICATION_METHOD_INNER": Option(),
    "OIDC_CLIENT_CRYPTO_PASS": Option(),
    "OIDC_DEFAULT_ORG": Option(typ=bool),
    "OIDC_PASSWORD_RESET": Option(),
    # Logging
    "SYSLOG_TARGET": Option(),
    "SYSLOG_PORT": Option(typ=int, default=601),
    "SYSLOG_PROTOCOL": Option(default="tcp"),
    "SENTRY_DSN": Option(),
    "SENTRY_ENVIRONMENT": Option(),
    # ZeroMQ
    "ZEROMQ_ENABLED": Option(typ=bool, default=False),
    "ZEROMQ_USERNAME": Option(),
    "ZEROMQ_PASSWORD": Option(),
    # SMTP
    "SMTP_HOST": Option(),
    "SMTP_USERNAME": Option(),
    "SMTP_PASSWORD": Option(),
    "SUPPORT_EMAIL": Option(),
    # MISP
    "MISP_BASEURL": Option(required=True),
    "MISP_ORG": Option(required=True),
    "MISP_EMAIL": Option(required=True),
    "MISP_UUID": Option(required=True),
    "MISP_MODULE_URL": Option(),
    "MISP_ATTACHMENT_SCAN_MODULE": Option(),
    "MISP_EMAIL_REPLY_TO": Option(),
    "MISP_HOST_ORG_ID": Option(typ=int, default=1),
    "MISP_DEBUG": Option(typ=bool, default=False),
    "MISP_TERMS_FILE": Option(),
    "MISP_HOME_LOGO": Option(),
    "MISP_FOOTER_LOGO": Option(),
    "MISP_CUSTOM_CSS": Option(),
    # Security
    "GNUPG_SIGN": Option(typ=bool, default=False),
    "GNUPG_PRIVATE_KEY_PASSWORD": Option(),
    "GNUPG_BODY_ONLY_ENCRYPTED": Option(typ=bool, default=False),
    "SECURITY_ADVANCED_AUTHKEYS": Option(typ=bool, default=False),
    "SECURITY_HIDE_ORGS": Option(typ=bool, default=False),
    "SECURITY_SALT": Option(required=True),
    "SECURITY_CRYPTO_POLICY": Option(default="DEFAULT:NO-SHA1"),
    "SECURITY_ENCRYPTION_KEY": Option(),
    "SECURITY_COOKIE_NAME": Option(),
    # PHP
    "PHP_XDEBUG_ENABLED": Option(typ=bool, default=False),
    "PHP_XDEBUG_PROFILER_TRIGGER": Option(),
    "PHP_SESSIONS_IN_REDIS": Option(typ=bool, default=True),
    "PHP_SNUFFLEUPAGUS": Option(typ=bool, default=True),
    "PHP_TIMEZONE": Option(default="UTC"),
    "PHP_MEMORY_LIMIT": Option(default="2048M"),
    "PHP_MAX_EXECUTION_TIME": Option(typ=int, default=300),
    "PHP_UPLOAD_MAX_FILESIZE": Option(default="50M"),
    "PHP_SESSIONS_COOKIE_SAMESITE": Option(),
    # Jobber
    "JOBBER_USER_ID": Option(typ=int, default=1),
    "JOBBER_CACHE_FEEDS_TIME": Option(default="0 R0-10 6,8,10,12,14,16,18"),
    "JOBBER_FETCH_FEEDS_TIME": Option(default="0 R0-10 6,8,10,12,14,16,18"),
    "JOBBER_PULL_SERVERS_TIME": Option(default="0 R0-10 6,10,15"),
    "JOBBER_SCAN_ATTACHMENT_TIME": Option(default="0 R0-10 6"),
    "JOBBER_LOG_ROTATE_TIME": Option(default="0 0 5"),
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

    for variable, option in VARIABLES.items():
        if variable not in os.environ:
            if option.required:
                error("Environment variable '{}' is required, but not set".format(variable))
            elif option.default is not None:
                value = option.default
            else:
                value = None
        else:
            value = os.environ.get(variable)
            if option.typ == int:
                value = convert_int(variable, value)
            elif option.typ == bool:
                value = convert_bool(variable, value)

        variables[variable] = value

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
