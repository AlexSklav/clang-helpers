#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from setuptools import setup

import versioneer

setup(name='clang_helpers',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='High-level API using `clang` module to provide static C++ class introspection.',
      keywords='c++ clang introspection',
      author='Christian Fobel',
      url='https://github.com/sci-bots/clang-helpers',
      license='GPL',
      packages=['clang_helpers']
      )
