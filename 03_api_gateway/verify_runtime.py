import os
import sys

dirs = ['/app/api/app', '/app/config', '/app/utils', '/app/sessions']

for d in dirs:
    if not os.path.isdir(d):
        print(f'ERROR: {d} missing')
        sys.exit(1)
    if not os.listdir(d):
        print(f'ERROR: {d} empty')
        sys.exit(1)

print('✅ All directories verified')