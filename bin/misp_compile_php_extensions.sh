#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
# Unfortunately, PHP packages from CentOS repos missing some required extensions, so we have to build them
set -e
set -o xtrace

download_and_check () {
  curl -L -o package.tar.gz $1
  echo "$2 package.tar.gz" | sha256sum -c
  tar zxf package.tar.gz --strip-components=1
  rm package.tar.gz
}

mkdir /tmp/php-modules/

# Compile igbinary
mkdir /tmp/igbinary
cd /tmp/igbinary
download_and_check https://github.com/igbinary/igbinary/archive/refs/tags/3.2.6.tar.gz 87cf65d8a003a3f972c0da08f9aec65b2bf3cb0dc8ac8b8cbd9524d581661250
phpize
./configure CFLAGS="-O2 -g" --enable-igbinary
make
make install # `make install` is necessary, so redis extension can be compiled with `--enable-redis-igbinary`
mv /tmp/igbinary/modules/*.so /tmp/php-modules/

# Compile redis
mkdir /tmp/redis
cd /tmp/redis
download_and_check https://github.com/phpredis/phpredis/archive/refs/tags/5.3.5.tar.gz 88d8c7e93bfd9576fb5a51e28e8f9cc62e3515af5a3bca5486a76e70657213f2
phpize
./configure --enable-redis-igbinary
make
mv /tmp/redis/modules/*.so /tmp/php-modules/

# Compile ssdeep
mkdir /tmp/ssdeep
cd /tmp/ssdeep
download_and_check https://github.com/php/pecl-text-ssdeep/archive/refs/tags/1.1.0.tar.gz 256c5c1d6b965f1c6e0f262b6548b1868f4857c5145ca255031a92d602e8b88d
phpize
./configure --with-ssdeep=/usr --with-libdir=lib64
make
mv /tmp/ssdeep/modules/*.so /tmp/php-modules/

# Compile brotli
mkdir /tmp/brotli
cd /tmp/brotli
download_and_check https://github.com/kjdev/php-ext-brotli/archive/refs/tags/0.13.1.tar.gz 1eca1af3208e2f6551064e3f26e771453def588898bfc25858ab1db985363e47
phpize
./configure --with-libbrotli
make
mv /tmp/brotli/modules/*.so /tmp/php-modules/

# Compile snuffleupagus
mkdir /tmp/snuffleupagus
cd /tmp/snuffleupagus
download_and_check https://github.com/jvoisin/snuffleupagus/archive/refs/tags/v0.7.1.tar.gz 0dfc3b82d77d20f7d6f8fbea9c23d28a081d14376984db42fad6b4a2216d9981
cd src
phpize
./configure --enable-snuffleupagus
make
mv /tmp/snuffleupagus/src/modules/*.so /tmp/php-modules/
