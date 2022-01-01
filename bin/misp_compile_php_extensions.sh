#!/usr/bin/env bash
# Copyright (C) 2022 National Cyber and Information Security Agency of the Czech Republic
# Unfortunately, PHP packages from CentOS repos missing some required extensions, so we have to build them
set -e
set -o xtrace

mkdir /tmp/php-modules/

# Download pickle, tool for compiling PHP extensions
cd /tmp/
curl -LO https://github.com/FriendsOfPHP/pickle/releases/latest/download/pickle.phar

# Compile igbinary
php pickle.phar install -n igbinary
mv /usr/lib64/php/modules/igbinary.so /tmp/php-modules/

# Compile redis
php pickle.phar install -n redis
mv /usr/lib64/php/modules/redis.so /tmp/php-modules/

# Compile ssdeep
mkdir /tmp/ssdeep
cd /tmp/ssdeep
curl -L https://github.com/php/pecl-text-ssdeep/archive/refs/tags/1.1.0.tar.gz | tar zx --strip-components=1
phpize
./configure --with-ssdeep=/usr --with-libdir=lib64
make
mv /tmp/ssdeep/modules/*.so /tmp/php-modules/

# Compile brotli
mkdir /tmp/brotli
cd /tmp/brotli
curl -L https://github.com/kjdev/php-ext-brotli/archive/refs/tags/0.13.1.tar.gz | tar zx --strip-components=1
phpize
./configure --with-libbrotli
make
mv /tmp/brotli/modules/*.so /tmp/php-modules/

# Compile snuffleupagus
mkdir /tmp/snuffleupagus
cd /tmp/snuffleupagus
curl -L https://github.com/jvoisin/snuffleupagus/archive/refs/tags/v0.7.1.tar.gz | tar zx --strip-components=1
cd src
phpize
./configure --enable-snuffleupagus
make
mv /tmp/snuffleupagus/src/modules/*.so /tmp/php-modules/
