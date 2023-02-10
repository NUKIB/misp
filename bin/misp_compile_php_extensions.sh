#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
# Unfortunately, PHP packages from CentOS repos missing some required extensions, so we have to build them
set -e
set -o xtrace

download_and_check () {
  curl --proto '=https' --tlsv1.3 -sS --location --fail -o package.tar.gz $1
  echo "$2 package.tar.gz" | sha256sum -c
  tar zxf package.tar.gz --strip-components=1
  rm -f package.tar.gz
}

# Install required packages for build
dnf install -y --setopt=tsflags=nodocs --setopt=install_weak_deps=False php-devel php-mbstring php-json php-xml brotli-devel diffutils file ssdeep-devel

mkdir /build/php-modules/

# Compile simdjson
mkdir /tmp/simdjson
cd /tmp/simdjson
download_and_check https://github.com/crazyxman/simdjson_php/releases/download/3.0.0/simdjson-3.0.0.tgz 23cdf65ee50d7f1d5c2aa623a885349c3208d10dbfe289a71f26bfe105ea8db9
phpize
./configure
make -j$(nproc)
mv modules/*.so /build/php-modules/

# Compile igbinary
mkdir /tmp/igbinary
cd /tmp/igbinary
download_and_check https://github.com/igbinary/igbinary/archive/refs/tags/3.2.13.tar.gz 4400ecefafe0901c2ead0e1770b0d4041151e0c51bcb27c4a6c30becb1acb7da
phpize
./configure --silent CFLAGS="-O2 -g" --enable-igbinary
make -j$(nproc)
make install # `make install` is necessary, so redis extension can be compiled with `--enable-redis-igbinary`
mv modules/*.so /build/php-modules/

# Compile zstd library and zstd extension
mkdir /tmp/zstd
cd /tmp/zstd
download_and_check https://github.com/kjdev/php-ext-zstd/archive/refs/tags/0.12.1.tar.gz f07d2bbf788565a7a161643b0de218d7d4de0efb07bf5cf600e20fdcd673763e
cd zstd
download_and_check https://github.com/facebook/zstd/releases/download/v1.5.4/zstd-1.5.4.tar.gz 0f470992aedad543126d06efab344dc5f3e171893810455787d38347343a4424
cd ..
phpize
./configure --silent
make --silent -j$(nproc)
mv modules/*.so /build/php-modules/

# Compile redis
mkdir /tmp/redis
cd /tmp/redis
download_and_check https://github.com/phpredis/phpredis/archive/refs/tags/5.3.7.tar.gz 6f5cda93aac8c1c4bafa45255460292571fb2f029b0ac4a5a4dc66987a9529e6
phpize
./configure --silent --enable-redis-igbinary
make -j$(nproc)
mv modules/*.so /build/php-modules/

# Compile ssdeep
mkdir /tmp/ssdeep
cd /tmp/ssdeep
download_and_check https://github.com/php/pecl-text-ssdeep/archive/refs/tags/1.1.0.tar.gz 256c5c1d6b965f1c6e0f262b6548b1868f4857c5145ca255031a92d602e8b88d
phpize
./configure --silent --with-ssdeep=/usr --with-libdir=lib64
make -j$(nproc)
mv modules/*.so /build/php-modules/

# Compile brotli
mkdir /tmp/brotli
cd /tmp/brotli
download_and_check https://github.com/kjdev/php-ext-brotli/archive/refs/tags/0.13.1.tar.gz 1eca1af3208e2f6551064e3f26e771453def588898bfc25858ab1db985363e47
phpize
./configure --silent --with-libbrotli
make -j$(nproc)
mv modules/*.so /build/php-modules/

# Compile snuffleupagus
mkdir /tmp/snuffleupagus
cd /tmp/snuffleupagus
download_and_check https://github.com/jvoisin/snuffleupagus/archive/refs/tags/v0.9.0.tar.gz 36c99dd9540444ab6c931c687255522dac6705275cdc291b4e25a1d416b7a42e
cd src
phpize
./configure --silent --enable-snuffleupagus
make -j$(nproc)
mv modules/*.so /build/php-modules/

# Remove debug symbols from binaries
strip /build/php-modules/*.so

# Cleanup
# 2022-05-06: Temporary disabled since stream8 has broken packages
# dnf history undo -y 0
