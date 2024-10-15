# Base image
ARG BASE_IMAGE=almalinux:9
FROM $BASE_IMAGE AS base

# Some packages requires building, so use different stage for that
FROM base AS builder
COPY su-exec.c /tmp/
RUN dnf install -y --setopt=tsflags=nodocs --setopt=install_weak_deps=False gcc-toolset-13 make && \
    source scl_source enable gcc-toolset-13 && \
    gcc -Wall -Werror -g -o /usr/local/bin/su-exec /tmp/su-exec.c

# Build PHP extensions that are not included in packages
FROM builder AS php-build
COPY bin/misp_compile_php_extensions.sh bin/misp_enable_epel.sh /build/
RUN --mount=type=tmpfs,target=/tmp \
    dnf module enable -y php:8.2 && \
    bash /build/misp_enable_epel.sh && \
    bash /build/misp_compile_php_extensions.sh

# Build jobber, that is not released for arm64 arch
FROM builder AS jobber-build
COPY bin/misp_compile_jobber.sh /build/
RUN --mount=type=tmpfs,target=/tmp bash /build/misp_compile_jobber.sh

# Build zlib-ng, faster alternative of zlib library
FROM builder AS zlib-ng-build
COPY bin/misp_compile_zlib_ng.sh /build/
RUN --mount=type=tmpfs,target=/tmp bash /build/misp_compile_zlib_ng.sh

# MISP image
FROM base AS misp

# Install required system and Python packages
COPY requirements.txt packages /tmp/
COPY bin/misp_enable_epel.sh bin/misp_enable_vector.sh /usr/local/bin/
RUN --mount=type=tmpfs,target=/var/cache/dnf \
    bash /usr/local/bin/misp_enable_epel.sh && \
    bash /usr/local/bin/misp_enable_vector.sh && \
    dnf module -y enable php:8.2 && \
    dnf install --setopt=tsflags=nodocs --setopt=install_weak_deps=False -y $(grep -vE "^\s*#" /tmp/packages | tr "\n" " ") && \
    pip3.12 --no-cache-dir install --disable-pip-version-check -r /tmp/requirements.txt && \
    mkdir /run/php-fpm && \
    rm -rf /tmp/packages

COPY --from=builder --chmod=755 /usr/local/bin/su-exec /usr/local/bin/
COPY --from=php-build /build/php-modules/* /usr/lib64/php/modules/
COPY --from=jobber-build /build/jobber*.rpm /tmp
COPY --from=zlib-ng-build /build/libz.so.1.3.1.zlib-ng /lib64/
COPY --chmod=755 bin/ /usr/local/bin/
COPY --chmod=644 misp.conf /etc/httpd/conf.d/misp.conf
COPY --chmod=644 httpd-errors/* /var/www/html/
COPY --chmod=644 vector.yaml /etc/vector/
COPY --chmod=644 rsyslog.conf /etc/
COPY --chmod=644 snuffleupagus-misp.rules /etc/php.d/
COPY --chmod=644 .jobber /root/
COPY --chmod=644 supervisor.ini /etc/supervisord.d/misp.ini
COPY --chmod=644 logrotate/* /etc/logrotate.d/

ARG CACHEBUST=1
ARG MISP_VERSION=2.5
ENV MISP_VERSION=$MISP_VERSION

RUN ln -f -s /lib64/libz.so.1.3.1.zlib-ng /lib64/libz.so.1 && \
    rpm -i /tmp/jobber*.rpm && \
    /usr/local/bin/misp_install.sh
COPY --chmod=444 Config/* /var/www/MISP/app/Config/
COPY --chmod=444 patches/cake.php /var/www/MISP/app/Console/

# Verify image
FROM misp AS verify
RUN touch /verified && \
    ln -s /usr/bin/python3.12 /usr/bin/python && \
    su-exec apache /usr/local/bin/misp_verify.sh && \
    rm /usr/bin/python && \
    /usr/bin/vector --config-dir /etc/vector/ validate

# Final image
FROM misp
# Hack that will force run verify stage
COPY --from=verify /verified /

ENV GNUPGHOME=/var/www/MISP/.gnupg

VOLUME /var/www/MISP/app/tmp/logs/
VOLUME /var/www/MISP/app/files/certs/
VOLUME /var/www/MISP/app/attachments/
VOLUME /var/www/MISP/app/files/img/orgs/
VOLUME /var/www/MISP/app/files/img/custom/
VOLUME /var/www/MISP/.gnupg/

WORKDIR /var/www/MISP/
# Web server
EXPOSE 80
# ZeroMQ
EXPOSE 50000
HEALTHCHECK CMD su-exec apache misp_status.py
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
