#!/usr/bin/env bash
# Copyright (C) 2024 National Cyber and Information Security Agency of the Czech Republic
set -e

# Enable GCC Toolset version 13
source scl_source enable gcc-toolset-13

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
download_and_check https://github.com/zlib-ng/zlib-ng/archive/refs/tags/2.2.1.tar.gz ec6a76169d4214e2e8b737e0850ba4acb806c69eeace6240ed4481b9f5c57cdf
CFLAGS="-flto=auto ${MARCH}" ./configure --zlib-compat
make -j$(nproc)
strip libz.so.1.3.1.zlib-ng
mv libz.so.1.3.1.zlib-ng /build/
