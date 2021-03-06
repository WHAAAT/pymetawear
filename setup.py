#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
The setup script for the PyMetaWear package.

.. moduleauthor:: hbldh <henrik.blidh@nedomkull.com>

Created on 2016-04-08

'''

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import subprocess
import shutil
import re
from codecs import open

from setuptools import setup, find_packages
from setuptools.command import build_py, develop


class PyMetaWearDeveloper(develop.develop):
    def run(self):
        build_solution()
        develop.develop.run(self)


class PyMetaWearBuilder(build_py.build_py):
    def run(self):
        build_solution()
        build_py.build_py.run(self)


def build_solution():
    # Establish source paths.
    basedir = os.path.abspath(os.path.dirname(__file__))
    pkg_dir = os.path.join(basedir, 'pymetawear')
    path_to_libmetawear_so = os.path.join(
        pkg_dir, 'Metawear-CppAPI', 'dist', 'release', 'lib',
        'x64' if os.uname()[-1] == 'x86_64' else 'x86', 'libmetawear.so')
    path_to_metawear_python_wrappers = os.path.join(
        pkg_dir, 'Metawear-CppAPI', 'wrapper', 'python')

    # Git submodule init
    p = subprocess.Popen(['git', 'submodule', 'init'],
                         cwd=basedir, stdout=sys.stdout, stderr=sys.stderr)
    p.communicate()

    # Git submodule update
    p = subprocess.Popen(['git', 'submodule', 'update'],
                         cwd=basedir, stdout=sys.stdout, stderr=sys.stderr)
    p.communicate()

    # Run make file for MetaWear-CppAPI
    p = subprocess.Popen(
        ['make', 'clean'],
        cwd=os.path.join(pkg_dir, 'Metawear-CppAPI'),
        stdout=sys.stdout, stderr=sys.stderr)
    p.communicate()
    p = subprocess.Popen(
        ['make', 'build'],
        cwd=os.path.join(pkg_dir, 'Metawear-CppAPI'),
        stdout=sys.stdout, stderr=sys.stderr)
    p.communicate()

    # Copy the built shared library to pymetawear folder.
    shutil.copy(path_to_libmetawear_so,
                os.path.join(pkg_dir, 'libmetawear.so'))
    
    # Copy the Mbientlab Python wrappers to pymetawear folder.
    # First create folders if needed.
    try:
        os.makedirs(os.path.join(pkg_dir, 'mbientlab', 'metawear'))
    except:
        pass

    init_files_to_create = [
        os.path.join(pkg_dir, 'mbientlab', '__init__.py'),
        os.path.join(pkg_dir, 'mbientlab', 'metawear', '__init__.py')
    ]
    for init_file in init_files_to_create:
        with open(init_file, 'w') as f:
            f.write("#!/usr/bin/env python\n# -*- coding: utf-8 -*-")

    # Copy all Python files from the MetWear C++ API Python wrapper
    for pth, _, pyfiles in os.walk(
            os.path.join(path_to_metawear_python_wrappers,
                         'mbientlab', 'metawear')):
        for py_file in filter(lambda x: os.path.splitext(x)[1] == '.py', pyfiles):
            try:
                shutil.copy(
                    os.path.join(pth, py_file),
                    os.path.join(pkg_dir, 'mbientlab', 'metawear', py_file))
            except:
                pass

with open('pymetawear/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)


def read(f):
    return open(f, encoding='utf-8').read()


setup(
    name='pymetawear',
    version=version,
    author='Henrik Blidh',
    author_email='henrik.blidh@nedobmkull.com',
    url='https://github.com/hbldh/pymetawear',
    description='Python Lib for connecting to and using MetaWear boards.',
    long_description=read('README.rst') + '\n\n' + read('HISTORY.rst'),
    license='MIT',
    platforms=['Linux'],
    keywords=['Bluetooth', 'IMU', 'MetaWear', 'MbientLab'],
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
    ],
    cmdclass={
        'build_py': PyMetaWearBuilder,
        'develop': PyMetaWearDeveloper
    },
    packages=find_packages(exclude=['tests', 'docs', 'examples']),
    # Adding MbientLab's Python code as package data since it is copied
    # to folder after ``find_packages`` is run.
    package_data={
        'pymetawear': [
            'libmetawear.so',
            'mbientlab/*.py',
            'mbientlab/metawear/*.py'
        ],
    },
    install_requires=[
        'pybluez[ble]>=0.22',
        'pygatt[GATTTOOL]>=2.0.1'
    ],
    ext_modules=[],
    entry_points={
    }
)
