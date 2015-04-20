#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages


with open('README.rst') as readme:
    long_description = readme.read()


with open('requirements.txt') as requirements:
    lines = requirements.readlines()
    libraries = [lib for lib in lines if not lib.startswith('-')]
    dependency_links = [link.split()[1] for link in lines if
        link.startswith('-f')]


setup(
    name='django-excalibur',
    version='0.0.1',
    packages=find_packages(),
    install_requires=libraries,
    dependency_links=dependency_links,
    long_description=long_description,
    author='Morgan Bohn',
    author_email='morgan.bohn@unistra.fr',
    maintainer='Morgan Bohn',
    maintainer_email='morgan.bohn@unistra.fr',
    description='Django Rest Framework implementation for Excalibur : A tool to manage plugins',
    keywords=['django', 'excalibur', 'plugins'],
    url='https://github.com/unistra/django-excalibur',
    download_url='https://github.com/unistra/django-excalibur',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ]
)
