#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dvha_app.py
"""
Script to start DVH Analytics
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics


import dvha.main
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    dvha.main.start()
