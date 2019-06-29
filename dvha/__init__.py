#!/usr/bin/env python
# -*- coding: utf-8 -*-

# main.py
"""
Package initialization for DVHA
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics


__author__ = 'Dan Cutright'
__email__ = 'dan.cutright@gmail.com'
__version__ = '0.6.0'
__version_info__ = (0, 6, 0)


from dvha.main import start

if __name__ == '__main__':
    import dvha.main
    dvha.main.start()
