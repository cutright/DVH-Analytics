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

from setuptools import setup, find_packages
from dvha.options import DefaultOptions

requires = [
    'wxpython',
    'pypubsub',
    'numpy',
    'scipy',
    'pydicom >= 1.0',
    'dicompyler-core',
    'bokeh >= 1.2',
    'python-dateutil',
    'psycopg2-binary',
    'shapely[vectorized]',
    'statsmodels',
    'scikit-learn',
    'regressors'
]

setup(
    name='dvha',
    include_package_data=True,
    python_requires='>3.5',
    packages=find_packages(),
    version=DefaultOptions().VERSION,
    description='Create a database of DVHs, GUI with wxPython, plots with Bokeh',
    author='Dan Cutright',
    author_email='dan.cutright@gmail.com',
    url='https://github.com/cutright/DVH-Analytics-Desktop',
    download_url='https://github.com/cutright/DVH-Analytics-Desktop/archive/master.zip',
    license="MIT License",
    keywords=['dvh', 'radiation therapy', 'research', 'dicom', 'dicom-rt', 'bokeh', 'analytics', 'wxpython'],
    classifiers=[],
    install_requires=requires,
    entry_points={'console_scripts': ['dvha = dvha.main:start']},
    long_description="""DVH Database for Clinicians and Researchers
    
    DVH Analytics is a software application to help radiation oncology departments build an in-house database of 
    treatment planning data for the purpose of historical comparisons and statistical analysis. This code is still in 
    development. Please contact the developer if you are interested in testing or collaborating.

    The application builds a SQL database of DVHs and various planning parameters from DICOM files (i.e., Plan, Structure, 
    Dose). Since the data is extracted directly from DICOM files, we intend to accommodate an array of treatment planning 
    system vendors.
    """
)