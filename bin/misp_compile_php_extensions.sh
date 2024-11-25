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
download_and_check https://github.com/JakubOnderka/simdjson_php/archive/defa31983378d93dab55bc2139725cf881426329.tar.gz 3fa2c7562bad50feab2228631059052fff2fefd3205b7c99c76d4952b0bd3c6b
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
download_and_check https://github.com/kjdev/php-ext-zstd/archive/refs/tags/0.13.3.tar.gz 547f84759c2177f4415ae4a5d5066f09d2979f06aa2b3b4b97b42c0990a1efc5
cd zstd
download_and_check https://github.com/facebook/zstd/releases/download/v1.5.6/zstd-1.5.6.tar.gz 8c29e06cf42aacc1eafc4077ae2ec6c6fcb96a626157e0593d5e82a34fd403c1
cd ..
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent
make --silent -j$NPROC
mv modules/*.so /build/php-modules/

# Compile redis
mkdir /tmp/redis
cd /tmp/redis
download_and_check https://github.com/JakubOnderka/phpredis/archive/c61ef491b0f67455dfd6ce0c74ec70f6d399e9a1.tar.gz 664c9d725843aba11d6c4ede553bfd3f1d549e9dc0a7c4a9f3806c50ab69196b
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
download_and_check https://github.com/kjdev/php-ext-brotli/archive/refs/tags/0.15.2.tar.gz b5e41174652993d516f14243873d217f46dd2d241252f12ccf899cbdbbfa693e
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent --with-libbrotli
make -j$NPROC
mv modules/*.so /build/php-modules/

# Compile snuffleupagus
mkdir /tmp/snuffleupagus
cd /tmp/snuffleupagus
download_and_check https://github.com/jvoisin/snuffleupagus/archive/refs/tags/v0.11.0.tar.gz 7ed7dd3aca0a8f0971e87b56c19c60a1a4d654ee4cbbee9a5091b9d4cca28a34
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
