#!/usr/bin/env bash
# Copyright (C) 2024 National Cyber and Information Security Agency of the Czech Republic
set -Eeuo pipefail
set -o xtrace

download_and_check () {
  curl --proto '=https' --tlsv1.3 -sS --location --fail -o package.tar.gz "$1"
  echo "$2 package.tar.gz" | sha256sum -c
  tar zxf package.tar.gz --strip-components=1
  rm -f package.tar.gz
}

ARCH=$(uname -m)
if [ "$ARCH" == 'x86_64' ]; then
  MARCH="-march=$DEFAULT_X86_64_MARCH";
else
  MARCH="";
fi

mkdir /tmp/zlib-ng
cd /tmp/zlib-ng
download_and_check https://github.com/zlib-ng/zlib-ng/archive/refs/tags/2.3.3.tar.gz f9c65aa9c852eb8255b636fd9f07ce1c406f061ec19a2e7d508b318ca0c907d1
CFLAGS="-flto=auto -fstack-protector-strong -D_FORTIFY_SOURCE=2 ${MARCH}" LDFLAGS="-flto=auto -Wl,-z,relro,-z,now" ./configure --zlib-compat
make -j"$(nproc)"
strip libz.so.1.3.1.zlib-ng
mv libz.so.1.3.1.zlib-ng /build/
