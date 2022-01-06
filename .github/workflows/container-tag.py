#!/usr/bin/env python3
import os

# GITHUB_EVENT_NAME

for k, v in sorted(os.environ.items()):
    print(k + ': ', v)
print('\n')


print("::set-output name=TEST::TEST")
