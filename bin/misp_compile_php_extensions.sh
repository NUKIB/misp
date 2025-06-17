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
dnf install -y --setopt=tsflags=nodocs --setopt=install_weak_deps=False php-devel brotli-devel diffutils file

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
download_and_check https://github.com/JakubOnderka/simdjson_php/archive/2838544f7589c39bab9d63ff6db01ff5e82838eb.tar.gz 23563ce992cd6da53010092eb5a489f0b32138dfdf16ea9cfa1dd5edcadea152
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
make -j$NPROC
mv modules/*.so /build/php-modules/

# Compile ssdeep
mkdir /tmp/ssdeep
cd /tmp/ssdeep
download_and_check https://github.com/JakubOnderka/pecl-text-ssdeep/archive/aa7ea7045a294548aedc3ccdfbb3936e1716bebd.tar.gz 1b4bc4985bf04fdd6026c5f76f7e4d75be100409235c54eb41aa031a18561299
cd ssdeep
download_and_check https://github.com/ssdeep-project/ssdeep/releases/download/release-2.14.1/ssdeep-2.14.1.tar.gz ff2eabc78106f009b4fb2def2d76fb0ca9e12acf624cbbfad9b3eb390d931313
cd ..
phpize
CFLAGS="$DEFAULT_FLAGS" ./configure --silent --enable-libfuzzy=no --with-libdir=lib64
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
