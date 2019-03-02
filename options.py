#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pickle
import types
from paths import PREF_DIR
import default_options


def save_options(options):
    abs_file_path = os.path.join(PREF_DIR, 'options')

    out_options = {}
    for i in options.__dict__:
        if not i.startswith('_'):
            out_options[i] = getattr(options, i)

    outfile = open(abs_file_path, 'wb')
    pickle.dump(out_options, outfile)
    outfile.close()


def load_options(return_attr=None):
    abs_file_path = os.path.join(PREF_DIR, 'options')

    if os.path.isfile(abs_file_path):

        try:
            infile = open(abs_file_path, 'rb')
            new_dict = pickle.load(infile)

            new_options = Object()
            for key, value in new_dict.items():
                setattr(new_options, key, value)

            infile.close()
            if return_attr:
                if hasattr(new_options, return_attr):
                    return getattr(new_options, return_attr)
                else:
                    print('Specified return attribute (%s) does not exist. Returning None.' % return_attr)
                    return None
            return new_options
        except EOFError:
            print('Corrupt options file, loading defaults.')

    if return_attr:
        if hasattr(default_options, return_attr):
            return getattr(default_options, return_attr)
        else:
            print('Specified return attribute (%s) does not exist. Returning None.' % return_attr)
            return None

    out_options = Object()
    for i in default_options.__dict__:
        if not i.startswith('_'):
            value = getattr(default_options, i)
            if not isinstance(value, types.ModuleType):  # ignore imports in options.py
                setattr(out_options, i, value)
    return out_options


def get_settings(settings_type):
    """
    :param settings_type: either 'sql' or 'import'
    :return:
    """

    return load_options(return_attr='SETTINGS_PATHS')[settings_type]


def parse_settings_file(abs_file_path):
    with open(abs_file_path, 'r') as document:
        settings = {}
        for line in document:
            line = line.split()
            if not line:
                continue
            if len(line) > 1:
                settings[line[0]] = line[1:][0]
                # Convert strings to boolean
                if line[1:][0].lower() == 'true':
                    settings[line[0]] = True
                elif line[1:][0].lower() == 'false':
                    settings[line[0]] = False
            else:
                settings[line[0]] = ''
    return settings


class Object():
    pass
