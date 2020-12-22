#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    setup for gstaws package
"""
import os
import re
import pathlib

from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext as _build_ext

ROOT = os.path.dirname(__file__)
VERSION_RE = re.compile(r'''__version__ = ['"]([0-9.]+)['"]''')

def read(file):
    return pathlib.Path(file).read_text('utf-8').strip()

def get_version():
    init = open(os.path.join(ROOT, 'gstaws', '__init__.py')).read()
    return VERSION_RE.search(init).group(1)

class CMakeExtension(Extension):
    def __init__(self, name):
        super().__init__(name, sources=[])

class build_ext(_build_ext):
    user_options = _build_ext.user_options
    boolean_options = _build_ext.boolean_options
    user_options.append(('cmake-args=', None, 'CMake arguments.'))

    def initialize_options(self):
        _build_ext.initialize_options(self)
        self.cmake_args = str()

    def finalize_options(self):
        _build_ext.finalize_options(self)

    def run(self):
        for ext in self.extensions:
            self.build_cmake(ext)
        super().run()

    def build_cmake(self, ext):
        cwd = pathlib.Path().absolute()

        # Create build dir
        build_temp = pathlib.Path(self.build_temp)
        build_temp.mkdir(parents=True, exist_ok=True)
        extdir = pathlib.Path(self.get_ext_fullpath(ext.name))
        extdir.mkdir(parents=True, exist_ok=True)
        libdir = os.path.abspath(os.path.dirname(extdir))
        print("Libdir: " + libdir)

        # CMake args
        config = 'Debug' if self.debug else 'Release'
        cmake_args = [
            '-DCMAKE_BUILD_TYPE=' + config,
            '-DPYTHON_PACKAGE_DIR=' + libdir
        ]
        if len(self.cmake_args) > 0:
            cmake_args += self.cmake_args.split(' ')
        print("cmake_args: " + str(cmake_args))

        # Build args
        build_args = [
            '--config', config,
            '--', '-j4'
        ]

        os.chdir(str(build_temp))
        self.spawn(['cmake', str(cwd)] + cmake_args)
        if not self.dry_run:
            self.spawn(['cmake', '--build', '.'] + build_args)
        os.chdir(str(cwd))

install_requires = [
    r for r in read('requirements.txt').split('\n') if r]

setup(
    name='gstaws',
    version=get_version(),
    description="AWS Streamer package",
    long_description='\n\n'.join((read('README.md'))),
    author="Bartek Pawlik",
    author_email='pawlikb@amazon.com',
    url='https://github.com/awslabs/aws-streamer',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    install_requires=install_requires,
    license="Apache Software License 2.0",
    ext_modules=[CMakeExtension('gstaws')],
    cmdclass={
        'build_ext': build_ext,
    }
)
