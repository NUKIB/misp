#!/usr/bin/env bash
# Copyright (C) 2023 National Cyber and Information Security Agency of the Czech Republic
set -e

if [ -f "/etc/yum.repos.d/vector.repo" ]; then
    echo "vector repository is already enabled." >&2
    exit
fi

cat >/etc/yum.repos.d/vector.repo <<'EOL'
[vector]
name = Vector
baseurl = https://yum.vector.dev/stable/vector-0/$basearch/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://keys.datadoghq.com/DATADOG_RPM_KEY_CURRENT.public
       https://keys.datadoghq.com/DATADOG_RPM_KEY_B01082D3.public
       https://keys.datadoghq.com/DATADOG_RPM_KEY_FD4BF915.public
EOL
