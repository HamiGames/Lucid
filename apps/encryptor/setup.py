#!/usr/bin/env python3
"""
Setup script for native libsodium encryptor extension
"""

from setuptools import setup, Extension
import os

# Check for libsodium
libsodium_paths = [
    '/usr/local/lib',
    '/usr/lib',
    '/opt/homebrew/lib',  # macOS Homebrew
    '/usr/lib/x86_64-linux-gnu',
    '/usr/lib/aarch64-linux-gnu'
]

libsodium_include_paths = [
    '/usr/local/include',
    '/usr/include',
    '/opt/homebrew/include',  # macOS Homebrew
    '/usr/include/x86_64-linux-gnu',
    '/usr/include/aarch64-linux-gnu'
]

# Find libsodium
libsodium_lib = None
libsodium_include = None

for path in libsodium_paths:
    if os.path.exists(os.path.join(path, 'libsodium.so')) or \
       os.path.exists(os.path.join(path, 'libsodium.dylib')) or \
       os.path.exists(os.path.join(path, 'libsodium.a')):
        libsodium_lib = path
        break

for path in libsodium_include_paths:
    if os.path.exists(os.path.join(path, 'sodium.h')):
        libsodium_include = path
        break

if not libsodium_lib or not libsodium_include:
    print("Warning: libsodium not found. Install libsodium-dev or libsodium-devel")
    print("Ubuntu/Debian: sudo apt-get install libsodium-dev")
    print("CentOS/RHEL: sudo yum install libsodium-devel")
    print("macOS: brew install libsodium")

# Define the extension module
encryptor_native = Extension(
    'encryptor_native',
    sources=[
        'src/encryptor.c',
        'src/crypto.c',
        'src/utils.c'
    ],
    include_dirs=[
        'src/',
        libsodium_include
    ] if libsodium_include else ['src/'],
    libraries=['sodium'],
    library_dirs=[libsodium_lib] if libsodium_lib else [],
    extra_compile_args=[
        '-O3',
        '-Wall',
        '-Wextra',
        '-std=c99',
        '-fPIC'
    ],
    extra_link_args=['-shared']
)

setup(
    name='encryptor-native',
    version='0.1.0',
    description='Native libsodium encryptor extension for Lucid RDP',
    ext_modules=[encryptor_native] if libsodium_lib and libsodium_include else [],
    python_requires='>=3.8',
    install_requires=[
        'PyNaCl>=1.5.0'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: C',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
