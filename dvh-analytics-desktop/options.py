#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle
from paths import OPTIONS_PATH, OPTIONS_CHECKSUM_PATH
import default_options
from os.path import isfile
import hashlib


class Options:
    def __init__(self):
        self.__set_default_properties()

        self.load()

        self.initial_options = Obj()
        self.set_initial_options()

    def __set_default_properties(self):
        option_attr = []
        for attr in default_options.__dict__:
            if not attr.startswith('_'):
                setattr(self, attr, getattr(default_options, attr))
                option_attr.append(attr)
        self.option_attr = option_attr

    def set_initial_options(self):
        for attr in self.option_attr:
            setattr(self.initial_options, attr, getattr(self, attr))

    def load(self):

        if isfile(OPTIONS_PATH) and self.validate_options_file():
            try:
                with open(OPTIONS_PATH, 'rb') as infile:
                    loaded_options = pickle.load(infile)
            except EOFError:
                print('ERROR: Options file corrupted. Loading default options.')
                loaded_options = {}

            for key, value in loaded_options.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def save(self):

        out_options = {}
        for attr in self.option_attr:
            out_options[attr] = getattr(self, attr)
        with open(OPTIONS_PATH, 'wb') as outfile:
            pickle.dump(out_options, outfile)
        self.save_checksum()

    def set_option(self, attr, value):
        setattr(self, attr, value)

    def save_checksum(self):
        check_sum = self.calculate_checksum()
        if check_sum:
            with open(OPTIONS_CHECKSUM_PATH, 'w') as outfile:
                outfile.write(check_sum)

    @staticmethod
    def calculate_checksum():
        if isfile(OPTIONS_PATH):
            with open(OPTIONS_PATH, 'rb') as infile:
                options_str = str(infile.read())
            return hashlib.md5(options_str.encode('utf-8')).hexdigest()
        return None

    @staticmethod
    def load_stored_checksum():
        if isfile(OPTIONS_CHECKSUM_PATH):
            with open(OPTIONS_CHECKSUM_PATH, 'r') as infile:
                checksum = infile.read()
            return checksum
        return None

    def validate_options_file(self):
        try:
            current_checksum = self.calculate_checksum()
            stored_checksum = self.load_stored_checksum()
            if current_checksum == stored_checksum:
                return True
        except:
            pass
        print('Corrupted options file detected. Loading default options.')
        return False


class Obj:
    pass
