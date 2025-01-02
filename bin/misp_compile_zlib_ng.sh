#!/usr/bin/env bash
# Copyright (C) 2024 National Cyber and Information Security Agency of the Czech Republic
set -e

# Enable GCC Toolset version 14
source scl_source enable gcc-toolset-14

set -o xtrace

download_and_check () {
  curl --proto '=https' --tlsv1.3 -sS --location --fail -o package.tar.gz "$1"
  echo "$2 package.tar.gz" | sha256sum -c
  tar zxf package.tar.gz --strip-components=1
  rm -f package.tar.gz
}

ARCH=$(uname -i)
if [ "$ARCH" == 'x86_64' ]; then
  MARCH="-march=x86-64-v2";
else
  MARCH="";
fi

mkdir /tmp/zlib-ng
cd /tmp/zlib-ng
download_and_check https://github.com/zlib-ng/zlib-ng/archive/refs/tags/2.2.3.tar.gz f2fb245c35082fe9ea7a22b332730f63cf1d42f04d84fe48294207d033cba4dd
CFLAGS="-flto=auto -fstack-protector-strong -D_FORTIFY_SOURCE=2 -Wl,-z,relro,-z,now ${MARCH}" ./configure --zlib-compat
make -j$(nproc)
strip libz.so.1.3.1.zlib-ng
mv libz.so.1.3.1.zlib-ng /build/
