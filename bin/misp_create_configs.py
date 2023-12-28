#!/usr/bin/env python3
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
import os
import sys
import glob
import uuid
import json
import hashlib
import argparse
from urllib.parse import urlparse
from typing import Optional, Type, Callable, Any, NoReturn, List, Union, Tuple
from jinja2 import Environment


class Option:
    def __init__(self, required: bool = False, typ: Type = str, default: Any = None,
                 validation: Callable[[str, Any], NoReturn] = None, options: Optional[Union[List, Tuple]] = None):
        self.required = required
        self.typ = typ
        self.default = default
        self.validation = validation
        self.options = options

    def get_value(self, env_name: str) -> Any:
        if env_name not in os.environ:
            if self.required:
                raise ValueError(f"Environment variable '{env_name}' is required, but not set")
            elif self.default is not None:
                value = self.default
            else:
                value = None
        else:
            value = os.environ.get(env_name)
            if self.typ == int:
                value = self.convert_int(env_name, value)
            elif self.typ == bool:
                value = self.convert_bool(env_name, value)

            if self.validation:
                self.validation(env_name, value)

            if self.options and value not in self.options:
                options = ", ".join([f"`{option}`" for option in self.options])
                raise ValueError(f"Environment variable '{env_name}' value `{value}` is invalid, must be one of: {options}")

        return value

    @staticmethod
    def convert_int(variable_name: str, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Environment variable '{variable_name}' must be integer, `{value}` given")

    @staticmethod
    def convert_bool(variable_name: str, value: str) -> bool:
        value = value.lower()
        if value in ("true", "1", "yes", "on"):
            return True
        if value in ("false", "0", "no", "off", ""):
            return False

        raise ValueError(f"Environment variable '{variable_name}' must be boolean (`true`, `1`, `yes`, `false`, `0` or `no`), `{value}` given")


def check_is_url(variable_name: str, value: str):
    baseurl = urlparse(value)
    if baseurl.scheme not in ("http", "https"):
        raise ValueError(f"Environment variable '{variable_name}' must start with 'http://' or 'https://'")

    if not baseurl.netloc:
        raise ValueError(f"Environment variable '{variable_name}' must be valid URL, `{value}` given")


def check_is_email(variable_name: str, value: str):
    if '@' not in value:
        raise ValueError(f"Environment variable '{variable_name}' must be email address, `{value}` given")


def check_is_uuid(variable_name: str, value: str):
    try:
        uuid.UUID(value)
    except ValueError:
        raise ValueError(f"Environment variable '{variable_name}' must valid UUID, `{value}` given")


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
    "REDIS_USE_TLS": Option(typ=bool, default=False),
    # Proxy
    "PROXY_HOST": Option(),
    "PROXY_PORT": Option(typ=int, default=3128),
    "PROXY_METHOD": Option(),
    "PROXY_USER": Option(),
    "PROXY_PASSWORD": Option(),
    # OIDC
    "OIDC_LOGIN": Option(typ=bool),
    "OIDC_PROVIDER": Option(validation=check_is_url),
    "OIDC_PROVIDER_INNER": Option(validation=check_is_url),
    "OIDC_CLIENT_ID": Option(),
    "OIDC_CLIENT_ID_INNER": Option(),
    "OIDC_CLIENT_SECRET": Option(),
    "OIDC_CLIENT_SECRET_INNER": Option(),
    "OIDC_CODE_CHALLENGE_METHOD": Option(),
    "OIDC_CODE_CHALLENGE_METHOD_INNER": Option(),
    "OIDC_AUTHENTICATION_METHOD": Option(default="client_secret_basic"),
    "OIDC_AUTHENTICATION_METHOD_INNER": Option(),
    "OIDC_CLIENT_CRYPTO_PASS": Option(),
    "OIDC_DEFAULT_ORG": Option(),
    "OIDC_PASSWORD_RESET": Option(validation=check_is_url),
    "OIDC_ROLES_PROPERTY": Option(default="roles"),
    "OIDC_ROLES_PROPERTY_INNER": Option(),
    "OIDC_ORGANISATION_PROPERTY": Option(default="organization"),
    "OIDC_OFFLINE_ACCESS": Option(typ=bool, default=False),
    "OIDC_CHECK_USER_VALIDITY": Option(typ=int, default=0),
    "OIDC_TOKEN_SIGNED_ALGORITHM": Option(),
    # Logging
    "ECS_LOG_ENABLED": Option(typ=bool, default=False),
    "ECS_LOG_CONSOLE": Option(typ=bool, default=True),
    "ECS_LOG_CONSOLE_FORMAT": Option(typ=str, options=("text", "ecs"), default="ecs"),
    "ECS_LOG_FILE": Option(typ=str),
    "ECS_LOG_FILE_FORMAT": Option(typ=str, options=("text", "ecs"), default="ecs"),
    "ECS_LOG_VECTOR_ADDRESS": Option(typ=str),
    "SYSLOG_ENABLED": Option(typ=bool, default=True),
    "SYSLOG_TARGET": Option(),
    "SYSLOG_PORT": Option(typ=int, default=601),
    "SYSLOG_PROTOCOL": Option(default="tcp"),
    "SYSLOG_FILE": Option(default="/var/log/messages"),
    "SYSLOG_FILE_FORMAT": Option(default="text-traditional", options=("text-traditional", "text", "json")),
    "SENTRY_DSN": Option(validation=check_is_url),
    "SENTRY_ENVIRONMENT": Option(),
    # ZeroMQ
    "ZEROMQ_ENABLED": Option(typ=bool, default=False),
    "ZEROMQ_USERNAME": Option(),
    "ZEROMQ_PASSWORD": Option(),
    # SMTP
    "SMTP_HOST": Option(),
    "SMTP_PORT": Option(typ=int, default=25),
    "SMTP_USERNAME": Option(),
    "SMTP_PASSWORD": Option(),
    "SUPPORT_EMAIL": Option(validation=check_is_email),
    # MISP
    "MISP_BASEURL": Option(required=True, validation=check_is_url),
    "MISP_ORG": Option(required=True),
    "MISP_EMAIL": Option(required=True, validation=check_is_email),
    "MISP_UUID": Option(required=True, validation=check_is_uuid),
    "MISP_MODULE_URL": Option(validation=check_is_url),
    "MISP_ATTACHMENT_SCAN_MODULE": Option(),
    "MISP_EMAIL_REPLY_TO": Option(validation=check_is_email),
    "MISP_DEFAULT_PUBLISH_ALERT": Option(typ=bool, default=False),
    "MISP_HOST_ORG_ID": Option(typ=int, default=1),
    "MISP_DEBUG": Option(typ=bool, default=False),
    "MISP_TERMS_FILE": Option(),
    "MISP_HOME_LOGO": Option(),
    "MISP_FOOTER_LOGO": Option(),
    "MISP_CUSTOM_CSS": Option(),
    # Security
    "GNUPG_SIGN": Option(typ=bool, default=False),
    "GNUPG_PRIVATE_KEY_PASSWORD": Option(),
    "GNUPG_PRIVATE_KEY": Option(),
    "GNUPG_BODY_ONLY_ENCRYPTED": Option(typ=bool, default=False),
    "SECURITY_ADVANCED_AUTHKEYS": Option(typ=bool, default=False),
    "SECURITY_HIDE_ORGS": Option(typ=bool, default=False),
    "SECURITY_SALT": Option(required=True),
    "SECURITY_CRYPTO_POLICY": Option(default="DEFAULT:NO-SHA1"),
    "SECURITY_ENCRYPTION_KEY": Option(),
    "SECURITY_COOKIE_NAME": Option(),
    "SECURITY_REST_CLIENT_ENABLE_ARBITRARY_URLS": Option(typ=bool, default=False),
    # PHP
    "PHP_XDEBUG_ENABLED": Option(typ=bool, default=False),
    "PHP_XDEBUG_PROFILER_TRIGGER": Option(),
    "PHP_SESSIONS_IN_REDIS": Option(typ=bool, default=True),
    "PHP_SNUFFLEUPAGUS": Option(typ=bool, default=True),
    "PHP_TIMEZONE": Option(default="UTC"),
    "PHP_MEMORY_LIMIT": Option(default="2048M"),
    "PHP_MAX_EXECUTION_TIME": Option(typ=int, default=300),
    "PHP_UPLOAD_MAX_FILESIZE": Option(default="50M"),
    "PHP_SESSIONS_COOKIE_SAMESITE": Option(options=("Strict", "Lax")),
    # Jobber
    "JOBBER_USER_ID": Option(typ=int, default=1),
    "JOBBER_CACHE_FEEDS_TIME": Option(default="0 R0-10 6,8,10,12,14,16,18"),
    "JOBBER_FETCH_FEEDS_TIME": Option(default="0 R0-10 6,8,10,12,14,16,18"),
    "JOBBER_PULL_SERVERS_TIME": Option(default="0 R0-10 6,10,15"),
    "JOBBER_CACHE_SERVERS_TIME": Option(default="0 R0-10 6,10,15"),
    "JOBBER_SCAN_ATTACHMENT_TIME": Option(default="0 R0-10 6"),
    "JOBBER_LOG_ROTATE_TIME": Option(default="0 0 5"),
    "JOBBER_USER_CHECK_VALIDITY_TIME": Option(default="0 0 5"),
    "JOBBER_SEND_PERIODIC_SUMMARY": Option(default="0 0 6 * * 1-5"),
    # Supervisor
    "DEFAULT_WORKERS": Option(typ=int, default=1),
    "EMAIL_WORKERS": Option(typ=int, default=3),
    "CACHE_WORKERS": Option(typ=int, default=1),
    "PRIO_WORKERS": Option(typ=int, default=3),
    "UPDATE_WORKERS": Option(typ=int, default=1),
}

CONFIG_CREATED_CANARY_FILE = "/.misp-configs-created"


def str_filter(value: Optional[str]) -> str:
    if value is None:
        return 'null'
    return "'" + value.replace("'", "\\'") + "'"


jinja_env = Environment(trim_blocks=True, lstrip_blocks=True)
jinja_env.filters["str"] = str_filter
jinja_env.filters["bool"] = lambda x: 'true' if x else 'false'


def error(message: str):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def warning(message: str):
    print(f"Warning: {message}", file=sys.stderr)


def write_file(path: str, content: str):
    try:
        with open(path, "w") as f:
            f.write(content)
    except OSError as e:
        error(f"Could not write content to {path}: {e}")


def collect() -> dict:
    variables = {}

    for variable, option in VARIABLES.items():
        try:
            variables[variable] = option.get_value(variable)
        except ValueError as e:
            error(str(e))

    return variables


def render_jinja_template(path: str, variables: dict):
    template = jinja_env.from_string(open(path, "r").read())
    rendered = template.render(variables)
    write_file(path, rendered)


def validate_jinja_template(path: str):
    jinja_env.from_string(open(path, "r").read())
    print(f"Template {path} is valid", file=sys.stderr)


def generate_apache_config(variables: dict):
    render_jinja_template("/etc/httpd/conf.d/misp.conf", variables)


def generate_jobber_config(variables: dict):
    render_jinja_template("/root/.jobber", variables)


def generate_supervisor_config(variables: dict):
    render_jinja_template("/etc/supervisord.d/misp.ini", variables)


def generate_xdebug_config(enabled: bool, profiler_trigger: str):
    xdebug_config_path = "/etc/php.d/15-xdebug.ini"

    if enabled:
        profiler_enabled = 1 if profiler_trigger else 0

        xdebug_config = f"zend_extension=xdebug.so\n" \
                        f"\n" \
                        f"xdebug.profiler_enable_trigger={profiler_enabled}\n" \
                        f"xdebug.profiler_enable_trigger_value=\"{profiler_trigger}\"\n" \
                        f"xdebug.remote_enable=1\n"

        write_file(xdebug_config_path, xdebug_config)


def generate_snuffleupagus_config(enabled: bool):
    if not enabled:
        return

    config = f"; Enable 'snuffleupagus' extension module\n" \
             f"extension = snuffleupagus.so\n" \
             f"\n" \
             f"; Path to rules configuration files, glob or comma separated list\n" \
             f"sp.configuration_file = '/etc/php.d/snuffleupagus-*.rules'\n"

    write_file("/etc/php.d/40-snuffleupagus.ini", config)


def generate_sessions_in_redis_config(enabled: bool, redis_host: str, redis_use_tls: Optional[bool] = False, redis_password: Optional[str] = None):
    if not enabled:
        return

    scheme = "tls" if redis_use_tls else "tcp"
    redis_path = f"{scheme}://{redis_host}:6379?database=12"
    if redis_password:
        redis_path = f"{redis_path}&auth={redis_password}"

    config_path = "/etc/php-fpm.d/sessions.conf"
    config = f"[www]\n" \
             f"php_value[session.save_handler] = redis\n" \
             f"php_value[session.save_path]    = \"{redis_path}\"\n"

    write_file(config_path, config)


def generate_rsyslog_config(variables: dict):
    if not variables["SYSLOG_ENABLED"]:
        return

    # Recommended setting from https://github.com/grafana/loki/blob/master/docs/clients/promtail/scraping.md#rsyslog-output-configuration
    if variables["SYSLOG_TARGET"]:
        config = f'action(\n' \
                 f'    type="omfwd"\n' \
                 f'    target="{variables["SYSLOG_TARGET"]}"\n' \
                 f'    port="{variables["SYSLOG_PORT"]}"\n' \
                 f'    protocol="{variables["SYSLOG_PROTOCOL"]}"\n' \
                 f'    Template="RSYSLOG_SyslogProtocol23Format"\n' \
                 f'    TCP_Framing="octet-counted"\n' \
                 f'    action.resumeRetryCount="100"\n' \
                 f'    queue.type="linkedList"\n' \
                 f'    queue.size="10000"\n' \
                 f')\n'

        write_file("/etc/rsyslog.d/forward.conf", config)

    if variables["SYSLOG_FILE"]:
        file_format = variables["SYSLOG_FILE_FORMAT"]
        if file_format == "text-traditional":
            file_format = "RSYSLOG_TraditionalFileFormat"
        elif file_format == "text":
            file_format = "RSYSLOG_FileFormat"

        config = f'# Output all logs to file\n' \
                 f'action(\n' \
                 f'    type="omfile"\n' \
                 f'    dirCreateMode="0700"\n' \
                 f'    FileCreateMode="0644"\n' \
                 f'    File="{variables["SYSLOG_FILE"]}"\n' \
                 f'    template="{file_format}"\n' \
                 f')\n'

        write_file("/etc/rsyslog.d/file.conf", config)


def generate_vector_config(variables: dict):
    if not variables["ECS_LOG_ENABLED"]:
        return

    sinks = {}

    if variables["ECS_LOG_CONSOLE"]:
        if variables["ECS_LOG_FILE_FORMAT"] == "ecs":
            sinks = {
                "console": {
                    "inputs": ["ecs_without_original_message"],
                    "type": "console",
                    "encoding": {
                        "codec": "json",
                    },
                    "framing": {
                        "method": "newline_delimited",
                    }
                }
            }
        else:
            sinks = {
                "console": {
                    "inputs": ["ecs_to_text"],
                    "type": "console",
                }
            }

    if variables["ECS_LOG_FILE"]:
        if variables["ECS_LOG_FILE_FORMAT"] == "ecs":
            sinks = {
                "file": {
                    "inputs": ["ecs_without_original_message"],
                    "type": "file",
                    "path": variables["ECS_LOG_FILE"],
                    "encoding": {
                        "codec": "json",
                    },
                    "framing": {
                        "method": "newline_delimited",
                    }
                }
            }

        else:
            sinks = {
                "file": {
                    "inputs": ["ecs_to_text"],
                    "type": "file",
                    "path": variables["ECS_LOG_FILE"],
                }
            }

    if variables["ECS_LOG_VECTOR_ADDRESS"]:
        sinks = {
            "vector": {
                "type": "vector",
                "inputs": ["ecs_without_original_message"],
                "address": variables["ECS_LOG_VECTOR_ADDRESS"],
            }
        }

    output = {
        "sinks": sinks,
    }
    write_file("/etc/vector/sinks.json", json.dumps(output, indent=2))


def generate_error_messages(email: str):
    for path in glob.glob('/var/www/html/*.*html'):
        render_jinja_template(path, {"SUPPORT_EMAIL": email})


def generate_php_config(variables: dict):
    opcache_validate_timestamps = 1 if variables["MISP_DEBUG"] else 0
    template = f"; Do not edit this file directly! It is automatically generated after every container start.\n" \
               f"date.timezone = '{variables['PHP_TIMEZONE']}'\n" \
               f"memory_limit = {variables['PHP_MEMORY_LIMIT']}\n" \
               f"max_execution_time = {variables['PHP_MAX_EXECUTION_TIME']}\n" \
               f"upload_max_filesize = {variables['PHP_UPLOAD_MAX_FILESIZE']}\n" \
               f"post_max_size = {variables['PHP_UPLOAD_MAX_FILESIZE']}\n" \
               f"session.cookie_samesite = '{variables['PHP_SESSIONS_COOKIE_SAMESITE']}'\n" \
               f"opcache.validate_timestamps = {opcache_validate_timestamps}"

    write_file("/etc/php.d/99-misp.ini", template)


def generate_crypto_policies(crypto_policy: Optional[str]):
    if crypto_policy:
        write_file("/etc/crypto-policies/config", crypto_policy)


def validate():
    for template_name in ("database.php", "config.php", "email.php"):
        path = f"/var/www/MISP/app/Config/{template_name}"
        validate_jinja_template(path)
    for path in glob.glob('/var/www/html/*.*html'):
        validate_jinja_template(path)
    validate_jinja_template("/etc/httpd/conf.d/misp.conf")
    validate_jinja_template("/etc/supervisord.d/misp.ini")


def create():
    variables = collect()
    variables["SERVER_NAME"] = urlparse(variables["MISP_BASEURL"]).netloc

    if len(variables["SECURITY_SALT"]) < 32:
        warning("'SECURITY_SALT' environment variable should be at least 32 chars long")

    if variables["SECURITY_ENCRYPTION_KEY"] is None:
        warning("Sensitive data will be stored in database unencrypted. Please set 'SECURITY_ENCRYPTION_KEY' to random string with at least 32 chars")
    elif len(variables["SECURITY_ENCRYPTION_KEY"]) < 32:
        warning("'SECURITY_ENCRYPTION_KEY' environment variable should be at least 32 chars long")

    if variables["SYSLOG_ENABLED"]:
        warning("Syslog is deprecated and will be removed in near future. Please switch to ECS log instead.")

    # if security cookie name is not set, generate it by using SECURITY_SALT and MISP_UUID, so it will survive container restart
    if not variables["SECURITY_COOKIE_NAME"]:
        uniq = hashlib.sha256(f"{variables['SECURITY_SALT']}|{variables['MISP_UUID']}".encode()).hexdigest()
        variables["SECURITY_COOKIE_NAME"] = f"MISP-session-{uniq[0:5]}"

    if variables["PHP_SESSIONS_COOKIE_SAMESITE"] is None:
        is_localhost = variables["MISP_BASEURL"].startswith(("http://localhost", "https://localhost"))
        variables["PHP_SESSIONS_COOKIE_SAMESITE"] = "Lax" if is_localhost else "Strict"

    variables["MISP_UUID"] = variables["MISP_UUID"].lower()

    for var in ("OIDC_PROVIDER_INNER", "OIDC_CLIENT_ID_INNER", "OIDC_CLIENT_SECRET_INNER", "OIDC_AUTHENTICATION_METHOD_INNER", "OIDC_CODE_CHALLENGE_METHOD_INNER", "OIDC_ROLES_PROPERTY_INNER"):
        if not variables[var]:
            variables[var] = variables[var.replace("_INNER", "")]

    if variables["OIDC_LOGIN"]:
        for var in ("OIDC_PROVIDER", "OIDC_CLIENT_CRYPTO_PASS", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET"):
            if not variables[var]:
                error(f"OIDC login is enabled, but required environment variable '{var}' is not set")

        for var in ("OIDC_CODE_CHALLENGE_METHOD", "OIDC_CODE_CHALLENGE_METHOD_INNER"):
            if variables[var] not in ("S256", "plain", "", None):
                error(f"Environment variable '{var}' value is not valid")

        # mod_auth_openidc require full URL to metadata
        if "/.well-known/openid-configuration" not in variables["OIDC_PROVIDER"]:
            variables["OIDC_PROVIDER"] = f"{variables['OIDC_PROVIDER'].rstrip('/')}/.well-known/openid-configuration"

    # Start modifying files
    open(CONFIG_CREATED_CANARY_FILE, 'a').close()  # touch

    for template_name in ("database.php", "config.php", "email.php"):
        path = f"/var/www/MISP/app/Config/{template_name}"
        render_jinja_template(path, variables)

    generate_xdebug_config(variables["PHP_XDEBUG_ENABLED"], variables["PHP_XDEBUG_PROFILER_TRIGGER"])
    generate_snuffleupagus_config(variables['PHP_SNUFFLEUPAGUS'])
    generate_sessions_in_redis_config(variables["PHP_SESSIONS_IN_REDIS"], variables["REDIS_HOST"], variables["REDIS_USE_TLS"], variables["REDIS_PASSWORD"])
    generate_apache_config(variables)
    generate_rsyslog_config(variables)
    generate_vector_config(variables)
    generate_error_messages(variables["SUPPORT_EMAIL"])
    generate_php_config(variables)
    generate_crypto_policies(variables["SECURITY_CRYPTO_POLICY"])
    generate_jobber_config(variables)
    generate_supervisor_config(variables)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="misp_create_configs",
        description="Create configs from env variables",
    )
    parser.add_argument("action", nargs="?", choices=("create", "validate"))
    parsed = parser.parse_args()

    configs_created = os.path.exists(CONFIG_CREATED_CANARY_FILE)

    if parsed.action == "validate":
        if configs_created:
            error(f"Configs was already created (canary file {CONFIG_CREATED_CANARY_FILE} exists), it is not possible to validate them")

        validate()
    else:
        if configs_created:
            print(f"Warning: Configs was already created (canary file {CONFIG_CREATED_CANARY_FILE} exists)", file=sys.stderr)
            sys.exit(0)

        create()
