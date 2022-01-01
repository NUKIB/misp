#!/usr/bin/env python3
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
import hashlib
import os
import sys
import glob
import uuid
from urllib.parse import urlparse
from typing import Optional
from jinja2 import Template

required_variables = (
    "MYSQL_HOST", "MYSQL_LOGIN", "MYSQL_DATABASE", "MISP_BASEURL", "SECURITY_SALT", "REDIS_HOST",
    "MISP_ORG", "MISP_EMAIL", "MISP_UUID")
optional_variables = (
    "REDIS_PASSWORD", "MYSQL_PASSWORD", "PHP_XDEBUG_ENABLED", "PHP_XDEBUG_PROFILER_TRIGGER", "PHP_SESSIONS_IN_REDIS",
    "GNUPG_PRIVATE_KEY_PASSWORD", "GNUPG_BODY_ONLY_ENCRYPTED", "PROXY_HOST", "PROXY_PORT", "PROXY_METHOD", "PROXY_USER", "PROXY_PASSWORD", "MISP_HOST_ORG_ID", "SECURITY_COOKIE_NAME",
    "ZEROMQ_ENABLED", "OIDC_LOGIN", "OIDC_PROVIDER", "OIDC_PROVIDER_INNER",
    "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET", "OIDC_CLIENT_ID_INNER", "OIDC_CLIENT_SECRET_INNER", "OIDC_PASSWORD_RESET",
    "OIDC_CLIENT_CRYPTO_PASS", "SYSLOG_TARGET", "SYSLOG_PORT", "SYSLOG_PROTOCOL", "MISP_EMAIL_REPLY_TO", "GNUPG_SIGN",
    "ZEROMQ_USERNAME", "ZEROMQ_PASSWORD", "SENTRY_DSN", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD",
    "MISP_MODULE_URL", "MISP_ATTACHMENT_SCAN_MODULE", "SECURITY_ADVANCED_AUTHKEYS", "SECURITY_HIDE_ORGS",
    "OIDC_DEFAULT_ORG", "SENTRY_ENVIRONMENT", "MISP_DEBUG", "SUPPORT_EMAIL", "PHP_SNUFFLEUPAGUS",
    "SECURITY_ENCRYPTION_KEY",
)
bool_variables = (
    "PHP_XDEBUG_ENABLED", "PHP_SESSIONS_IN_REDIS", "ZEROMQ_ENABLED", "OIDC_LOGIN",
    "GNUPG_BODY_ONLY_ENCRYPTED", "GNUPG_SIGN", "SECURITY_ADVANCED_AUTHKEYS", "SECURITY_HIDE_ORGS",
    "OIDC_DEFAULT_ORG", "MISP_DEBUG",  "PHP_SNUFFLEUPAGUS"
)
default_values = {
    "PHP_SESSIONS_IN_REDIS": "true",
    "PHP_SNUFFLEUPAGUS": "true",
    "MISP_HOST_ORG_ID": "1",
}


def error(message: str):
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(1)


def convert_bool(input_string: str) -> bool:
    return input_string.lower() in ("true", "1", "yes")


def generate_apache_config(variables: dict):
    path = "/etc/httpd/conf.d/misp.conf"
    template = Template(open(path, "r").read())
    template = template.render(variables)
    open(path, "w").write(template)


def generate_xdebug_config(enabled: bool, profiler_trigger: str):
    if profiler_trigger and not enabled:
        error("Environment variable 'PHP_XDEBUG_PROFILER_TRIGGER' is set, but xdebug is not enabled")

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


def generate_rsyslog_config(syslog_target: Optional[str], syslog_port: Optional[str] = None,
                            syslog_protocol: Optional[str] = None):
    if not syslog_target:
        return

    if not syslog_port:
        syslog_port = 601

    if not syslog_protocol:
        syslog_protocol = "tcp"

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


def generate_error_messages(email):
    for path in glob.glob('/var/www/html/*.html'):
        template = Template(open(path, "r").read())
        template = template.render({"SUPPORT_EMAIL": email})
        open(path, "w").write(template)


if __name__ == "__main__":
    variables = {}

    for variable in required_variables:
        if variable not in os.environ:
            error("Environment variable '{}' is required, but not set.".format(variable))

        variables[variable] = os.environ.get(variable)

    for variable in optional_variables:
        if variable in os.environ:
            variables[variable] = os.environ.get(variable)
        else:
            variables[variable] = default_values[variable] if variable in default_values else ""

    for bool_variable in bool_variables:
        variables[bool_variable] = convert_bool(variables[bool_variable])

    # Convert to int
    variables["MISP_HOST_ORG_ID"] = int(variables["MISP_HOST_ORG_ID"])

    baseurl = urlparse(variables["MISP_BASEURL"])
    if baseurl.scheme not in ("http", "https"):
        error("Environment variable 'MISP_BASEURL' must start with 'http://' or 'https://'")

    if baseurl.netloc == "":
        error("Environment variable 'MISP_BASEURL' must be valid URL")

    variables["SERVER_NAME"] = baseurl.netloc

    if variables["MISP_MODULE_URL"] and not (variables["MISP_MODULE_URL"].startswith("http://") or variables["MISP_MODULE_URL"].startswith("https://")):
        error("Environment variable 'MISP_MODULE_URL' must start with 'http://' or 'https://'")

    if len(variables["SECURITY_SALT"]) < 32:
        print("Warning: 'SECURITY_SALT' environment variable should be at least 32 chars long.", file=sys.stderr)

    # if security cookie name is not set, generate it by using SECURITY_SALT and MISP_UUID so it will survive container restart
    if len(variables["SECURITY_COOKIE_NAME"]) == 0:
        uniq = hashlib.sha256("{}|{}".format(variables["SECURITY_SALT"], variables["MISP_UUID"]).encode()).hexdigest()
        variables["SECURITY_COOKIE_NAME"] = "MISP-session-{}".format(uniq[0:5])

    try:
        uuid.UUID(variables["MISP_UUID"])
    except TypeError:
        error("MISP_UUID is not valid UUID.")

    variables["MISP_UUID"] = variables["MISP_UUID"].lower()

    for var in ("OIDC_PROVIDER_INNER", "OIDC_CLIENT_ID_INNER", "OIDC_CLIENT_SECRET_INNER"):
        if variables[var] == "":
            variables[var] = variables[var.replace("_INNER", "")]

    for template_name in ("database.php", "config.php", "email.php"):
        path = "/var/www/MISP/app/Config/{}".format(template_name)

        template = Template(open(path, "r").read())
        template = template.render(variables)
        open(path, "w").write(template)

    generate_xdebug_config(variables["PHP_XDEBUG_ENABLED"], variables["PHP_XDEBUG_PROFILER_TRIGGER"])
    generate_snuffleupagus_config(variables['PHP_SNUFFLEUPAGUS'])
    generate_sessions_in_redis_config(variables["PHP_SESSIONS_IN_REDIS"], variables["REDIS_HOST"], variables["REDIS_PASSWORD"])
    generate_apache_config(variables)
    generate_rsyslog_config(variables["SYSLOG_TARGET"], variables["SYSLOG_PORT"], variables["SYSLOG_PROTOCOL"])
    generate_error_messages(variables["SUPPORT_EMAIL"] if "SUPPORT_EMAIL" in variables["SUPPORT_EMAIL"] else "no@example.com")
