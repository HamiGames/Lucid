"""
File: /app/03_api_gateway/verify_runtime.py
x-lucid-file-path: /app/03_api_gateway/verify_runtime.py
x-lucid-file-type: python
"""

import os
import sys

dirs = [
    '/app/api/app', '/app/config', '/app/utils', '/app/api', '/app/usr', '/app/etc', '/app/var',
    '/app/tmp', '/app/wheels', '/app/services', '/app/database', '/app/models', '/app/endpoints',
    '/app/common', '/app/server',
    '/app/api/app/middleware', '/app/api/app/utils', '/app/api/app/schemas', '/app/api/app/models',
    '/app/api/app/services', '/app/api/app/db', '/app/api/app/db/models', '/app/api/app/routers',
    '/app/api/app/routes',
]

for d in dirs:
    if not os.path.isdir(d):
        print(f'ERROR: {d} missing')
        sys.exit(1)
    if not os.listdir(d):
        print(f'ERROR: {d} empty')
        sys.exit(1)

print('✅ All directories verified')