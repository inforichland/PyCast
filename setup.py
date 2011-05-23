#!/usr/bin/env python

"""Setup script for PyCast"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='PyCast',
      version='0.1',
      description='Python Shoutcast Server',
      license='BSD',l
      author='Tim Wawrzynczak',
      author_email='inforichland@gmail.com',
      url='http://github.com/inforichland/PyCast',
      package_dir={'src'},
      packages = [
        'PyCast'
      ],
      zip_safe=True
)

