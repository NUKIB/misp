#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
set -e
set -o xtrace

download_and_check () {
  curl --proto '=https' --tlsv1.3 -sS --location --fail -o package.tar.gz $1
  echo "$2 package.tar.gz" | sha256sum -c
  tar zxf package.tar.gz --strip-components=1
  rm -f package.tar.gz
}

mkdir /tmp/jobber
cd /tmp/jobber

download_and_check https://github.com/dshearer/jobber/archive/refs/tags/v1.4.4.tar.gz fd88a217a413c5218316664fab5510ace941f4fdb68dcb5428385ff09c68dcc2

dnf install -y --setopt=tsflags=nodocs --setopt=install_weak_deps=False rpmdevtools
dnf builddep -y --setopt=tsflags=nodocs --setopt=install_weak_deps=False packaging/rpm/*.spec
# Required for jobber makefile
echo '#!/usr/bin/env bash
dnf builddep $*' > /usr/local/bin/yum-builddep
chmod u+x /usr/local/bin/yum-builddep

make -C packaging/rpm pkg-local "DESTDIR=/build/"

# Cleanup
# 2022-05-06: Temporary disabled since stream8 has broken packages
#dnf history rollback -y last-2
