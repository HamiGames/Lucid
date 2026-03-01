#!/usr/bin/env python3
"""
Setup script for native chunker extension
"""

from setuptools import setup, Extension
import numpy as np

# Define the extension module
chunker_native = Extension(
    'chunker_native',
    sources=[
        'src/chunker.c',
        'src/compression.c',
        'src/utils.c'
    ],
    include_dirs=[
        np.get_include(),
        'src/'
    ],
    libraries=['z'],
    library_dirs=[],
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
    name='chunker-native',
    version='0.1.0',
    description='Native chunker extension for Lucid RDP',
    ext_modules=[chunker_native],
    python_requires='>=3.8',
    install_requires=[
        'numpy>=1.19.0'
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
