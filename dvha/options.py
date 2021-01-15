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
from dvha.paths import (
    OPTIONS_PATH,
    OPTIONS_CHECKSUM_PATH,
    INBOX_DIR,
    IMPORTED_DIR,
    REVIEW_DIR,
)
from dvha.tools.errors import push_to_log


class DefaultOptions:
    """Create default options, to be inherited by Options class"""

    def __init__(self):
        self.VERSION = __version__
        self.is_edited = False

        self.DB_TYPE = "sqlite"
        self.SQL_PGSQL_IP_HIST = []
        self.DEFAULT_CNF = {
            "pgsql": {"host": "localhost", "dbname": "dvh", "port": "5432"},
            "sqlite": {"host": "dvha.db"},
        }
        self.SQL_LAST_CNX = deepcopy(self.DEFAULT_CNF)

        self.DB_TYPE_GRPS = {grp: deepcopy(self.DB_TYPE) for grp in [1, 2]}
        self.SQL_LAST_CNX_GRPS = {
            1: deepcopy(self.DEFAULT_CNF),
            2: deepcopy(self.DEFAULT_CNF),
        }
        self.SYNC_SQL_CNX = True
        self._sql_vars = [
            "DB_TYPE",
            "SQL_PGSQL_IP_HIST",
            "DEFAULT_CNF",
            "SQL_LAST_CNX",
            "DB_TYPE_GRPS",
            "SQL_LAST_CNX_GRPS",
        ]

        self.MIN_BORDER = 50

        # These colors propagate to all tabs that visualize your two groups
        self.PLOT_COLOR = "blue"
        self.PLOT_COLOR_2 = "red"

        # The line width and style of selected DVHs in the DVH plot
        self.DVH_LINE_WIDTH_NONSELECTION = 2
        self.DVH_LINE_DASH_NONSELECTION = "solid"
        self.DVH_LINE_ALPHA_NONSELECTION = 0.075
        self.DVH_LINE_COLOR_NONSELECTION = "black"

        self.DVH_LINE_WIDTH_SELECTION = 4
        self.DVH_LINE_DASH_SELECTION = "solid"
        self.DVH_LINE_ALPHA_SELECTION = 1.0

        # Adjusts the opacity of the inner-quartile ranges
        self.IQR_ALPHA = 0.3

        # Adjust the plot font sizes
        self.PLOT_AXIS_LABEL_FONT_SIZE = "12pt"
        self.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE = "10pt"

        # Grid line properties
        self.GRID_LINE_COLOR = "lightgrey"
        self.GRID_LINE_WIDTH = 1
        self.GRID_ALPHA = 1.0

        # Number of data points are reduced by this factor during dynamic
        # plot interaction to speed-up visualizations
        # This is only applied to the DVH plot since it has a large amount
        # of data
        self.LOD_FACTOR = 100

        # All DVHs in SQL DB have 1cGy bin widths regardless of this value.
        # However, the queried DVHs will be
        # down-sampled using this bin_width
        self.dvh_bin_width = 5

        # Passed into dicompyler-core to put a cap on the maximium dose to
        # prevent numpy.histogram from
        # blowing up memory allocation
        self.dvh_bin_max_dose = {"Gy": 500.0, "% Rx": 300.0}
        self.dvh_bin_max_dose_units = "Gy"
        self.dvh_bin_max_dose_options = ["Gy", "% Rx"]

        # Options for the group statistical DVHs in the DVHs tab
        self.STATS_MEDIAN_LINE_WIDTH = 2
        self.STATS_MEDIAN_LINE_DASH = "solid"
        self.STATS_MEDIAN_ALPHA = 0.6
        self.STATS_MEAN_LINE_WIDTH = 3
        self.STATS_MEAN_LINE_DASH = "dashed"
        self.STATS_MEAN_ALPHA = 0.5
        self.STATS_MAX_LINE_WIDTH = 2
        self.STATS_MAX_LINE_DASH = "dotted"
        self.STATS_MAX_ALPHA = 1
        self.STATS_MIN_LINE_WIDTH = 2
        self.STATS_MIN_LINE_DASH = "dotted"
        self.STATS_MIN_ALPHA = 1

        # Options for the time-series plot
        self.CORRELATION_POS_COLOR_1 = "blue"
        self.CORRELATION_NEG_COLOR_1 = "green"
        self.CORRELATION_POS_COLOR_2 = "red"
        self.CORRELATION_NEG_COLOR_2 = "purple"
        self.CORRELATION_MATRIX_VARS = [
            "Beam Area (Mean)",
            "Beam Dose (Mean)",
            "Beam MU (Mean)",
            "Beam Perimeter (Mean)",
            "PTV Cross-Section Median",
            "PTV Distance (Centroids)",
            "PTV Distance (Max)",
            "PTV Distance (Mean)",
            "PTV Distance (Median)",
            "PTV Distance (Min)",
            "PTV Max Dose",
            "PTV Min Dose",
            "PTV Surface Area",
            "PTV Volume",
            "Plan Complexity",
            "ROI Cross-Section Max",
            "ROI Cross-Section Median",
            "ROI Max Dose",
            "ROI Mean Dose",
            "ROI Min Dose",
            "ROI Surface Area",
            "ROI Volume",
            "Rx Dose",
            "Total Plan MU",
        ]

        # Options for the time-series plot
        self.TIME_SERIES_CIRCLE_SIZE = 10
        self.TIME_SERIES_CIRCLE_ALPHA = 0.3
        self.TIME_SERIES_TREND_LINE_WIDTH = 1
        self.TIME_SERIES_TREND_LINE_DASH = "solid"
        self.TIME_SERIES_AVG_LINE_WIDTH = 1
        self.TIME_SERIES_AVG_LINE_DASH = "dotted"
        self.TIME_SERIES_PATCH_ALPHA = 0.1

        # Options for the time-series plot
        self.CONTROL_CHART_CIRCLE_SIZE = 10
        self.CONTROL_CHART_CIRCLE_ALPHA = 0.3
        self.CONTROL_CHART_LINE_WIDTH = 1
        self.CONTROL_CHART_LINE_DASH = "solid"
        self.CONTROL_CHART_LINE_COLOR = "black"
        self.CONTROL_CHART_CENTER_LINE_WIDTH = 2
        self.CONTROL_CHART_CENTER_LINE_DASH = "solid"
        self.CONTROL_CHART_CENTER_LINE_COLOR = "black"
        self.CONTROL_CHART_CENTER_LINE_ALPHA = 1
        self.CONTROL_CHART_UCL_LINE_WIDTH = 2
        self.CONTROL_CHART_UCL_LINE_DASH = "dashed"
        self.CONTROL_CHART_UCL_LINE_COLOR = "red"
        self.CONTROL_CHART_UCL_LINE_ALPHA = 1
        self.CONTROL_CHART_LCL_LINE_WIDTH = 2
        self.CONTROL_CHART_LCL_LINE_DASH = "dashed"
        self.CONTROL_CHART_LCL_LINE_COLOR = "red"
        self.CONTROL_CHART_LCL_LINE_ALPHA = 1
        self.CONTROL_CHART_PATCH_ALPHA = 0.1
        self.CONTROL_CHART_PATCH_COLOR = "grey"
        self.CONTROL_CHART_OUT_OF_CONTROL_COLOR = "green"
        self.CONTROL_CHART_OUT_OF_CONTROL_COLOR_2 = "purple"
        self.CONTROL_CHART_OUT_OF_CONTROL_ALPHA = 1

        # Adjust the opacity of the histograms
        self.HISTOGRAM_ALPHA = 0.3

        # Options for the plot in the Multi-Variable Regression tab
        self.REGRESSION_CIRCLE_SIZE = 10
        self.REGRESSION_ALPHA = 0.5
        self.REGRESSION_LINE_WIDTH = 2
        self.REGRESSION_LINE_DASH = "dashed"

        self.REGRESSION_RESIDUAL_CIRCLE_SIZE = 3
        self.REGRESSION_RESIDUAL_ALPHA = 0.5
        self.REGRESSION_RESIDUAL_LINE_WIDTH = 2
        self.REGRESSION_RESIDUAL_LINE_DASH = "solid"
        self.REGRESSION_RESIDUAL_LINE_COLOR = "black"

        # Random forest
        self.MACHINE_LEARNING_ALPHA = 0.5
        self.MACHINE_LEARNING_ALPHA_DIFF = 0.35
        self.MACHINE_LEARNING_SIZE_PREDICT = 5
        self.MACHINE_LEARNING_SIZE_DATA = 5
        self.MACHINE_LEARNING_SIZE_MULTI_VAR = 5
        self.MACHINE_LEARNING_COLOR_PREDICT = "blue"
        self.MACHINE_LEARNING_COLOR_DATA = "black"
        self.MACHINE_LEARNING_COLOR_MULTI_VAR = "red"

        # This is the number of bins up do 100% used when resampling a DVH
        # to fractional dose
        self.RESAMPLED_DVH_BIN_COUNT = 5000

        self.MLC_ANALYZER_OPTIONS = {
            "max_field_size_x": 400.0,
            "max_field_size_y": 400.0,
            "complexity_weight_x": 1.0,
            "complexity_weight_y": 1.0,
        }

        # Per TG-263 (plus NONE, ITV, and IGNORED)
        self.ROI_TYPES = [
            "NONE",
            "ORGAN",
            "PTV",
            "ITV",
            "CTV",
            "GTV",
            "AVOIDANCE",
            "BOLUS",
            "CAVITY",
            "CONTRAST_AGENT",
            "EXTERNAL",
            "IRRAD_VOLUME",
            "REGISTRATION",
            "TREATED_VOLUME",
            "IGNORED",
        ]

        self.KEEP_IN_INBOX = 0
        self.SEARCH_SUBFOLDERS = 1
        self.IMPORT_UNCATEGORIZED = 0
        self.COPY_MISC_FILES = 0

        self.INBOX_DIR = INBOX_DIR
        self.IMPORTED_DIR = IMPORTED_DIR
        self.REVIEW_DIR = REVIEW_DIR

        self.MAX_DOSE_VOLUME = 0.03

        self.USE_DICOM_DVH = False
        self.AUTO_SUM_DOSE = True

        self.save_fig_param = {
            "figure": {
                "y_range_start": -0.0005,
                "x_range_start": 0.0,
                "y_range_end": 1.0005,
                "x_range_end": 10000.0,
                "background_fill_color": "none",
                "border_fill_color": "none",
                "plot_height": 600,
                "plot_width": 820,
            },
            "legend": {
                "background_fill_color": "white",
                "background_fill_alpha": 1.0,
                "border_line_color": "white",
                "border_line_alpha": 1.0,
                "border_line_width": 1,
            },
        }
        self.apply_range_edits = False

        self.positions = {
            "user_settings": None,
            "export_figure": None,
            "main": None,
        }
        self.window_sizes = {"main": None, "import": None}

        self.AUTO_SQL_DB_BACKUP = False

        self.MIN_RESOLUTION_MAIN = (1200, 700)
        self.MAX_INIT_RESOLUTION_MAIN = (1550, 900)

        self.SHOW_NEW_PTV_CALC_WARNING = True

        self.GET_DVH_KWARGS = {
            "calculate_full_volume": True,
            "use_structure_extents": False,
            "interpolation_resolution": None,
            "interpolation_segments_between_planes": 0,
            "memmap_rtdose": False,
        }
        self.DVH_SMALL_VOLUME_THRESHOLD = (
            10  # compute high resolution DVH if volume less than this (cc)
        )
        self.DVH_HIGH_RESOLUTION_FACTOR = 8  # Must be a factor of 2
        self.DVH_HIGH_RESOLUTION_FACTOR_OPTIONS = ["2", "4", "8", "16", "32"]
        self.DVH_HIGH_RESOLUTION_SEGMENTS_BETWEEN = 3  # Must be int

        self.ENABLE_EDGE_BACKEND = False


class Options(DefaultOptions):
    def __init__(self):
        DefaultOptions.__init__(self)
        self.__set_option_attr()

        self.load()

    def __set_option_attr(self):
        option_attr = []
        for attr in self.__dict__:
            if not attr.startswith("_"):
                option_attr.append(attr)
        self.option_attr = option_attr

    def load(self):
        self.is_edited = False
        if isfile(OPTIONS_PATH) and self.is_options_file_valid:
            try:
                with open(OPTIONS_PATH, "rb") as infile:
                    loaded_options = pickle.load(infile)
                self.upgrade_options(loaded_options)
            except Exception as e:
                msg = (
                    "Options.load: Options file corrupted. Loading "
                    "default options."
                )
                push_to_log(e, msg=msg)
                loaded_options = {}

            for key, value in loaded_options.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def save(self):
        self.is_edited = False
        out_options = {}
        for attr in self.option_attr:
            out_options[attr] = getattr(self, attr)
        out_options["VERSION"] = DefaultOptions().VERSION
        with open(OPTIONS_PATH, "wb") as outfile:
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
            msg = "Options.set_option: %s did not previously exist" % attr
            push_to_log(msg=msg)
        setattr(self, attr, value)
        self.is_edited = True

    def save_checksum(self):
        check_sum = self.calculate_checksum()
        if check_sum:
            with open(OPTIONS_CHECKSUM_PATH, "w") as outfile:
                outfile.write(check_sum)

    @staticmethod
    def calculate_checksum():
        if isfile(OPTIONS_PATH):
            with open(OPTIONS_PATH, "rb") as infile:
                options_str = str(infile.read())
            return hashlib.md5(options_str.encode("utf-8")).hexdigest()
        return None

    @staticmethod
    def load_stored_checksum():
        if isfile(OPTIONS_CHECKSUM_PATH):
            with open(OPTIONS_CHECKSUM_PATH, "r") as infile:
                checksum = infile.read()
            return checksum
        return None

    @property
    def is_options_file_valid(self):
        try:
            current_checksum = self.calculate_checksum()
            stored_checksum = self.load_stored_checksum()
            if current_checksum == stored_checksum:
                return True
        except Exception as e:
            msg = (
                "Options.is_options_file_valid: Corrupted options file "
                "detected. Loading default options."
            )
            push_to_log(e, msg=msg)
            return False

    def restore_defaults(self):
        """Delete the store options file and checksum, load defaults"""
        if isfile(OPTIONS_PATH):
            unlink(OPTIONS_PATH)
        if isfile(OPTIONS_CHECKSUM_PATH):
            unlink(OPTIONS_CHECKSUM_PATH)
        default_options = DefaultOptions()

        for attr in default_options.__dict__:
            if not attr.startswith("_") and attr not in self._sql_vars:
                setattr(self, attr, getattr(default_options, attr))

    def clear_positions(self, *evt):
        """Clear all stored window positions, may be useful if window is
        off screen on Show"""
        self.positions = {key: None for key in list(self.positions)}

    def clear_window_sizes(self, *evt):
        """Clear all stored window sizes, may be useful if window is
        off screen on Show"""
        self.window_sizes = {key: None for key in list(self.window_sizes)}

    def apply_window_position(self, frame, position_key):
        """Given a frame, set to previously stored position or center it"""
        if self.positions[position_key] is not None:
            frame.SetPosition(self.positions[position_key])
        else:
            frame.Center()

    def set_window_size(self, frame, size_key):
        if size_key in self.window_sizes.keys():
            self.window_sizes[size_key] = frame.GetSize()

    def save_window_position(self, frame, position_key):
        """Store the position of the provided frame"""
        self.positions[position_key] = frame.GetPosition()

    def upgrade_options(self, loaded_options):
        """Reserve this space to apply all option file upgrades"""
        # This method is only needed for options that change type or structure
        # New options using a new attribute name will be automatically
        # generated by the DefaultOptions class
        self.db_group_upgrade(loaded_options)
        self.dvh_selection_upgrade(loaded_options)
        self.roi_type_upgrade(loaded_options)
        self.positions_upgrade(loaded_options)

    def positions_upgrade(self, loaded_options):
        if "main" not in loaded_options["positions"]:
            loaded_options["positions"]["main"] = None

    def db_group_upgrade(self, loaded_options):
        """DVHA v0.8.1 has a SQL cnx per group"""
        for key in ["DB_TYPE", "SQL_LAST_CNX"]:
            new_key = key + "_GRPS"
            if new_key not in loaded_options.keys():

                # DVHA <0.6.7 did not have DB_TYPE or SQL_LAST_CNX
                backup_value = (
                    "pgsql" if key == "DB_TYPE" else getattr(self, key)
                )  # sqlite not supported <0.6.7
                new_value = (
                    loaded_options[key]
                    if key in loaded_options.keys()
                    else backup_value
                )

                if sorted(list(new_value)) == [
                    1,
                    2,
                ]:  # users who may have used the dev branch
                    loaded_options[new_key] = {
                        grp: deepcopy(new_value[grp]) for grp in [1, 2]
                    }
                else:
                    loaded_options[new_key] = {
                        grp: deepcopy(new_value) for grp in [1, 2]
                    }

    def dvh_selection_upgrade(self, loaded_options):
        # Making nonselection dvh lines visible as v0.8.3
        # The following keys need updates to look nice, user can always
        # change later
        if "DVH_LINE_WIDTH_SELECTION" not in list(loaded_options):
            keys = [
                "IQR_ALPHA",
                "STATS_MEDIAN_LINE_WIDTH",
                "STATS_MEAN_LINE_WIDTH",
                "STATS_MAX_LINE_WIDTH",
                "STATS_MIN_LINE_WIDTH",
            ]
            for key in keys:
                loaded_options[key] = getattr(self, key)

    @staticmethod
    def roi_type_upgrade(loaded_options):
        """DVHA v0.8.3 added ROI Types into the ROI MAP, and added NONE and
        IGNORED types"""
        if "NONE" not in loaded_options["ROI_TYPES"]:
            loaded_options["ROI_TYPES"].insert(0, "NONE")
        if "IGNORED" not in loaded_options["ROI_TYPES"]:
            loaded_options["ROI_TYPES"].append("IGNORED")
