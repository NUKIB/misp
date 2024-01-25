# Base image
ARG BASE_IMAGE=quay.io/centos/centos:stream8
FROM $BASE_IMAGE as base

# Some packages requires building, so use different stage for that
FROM base as builder
COPY su-exec.c /tmp/
RUN dnf install -y --setopt=tsflags=nodocs --setopt=install_weak_deps=False gcc make && \
    gcc -Wall -Werror -g -o /usr/local/bin/su-exec /tmp/su-exec.c

# Build PHP extensions that are not included in packages
FROM builder as php-build
COPY bin/misp_compile_php_extensions.sh bin/misp_enable_epel.sh /build/
RUN --mount=type=tmpfs,target=/tmp \
    dnf module enable -y php:7.4 && \
    bash /build/misp_enable_epel.sh && \
    bash /build/misp_compile_php_extensions.sh

# Build jobber, that is not released for arm64 arch
FROM builder as jobber-build
COPY bin/misp_compile_jobber.sh /build/
RUN --mount=type=tmpfs,target=/tmp bash /build/misp_compile_jobber.sh

# Build zlib-ng, faster alternative of zlib library
FROM builder as zlib-ng-build
RUN --mount=type=tmpfs,target=/tmp mkdir /tmp/zlib-ng && \
    cd /tmp/zlib-ng && \
    curl --fail -sS --location -o zlib-ng.tar.gz https://github.com/zlib-ng/zlib-ng/archive/refs/tags/2.1.6.tar.gz && \
    echo "a5d504c0d52e2e2721e7e7d86988dec2e290d723ced2307145dedd06aeb6fef2 zlib-ng.tar.gz" | sha256sum -c && \
    tar zxf zlib-ng.tar.gz --strip-components=1 && \
    ./configure --zlib-compat && \
    make -j$(nproc) && \
    strip libz.so.1.3.0.zlib-ng && \
    mkdir /build && \
    cp libz.so.1.3.0.zlib-ng /build/

# MISP image
FROM base as misp

# Install required system and Python packages
COPY packages /tmp/packages
COPY requirements.txt /tmp/
COPY bin/misp_enable_epel.sh bin/misp_enable_vector.sh /usr/local/bin/
RUN --mount=type=tmpfs,target=/var/cache/dnf \
    bash /usr/local/bin/misp_enable_epel.sh && \
    bash /usr/local/bin/misp_enable_vector.sh && \
    dnf module -y enable mod_auth_openidc php:7.4 && \
    dnf install --setopt=tsflags=nodocs --setopt=install_weak_deps=False -y $(grep -vE "^\s*#" /tmp/packages | tr "\n" " ") && \
    alternatives --set python3 /usr/bin/python3.11 && \
    alternatives --set python /usr/bin/python3.11 && \
    pip3 --no-cache-dir install --disable-pip-version-check -r /tmp/requirements.txt && \
    rm -rf /tmp/packages

COPY --from=builder /usr/local/bin/su-exec /usr/local/bin/
COPY --from=php-build /build/php-modules/* /usr/lib64/php/modules/
COPY --from=jobber-build /build/jobber*.rpm /tmp
COPY --from=zlib-ng-build /build/libz.so.1.3.0.zlib-ng /lib64/
COPY bin/ /usr/local/bin/
COPY misp.conf /etc/httpd/conf.d/misp.conf
COPY httpd-errors/* /var/www/html/
COPY vector.yaml /etc/vector/
COPY rsyslog.conf /etc/
COPY snuffleupagus-misp.rules /etc/php.d/
COPY .jobber /root/
COPY supervisor.ini /etc/supervisord.d/misp.ini
COPY logrotate/* /etc/logrotate.d/

ARG CACHEBUST=1
ARG MISP_VERSION=2.4
ENV MISP_VERSION $MISP_VERSION

RUN rm /lib64/libz.so.1 && \
    ln -s /lib64/libz.so.1.3.0.zlib-ng /lib64/libz.so.1 && \
    rpm -i /tmp/jobber*.rpm && \
    chmod u=rwx,g=rx,o=rx /usr/local/bin/* &&  \
    /usr/local/bin/misp_install.sh
COPY Config/* /var/www/MISP/app/Config/
RUN chmod u=r,g=r,o=r /var/www/MISP/app/Config/* && \
    chmod 644 /etc/supervisord.d/misp.ini && \
    chmod 644 /etc/rsyslog.conf && \
    chmod 644 /etc/httpd/conf.d/misp.conf && \
    chmod 644 /etc/php.d/snuffleupagus-misp.rules && \
    chmod 644 /etc/logrotate.d/* && \
    chmod 644 /root/.jobber && \
    mkdir /run/php-fpm

# Verify image
FROM misp as verify
RUN touch /verified && \
    su-exec apache /usr/local/bin/misp_verify.sh && \
    /usr/bin/vector --config-dir /etc/vector/ validate

# Final image
FROM misp
# Hack that will force run verify stage
COPY --from=verify /verified /

ENV GNUPGHOME /var/www/MISP/.gnupg

VOLUME /var/www/MISP/app/tmp/logs/
VOLUME /var/www/MISP/app/files/certs/
VOLUME /var/www/MISP/app/attachments/
VOLUME /var/www/MISP/.gnupg/

WORKDIR /var/www/MISP/
# Web server
EXPOSE 80
# ZeroMQ
EXPOSE 50000
HEALTHCHECK CMD su-exec apache misp_status.py
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
