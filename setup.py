#!/usr/bin/env python
# -*- coding: utf-8 -*-

# setup.py
"""
A setuptools setup file for DVH Analytics
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import os
from setuptools import setup, find_packages
from dvha._version import __version__


if os.environ.get("READTHEDOCS") == "True":
    requirements_path = "docs/requirements.txt"
else:
    requirements_path = "requirements.txt"

with open(requirements_path, "r") as doc:
    requires = [line.strip() for line in doc]

with open("README.rst", "r") as doc:
    long_description = doc.read()


setup(
    name="dvha",
    include_package_data=True,
    python_requires=">3.5",
    packages=find_packages(),
    version=__version__,
    description="Create a database of DVHs, GUI with wxPython, "
                "plots with Bokeh",
    author="Dan Cutright",
    author_email="dan.cutright@gmail.com",
    url="https://github.com/cutright/DVH-Analytics",
    download_url="https://github.com/cutright/DVH-Analytics-Desktop/archive/master.zip",
    license="BSD License",
    keywords=[
        "dvh",
        "radiation therapy",
        "research",
        "dicom",
        "dicom-rt",
        "bokeh",
        "analytics",
        "wxpython",
    ],
    classifiers=[],
    install_requires=requires,
    entry_points={"console_scripts": ["dvha = dvha.main:start"]},
    long_description=long_description,
)
