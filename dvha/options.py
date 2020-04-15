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
from dvha._version import __version__
from dvha.paths import OPTIONS_PATH, OPTIONS_CHECKSUM_PATH, INBOX_DIR, IMPORTED_DIR, REVIEW_DIR


class DefaultOptions:
    """Create default options, to be inherited by Options class"""
    def __init__(self):
        self.VERSION = __version__
        self.is_edited = False

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

        # Grid line properties
        self.GRID_LINE_COLOR = 'lightgrey'
        self.GRID_LINE_WIDTH = 1
        self.GRID_ALPHA = 1.

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

        # Per TG-263 (plus ITV)
        self.ROI_TYPES = ['ORGAN', 'PTV', 'ITV', 'CTV', 'GTV',
                          'AVOIDANCE', 'BOLUS', 'CAVITY', 'CONTRAST_AGENT', 'EXTERNAL',
                          'IRRAD_VOLUME', 'REGISTRATION', 'TREATED_VOLUME']

        self.KEEP_IN_INBOX = 0
        self.SEARCH_SUBFOLDERS = 1
        self.IMPORT_UNCATEGORIZED = 0

        self.INBOX_DIR = INBOX_DIR
        self.IMPORTED_DIR = IMPORTED_DIR
        self.REVIEW_DIR = REVIEW_DIR

        self.MAX_DOSE_VOLUME = 0.03

        self.USE_DICOM_DVH = False
        self.AUTO_SUM_DOSE = True

        self.save_fig_param = {'figure': {'y_range_start': -0.0005,
                                          'x_range_start': 0.,
                                          'y_range_end': 1.0005,
                                          'x_range_end': 10000.,
                                          'background_fill_color': 'none',
                                          'border_fill_color': 'none',
                                          'plot_height': 600,
                                          'plot_width': 820},
                               'legend': {'background_fill_color': 'white',
                                          'background_fill_alpha': 1.,
                                          'border_line_color': 'white',
                                          'border_line_alpha': 1.,
                                          'border_line_width': 1}}
        self.apply_range_edits = False

        self.positions = {'user_settings': None,
                          'export_figure': None}

        self.AUTO_SQL_DB_BACKUP = False


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
        self.is_edited = False
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
        self.is_edited = False
        out_options = {}
        for attr in self.option_attr:
            out_options[attr] = getattr(self, attr)
        out_options['VERSION'] = DefaultOptions().VERSION
        with open(OPTIONS_PATH, 'wb') as outfile:
            pickle.dump(out_options, outfile)
        self.save_checksum()

    def set_option(self, attr, value):
        """
        Change or create an option value
        :param attr: name of option
        :type attr: str
        :param value: value of option
        """
        if not hasattr(self, attr):
            print('WARNING: This option did not previously exist!')
        setattr(self, attr, value)
        self.is_edited = True

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
            print('Corrupted options file detected. Loading default options.')
            return False

    def restore_defaults(self):
        """Delete the store options file and checksum, load defaults"""
        if isfile(OPTIONS_PATH):
            unlink(OPTIONS_PATH)
        if isfile(OPTIONS_CHECKSUM_PATH):
            unlink(OPTIONS_CHECKSUM_PATH)
        default_options = DefaultOptions()

        for attr in default_options.__dict__:
            if not attr.startswith('_') and attr not in self._sql_vars:
                setattr(self, attr, getattr(default_options, attr))

    def clear_positions(self, *evt):
        """Clear all stored window positions, may be useful if window is off screen on Show"""
        self.positions = {key: None for key in list(self.positions)}

    def set_window_position(self, frame, position_key):
        """Given a frame, set to previously stored window position or center it"""
        if self.positions[position_key] is not None:
            frame.SetPosition(self.positions[position_key])
        else:
            frame.Center()

    def save_window_position(self, frame, position_key):
        """Store the position of the provided frame"""
        self.positions[position_key] = frame.GetPosition()

