"""
Setup script for MiniKernel native syscall bridge
Compiles C extension for direct hardware access
"""

from setuptools import setup, Extension

syscall_bridge = Extension(
    'minikernel.core.syscall_bridge',
    sources=['syscall_bridge.c'],
    extra_compile_args=['-O3', '-Wall', '-Wextra'],
    include_dirs=[],
    libraries=[],
)

setup(
    name='minikernel-syscall-bridge',
    version='0.1.0',
    description='MiniKernel system call bridge',
    ext_modules=[syscall_bridge],
    zip_safe=False,
)
