# Base image
ARG BASE_IMAGE=quay.io/centos/centos:stream8
FROM $BASE_IMAGE as base

# pydeep requires building, so use different stage for that and also build su-exec from source code
FROM base as build
COPY su-exec.c /tmp/
RUN dnf install -y epel-release && \
    dnf install -y --setopt=tsflags=nodocs gcc python39-devel python39-wheel ssdeep-devel unzip make && \
    pip3 wheel pydeep -w /wheels && \
    gcc -Wall -Werror -g -o /tmp/su-exec /tmp/su-exec.c

# MISP image
FROM base as misp

# Install required system and Python packages
COPY packages /tmp/packages
COPY requirements.txt /tmp/
COPY RPM-GPG-KEY-remi.el8 /etc/pki/rpm-gpg/
RUN curl -O https://rpms.remirepo.net/enterprise/remi-release-8.rpm && \
    rpmkeys --import /etc/pki/rpm-gpg/RPM-GPG-KEY-remi.el8 && \
    rpmkeys --checksig remi-release-8.rpm && \
    dnf install -y --setopt=tsflags=nodocs epel-release ./remi-release-8.rpm && \
    rm remi-release-8.rpm && \
    dnf module -y enable mod_auth_openidc php:remi-7.4 python39 && \
    dnf install --setopt=tsflags=nodocs --setopt=install_weak_deps=False -y $(grep -vE "^\s*#" /tmp/packages | tr "\n" " ") && \
    alternatives --set python3 /usr/bin/python3.9 && \
    pip3 --no-cache-dir install --disable-pip-version-check -r /tmp/requirements.txt && \
    rm -rf /var/cache/dnf /tmp/packages

ARG MISP_VERSION=develop
ENV MISP_VERSION $MISP_VERSION
ENV GNUPGHOME /var/www/MISP/.gnupg

COPY --from=build /wheels /wheels
COPY --from=build /tmp/su-exec /usr/local/bin/
COPY bin/ /usr/local/bin/
COPY misp.conf /etc/httpd/conf.d/misp.conf
COPY httpd-errors/* /var/www/html/
COPY rsyslog.conf /etc/
COPY snuffleupagus-default.rules /etc/php.d/
COPY .jobber /root/
COPY supervisor.ini /etc/supervisord.d/misp.ini
RUN chmod u=rwx,g=rx,o=rx /usr/local/bin/* &&  \
    pip3 install --disable-pip-version-check /wheels/* && \
    /usr/local/bin/misp_install.sh
COPY Config/* /var/www/MISP/app/Config/
RUN chmod u=r,g=r,o=r /var/www/MISP/app/Config/* && \
    chmod 644 /etc/supervisord.d/misp.ini && \
    chmod 644 /etc/rsyslog.conf && \
    chmod 644 /etc/httpd/conf.d/misp.conf && \
    chmod 644 /etc/php.d/snuffleupagus-default.rules && \
    chmod 644 /root/.jobber && \
    mkdir /run/php-fpm

# Verify image
FROM misp as verify
RUN touch /verified && \
    pip3 install safety && \
    su-exec apache /usr/local/bin/misp_verify.sh

# Final image
FROM misp
# Hack that will force run verify stage
COPY --from=verify /verified /

VOLUME /var/www/MISP/app/tmp/logs/
VOLUME /var/www/MISP/app/files/certs/
VOLUME /var/www/MISP/app/attachments/
VOLUME /var/www/MISP/.gnupg/

WORKDIR /var/www/MISP/
# Web server
EXPOSE 80
# ZeroMQ
EXPOSE 50000
# This is a hack how to go trought mod_auth_openidc
HEALTHCHECK CMD su-exec apache curl -H "Authorization: dummydummydummydummydummydummydummydummy" --fail http://127.0.0.1/fpm-status || exit 1
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
