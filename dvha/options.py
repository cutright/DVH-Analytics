#!/usr/bin/env python
# -*- coding: utf-8 -*-

# options.py
"""
Class used to manage user options
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import pickle
from os.path import isfile
from os import unlink
import hashlib
from copy import deepcopy
from dvha.paths import OPTIONS_PATH, OPTIONS_CHECKSUM_PATH


class DefaultOptions:
    """
    Create default options, to be inherited by Options class
    """
    def __init__(self):
        self.VERSION = '0.7.2post2'

        self.DB_TYPE = 'sqlite'
        self.SQL_PGSQL_IP_HIST = []
        self.DEFAULT_CNF = {'pgsql': {'host': 'localhost',
                                      'dbname': 'dvh',
                                      'port': '5432'},
                            'sqlite': {'host': 'dvha.db'}}
        self.SQL_LAST_CNX = deepcopy(self.DEFAULT_CNF)
        self._sql_vars = ['DB_TYPE', 'SQL_PGSQL_IP_HIST', 'DEFAULT_CNF', 'SQL_LAST_CNX']

        self.MIN_BORDER = 50

        self.MAX_FIELD_SIZE_X = 400  # in mm
        self.MAX_FIELD_SIZE_Y = 400  # in mm

        # These colors propagate to all tabs that visualize your two groups
        self.PLOT_COLOR = 'blue'
        self.PLOT_COLOR_2 = 'red'

        # The line width and style of selected DVHs in the DVH plot
        self.DVH_LINE_WIDTH = 2
        self.DVH_LINE_DASH = 'solid'

        # Adjusts the opacity of the inner-quartile ranges
        self.IQR_ALPHA = 0.1

        # Adjust the plot font sizes
        self.PLOT_AXIS_LABEL_FONT_SIZE = "12pt"
        self.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE = "10pt"

        # Number of data points are reduced by this factor during dynamic plot interaction to speed-up visualizations
        # This is only applied to the DVH plot since it has a large amount of data
        self.LOD_FACTOR = 100

        # All DVHs in SQL DB have 1cGy bin widths regardless of this value.  However, the queried DVHs will be
        # down-sampled using this bin_width
        self.dvh_bin_width = 5

        # Options for the group statistical DVHs in the DVHs tab
        self.STATS_MEDIAN_LINE_WIDTH = 1
        self.STATS_MEDIAN_LINE_DASH = 'solid'
        self.STATS_MEDIAN_ALPHA = 0.6
        self.STATS_MEAN_LINE_WIDTH = 2
        self.STATS_MEAN_LINE_DASH = 'dashed'
        self.STATS_MEAN_ALPHA = 0.5
        self.STATS_MAX_LINE_WIDTH = 1
        self.STATS_MAX_LINE_DASH = 'dotted'
        self.STATS_MAX_ALPHA = 1
        self.STATS_MIN_LINE_WIDTH = 1
        self.STATS_MIN_LINE_DASH = 'dotted'
        self.STATS_MIN_ALPHA = 1

        # Options for the time-series plot
        self.CORRELATION_POS_COLOR_1 = 'blue'
        self.CORRELATION_NEG_COLOR_1 = 'green'
        self.CORRELATION_POS_COLOR_2 = 'red'
        self.CORRELATION_NEG_COLOR_2 = 'purple'
        self.CORRELATION_MATRIX_VARS = ['Beam Area (Mean)', 'Beam Dose (Mean)', 'Beam MU (Mean)',
                                        'Beam Perimeter (Mean)', 'PTV Cross-Section Median', 'PTV Distance (Centroids)',
                                        'PTV Distance (Max)', 'PTV Distance (Mean)', 'PTV Distance (Median)',
                                        'PTV Distance (Min)', 'PTV Max Dose', 'PTV Min Dose', 'PTV Surface Area',
                                        'PTV Volume', 'Plan Complexity', 'ROI Cross-Section Max',
                                        'ROI Cross-Section Median', 'ROI Max Dose', 'ROI Mean Dose', 'ROI Min Dose',
                                        'ROI Surface Area', 'ROI Volume', 'Rx Dose', 'Total Plan MU']

        # Options for the time-series plot
        self.TIME_SERIES_CIRCLE_SIZE = 10
        self.TIME_SERIES_CIRCLE_ALPHA = 0.3
        self.TIME_SERIES_TREND_LINE_WIDTH = 1
        self.TIME_SERIES_TREND_LINE_DASH = 'solid'
        self.TIME_SERIES_AVG_LINE_WIDTH = 1
        self.TIME_SERIES_AVG_LINE_DASH = 'dotted'
        self.TIME_SERIES_PATCH_ALPHA = 0.1

        # Options for the time-series plot
        self.CONTROL_CHART_CIRCLE_SIZE = 10
        self.CONTROL_CHART_CIRCLE_ALPHA = 0.3
        self.CONTROL_CHART_LINE_WIDTH = 1
        self.CONTROL_CHART_LINE_DASH = 'solid'
        self.CONTROL_CHART_LINE_COLOR = 'black'
        self.CONTROL_CHART_CENTER_LINE_WIDTH = 2
        self.CONTROL_CHART_CENTER_LINE_DASH = 'solid'
        self.CONTROL_CHART_CENTER_LINE_COLOR = 'black'
        self.CONTROL_CHART_CENTER_LINE_ALPHA = 1
        self.CONTROL_CHART_UCL_LINE_WIDTH = 2
        self.CONTROL_CHART_UCL_LINE_DASH = 'dashed'
        self.CONTROL_CHART_UCL_LINE_COLOR = 'red'
        self.CONTROL_CHART_UCL_LINE_ALPHA = 1
        self.CONTROL_CHART_LCL_LINE_WIDTH = 2
        self.CONTROL_CHART_LCL_LINE_DASH = 'dashed'
        self.CONTROL_CHART_LCL_LINE_COLOR = 'red'
        self.CONTROL_CHART_LCL_LINE_ALPHA = 1
        self.CONTROL_CHART_PATCH_ALPHA = 0.1
        self.CONTROL_CHART_PATCH_COLOR = 'grey'
        self.CONTROL_CHART_OUT_OF_CONTROL_COLOR = 'green'
        self.CONTROL_CHART_OUT_OF_CONTROL_COLOR_2 = 'purple'
        self.CONTROL_CHART_OUT_OF_CONTROL_ALPHA = 1

        # Adjust the opacity of the histograms
        self.HISTOGRAM_ALPHA = 0.3

        # Options for the plot in the Multi-Variable Regression tab
        self.REGRESSION_CIRCLE_SIZE = 10
        self.REGRESSION_ALPHA = 0.5
        self.REGRESSION_LINE_WIDTH = 2
        self.REGRESSION_LINE_DASH = 'dashed'

        self.REGRESSION_RESIDUAL_CIRCLE_SIZE = 3
        self.REGRESSION_RESIDUAL_ALPHA = 0.5
        self.REGRESSION_RESIDUAL_LINE_WIDTH = 2
        self.REGRESSION_RESIDUAL_LINE_DASH = 'solid'
        self.REGRESSION_RESIDUAL_LINE_COLOR = 'black'

        # Random forest
        self.MACHINE_LEARNING_ALPHA = 0.5
        self.MACHINE_LEARNING_ALPHA_DIFF = 0.35
        self.MACHINE_LEARNING_SIZE_PREDICT = 5
        self.MACHINE_LEARNING_SIZE_DATA = 5
        self.MACHINE_LEARNING_SIZE_MULTI_VAR = 5
        self.MACHINE_LEARNING_COLOR_PREDICT = 'blue'
        self.MACHINE_LEARNING_COLOR_DATA = 'black'
        self.MACHINE_LEARNING_COLOR_MULTI_VAR = 'red'

        # This is the number of bins up do 100% used when resampling a DVH to fractional dose
        self.RESAMPLED_DVH_BIN_COUNT = 5000

        self.COMPLEXITY_SCORE_X_WEIGHT = 1.
        self.COMPLEXITY_SCORE_Y_WEIGHT = 1.

        self.ROI_TYPES = ['ORGAN', 'PTV', 'ITV', 'CTV', 'GTV', 'EXTERNAL',
                          'FIDUCIAL', 'IMPLANT', 'OPTIMIZATION', 'PRV', 'SUPPORT', 'NONE']


class Options(DefaultOptions):
    def __init__(self):
        DefaultOptions.__init__(self)
        self.__set_option_attr()

        self.load()

    def __set_option_attr(self):
        option_attr = []
        for attr in self.__dict__:
            if not attr.startswith('_'):
                option_attr.append(attr)
        self.option_attr = option_attr

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
        out_options['VERSION'] = DefaultOptions().VERSION
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
        except Exception:
            pass
        print('Corrupted options file detected. Loading default options.')
        return False

    def restore_defaults(self):
        if isfile(OPTIONS_PATH):
            unlink(OPTIONS_PATH)
        if isfile(OPTIONS_CHECKSUM_PATH):
            unlink(OPTIONS_CHECKSUM_PATH)
        default_options = DefaultOptions()

        for attr in default_options.__dict__:
            if not attr.startswith('_') and attr not in self._sql_vars:
                setattr(self, attr, getattr(default_options, attr))

