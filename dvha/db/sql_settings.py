#!/usr/bin/env python
# -*- coding: utf-8 -*-

# db.sql_settings.py
"""
Functions related to reading, loading, and validating SQL connection credentials
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import os
from dvha.paths import SQL_CNF_PATH, parse_settings_file
from dvha.db.sql_connector import DVH_SQL


def is_sql_connection_defined():
    """
    Checks if sql_connection.cnf exists
    :rtype: bool
    """
    return os.path.isfile(SQL_CNF_PATH)


def write_sql_connection_settings(config):
    """
    :param config: a dict with keys 'host', 'dbname', 'port' and optionally 'user' and 'password'
    """

    text = ["%s %s" % (key, value) for key, value in config.items() if value]
    text = '\n'.join(text)

    with open(SQL_CNF_PATH, "w") as text_file:
        text_file.write(text)


def load_sql_settings():
    """
    Load SQL database login credentials
    :return: login credentials
    :rtype: dict
    """
    if is_sql_connection_defined():
        config = parse_settings_file(SQL_CNF_PATH)
        validate_config(config)

    else:
        config = {'host': 'localhost',
                  'port': '5432',
                  'dbname': 'dvh',
                  'user': '',
                  'password': ''}

    return config


def validate_config(config):
    """
    Validate a login configuration, sets empty values for user and password if needed
    :param config: database login credentials
    :type config; dict
    """
    for key in ['password', 'user']:
        if key not in config.keys():
            config[key] = ''


def validate_sql_connection(config=None, verbose=False):
    """
    :param config: login credentials defining 'host', 'dbname', 'port' and optionally 'user' and 'password'
    :type config: dict
    :param verbose: indicates if cmd line printing should be performed
    :type verbose: bool
    :return: True if configuration is valid
    :rtype: bool
    """

    valid = True
    if config:
        try:
            with DVH_SQL(config) as cnx:
                pass
        except:
            valid = False
    else:
        try:
            with DVH_SQL() as cnx:
                pass
        except:
            valid = False

    if verbose:
        if valid:
            print("SQL DB is alive!")
        else:
            print("Connection to SQL DB could not be established.")

    return valid
