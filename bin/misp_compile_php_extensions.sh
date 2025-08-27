#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
# Unfortunately, PHP packages from CentOS repos missing some required extensions, so we have to build them
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

# Install required packages for build
dnf install -y --setopt=tsflags=nodocs --setopt=install_weak_deps=False php-devel brotli-devel diffutils file ssdeep-devel

# Fix PHP for GCC 14
sed -i "s/#if __has_feature(c_atomic)/#if __has_feature(c_atomic) \&\& defined(__clang__)/" /usr/include/php/Zend/zend_atomic.h

# Build modules with march optimised for x86-64-v2
NPROC=$(nproc)
ARCH=$(uname -i)
if [ "$ARCH" == 'x86_64' ]; then
  MARCH="-march=x86-64-v2";
else
  MARCH="";
fi

DEFAULT_FLAGS="-O2 -g -Wl,-z,relro,-z,now -flto=auto -fstack-protector-strong ${MARCH}"

mkdir /build/php-modules/

# Compile simdjson
mkdir /tmp/simdjson
cd /tmp/simdjson
download_and_check https://github.com/JakubOnderka/simdjson_php/archive/292309a311edf94db2b5c538a4e677cb93be1c91.tar.gz 4d3e54a16ea96a2f6d04eeb6f9cdde96c144725dd033c0ed44add7b7e198c66b
phpize
CPPFLAGS="$DEFAULT_FLAGS" ./configure --silent
make -j$NPROC
mv modules/*.so /build/php-modules/

# Compile igbinary
mkdir /tmp/igbinary
cd /tmp/igbinary
download_and_check https://github.com/igbinary/igbinary/archive/refs/tags/3.2.16.tar.gz 941f1cf2ccbecdc1c221dbfae9213439d334be5d490a2f3da2be31e8a00b0cdb
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent --enable-igbinary
make -j$NPROC
make install # `make install` is necessary, so redis extension can be compiled with `--enable-redis-igbinary`
mv modules/*.so /build/php-modules/

# Compile zstd library and zstd extension
mkdir /tmp/zstd
cd /tmp/zstd
download_and_check https://github.com/kjdev/php-ext-zstd/archive/ac2cef86b4d04322ee703d23a684e67f1763cded.tar.gz 68327fcdfe317b97b60327115e020404bd514aff283c799ec0b2465ca5678dd1
cd zstd
download_and_check https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3
cd ..
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent
make --silent -j$NPROC
mv modules/*.so /build/php-modules/

# Compile redis
mkdir /tmp/redis
cd /tmp/redis
download_and_check https://github.com/phpredis/phpredis/archive/refs/tags/6.2.0.tar.gz 470333b27cbf9485d36b610b81300c06491a6575f22c6801a9cefc55285ed123
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent --enable-redis-igbinary
#./configure --silent --enable-redis-igbinary
make -j$NPROC
mv modules/*.so /build/php-modules/

# Compile ssdeep
mkdir /tmp/ssdeep
cd /tmp/ssdeep
download_and_check https://github.com/JakubOnderka/pecl-text-ssdeep/archive/3a2e2d9e5d58fe55003aa8b1f31009c7ad7f54e0.tar.gz 275bb3d6ed93b5897c9b37dac358509c3696239f521453d175ac582c81e23cbb
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent --with-ssdeep=/usr --with-libdir=lib64
make -j$NPROC
mv modules/*.so /build/php-modules/

# Compile brotli
mkdir /tmp/brotli
cd /tmp/brotli
download_and_check https://github.com/kjdev/php-ext-brotli/archive/refs/tags/0.18.0.tar.gz ce695a22af23698f50505bd95c1d75dc75aba4d5b86c2fdfc6a7dcf3701351dc
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent --with-libbrotli
make -j$NPROC
mv modules/*.so /build/php-modules/

# Compile snuffleupagus
mkdir /tmp/snuffleupagus
cd /tmp/snuffleupagus
download_and_check https://github.com/jvoisin/snuffleupagus/archive/refs/tags/v0.12.0.tar.gz 48e8f5c453290a077d29e43d7de7229cb697d8bf98e61ae2e129d45ce3a49ebf
cd src
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent --enable-snuffleupagus
make -j$NPROC
mv modules/*.so /build/php-modules/

# Remove debug symbols from binaries
strip /build/php-modules/*.so

# Cleanup
# 2022-05-06: Temporary disabled since stream8 has broken packages
# dnf history undo -y 0
