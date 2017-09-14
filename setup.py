#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2017 IRISA, Jean Coquet, Pierre Vignet
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Contributor(s): Jean Coquet, Pierre Vignet
#
# The original code contained here was initially developed by:
#
#     Pierre Vignet, Jean Coquet.
#     IRISA
#     Dyliss team
#     IRISA Campus de Beaulieu
#     35042 RENNES Cedex, FRANCE

"""Definition of setup function for setuptools module."""

# Standard imports
import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

__PACKAGE_VERSION__ = "0.1.0"

################################################################################

class PyTest(TestCommand):
    """Call tests with the custom 'python setup.py test' command."""

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import pytest
        errno = pytest.main()
        sys.exit(errno)

################################################################################

setup(

    # Library name & version
    name='biopax2cadbiom',
    version=__PACKAGE_VERSION__,

    # Search all packages recursively
    packages=find_packages(),

    # Include MANIFEST.in
    include_package_data=True,

    # Authors
    author="pvignet, jcoquet",
    author_email="pierre.vignet@irisa.fr, jean.coquet@inria.fr",

    # Description
    description="Command line tool to transform a BioPAX RDF data \
        from a triplestore to a CADBIOM model.",
    long_description=open('README.md').read(),

    # Official page
    url = "https://gitlab.inria.fr/jcoquet/biopax2cadbiom",

    # Metadata
    classifiers=[
        "Environment :: Console",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: French",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],

    entry_points={
        'console_scripts': [
            'biopax2cadbiom = biopax2cadbiom.__main__:main'
        ],
    },

    install_requires=['cadbiom>0.1.2', 'SPARQLWrapper', 'sympy', 'lxml', 'dill'],

    # Tests
    tests_require=['pytest', 'cadbiom-cmd'],
    cmdclass={'test': PyTest},
)
