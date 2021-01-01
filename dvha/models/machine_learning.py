#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.machine_learning.py
"""
Classes to view and calculate Machine Learning predictions
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
import numpy as np
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    RandomForestClassifier,
    GradientBoostingClassifier,
)
from sklearn.model_selection import train_test_split
from sklearn.svm import SVR, SVC
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier, MLPRegressor
from dvha.dialogs.export import save_data_to_file
from dvha.dialogs.main import ShowList
from dvha.options import DefaultOptions
from dvha.paths import MODELS_DIR
from dvha.models.plot import PlotMachineLearning, PlotFeatureImportance
from dvha.tools.utilities import (
    set_msw_background_color,
    get_window_size,
    load_object_from_file,
    set_frame_icon,
    get_selected_listctrl_items,
)


class MachineLearningFrame(wx.Frame):
    def __init__(
        self,
        main_app_frame,
        data,
        title,
        sklearn_predictor=None,
        alg_type="regressor",
        tool_tips=None,
        include_test_data=True,
    ):
        wx.Frame.__init__(self, None)

        self.main_app_frame = main_app_frame
        self.data = data
        self.title = title
        self.sklearn_predictor = [
            sklearn_predictor,
            ALGORITHMS[title][alg_type],
        ][sklearn_predictor is None]
        self.tool_tips = [tool_tips, ALGORITHMS[title]["tool_tips"]][
            tool_tips is None
        ]
        self.include_test_data = include_test_data

        self.model = None
        is_classifier = alg_type == "classifier"
        self.plot = PlotMachineLearning(
            self,
            ml_type=self.title,
            ml_type_short=self.ml_type_short,
            include_test_data=include_test_data,
            is_classifier=is_classifier,
            **self.data
        )

        self.feature_importance_dlg = None

        self.input = {}
        self.defaults = {}
        self.getters = {}

        self.data_split_input = {
            "test_size": wx.TextCtrl(self, wx.ID_ANY, "0.25"),
            "train_size": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "random_state": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "shuffle": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
        }

        self.data_split_defaults = {
            "test_size": 0.25,
            "train_size": None,
            "random_state": None,
            "shuffle": True,
        }

        self.data_split_getters = {
            "test_size": self.to_float_or_none,
            "train_size": self.to_float_or_none,
            "random_state": self.to_int_or_none,
            "shuffle": self.to_bool,
        }

        self.button_calculate = wx.Button(self, wx.ID_ANY, "Calculate")
        self.button_features = wx.Button(self, wx.ID_ANY, "Features")
        self.button_importance = wx.Button(self, wx.ID_ANY, "Importance Plot")
        self.button_export_data = wx.Button(self, wx.ID_ANY, "Export Data")
        self.button_save_figure = wx.Button(self, wx.ID_ANY, "Save Figure")
        self.button_save_model = wx.Button(self, wx.ID_ANY, "Save Model")

        self.do_bind()

    def do_bind(self):
        self.Bind(
            wx.EVT_BUTTON, self.on_calculate, id=self.button_calculate.GetId()
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_features, id=self.button_features.GetId()
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_feature_importance,
            id=self.button_importance.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_export, id=self.button_export_data.GetId()
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_save_figure,
            id=self.button_save_figure.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_save_model,
            id=self.button_save_model.GetId(),
        )
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def set_properties(self):
        self.SetTitle(self.title)
        x_size = [0.6, 0.8][self.include_test_data]
        self.SetMinSize(get_window_size(x_size, 0.7))
        self.set_defaults()

        for key, input_obj in self.input.items():
            input_obj.SetToolTip(self.tool_tips[key])

        for key, input_obj in self.data_split_input.items():
            input_obj.SetToolTip(DATA_SPLIT_TOOL_TIPS[key])

    def do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_side_bar = wx.BoxSizer(wx.VERTICAL)
        sizer_actions = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Actions"), wx.VERTICAL
        )
        sizer_param = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Parameters"), wx.VERTICAL
        )
        sizer_split_param = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Data Split"), wx.VERTICAL
        )

        variables = list(self.input)
        variables.sort()
        sizer_input = {
            variable: wx.BoxSizer(wx.HORIZONTAL) for variable in variables
        }
        for variable in variables:
            sizer_input[variable].Add(
                wx.StaticText(self, wx.ID_ANY, "%s:\t" % variable),
                0,
                wx.EXPAND,
                0,
            )
            sizer_input[variable].Add(self.input[variable], 1, wx.EXPAND, 0)
            sizer_param.Add(sizer_input[variable], 1, wx.EXPAND | wx.ALL, 2)
        sizer_side_bar.Add(sizer_param, 0, wx.ALL | wx.EXPAND, 5)

        split_variables = [
            "test_size",
            "train_size",
            "random_state",
            "shuffle",
        ]
        sizer_split_input = {
            variable: wx.BoxSizer(wx.HORIZONTAL)
            for variable in split_variables
        }
        for variable in split_variables:
            sizer_split_input[variable].Add(
                wx.StaticText(self, wx.ID_ANY, "%s:\t" % variable),
                0,
                wx.EXPAND,
                0,
            )
            sizer_split_input[variable].Add(
                self.data_split_input[variable], 1, wx.EXPAND, 0
            )
            sizer_split_param.Add(
                sizer_split_input[variable], 1, wx.EXPAND | wx.ALL, 2
            )
        sizer_side_bar.Add(sizer_split_param, 0, wx.ALL | wx.EXPAND, 5)

        sizer_actions.Add(
            self.button_calculate,
            1,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            5,
        )
        sizer_actions.Add(
            self.button_features, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5
        )
        sizer_actions.Add(
            self.button_importance,
            1,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            5,
        )
        sizer_actions.Add(
            self.button_export_data, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_actions.Add(
            self.button_save_figure, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_actions.Add(
            self.button_save_model,
            1,
            wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_side_bar.Add(sizer_actions, 0, wx.ALL | wx.EXPAND, 5)

        sizer_wrapper.Add(sizer_side_bar, 0, wx.EXPAND, 0)

        sizer_wrapper.Add(self.plot.layout, 1, wx.EXPAND, 0)

        set_msw_background_color(
            self
        )  # If windows, change the background color
        set_frame_icon(self)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def get_param(self, variable):
        ans = variable in list(self.input)
        input_dict = [self.data_split_input, self.input][ans]
        default_dict = [self.data_split_defaults, self.defaults][ans]
        getters_dict = [self.data_split_getters, self.getters][ans]

        try:
            return getters_dict[variable](input_dict[variable].GetValue())
        except Exception:
            return default_dict[variable]

    def set_defaults(self):
        for variable, input_obj in self.input.items():
            input_obj.SetValue(self.to_str_for_gui(self.defaults[variable]))
        for variable, input_obj in self.data_split_input.items():
            input_obj.SetValue(
                self.to_str_for_gui(self.data_split_defaults[variable])
            )

    @property
    def input_parameters(self):
        return {
            variable: self.get_param(variable)
            for variable in self.input.keys()
            if self.get_param(variable) != self.defaults[variable]
        }

    def set_input_parameters(self, input_parameters):
        for variable, value in input_parameters.items():
            self.input[variable].SetValue(str(value))

    @property
    def data_split_parameters(self):
        return {
            variable: self.get_param(variable)
            for variable in self.data_split_input.keys()
            if self.get_param(variable) != self.data_split_defaults[variable]
        }

    def set_data_split_parameters(self, data_split_input):
        for variable, value in data_split_input.keys():
            self.data_split_input[variable].SetValue(str(value))

    def to_int_float_or_none(self, str_value):
        if str_value.lower() == "none":
            return None
        return self.to_int_or_float(str_value)

    @staticmethod
    def to_int_float_string_or_none(str_value):
        if str_value.lower() == "none":
            return None
        if str_value.isnumeric():  # int
            return int(float(str_value))
        if "." in str_value and len(str_value.split(".") == 2):
            return float(str_value)
        return str_value

    @staticmethod
    def to_int_or_float(str_value):
        if str_value.isnumeric():  # int
            return int(float(str_value))
        return float(str_value)

    def to_int_or_none(self, str_value):
        if str_value.lower() == "none":
            return None
        return self.to_int(str_value)

    def to_float_or_none(self, str_value):
        if str_value.lower() == "none":
            return None
        return self.to_float(str_value)

    @staticmethod
    def to_int(str_value):
        return int(float(str_value))

    @staticmethod
    def to_float(str_value):
        return float(str_value)

    @staticmethod
    def to_str(str_value):
        return str_value

    @staticmethod
    def to_float_or_str(str_value):
        if "." in str_value and len(str_value.split(".") == 2):
            if (
                "%s" % (str_value.split(".")[0] + str_value.split(".")[1])
            ).isnumeric():
                return float(str_value)
        return str_value

    def to_float_str_or_none(self, str_value):
        try:
            return self.to_float_or_none(str_value)
        except Exception:
            return str_value

    @staticmethod
    def to_bool(str_value):
        if str_value.lower() == "true":
            return True
        return False

    @staticmethod
    def to_bool_or_str(str_value):
        if str_value.lower() == "true":
            return True
        if str_value.lower() == "false":
            return False
        return str_value

    @staticmethod
    def to_str_for_gui(value):
        if value is None:
            return "None"
        return str(value)

    @property
    def plot_data(self):
        try:
            self.model = self.sklearn_predictor(**self.input_parameters)
            return MachineLearningPlotData(
                self.data["X"],
                self.data["y"],
                self.model,
                **self.data_split_parameters
            )
        except Exception as e:
            wx.MessageBox(
                str(e), "Error!", wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING
            )

    def do_prediction(self):
        self.model = self.sklearn_predictor(**self.input_parameters)
        return MachineLearningPlotData(
            self.data["X"],
            self.data["y"],
            self.model,
            **self.data_split_parameters
        )

    def on_calculate(self, evt):
        data = self.plot_data
        if data is not None:
            self.plot.update_data(data)

    def redraw_plot(self):
        self.plot.redraw_plot()

    def on_resize(self, *evt):
        try:
            self.Refresh()
            self.Layout()
            wx.CallAfter(self.redraw_plot)
        except RuntimeError:
            pass

    def on_export(self, evt):
        save_data_to_file(
            self, "Save machine learning data to csv", self.plot.get_csv()
        )

    def on_save_figure(self, *evt):
        title = "Save %s Plot to .html" % self.title.title()
        export_frame = self.main_app_frame.export_figure
        attr_dicts = None if export_frame is None else export_frame.attr_dicts
        self.plot.save_figure_dlg(self, title, attr_dicts=attr_dicts)

    def on_save_model(self, evt):
        data = {
            "y_variable": self.plot.y_variable,
            "model": self.model,
            "sklearn_predictor": self.sklearn_predictor,
            "tool_tips": self.tool_tips,
            "x_variables": self.plot.x_variables,
            "title": self.title,
            "input_parameters": self.input_parameters,
            "data_split": self.data_split_parameters,
            "version": DefaultOptions().VERSION,
        }
        save_data_to_file(
            self,
            "Save Model",
            data,
            wildcard="MODEL files (*.ml)|*.ml",
            data_type="pickle",
            initial_dir=MODELS_DIR,
        )

    def run(self):
        self.set_properties()
        self.do_layout()
        self.Show()
        self.on_calculate(None)

    @property
    def frame_size(self):
        return self.GetSize()

    @property
    def ml_type_short(self):
        return "".join([s[0] for s in self.title.split(" ")]).upper()

    def on_features(self, *evt):
        ShowList(self.plot.x_variables, "Features")

    def on_feature_importance(self, evt):
        title = "Importance Figure for %s (%s)" % (
            self.title,
            self.data["y_variable"],
        )
        plot_title = "%s Feature Importances for %s" % (
            self.title,
            self.data["y_variable"],
        )
        self.feature_importance_dlg = FeatureImportanceFrame(
            self.data["options"],
            self.data["x_variables"],
            self.model.feature_importances_,
            title,
            plot_title,
        )
        self.feature_importance_dlg.Show()


class RandomForestFrame(MachineLearningFrame):
    def __init__(
        self,
        main_app_frame,
        data,
        include_test_data=True,
        alg_type="regressor",
    ):
        tool_tips = [RF_TOOL_TIPS_CLASSIFIER, RF_TOOL_TIPS][
            alg_type == "regressor"
        ]
        crit_choices = [["gini", "entropy"], ["mse", "mae"]][
            alg_type == "regressor"
        ]
        MachineLearningFrame.__init__(
            self,
            main_app_frame,
            data,
            "Random Forest",
            include_test_data=include_test_data,
            alg_type=alg_type,
            tool_tips=tool_tips,
        )

        self.input = {
            "n_estimators": wx.TextCtrl(self, wx.ID_ANY, "100"),
            "criterion": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=crit_choices,
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "max_depth": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "min_samples_split": wx.TextCtrl(self, wx.ID_ANY, "2"),
            "min_samples_leaf": wx.TextCtrl(self, wx.ID_ANY, "1"),
            "min_weight_fraction_leaf": wx.TextCtrl(self, wx.ID_ANY, "0"),
            "max_features": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "max_leaf_nodes": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "min_impurity_decrease": wx.TextCtrl(self, wx.ID_ANY, "0"),
            "bootstrap": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "oob_score": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "n_jobs": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "random_state": wx.TextCtrl(self, wx.ID_ANY, "None"),
        }

        self.defaults = {
            "n_estimators": 100,
            "criterion": crit_choices[0],
            "max_depth": None,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "min_weight_fraction_leaf": 0.0,
            "max_features": None,
            "max_leaf_nodes": None,
            "min_impurity_decrease": 0.0,
            "bootstrap": True,
            "oob_score": False,
            "n_jobs": None,
            "random_state": None,
        }

        self.getters = {
            "n_estimators": self.to_int,
            "criterion": self.to_str,
            "max_depth": self.to_int_or_none,
            "min_samples_split": self.to_int_or_float,
            "min_samples_leaf": self.to_int_or_float,
            "min_weight_fraction_leaf": self.to_float,
            "max_features": self.to_int_float_string_or_none,
            "max_leaf_nodes": self.to_int_or_none,
            "min_impurity_decrease": self.to_float,
            "bootstrap": self.to_bool,
            "oob_score": self.to_bool,
            "n_jobs": self.to_int_or_none,
            "random_state": self.to_int_or_none,
        }

        self.run()


class GradientBoostingFrame(MachineLearningFrame):
    def __init__(
        self,
        main_app_frame,
        data,
        include_test_data=True,
        alg_type="regressor",
    ):
        MachineLearningFrame.__init__(
            self,
            main_app_frame,
            data,
            "Gradient Boosting",
            include_test_data=include_test_data,
            alg_type=alg_type,
        )

        self.input = {
            "loss": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["ls", "lad", "huber", "quantile"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "learning_rate": wx.TextCtrl(self, wx.ID_ANY, "0.1"),
            "n_estimators": wx.TextCtrl(self, wx.ID_ANY, "100"),
            "subsample": wx.TextCtrl(self, wx.ID_ANY, "1.0"),
            "criterion": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["friedman_mse", "mse", "mae"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "max_depth": wx.TextCtrl(self, wx.ID_ANY, "3"),
            "min_samples_split": wx.TextCtrl(self, wx.ID_ANY, "2"),
            "min_samples_leaf": wx.TextCtrl(self, wx.ID_ANY, "1"),
            "min_weight_fraction_leaf": wx.TextCtrl(self, wx.ID_ANY, "0"),
            "max_features": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "alpha": wx.TextCtrl(self, wx.ID_ANY, "0.9"),
            "max_leaf_nodes": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "min_impurity_decrease": wx.TextCtrl(self, wx.ID_ANY, "0"),
            "init": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["DummyEstimator", "zero"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "random_state": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "presort": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["auto", "True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "validation_fraction": wx.TextCtrl(self, wx.ID_ANY, "0.1"),
            "n_iter_no_change": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "tol": wx.TextCtrl(self, wx.ID_ANY, "1e-4"),
        }

        self.defaults = {
            "loss": "ls",
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 1.0,
            "criterion": "friedman_mse",
            "max_depth": 3,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "min_weight_fraction_leaf": 0,
            "max_features": None,
            "alpha": 0.9,
            "max_leaf_nodes": None,
            "min_impurity_decrease": 0,
            "init": "DummyEstimator",
            "random_state": None,
            "presort": "auto",
            "validation_fraction": 0.1,
            "n_iter_no_change": None,
            "tol": float("1e-4"),
        }

        self.getters = {
            "loss": self.to_str,
            "learning_rate": self.to_float,
            "n_estimators": self.to_int,
            "subsample": self.to_float,
            "criterion": self.to_str,
            "max_depth": self.to_int,
            "min_samples_split": self.to_int_or_float,
            "min_samples_leaf": self.to_int_or_float,
            "min_weight_fraction_leaf": self.to_float,
            "max_features": self.to_int_float_string_or_none,
            "alpha": self.to_float,
            "max_leaf_nodes": self.to_int_or_none,
            "min_impurity_decrease": self.to_float,
            "init": self.to_str,
            "random_state": self.to_int_or_none,
            "presort": self.to_bool_or_str,
            "validation_fraction": self.to_float,
            "n_iter_no_change": self.to_int_or_none,
            "tol": self.to_float,
        }

        self.run()


class DecisionTreeFrame(MachineLearningFrame):
    def __init__(
        self,
        main_app_frame,
        data,
        include_test_data=True,
        alg_type="regressor",
    ):
        MachineLearningFrame.__init__(
            self,
            main_app_frame,
            data,
            "Decision Tree",
            include_test_data=include_test_data,
            alg_type=alg_type,
        )

        self.input = {
            "criterion": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["mse", "friedman_mse", "mae"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "splitter": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["best", "random"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "max_depth": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "min_samples_split": wx.TextCtrl(self, wx.ID_ANY, "2"),
            "min_samples_leaf": wx.TextCtrl(self, wx.ID_ANY, "1"),
            "min_weight_fraction_leaf": wx.TextCtrl(self, wx.ID_ANY, "0"),
            "max_features": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "max_leaf_nodes": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "min_impurity_decrease": wx.TextCtrl(self, wx.ID_ANY, "0"),
            "random_state": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "presort": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
        }

        self.defaults = {
            "criterion": "mse",
            "splitter": "best",
            "max_depth": None,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "min_weight_fraction_leaf": 0.0,
            "max_features": None,
            "max_leaf_nodes": None,
            "min_impurity_decrease": 0.0,
            "random_state": None,
            "presort": False,
        }

        self.getters = {
            "criterion": self.to_str,
            "splitter": self.to_str,
            "max_depth": self.to_int_or_none,
            "min_samples_split": self.to_int_or_float,
            "min_samples_leaf": self.to_int_or_float,
            "min_weight_fraction_leaf": self.to_float,
            "max_features": self.to_int_float_string_or_none,
            "max_leaf_nodes": self.to_int_or_none,
            "min_impurity_decrease": self.to_float,
            "random_state": self.to_int_or_none,
            "presort": self.to_bool,
        }

        self.run()


class SupportVectorRegressionFrame(MachineLearningFrame):
    def __init__(
        self,
        main_app_frame,
        data,
        include_test_data=True,
        alg_type="regressor",
    ):
        MachineLearningFrame.__init__(
            self,
            main_app_frame,
            data,
            "Support Vector Machine",
            include_test_data=include_test_data,
            alg_type=alg_type,
        )

        self.input = {
            "kernel": wx.ComboBox(
                self,
                wx.ID_ANY,
                "rbf",
                choices=["linear", "poly", "rbf", "sigmoid", "precomputed"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "degree": wx.TextCtrl(self, wx.ID_ANY, "3"),
            "gamma": wx.TextCtrl(self, wx.ID_ANY, "auto"),
            "coef0": wx.TextCtrl(self, wx.ID_ANY, "0.0"),
            "tol": wx.TextCtrl(self, wx.ID_ANY, "1e-3"),
            "C": wx.TextCtrl(self, wx.ID_ANY, "1.0"),
            "epsilon": wx.TextCtrl(self, wx.ID_ANY, "0.1"),
            "shrinking": wx.ComboBox(
                self,
                wx.ID_ANY,
                "True",
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "cache_size": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "max_iter": wx.TextCtrl(self, wx.ID_ANY, "-1"),
        }

        self.defaults = {
            "kernel": "rbf",
            "degree": 3,
            "gamma": "scale",
            "coef0": 0.0,
            "tol": 0.001,
            "C": 1.0,
            "epsilon": 0.1,
            "shrinking": True,
            "cache_size": None,
            "max_iter": -1,
        }

        self.getters = {
            "kernel": self.to_str,
            "degree": self.to_int,
            "gamma": self.to_float_or_str,
            "coef0": self.to_float,
            "tol": self.to_float,
            "C": self.to_float,
            "epsilon": self.to_float,
            "shrinking": self.to_bool,
            "cache_size": self.to_float_or_none,
            "max_iter": self.to_int,
        }

        self.button_importance.Disable()

        self.run()


class MLPFrame(MachineLearningFrame):
    def __init__(
        self,
        main_app_frame,
        data,
        include_test_data=True,
        alg_type="regressor",
    ):
        MachineLearningFrame.__init__(
            self,
            main_app_frame,
            data,
            "Multilayer Perceptron",
            include_test_data=include_test_data,
            alg_type=alg_type,
        )

        self.input = {
            "activation": wx.ComboBox(
                self,
                wx.ID_ANY,
                "relu",
                choices=["identity", "logistic", "tanh", "relu"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "solver": wx.ComboBox(
                self,
                wx.ID_ANY,
                "adam",
                choices=["lbfgs", "sgd", "adam"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "alpha": wx.TextCtrl(self, wx.ID_ANY, "0.001"),
            "batch_size": wx.TextCtrl(self, wx.ID_ANY, "auto"),
            "learning_rate": wx.ComboBox(
                self,
                wx.ID_ANY,
                "constant",
                choices=["constant", "invscaling", "adaptive"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "learning_rate_init": wx.TextCtrl(self, wx.ID_ANY, "0.001"),
            "power_t": wx.TextCtrl(self, wx.ID_ANY, "0.5"),
            "max_iter": wx.TextCtrl(self, wx.ID_ANY, "200"),
            "shuffle": wx.ComboBox(
                self,
                wx.ID_ANY,
                "True",
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "random_state": wx.TextCtrl(self, wx.ID_ANY, "None"),
            "tol": wx.TextCtrl(self, wx.ID_ANY, "1e-4"),
            "warm_start": wx.ComboBox(
                self,
                wx.ID_ANY,
                "False",
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "momentum": wx.TextCtrl(self, wx.ID_ANY, "0.9"),
            "nesterovs_momentum": wx.ComboBox(
                self,
                wx.ID_ANY,
                "True",
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "early_stopping": wx.ComboBox(
                self,
                wx.ID_ANY,
                "False",
                choices=["True", "False"],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "validation_fraction": wx.TextCtrl(self, wx.ID_ANY, "0.1"),
            "beta_1": wx.TextCtrl(self, wx.ID_ANY, "0.9"),
            "beta_2": wx.TextCtrl(self, wx.ID_ANY, "0.999"),
            "epsilon": wx.TextCtrl(self, wx.ID_ANY, "1e-8"),
            "n_iter_no_change": wx.TextCtrl(self, wx.ID_ANY, "10"),
        }

        self.defaults = {
            "activation": "relu",
            "solver": "adam",
            "alpha": 0.0001,
            "batch_size": "auto",
            "learning_rate": "constant",
            "learning_rate_init": 0.001,
            "power_t": 0.5,
            "max_iter": 200,
            "shuffle": True,
            "random_state": None,
            "tol": 1e-4,
            "warm_start": False,
            "momentum": 0.9,
            "nesterovs_momentum": True,
            "early_stopping": False,
            "validation_fraction": 0.1,
            "beta_1": 0.9,
            "beta_2": 0.999,
            "epsilon": 1e-08,
            "n_iter_no_change": 10,
        }

        self.getters = {
            "activation": self.to_str,
            "solver": self.to_str,
            "alpha": self.to_float,
            "batch_size": self.to_float_or_str,
            "learning_rate": self.to_str,
            "learning_rate_init": self.to_float,
            "power_t": self.to_float,
            "max_iter": self.to_int,
            "shuffle": self.to_bool,
            "random_state": self.to_int_or_none,
            "tol": self.to_float,
            "warm_start": self.to_bool,
            "momentum": self.to_float,
            "nesterovs_momentum": self.to_bool,
            "early_stopping": self.to_bool,
            "validation_fraction": self.to_float,
            "beta_1": self.to_float,
            "beta_2": self.to_float,
            "epsilon": self.to_float,
            "n_iter_no_change": self.to_int,
        }

        self.button_importance.Disable()

        self.run()


RF_TOOL_TIPS = {
    "n_estimators": "int\nThe number of trees in the forest.",
    "criterion": "The function to measure the quality of a split. Supported criteria are "
    "“mse” for the mean squared error, which is equal to variance reduction as"
    " feature selection criterion, and “mae” for the mean absolute error.",
    "max_depth": "int, None\nThe maximum depth of the tree. If None, then nodes are expanded until all "
    "leaves are pure or until all leaves contain less than min_samples_split samples.",
    "min_samples_split": "int, float\nThe minimum number of samples required to split an "
    "internal node:\n• If int, then consider min_samples_split as the "
    "minimum number.\n• If float, then min_samples_split is a fraction "
    "and ceil(min_samples_split * n_samples) are the minimum number "
    "of samples for each split.",
    "min_samples_leaf": "int, float\nThe minimum number of samples required to be at a leaf"
    " node. A split point at any depth will only be considered if it "
    "leaves at least min_samples_leaf training samples in each of the "
    "left and right branches. This may have the effect of smoothing "
    "the model, especially in regression.\n• If int, then consider min_"
    "samples_leaf as the minimum number.\n• If float, then min_samples_"
    "leaf is a fraction and ceil(min_samples_leaf * n_samples) are the "
    "minimum number of samples for each node.",
    "min_weight_fraction_leaf": "float\nThe minimum weighted fraction of the sum total of "
    "weights (of all the input samples) required to be at a leaf"
    " node. Samples have equal weight when sample_weight is not"
    " provided.",
    "max_features": "int, float, string, or None\nThe number of features to consider when "
    "looking for the best split:\n• If int, then consider max_features "
    "features at each split.\n• If float, then max_features is a fraction"
    " and int(max_features * n_features) features are considered at each "
    "split.\n• If “auto”, then max_features=n_features.\n• If “sqrt”, "
    "then max_features=sqrt(n_features).\n• If “log2”, then max_"
    "features=log2(n_features).\n• If None, then max_features=n_features.",
    "max_leaf_nodes": "int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
    "Best nodes are defined as relative reduction in impurity. If None "
    "then unlimited number of leaf nodes.",
    "min_impurity_decrease": "float\nA node will be split if this split induces a decrease "
    "of the impurity greater than or equal to this value.\nThe "
    "weighted impurity decrease equation is the following:\n"
    "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
    "                    - N_t_L / N_t * left_impurity)\n"
    "where N is the total number of samples, N_t is the number of "
    "samples at the current node, N_t_L is the number of samples "
    "in the left child, and N_t_R is the number of samples in the "
    "right child.\nN, N_t, N_t_R and N_t_L all refer to the "
    "weighted sum, if sample_weight is passed.",
    "bootstrap": "Whether bootstrap samples are used when building trees. If False, the "
    "whole datset is used to build each tree.",
    "oob_score": "whether to use out-of-bag samples to estimate the R^2 on unseen data.",
    "n_jobs": "int or None\nThe number of jobs to run in parallel for both fit and "
    "predict. None` means 1 unless in a joblib.parallel_backend context. -1 "
    "means using all processors.",
    "random_state": "int or None\nIf int, random_state is the seed used by the random "
    "number generator; If None, the random number generator is the "
    "RandomState instance used by np.random.",
}

RF_TOOL_TIPS_CLASSIFIER = {key: value for key, value in RF_TOOL_TIPS.items()}
RF_TOOL_TIPS_CLASSIFIER["criterion"] = (
    "The function to measure the quality of a split. Supported criteria "
    "are “gini” for the Gini impurity and “entropy” for the information gain. \n"
    "Note: this parameter is tree-specific."
)

GB_TOOL_TIPS = {
    "loss": "loss function to be optimized. ‘ls’ refers to least squares regression. "
    "‘lad’ (least absolute deviation) is a highly robust loss function solely "
    "based on order information of the input variables. ‘huber’ is a combination "
    "of the two. ‘quantile’ allows quantile regression (use alpha to specify the "
    "quantile).",
    "learning_rate": "float\nlearning rate shrinks the contribution of each tree by "
    "learning_rate. There is a trade-off between learning_rate and n_estimators.",
    "n_estimators": "int\nThe number of boosting stages to perform. Gradient boosting is "
    "fairly robust to over-fitting so a large number usually results in "
    "better performance.",
    "subsample": "float\nThe fraction of samples to be used for fitting the individual "
    "base learners. If smaller than 1.0 this results in Stochastic Gradient "
    "Boosting. subsample interacts with the parameter n_estimators. Choosing "
    "subsample < 1.0 leads to a reduction of variance and an increase in bias.",
    "criterion": "The function to measure the quality of a split. Supported criteria are"
    " “friedman_mse” for the mean squared error with improvement score by "
    "Friedman, “mse” for mean squared error, and “mae” for the mean absolute"
    " error. The default value of “friedman_mse” is generally the best as it "
    "can provide a better approximation in some cases.",
    "max_depth": "int\nmaximum depth of the individual regression estimators. The maximum "
    "depth limits the number of nodes in the tree. Tune this parameter for "
    "best performance; the best value depends on the interaction of the input"
    " variables.",
    "min_samples_split": "int, float\nThe minimum number of samples required to split an "
    "internal node:\n• If int, then consider min_samples_split as "
    "the minimum number.\n• If float, then min_samples_split is a "
    "fraction and ceil(min_samples_split * n_samples) are the minimum"
    " number of samples for each split.",
    "min_samples_leaf": "int, float\nThe minimum number of samples required to be at a "
    "leaf node. A split point at any depth will only be considered if "
    "it leaves at least min_samples_leaf training samples in each of "
    "the left and right branches. This may have the effect of "
    "smoothing the model, especially in regression.\n• If int, then "
    "consider min_samples_leaf as the minimum number.\n• If float, "
    "then min_samples_leaf is a fraction and ceil(min_samples_leaf * "
    "n_samples) are the minimum number of samples for each node.",
    "min_weight_fraction_leaf": "float\nThe minimum weighted fraction of the sum total of "
    "weights (of all the input samples) required to be at a "
    "leaf node. Samples have equal weight when sample_weight is"
    " not provided.",
    "max_features": "int, float, string, or None\nThe number of features to consider when"
    " looking for the best split:\n• If int, then consider max_features"
    " features at each split.\n• If float, then max_features is a "
    "fraction and int(max_features * n_features) features are considered "
    "at each split.\n• If “auto”, then max_features=n_features.\n• If "
    "“sqrt”, then max_features=sqrt(n_features).\n• If “log2”, then max"
    "_features=log2(n_features).\n• If None, then max_features=n_features."
    "\nChoosing max_features < n_features leads to a reduction of variance"
    " and an increase in bias.",
    "alpha": "float\nThe alpha-quantile of the huber loss function and the quantile loss "
    "function. Only if loss='huber' or loss='quantile'.",
    "max_leaf_nodes": "int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
    "Best nodes are defined as relative reduction in impurity. If None "
    "then unlimited number of leaf nodes.",
    "min_impurity_decrease": "float\nA node will be split if this split induces a decrease "
    "of the impurity greater than or equal to this value.\nThe "
    "weighted impurity decrease equation is the following:\n"
    "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
    "                    - N_t_L / N_t * left_impurity)\nwhere N is"
    " the total number of samples, N_t is the number of samples at"
    " the current node, N_t_L is the number of samples in the left"
    " child, and N_t_R is the number of samples in the right child."
    "\nN, N_t, N_t_R and N_t_L all refer to the weighted sum, if "
    "sample_weight is passed.",
    "init": "If ‘zero’, the initial raw predictions are set to zero. By default a "
    "DummyEstimator is used, predicting either the average target value "
    "(for loss=’ls’), or a quantile for the other losses.",
    "random_state": "int or None\nIf int, random_state is the seed used by the random number"
    " generator; If None, the random number generator is the RandomState "
    "instance used by np.random.",
    "presort": "Whether to presort the data to speed up the finding of best splits in "
    "fitting. Auto mode by default will use presorting on dense data and default "
    "to normal sorting on sparse data. Setting presort to true on sparse data "
    "will raise an error.",
    "validation_fraction": "float\nThe proportion of training data to set aside as "
    "validation set for early stopping. Must be between 0 and 1. "
    "Only used if n_iter_no_change is set to an integer.",
    "n_iter_no_change": "int or None\nn_iter_no_change is used to decide if early stopping "
    "will be used to terminate training when validation score is not "
    "improving. By default it is set to None to disable early stopping."
    " If set to a number, it will set aside validation_fraction size of"
    " the training data as validation and terminate training when "
    "validation score is not improving in all of the previous "
    "n_iter_no_change numbers of iterations.",
    "tol": "float\nTolerance for the early stopping. When the loss is not improving by at "
    "least tol for n_iter_no_change iterations (if set to a number), the training "
    "stops.",
}

DT_TOOL_TIPS = {
    "criterion": "The function to measure the quality of a split. Supported criteria are "
    "“mse” for the mean squared error, which is equal to variance reduction "
    "as feature selection criterion and minimizes the L2 loss using the mean "
    "of each terminal node, “friedman_mse”, which uses mean squared error "
    "with Friedman’s improvement score for potential splits, and “mae” for "
    "the mean absolute error, which minimizes the L1 loss using the median of"
    " each terminal node.",
    "splitter": "The strategy used to choose the split at each node. Supported strategies "
    "are “best” to choose the best split and “random” to choose the best "
    "random split.",
    "max_depth": "int, None\nThe maximum depth of the tree. If None, then nodes are expanded"
    " until all leaves are pure or until all leaves contain less than "
    "min_samples_split samples.",
    "min_samples_split": "int, float\nThe minimum number of samples required to split an "
    "internal node:\n• If int, then consider min_samples_split as the "
    "minimum number.\n• If float, then min_samples_split is a fraction"
    " and ceil(min_samples_split * n_samples) are the minimum number "
    "of samples for each split.",
    "min_samples_leaf": "int, float\nThe minimum number of samples required to be at a leaf"
    " node. A split point at any depth will only be considered if it "
    "leaves at least min_samples_leaf training samples in each of the "
    "left and right branches. This may have the effect of smoothing the"
    " model, especially in regression.\n• If int, then consider "
    "min_samples_leaf as the minimum number.\n• If float, then "
    "min_samples_leaf is a fraction and ceil(min_samples_leaf * "
    "n_samples) are the minimum number of samples for each node.",
    "min_weight_fraction_leaf": "float\nThe minimum weighted fraction of the sum total of "
    "weights (of all the input samples) required to be at a leaf"
    " node. Samples have equal weight when sample_weight is not"
    " provided.",
    "max_features": "int, float, string, or None\nThe number of features to consider when"
    " looking for the best split:\n• If int, then consider max_features "
    "features at each split.\n• If float, then max_features is a fraction"
    " and int(max_features * n_features) features are considered at each "
    "split.\n• If “auto”, then max_features=n_features.\n• If “sqrt”, "
    "then max_features=sqrt(n_features).\n• If “log2”, "
    "then max_features=log2(n_features).\n• If None, then "
    "max_features=n_features.",
    "max_leaf_nodes": "int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
    "Best nodes are defined as relative reduction in impurity. If None "
    "then unlimited number of leaf nodes.",
    "min_impurity_decrease": "float\nA node will be split if this split induces a decrease "
    "of the impurity greater than or equal to this value.\nThe "
    "weighted impurity decrease equation is the following:\n"
    "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
    "                    - N_t_L / N_t * left_impurity)\nwhere N is"
    " the total number of samples, N_t is the number of samples at"
    " the current node, N_t_L is the number of samples in the left"
    " child, and N_t_R is the number of samples in the right child."
    "\nN, N_t, N_t_R and N_t_L all refer to the weighted sum, if "
    "sample_weight is passed.",
    "random_state": "int or None\nIf int, random_state is the seed used by the random number"
    " generator; If None, the random number generator is the RandomState "
    "instance used by np.random.",
    "presort": "Whether to presort the data to speed up the finding of best splits in "
    "fitting. For the default settings of a decision tree on large datasets, "
    "setting this to true may slow down the training process. When using either "
    "a smaller dataset or a restricted depth, this may speed up the training.",
}

SVR_TOOL_TIPS = {
    "kernel": "string\n"
    "Specifies the kernel type to be used in the algorithm. It must be one of ‘linear’, ‘poly’, "
    "‘rbf’, ‘sigmoid’, ‘precomputed’ or a callable. If none is given, ‘rbf’ will be used. If "
    "a callable is given it is used to precompute the kernel matrix.",
    "degree": "int\n"
    "Degree of the polynomial kernel function (‘poly’). Ignored by all other kernels.",
    "gamma": "float\n"
    "Kernel coefficient for ‘rbf’, ‘poly’ and ‘sigmoid’.\n\n"
    "Current default is ‘auto’ which uses 1 / n_features, if gamma='scale' is passed then it "
    "uses 1 / (n_features * X.var()) as value of gamma. The current default of gamma, ‘auto’, "
    "will change to ‘scale’ in version 0.22. ‘auto_deprecated’, a deprecated version of ‘auto’ "
    "is used as a default indicating that no explicit value of gamma was passed.",
    "coef0": "float\n"
    "Independent term in kernel function. It is only significant in ‘poly’ and ‘sigmoid’",
    "tol": "float\n" "Tolerance for stopping criterion.",
    "C": "float\n" "Penalty parameter C of the error term.",
    "epsilon": "float\n"
    "Epsilon in the epsilon-SVR model. It specifies the epsilon-tube within which no penalty is"
    " associated in the training loss function with points predicted within a distance epsilon"
    " from the actual value.",
    "shrinking": "boolean\n" "Whether to use the shrinking heuristic",
    "cache_size": "float\n" "Specify the size of the kernel cache (in MB)",
    "max_iter": "int\n"
    "Hard limit on iterations within solver, or -1 for no limit.",
}

DATA_SPLIT_TOOL_TIPS = {
    "test_size": "float, int, or None\n"
    "If float, should be between 0.0 and 1.0 and represent the proportion of the "
    "dataset to include in the test split. If int, represents the absolute number of "
    "test samples. If None, the value is set to the complement of the train size. If "
    "train_size is also None, it will be set to 0.25.",
    "train_size": "float, int, or None\n"
    "If float, should be between 0.0 and 1.0 and represent the proportion of the "
    "dataset to include in the train split. If int, represents the absolute number "
    "of train samples. If None, the value is automatically set to the complement of "
    "the test size.",
    "random_state": "int or None\n"
    "If int, random_state is the seed used by the random number generator; If None,"
    " the random number generator is the RandomState instance used by np.random.",
    "shuffle": "boolean\n"
    "Whether or not to shuffle the data before splitting. If shuffle=False then stratify"
    " must be None.",
}


MLP_TOOL_TIPS = {
    "hidden_layer_sizes": "tuple, length = n_layers - 2\n",
    "activation": "string\n"
    "Activation function for the hidden layer.\n"
    "identity: no-op activation, useful to implement linear bottleneck, returns f(x) = x.\n"
    "logistic: the logistic sigmoid function, returns f(x) = 1 / (1 + exp(-x)).\n"
    "tanh: the hyperbolic tan function, returns f(x) = tanh(x).\n"
    "relu: the rectified linear unit function, returns f(x) = max(0, x)",
    "solver": "string\nThe solver for weight optimization."
    "lbfgs is an optimizer in the family of quasi-Newton methods.\n"
    "sgd refers to stochastic gradient descent.\n"
    "adam refers to a stochastic gradient-based optimizer proposed by Kingma, Diederik, "
    "and Jimmy Ba\n\n"
    "Note: The default solver ‘adam’ works pretty well on relatively large datasets "
    "(with thousands of training samples or more) in terms of both training time and validation "
    "score. For small datasets, however, ‘lbfgs’ can converge faster and perform better.",
    "alpha": "float\n" "L2 penalty (regularization term) parameter.",
    "batch_size": "int or string\n"
    "Size of minibatches for stochastic optimizers. If the solver is ‘lbfgs’, the "
    "classifier will not use minibatch. When set to “auto”, batch_size=min(200, n_samples)",
    "learning_rate": "string\n"
    "Learning rate schedule for weight updates.\n"
    "constant is a constant learning rate given by ‘learning_rate_init’.\n"
    "invscaling gradually decreases the learning rate at each time step ‘t’ "
    "using an inverse scaling exponent of ‘power_t’. effective_"
    "learning_rate = learning_rate_init / pow(t, power_t)\n"
    "adaptive keeps the learning rate constant to ‘learning_rate_init’ as long as "
    "training loss keeps decreasing. Each time two consecutive epochs fail to decrease "
    "training loss by at least tol, or fail to increase validation score by at least "
    "tol if ‘early_stopping’ is on, the current learning rate is divided by 5.",
    "learning_rate_init": "double\n"
    "The initial learning rate used. It controls the step-size in updating the "
    "weights. Only used when solver=’sgd’ or ‘adam’.",
    "power_t": "double\n"
    "The exponent for inverse scaling learning rate. It is used in updating effective "
    "learning rate when the learning_rate is set to ‘invscaling’. Only used when solver=’sgd’.",
    "max_iter": "int\n"
    "Maximum number of iterations. The solver iterates until convergence (determined by "
    "‘tol’) or this number of iterations. For stochastic solvers (‘sgd’, ‘adam’), note that "
    "this determines the number of epochs (how many times each data point will be used), not "
    "the number of gradient steps.",
    "shuffle": "bool\n"
    "Whether to shuffle samples in each iteration. Only used when solver=’sgd’ or ‘adam’.",
    "random_state": "int or None\n"
    "If int, random_state is the seed used by the random number generator; "
    "If None, the random number generator is the RandomState instance used by np.random.",
    "tol": "float\n"
    "Tolerance for the optimization. When the loss or score is not improving by at least tol for "
    "n_iter_no_change consecutive iterations, unless learning_rate is set to ‘adaptive’, "
    "convergence is considered to be reached and training stops.",
    "warm_start": "bool\n"
    "When set to True, reuse the solution of the previous call to fit as initialization, "
    "otherwise, just erase the previous solution.",
    "momentum": "float\n"
    "Momentum for gradient descent update. Should be between 0 and 1. "
    "Only used when solver=’sgd’.",
    "nesterovs_momentum": "bool\n"
    "Whether to use Nesterov’s momentum. Only used when solver=’sgd’ "
    "and momentum > 0.",
    "early_stopping": "bool\n"
    "Whether to use early stopping to terminate training when validation score is not "
    "improving. If set to true, it will automatically set aside 10% of training data "
    "as validation and terminate training when validation score is not improving by "
    "at least tol for n_iter_no_change consecutive epochs. The split is stratified, "
    "except in a multilabel setting. Only effective when solver=’sgd’ or ‘adam’",
    "validation_fraction": "float\n"
    "The proportion of training data to set aside as validation set for early "
    "stopping. Must be between 0 and 1. Only used if early_stopping is True",
    "beta_1": "float\n"
    "Exponential decay rate for estimates of first moment vector in adam, should be in [0, 1). "
    "Only used when solver=’adam’",
    "beta_2": "float\n"
    "Exponential decay rate for estimates of second moment vector in adam, should be in [0, 1)."
    " Only used when solver=’adam’",
    "epsilon": "float\n"
    "Value for numerical stability in adam. Only used when solver=’adam’",
    "n_iter_no_change": "int\n"
    "Maximum number of epochs to not meet tol improvement. Only effective when "
    "solver=’sgd’ or ‘adam’",
}


ALGORITHMS = {
    "Random Forest": {
        "regressor": RandomForestRegressor,
        "classifier": RandomForestClassifier,
        "tool_tips": RF_TOOL_TIPS,
        "frame": RandomForestFrame,
    },
    "Support Vector Machine": {
        "regressor": SVR,
        "classifier": SVC,
        "tool_tips": SVR_TOOL_TIPS,
        "frame": SupportVectorRegressionFrame,
    },
    "Gradient Boosting": {
        "regressor": GradientBoostingRegressor,
        "classifier": GradientBoostingClassifier,
        "tool_tips": GB_TOOL_TIPS,
        "frame": GradientBoostingFrame,
    },
    "Decision Tree": {
        "regressor": DecisionTreeRegressor,
        "classifier": DecisionTreeClassifier,
        "tool_tips": DT_TOOL_TIPS,
        "frame": DecisionTreeFrame,
    },
    "Multilayer Perceptron": {
        "regressor": MLPRegressor,
        "classifier": MLPClassifier,
        "tool_tips": MLP_TOOL_TIPS,
        "frame": MLPFrame,
    },
}


class MachineLearningPlotData:
    def __init__(self, X, y, model, do_training=True, **kwargs):
        self.model = model
        self.split_args = kwargs

        indices = list(range(len(y)))

        # split the data for training and testing
        split_data = train_test_split(X, indices, **kwargs)
        self.X = {"data": X, "train": split_data[0], "test": split_data[1]}
        self.indices = {
            "data": indices,
            "train": split_data[2],
            "test": split_data[3],
        }
        self.y = {
            "data": y,
            "train": [y[i] for i in split_data[2]],
            "test": [y[i] for i in split_data[3]],
        }
        self.x = {
            key: [i + 1 for i in range(len(data))]
            for key, data in self.y.items()
        }

        # Train model, then calculate predictions, residuals, and mse
        if do_training:
            self.model.fit(self.X["train"], self.y["train"])
        self.predictions = {
            key: self.get_prediction(key) for key in self.y.keys()
        }
        self.residuals = {key: self.get_residual(key) for key in self.y.keys()}
        self.mse = {key: self.get_mse(key) for key in self.y.keys()}
        self.accuracy = {key: self.get_accuracy(key) for key in self.y.keys()}

    def get_prediction(self, key):
        return self.model.predict(self.X[key])

    def get_mse(self, key):
        return np.mean(
            np.square(np.subtract(self.predictions[key], self.y[key]))
        )

    def get_residual(self, key):
        return np.subtract(self.y[key], self.model.predict(self.X[key]))

    def get_accuracy(self, key):
        """Only applicable for classifiers"""
        return np.count_nonzero(
            np.subtract(self.predictions[key], self.y[key]) == 0
        ) / len(self.y[key])

    @property
    def feature_importances(self):
        if hasattr(self.model, "feature_importances_"):
            return self.model.feature_importances_
        return None


class FeatureImportanceFrame(wx.Frame):
    def __init__(
        self,
        options,
        x_variables,
        feature_importances,
        frame_title,
        plot_title,
    ):
        wx.Frame.__init__(self, None)

        self.title = frame_title

        self.plot = PlotFeatureImportance(
            self, options, x_variables, feature_importances, plot_title
        )

        self.set_properties()
        self.do_layout()

        self.Bind(wx.EVT_SIZE, self.on_resize)

    def set_properties(self):
        self.SetTitle(self.title)
        self.SetMinSize(get_window_size(0.35, 0.8))

    def do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_wrapper.Add(self.plot.layout, 1, wx.EXPAND, 0)

        set_msw_background_color(
            self
        )  # If windows, change the background color
        set_frame_icon(self)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def redraw_plot(self):
        self.plot.redraw_plot()

    def on_resize(self, *evt):
        try:
            self.Refresh()
            self.Layout()
            wx.CallAfter(self.redraw_plot)
        except RuntimeError:
            pass


class MachineLearningModelViewer:
    def __init__(self, parent, group_data, group, options, mvr=None):
        self.parent = parent
        self.group_data = group_data
        self.group = group
        self.stats_data = group_data[group]["stats_data"]
        self.options = options

        self.file_path = self.file_select_dlg()

        if self.file_path:

            self.__load_ml_file()
            try:
                if self.is_valid:
                    self.__set_X_and_y_data()

                    self.mvr = mvr
                    self.multi_var_pred = (
                        None if mvr is None else self.mvr.predictions
                    )

                    data_keys = [
                        "X",
                        "y",
                        "x_variables",
                        "y_variable",
                        "multi_var_pred",
                        "options",
                        "mrn",
                        "study_date",
                        "uid",
                    ]
                    data = {key: getattr(self, key) for key in data_keys}
                    frame = ALGORITHMS[self.title]["frame"]
                    self.ml_frame = frame(
                        parent, data, include_test_data=False
                    )
                    self.__load_model()

                    set_msw_background_color(self.ml_frame)
                    set_frame_icon(self.ml_frame)

                    self.ml_frame.run()
                else:
                    if self.stats_data is None:
                        msg = "No data has been queried for Group %s." % group
                    elif not self.is_ml:
                        msg = "Selected file is not a valid machine learning model save file."
                    elif not self.stats_data_has_y:
                        msg = (
                            "The model's dependent variable is not found in your queried data:\n%s"
                            % self.y_variable
                        )
                    elif self.missing_x_variables:
                        msg = (
                            "Your queried data is missing the following independent variables:\n%s"
                            % ", ".join(self.missing_x_variables)
                        )
                    else:
                        msg = "Unknown error."

                    wx.MessageBox(
                        msg,
                        "Model Loading Error",
                        wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
                    )
            except Exception as e:
                msg = str(e)
                wx.MessageBox(
                    msg,
                    "Model Loading Error",
                    wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
                )

    def file_select_dlg(self):
        with wx.FileDialog(
            self.parent,
            "Load a machine learning model",
            wildcard="*.ml",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN,
        ) as dlg:
            dlg.SetDirectory(MODELS_DIR)
            if dlg.ShowModal() == wx.ID_OK:
                return dlg.GetPath()

    def __load_ml_file(self):
        self.loaded_data = load_object_from_file(self.file_path)

        self.y_variable = self.loaded_data["y_variable"]
        self.tool_tips = self.loaded_data["tool_tips"]
        self.x_variables = self.loaded_data["x_variables"]
        self.title = self.loaded_data["title"]
        self.input_parameters = self.loaded_data["input_parameters"]
        self.data_split = self.loaded_data["data_split"]
        self.version = self.loaded_data["version"]

        # As of v0.8.9, model -> sklearn_predictor, regression -> model
        if "sklearn_predictor" in self.loaded_data.keys():
            self.model = self.loaded_data["model"]
            self.sklearn_predictor = self.loaded_data["sklearn_predictor"]
        else:
            self.model = self.loaded_data["regression"]
            self.sklearn_predictor = self.loaded_data["model"]

    def __load_model(self):
        self.ml_frame.model = self.model
        self.ml_frame.set_input_parameters(self.input_parameters)
        self.ml_frame.set_data_split_parameters(self.data_split)
        self.__disable_input()

    def __disable_input(self):
        for variable, input_obj in self.ml_frame.input.items():
            input_obj.Disable()
        for variable, input_obj in self.ml_frame.data_split_input.items():
            input_obj.Disable()
        self.ml_frame.button_calculate.Disable()
        self.ml_frame.button_save_model.Disable()

    def __set_X_and_y_data(self):
        (
            self.X,
            self.y,
            self.mrn,
            self.uid,
            self.study_date,
        ) = self.stats_data.get_X_and_y(
            self.y_variable, self.x_variables, include_patient_info=True
        )

    @property
    def is_ml(self):
        return "title" in list(self.loaded_data) and self.loaded_data[
            "title"
        ] in list(ALGORITHMS)

    @property
    def is_valid(self):
        return (
            self.stats_data is not None
            and self.is_ml
            and not self.missing_x_variables
            and self.stats_data_has_y
        )

    @property
    def missing_x_variables(self):
        return [
            x for x in self.x_variables if x not in list(self.stats_data.data)
        ]

    @property
    def stats_data_has_y(self):
        return self.y_variable in list(self.stats_data.data)

    def apply_plot_options(self):
        self.ml_frame.plot.apply_options()
        self.ml_frame.redraw_plot()


class MachineLearningSetupDlg(wx.Dialog):
    def __init__(self, stats_data, options):
        wx.Dialog.__init__(self, None, title="Machine Learning")

        self.stats_data = stats_data
        self.options = options

        self.combo_box_type = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["Regression", "Classification"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_alg = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=sorted(list(ALGORITHMS.keys())),
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_nan = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["Ignore Study", "Ignore Feature"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_y = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=stats_data.variables,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )

        self.list_ctrl_features = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_NO_HEADER | wx.LC_REPORT
        )

        bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size=(16, 16))
        self.button_info = wx.BitmapButton(self, id=wx.ID_ANY, bitmap=bmp)

        self.button_select_all = wx.Button(self, wx.ID_ANY, "Select All")
        self.button_deselect_all = wx.Button(self, wx.ID_ANY, "Deselect All")
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")

        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()

        self.__do_bind()
        self.__do_layout()

    def __set_properties(self):
        self.list_ctrl_features.AppendColumn(
            "Features", format=wx.LIST_FORMAT_LEFT, width=400
        )

        for choice in self.stats_data.variables:
            self.list_ctrl_features.InsertItem(50000, choice)

        self.combo_box_type.SetValue("Regression")
        self.combo_box_alg.SetValue(sorted(list(ALGORITHMS.keys()))[0])
        self.combo_box_nan.SetValue("Ignore Study")
        self.combo_box_y.SetValue(self.stats_data.variables[0])

    def __do_bind(self):
        self.Bind(
            wx.EVT_BUTTON, self.select_all, id=self.button_select_all.GetId()
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.deselect_all,
            id=self.button_deselect_all.GetId(),
        )
        self.Bind(wx.EVT_BUTTON, self.on_info, id=self.button_info.GetId())

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_input_wrapper = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL
        )
        sizer_input = wx.BoxSizer(wx.VERTICAL)
        sizer_type = wx.BoxSizer(wx.VERTICAL)
        sizer_type_sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer_alg = wx.BoxSizer(wx.VERTICAL)
        sizer_nan_policy = wx.BoxSizer(wx.VERTICAL)
        sizer_y_var = wx.BoxSizer(wx.VERTICAL)
        sizer_features = wx.BoxSizer(wx.VERTICAL)
        sizer_select_all = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)

        label_type = wx.StaticText(self, wx.ID_ANY, "ML Type:")
        label_alg = wx.StaticText(self, wx.ID_ANY, "Algorithm:")
        label_nan_policy = wx.StaticText(self, wx.ID_ANY, "NaN Policy:")
        label_y = wx.StaticText(self, wx.ID_ANY, "Dependent Variable:")
        label_features = wx.StaticText(self, wx.ID_ANY, "Features:")

        sizer_type.Add(label_type, 0, 0, 0)
        sizer_type_sub_sizer.Add(self.combo_box_type, 1, wx.EXPAND, 0)
        sizer_type_sub_sizer.Add(self.button_info, 0, wx.EXPAND | wx.LEFT, 5)
        sizer_type.Add(sizer_type_sub_sizer, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_type, 0, wx.ALL | wx.EXPAND, 5)

        sizer_alg.Add(label_alg, 0, 0, 0)
        sizer_alg.Add(self.combo_box_alg, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_alg, 0, wx.ALL | wx.EXPAND, 5)

        sizer_nan_policy.Add(label_nan_policy, 0, 0, 0)
        sizer_nan_policy.Add(self.combo_box_nan, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_nan_policy, 0, wx.ALL | wx.EXPAND, 5)

        sizer_y_var.Add(label_y, 0, 0, 0)
        sizer_y_var.Add(self.combo_box_y, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_y_var, 0, wx.ALL | wx.EXPAND, 5)

        sizer_features.Add(label_features, 0, wx.BOTTOM | wx.EXPAND, 5)
        sizer_features.Add(self.list_ctrl_features, 1, wx.EXPAND, 0)
        sizer_select_all.Add(self.button_select_all, 0, wx.ALL, 5)
        sizer_select_all.Add(self.button_deselect_all, 0, wx.ALL, 5)
        sizer_features.Add(sizer_select_all, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        sizer_input.Add(
            sizer_features, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5
        )

        sizer_input_wrapper.Add(sizer_input, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_input_wrapper, 1, wx.EXPAND | wx.RIGHT, 5)

        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_main.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.RIGHT, 5)

        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)

        self.Layout()
        self.Center()

    def select_all(self, evt):
        self.apply_global_selection()

    def deselect_all(self, evt):
        self.apply_global_selection(on=0)

    def apply_global_selection(self, on=1):
        for i in range(len(self.stats_data.variables)):
            self.list_ctrl_features.Select(i, on=on)

    @property
    def selected_indices(self):
        if len(get_selected_listctrl_items(self.list_ctrl_features)) == 0:
            self.apply_global_selection()
        return get_selected_listctrl_items(self.list_ctrl_features)

    @property
    def selected_features(self):
        features = [
            self.list_ctrl_features.GetItem(i, 0).GetText()
            for i in self.selected_indices
        ]
        ignore_me = [self.y]
        if self.ignore_feature_if_nan:
            ignore_me.extend(self.stats_data.vars_with_nan_values)
        return sorted(list(set(features) - set(ignore_me)))

    @property
    def alg_type(self):
        return ["classifier", "regressor"][
            self.combo_box_type.GetValue() == "Regression"
        ]

    @property
    def ml_alg(self):
        return self.combo_box_alg.GetValue()

    @property
    def y(self):
        return self.combo_box_y.GetValue()

    @property
    def ignore_feature_if_nan(self):
        return self.combo_box_nan.GetValue() == "Ignore Feature"

    @property
    def ml_input_data(self):
        X, y, mrn, uid, dates = self.stats_data.get_X_and_y(
            self.y, self.selected_features, include_patient_info=True
        )

        return {
            "X": X,
            "y": y,
            "x_variables": self.selected_features,
            "y_variable": self.y,
            "options": self.options,
            "mrn": mrn,
            "study_date": dates,
            "uid": uid,
        }

    def on_info(self, *evt):
        msg = (
            "You can add new features by going to Data -> Show Stats Data in the menu bar. "
            "Right-click a column header to add a new column. You can copy/paste data to/from MS Excel.\n\n"
            "This is how you can add categorical data for a classifier (e.g., toxicity grade), however, "
            "data currently MUST be numeric. You'll need to use integers to represent your categories."
        )
        wx.MessageBox(
            msg,
            "Data Editing Tip",
            wx.OK | wx.OK_DEFAULT | wx.ICON_INFORMATION,
        )
