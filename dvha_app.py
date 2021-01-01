#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dvha_app.py
"""
Script to start DVH Analytics
"""
# Copyright (c) 2016-2020 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics


import dvha.main
from dvha.paths import set_phantom_js_path_environment
import multiprocessing

if __name__ == "__main__":

    # Required if running from PyInstaller freeze
    # Multiprocessing library used for dose summation to avoid memory
    # allocation issues
    multiprocessing.freeze_support()

    # SVG export with Bokeh requires PhantomJS
    # Edit PATH environment so Bokeh can find phantomjs binary
    set_phantom_js_path_environment()

    # Begin the main application
    dvha.main.start()
