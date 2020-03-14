#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.protocols.py
"""
Classes to load and interact with DVH Endpoint Constraints
"""
# Copyright (c) 2016-2020 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from os import listdir
from os.path import join, basename, splitext
from dvha.options import Options
from dvha.paths import PROTOCOL_DIR

MAX_DOSE_VOLUME = Options().MAX_DOSE_VOLUME


class Protocols:
    def __init__(self, max_dose_volume=MAX_DOSE_VOLUME):
        self.max_dose_volume = max_dose_volume
        self.__load()

    def __load(self):
        self.data = {}
        for f in self.file_paths:
            file_name = splitext(str(basename(f)))[0]
            name_fxs = file_name.split('_')
            protocol_name = name_fxs[0]
            fxs = name_fxs[1]
            if protocol_name not in list(self.data):
                self.data[protocol_name] = {}
            self.data[protocol_name][fxs] = self.parse_protocol_file(f)

    @property
    def file_paths(self):
        return [join(PROTOCOL_DIR, f) for f in listdir(PROTOCOL_DIR) if self.is_protocol_file(f)]

    @staticmethod
    def is_protocol_file(file_path):
        return splitext(file_path)[1].lower() == '.scp'

    @staticmethod
    def parse_protocol_file(file_path):
        constraints = {}
        current_key = None
        with open(file_path, 'r') as document:
            for line in document:
                if not(line.startswith('#') or line.strip() == ''):  # Skip line if empty or starts with #
                    if line[0] not in {'\t', ' '}:  # Constraint
                        current_key = line.strip()
                        constraints[current_key] = {}
                    else:  # OAR Name
                        line_data = line.split()
                        constraints[current_key][line_data[0]] = line_data[1]
        return constraints

    @property
    def protocol_names(self):
        return sorted(list(self.data))

    def get_fractionations(self, protocol_name):
        return [fx.replace('Fx', '') for fx in sorted(list(self.data[protocol_name]))]

    def get_rois(self, protocol_name, fractionation):
        return sorted(list(self.data[protocol_name][fractionation]))

    def get_constraints(self, protocol_name, fractionation, roi_name):
        return self.data[protocol_name][fractionation][roi_name]

    def get_column_data(self, protocol_name, fractionation):
        roi_template = []
        keys = ['string_rep', 'operator', 'input_value', 'input_units', 'input_type', 'output_units', 'output_type',
                'input_scale', 'output_scale', 'threshold_value', 'calc_type']
        data = {key: [] for key in keys}

        for roi in self.get_rois(protocol_name, fractionation):
            roi_type = ['OAR', 'PTV']['PTV' in roi]
            for constraint_label, threshold in self.get_constraints(protocol_name, fractionation, roi).items():
                roi_template.append(roi)
                constraint = Constraint(constraint_label, threshold, roi_type=roi_type,
                                        max_dose_volume=self.max_dose_volume)
                for key, column in data.items():
                    column.append(getattr(constraint, key))
        data['roi_template'] = roi_template

        return data


class Constraint:
    def __init__(self, constraint_label, threshold, roi_type='OAR', max_dose_volume=MAX_DOSE_VOLUME):
        self.constraint_label = constraint_label
        self.threshold = threshold
        self.roi_type = roi_type
        self.max_dose_volume = max_dose_volume

    def __str__(self):
        return "%s %s %s" % (self.constraint_label, self.operator, self.threshold)

    def __repr__(self):
        return self.__str__()

    @property
    def threshold_value(self):
        if '%' in self.threshold:
            return float(self.threshold.replace('%', '')) / 100.
        return float(self.threshold)

    @property
    def string_rep(self):
        return self.__str__()

    @property
    def operator(self):
        if self.output_type == 'MVS':
            return ['<', '>']['OAR' in self.roi_type]
        return ['>', '<']['OAR' in self.roi_type]

    @property
    def output_type(self):
        if self.constraint_label == 'Mean':
            return 'D'
        return self.constraint_label.split('_')[0]

    @property
    def output_units(self):
        return ['Gy', 'cc'][self.output_type in {'V', 'MVS'}]

    @property
    def input(self):
        if self.constraint_label == 'Mean':
            return None
        return self.constraint_label.split('_')[1]

    @property
    def input_type(self):
        return ['Volume', 'Dose'][self.output_type in {'V', 'MVS'}]

    @property
    def calc_type(self):
        if 'MVS' in self.constraint_label:
            return 'MVS'
        if 'Mean' in self.constraint_label:
            return 'Mean'
        return self.input_type

    @property
    def input_value(self):
        if self.input is None:
            return None
        if 'max' in self.input:
            return self.max_dose_volume
        return float(self.input.replace('%', '').replace('_', ''))

    @property
    def input_scale(self):
        if self.input is None:
            return None
        return ['absolute', 'relative']['%' in self.input]

    @property
    def output_scale(self):
        return ['absolute', 'relative']['%' in self.threshold]

    @property
    def input_units(self):
        if self.input is None:
            return None
        scale = ['absolute', 'relative']['%' in self.input]
        abs_units = ['cc', 'Gy'][self.input_type == 'Dose']
        return ['%', abs_units][scale == 'absolute']
