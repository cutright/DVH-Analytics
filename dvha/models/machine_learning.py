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
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from dvha.dialogs.export import save_data_to_file
from dvha.options import DefaultOptions
from dvha.paths import MODELS_DIR
from dvha.models.plot import PlotMachineLearning, PlotFeatureImportance
from dvha.tools.stats import MultiVariableRegression
from dvha.tools.utilities import set_msw_background_color, get_window_size, load_object_from_file


class MachineLearningFrame(wx.Frame):
    def __init__(self, data, title, regressor=None, tool_tips=None, include_test_data=True):
        wx.Frame.__init__(self, None)

        self.data = data
        self.title = title
        self.regressor = [regressor, ALGORITHMS[title]['regressor']][regressor is None]
        self.tool_tips = [tool_tips, ALGORITHMS[title]['tool_tips']][tool_tips is None]
        self.include_test_data = include_test_data

        self.reg = None
        self.plot = PlotMachineLearning(self, ml_type=self.title, ml_type_short=self.ml_type_short,
                                        include_test_data=include_test_data, **self.data)

        self.feature_importance_dlg = None

        self.input = {}
        self.defaults = {}
        self.getters = {}

        self.data_split_input = {'test_size': wx.TextCtrl(self, wx.ID_ANY, "0.25"),
                                 'train_size': wx.TextCtrl(self, wx.ID_ANY, "None"),
                                 'random_state': wx.TextCtrl(self, wx.ID_ANY, "None"),
                                 'shuffle': wx.ComboBox(self, wx.ID_ANY, choices=["True", "False"],
                                                        style=wx.CB_DROPDOWN | wx.CB_READONLY)}

        self.data_split_defaults = {'test_size': 0.25,
                                    'train_size': None,
                                    'random_state': None,
                                    'shuffle': True}

        self.data_split_getters = {'test_size': self.to_float_or_none,
                                   'train_size': self.to_float_or_none,
                                   'random_state': self.to_int_or_none,
                                   'shuffle': self.to_bool}

        self.button_calculate = wx.Button(self, wx.ID_ANY, "Calculate")
        self.button_importance = wx.Button(self, wx.ID_ANY, "Importance Plot")
        self.button_export_data = wx.Button(self, wx.ID_ANY, "Export Data")
        self.button_save_plot = wx.Button(self, wx.ID_ANY, "Save Plot")
        self.button_save_model = wx.Button(self, wx.ID_ANY, "Save Model")

        self.do_bind()

    def do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_calculate, id=self.button_calculate.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_feature_importance, id=self.button_importance.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_export, id=self.button_export_data.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_save_plot, id=self.button_save_plot.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_save_model, id=self.button_save_model.GetId())
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
        sizer_actions = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Actions"), wx.VERTICAL)
        sizer_param = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Parameters"), wx.VERTICAL)
        sizer_split_param = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Data Split"), wx.VERTICAL)

        variables = list(self.input)
        variables.sort()
        sizer_input = {variable: wx.BoxSizer(wx.HORIZONTAL) for variable in variables}
        for variable in variables:
            sizer_input[variable].Add(wx.StaticText(self, wx.ID_ANY, "%s:\t" % variable), 0, wx.EXPAND, 0)
            sizer_input[variable].Add(self.input[variable], 1, wx.EXPAND, 0)
            sizer_param.Add(sizer_input[variable], 1, wx.EXPAND | wx.ALL, 2)
        sizer_side_bar.Add(sizer_param, 0, wx.ALL | wx.EXPAND, 5)

        split_variables = ['test_size', 'train_size', 'random_state', 'shuffle']
        sizer_split_input = {variable: wx.BoxSizer(wx.HORIZONTAL) for variable in split_variables}
        for variable in split_variables:
            sizer_split_input[variable].Add(wx.StaticText(self, wx.ID_ANY, "%s:\t" % variable), 0, wx.EXPAND, 0)
            sizer_split_input[variable].Add(self.data_split_input[variable], 1, wx.EXPAND, 0)
            sizer_split_param.Add(sizer_split_input[variable], 1, wx.EXPAND | wx.ALL, 2)
        sizer_side_bar.Add(sizer_split_param, 0, wx.ALL | wx.EXPAND, 5)

        sizer_actions.Add(self.button_calculate, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_actions.Add(self.button_importance, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_actions.Add(self.button_export_data, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_actions.Add(self.button_save_plot, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_actions.Add(self.button_save_model, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_side_bar.Add(sizer_actions, 0, wx.ALL | wx.EXPAND, 5)

        sizer_wrapper.Add(sizer_side_bar, 0, wx.EXPAND, 0)

        sizer_wrapper.Add(self.plot.layout, 1, wx.EXPAND, 0)

        set_msw_background_color(self)  # If windows, change the background color

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
            input_obj.SetValue(self.to_str_for_gui(self.data_split_defaults[variable]))

    @property
    def input_parameters(self):
        return {variable: self.get_param(variable) for variable in self.input.keys()
                if self.get_param(variable) != self.defaults[variable]}

    def set_input_parameters(self, input_parameters):
        for variable, value in input_parameters.keys():
            self.input[variable].SetValue(str(value))

    @property
    def data_split_parameters(self):
        return {variable: self.get_param(variable) for variable in self.data_split_input.keys()
                if self.get_param(variable) != self.data_split_defaults[variable]}

    def set_data_split_parameters(self, data_split_input):
        for variable, value in data_split_input.keys():
            self.data_split_input[variable].SetValue(str(value))

    def to_int_float_or_none(self, str_value):
        if str_value.lower() == 'none':
            return None
        return self.to_int_or_float(str_value)

    @staticmethod
    def to_int_float_string_or_none(str_value):
        if str_value.lower() == 'none':
            return None
        if str_value.isnumeric():  # int
            return int(float(str_value))
        if '.' in str_value and len(str_value.split('.') == 2):
            return float(str_value)
        return str_value

    @staticmethod
    def to_int_or_float(str_value):
        if str_value.isnumeric():  # int
            return int(float(str_value))
        return float(str_value)

    def to_int_or_none(self, str_value):
        if str_value.lower() == 'none':
            return None
        return self.to_int(str_value)

    def to_float_or_none(self, str_value):
        if str_value.lower() == 'none':
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
        if '.' in str_value and len(str_value.split('.') == 2):
            if ("%s" % (str_value.split('.')[0] + str_value.split('.')[1])).isnumeric():
                return float(str_value)
        return str_value

    def to_float_str_or_none(self, str_value):
        try:
            return self.to_float_or_none(str_value)
        except Exception:
            return str_value

    @staticmethod
    def to_bool(str_value):
        if str_value.lower() == 'true':
            return True
        return False

    @staticmethod
    def to_bool_or_str(str_value):
        if str_value.lower() == 'true':
            return True
        if str_value.lower() == 'false':
            return False
        return str_value

    @staticmethod
    def to_str_for_gui(value):
        if value is None:
            return 'None'
        return str(value)

    @property
    def plot_data(self):
        try:
            self.reg = self.regressor(**self.input_parameters)
            return MachineLearningPlotData(self.data['X'], self.data['y'], self.reg, **self.data_split_parameters)
        except Exception as e:
            wx.MessageBox(str(e), 'Error!',
                          wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING)

    def do_regression(self):
        self.reg = self.regressor(**self.input_parameters)
        return MachineLearningPlotData(self.data['X'], self.data['y'], self.reg, **self.data_split_parameters)

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
        save_data_to_file(self, 'Save machine learning data to csv', self.plot.get_csv())

    def on_save_plot(self, evt):
        save_data_to_file(self, 'Save random forest plot', self.plot.html_str,
                          wildcard="HTML files (*.html)|*.html")

    def on_save_model(self, evt):
        data = {'y_variable': self.plot.y_variable,
                'regression': self.reg,
                'regressor': self.regressor,
                'tool_tips': self.tool_tips,
                'x_variables': self.plot.x_variables,
                'title': self.title,
                'input_parameters': self.input_parameters,
                'data_split': self.data_split_parameters,
                'version': DefaultOptions().VERSION}
        save_data_to_file(self, 'Save Model', data,
                          wildcard="MODEL files (*.mlr)|*.mlr", data_type='pickle', initial_dir=MODELS_DIR)

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
        return ''.join([s[0] for s in self.title.split(' ')]).upper()

    def on_feature_importance(self, evt):
        title = "Importance Figure for %s (%s)" % (self.title, self.data['y_variable'])
        plot_title = "%s Feature Importances for %s" % (self.title, self.data['y_variable'])
        self.feature_importance_dlg = FeatureImportanceFrame(self.data['options'], self.data['x_variables'],
                                                             self.reg.feature_importances_, title, plot_title)
        self.feature_importance_dlg.Show()


class RandomForestFrame(MachineLearningFrame):
    def __init__(self, data, include_test_data=True):
        MachineLearningFrame.__init__(self, data, 'Random Forest', include_test_data=include_test_data)

        self.input = {'n_estimators': wx.TextCtrl(self, wx.ID_ANY, "100"),
                      'criterion': wx.ComboBox(self, wx.ID_ANY, choices=["mse", "mae"],
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'max_depth': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'min_samples_split': wx.TextCtrl(self, wx.ID_ANY, "2"),
                      'min_samples_leaf': wx.TextCtrl(self, wx.ID_ANY, "1"),
                      'min_weight_fraction_leaf': wx.TextCtrl(self, wx.ID_ANY, "0"),
                      'max_features': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'max_leaf_nodes': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'min_impurity_decrease': wx.TextCtrl(self, wx.ID_ANY, "0"),
                      'bootstrap': wx.ComboBox(self, wx.ID_ANY, choices=["True", "False"],
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'oob_score': wx.ComboBox(self, wx.ID_ANY, choices=["True", "False"],
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'n_jobs': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'random_state': wx.TextCtrl(self, wx.ID_ANY, "None")}

        self.defaults = {'n_estimators': 100,
                         'criterion': 'mse',
                         'max_depth': None,
                         'min_samples_split': 2,
                         'min_samples_leaf': 1,
                         'min_weight_fraction_leaf': 0.,
                         'max_features': None,
                         'max_leaf_nodes': None,
                         'min_impurity_decrease': 0.,
                         'bootstrap': True,
                         'oob_score': False,
                         'n_jobs': None,
                         'random_state': None}

        self.getters = {'n_estimators': self.to_int,
                        'criterion': self.to_str,
                        'max_depth': self.to_int_or_none,
                        'min_samples_split': self.to_int_or_float,
                        'min_samples_leaf': self.to_int_or_float,
                        'min_weight_fraction_leaf': self.to_float,
                        'max_features': self.to_int_float_string_or_none,
                        'max_leaf_nodes': self.to_int_or_none,
                        'min_impurity_decrease': self.to_float,
                        'bootstrap': self.to_bool,
                        'oob_score': self.to_bool,
                        'n_jobs': self.to_int_or_none,
                        'random_state': self.to_int_or_none}

        self.run()


class GradientBoostingFrame(MachineLearningFrame):
    def __init__(self, data, include_test_data=True):
        MachineLearningFrame.__init__(self, data, 'Gradient Boosting', include_test_data=include_test_data)

        self.input = {'loss': wx.ComboBox(self, wx.ID_ANY, choices=["ls", "lad", "huber", "quantile"],
                                          style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'learning_rate': wx.TextCtrl(self, wx.ID_ANY, "0.1"),
                      'n_estimators': wx.TextCtrl(self, wx.ID_ANY, "100"),
                      'subsample': wx.TextCtrl(self, wx.ID_ANY, "1.0"),
                      'criterion': wx.ComboBox(self, wx.ID_ANY, choices=["friedman_mse", "mse", "mae"],
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'max_depth': wx.TextCtrl(self, wx.ID_ANY, "3"),
                      'min_samples_split': wx.TextCtrl(self, wx.ID_ANY, "2"),
                      'min_samples_leaf': wx.TextCtrl(self, wx.ID_ANY, "1"),
                      'min_weight_fraction_leaf': wx.TextCtrl(self, wx.ID_ANY, "0"),
                      'max_features': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'alpha': wx.TextCtrl(self, wx.ID_ANY, "0.9"),
                      'max_leaf_nodes': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'min_impurity_decrease': wx.TextCtrl(self, wx.ID_ANY, "0"),
                      'init': wx.ComboBox(self, wx.ID_ANY, choices=["DummyEstimator", "zero"],
                                          style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'random_state': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'presort': wx.ComboBox(self, wx.ID_ANY, choices=["auto", "True", "False"],
                                             style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'validation_fraction': wx.TextCtrl(self, wx.ID_ANY, "0.1"),
                      'n_iter_no_change': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'tol': wx.TextCtrl(self, wx.ID_ANY, "1e-4")}

        self.defaults = {'loss': 'ls',
                         'learning_rate': 0.1,
                         'n_estimators': 100,
                         'subsample': 1.0,
                         'criterion': 'friedman_mse',
                         'max_depth': 3,
                         'min_samples_split': 2,
                         'min_samples_leaf': 1,
                         'min_weight_fraction_leaf': 0,
                         'max_features': None,
                         'alpha': 0.9,
                         'max_leaf_nodes': None,
                         'min_impurity_decrease': 0,
                         'init': 'DummyEstimator',
                         'random_state': None,
                         'presort': 'auto',
                         'validation_fraction': 0.1,
                         'n_iter_no_change': None,
                         'tol': float('1e-4')}

        self.getters = {'loss': self.to_str,
                        'learning_rate': self.to_float,
                        'n_estimators': self.to_int,
                        'subsample': self.to_float,
                        'criterion': self.to_str,
                        'max_depth': self.to_int,
                        'min_samples_split': self.to_int_or_float,
                        'min_samples_leaf': self.to_int_or_float,
                        'min_weight_fraction_leaf': self.to_float,
                        'max_features': self.to_int_float_string_or_none,
                        'alpha': self.to_float,
                        'max_leaf_nodes': self.to_int_or_none,
                        'min_impurity_decrease': self.to_float,
                        'init': self.to_str,
                        'random_state': self.to_int_or_none,
                        'presort': self.to_bool_or_str,
                        'validation_fraction': self.to_float,
                        'n_iter_no_change': self.to_int_or_none,
                        'tol': self.to_float}

        self.run()


class DecisionTreeFrame(MachineLearningFrame):
    def __init__(self, data, include_test_data=True):
        MachineLearningFrame.__init__(self, data, 'Decision Tree', include_test_data=include_test_data)

        self.input = {'criterion': wx.ComboBox(self, wx.ID_ANY, choices=["mse", "friedman_mse", "mae"],
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'splitter': wx.ComboBox(self, wx.ID_ANY, choices=["best", "random"],
                                              style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'max_depth': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'min_samples_split': wx.TextCtrl(self, wx.ID_ANY, "2"),
                      'min_samples_leaf': wx.TextCtrl(self, wx.ID_ANY, "1"),
                      'min_weight_fraction_leaf': wx.TextCtrl(self, wx.ID_ANY, "0"),
                      'max_features': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'max_leaf_nodes': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'min_impurity_decrease': wx.TextCtrl(self, wx.ID_ANY, "0"),
                      'random_state': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'presort': wx.ComboBox(self, wx.ID_ANY, choices=["True", "False"],
                                             style=wx.CB_DROPDOWN | wx.CB_READONLY)}

        self.defaults = {'criterion': 'mse',
                         'splitter': 'best',
                         'max_depth': None,
                         'min_samples_split': 2,
                         'min_samples_leaf': 1,
                         'min_weight_fraction_leaf': 0.,
                         'max_features': None,
                         'max_leaf_nodes': None,
                         'min_impurity_decrease': 0.,
                         'random_state': None,
                         'presort': False}

        self.getters = {'criterion': self.to_str,
                        'splitter': self.to_str,
                        'max_depth': self.to_int_or_none,
                        'min_samples_split': self.to_int_or_float,
                        'min_samples_leaf': self.to_int_or_float,
                        'min_weight_fraction_leaf': self.to_float,
                        'max_features': self.to_int_float_string_or_none,
                        'max_leaf_nodes': self.to_int_or_none,
                        'min_impurity_decrease': self.to_float,
                        'random_state': self.to_int_or_none,
                        'presort': self.to_bool}

        self.run()


class SupportVectorRegressionFrame(MachineLearningFrame):
    def __init__(self, data, include_test_data=True):
        MachineLearningFrame.__init__(self, data, 'Support Vector Machine', include_test_data=include_test_data)

        self.input = {'kernel': wx.ComboBox(self, wx.ID_ANY, "rbf",
                                            choices=["linear", "poly", "rbf", "sigmoid", "precomputed"],
                                            style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'degree': wx.TextCtrl(self, wx.ID_ANY, "3"),
                      'gamma': wx.TextCtrl(self, wx.ID_ANY, "auto"),
                      'coef0': wx.TextCtrl(self, wx.ID_ANY, "0.0"),
                      'tol': wx.TextCtrl(self, wx.ID_ANY, "1e-3"),
                      'C': wx.TextCtrl(self, wx.ID_ANY, "1.0"),
                      'epsilon': wx.TextCtrl(self, wx.ID_ANY, "0.1"),
                      'shrinking': wx.ComboBox(self, wx.ID_ANY, "True",
                                               choices=["True", "False"],
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'cache_size': wx.TextCtrl(self, wx.ID_ANY, "None"),
                      'max_iter': wx.TextCtrl(self, wx.ID_ANY, "-1")}

        self.defaults = {'kernel': 'rbf',
                         'degree': 3,
                         'gamma': 'scale',
                         'coef0': 0.0,
                         'tol': 0.001,
                         'C': 1.0,
                         'epsilon': 0.1,
                         'shrinking': True,
                         'cache_size': None,
                         'max_iter': -1}

        self.getters = {'kernel': self.to_str,
                        'degree': self.to_int,
                        'gamma': self.to_float_or_str,
                        'coef0': self.to_float,
                        'tol': self.to_float,
                        'C': self.to_float,
                        'epsilon': self.to_float,
                        'shrinking': self.to_bool,
                        'cache_size': self.to_float_or_none,
                        'max_iter': self.to_int}

        self.button_importance.Disable()

        self.run()


RF_TOOL_TIPS = {'n_estimators': "int\nThe number of trees in the forest.",
                'criterion': "The function to measure the quality of a split. Supported criteria are "
                             "“mse” for the mean squared error, which is equal to variance reduction as"
                             " feature selection criterion, and “mae” for the mean absolute error.",
                'max_depth': "int, None\nThe maximum depth of the tree. If None, then nodes are expanded until all "
                             "leaves are pure or until all leaves contain less than min_samples_split samples.",
                'min_samples_split': "int, float\nThe minimum number of samples required to split an "
                                     "internal node:\n• If int, then consider min_samples_split as the "
                                     "minimum number.\n• If float, then min_samples_split is a fraction "
                                     "and ceil(min_samples_split * n_samples) are the minimum number "
                                     "of samples for each split.",
                'min_samples_leaf': "int, float\nThe minimum number of samples required to be at a leaf"
                                    " node. A split point at any depth will only be considered if it "
                                    "leaves at least min_samples_leaf training samples in each of the "
                                    "left and right branches. This may have the effect of smoothing "
                                    "the model, especially in regression.\n• If int, then consider min_"
                                    "samples_leaf as the minimum number.\n• If float, then min_samples_"
                                    "leaf is a fraction and ceil(min_samples_leaf * n_samples) are the "
                                    "minimum number of samples for each node.",
                'min_weight_fraction_leaf': "float\nThe minimum weighted fraction of the sum total of "
                                            "weights (of all the input samples) required to be at a leaf"
                                            " node. Samples have equal weight when sample_weight is not"
                                            " provided.",
                'max_features': "int, float, string, or None\nThe number of features to consider when "
                                "looking for the best split:\n• If int, then consider max_features "
                                "features at each split.\n• If float, then max_features is a fraction"
                                " and int(max_features * n_features) features are considered at each "
                                "split.\n• If “auto”, then max_features=n_features.\n• If “sqrt”, "
                                "then max_features=sqrt(n_features).\n• If “log2”, then max_"
                                "features=log2(n_features).\n• If None, then max_features=n_features.",
                'max_leaf_nodes': "int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
                                  "Best nodes are defined as relative reduction in impurity. If None "
                                  "then unlimited number of leaf nodes.",
                'min_impurity_decrease': "float\nA node will be split if this split induces a decrease "
                                         "of the impurity greater than or equal to this value.\nThe "
                                         "weighted impurity decrease equation is the following:\n"
                                         "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
                                         "                    - N_t_L / N_t * left_impurity)\n"
                                         "where N is the total number of samples, N_t is the number of "
                                         "samples at the current node, N_t_L is the number of samples "
                                         "in the left child, and N_t_R is the number of samples in the "
                                         "right child.\nN, N_t, N_t_R and N_t_L all refer to the "
                                         "weighted sum, if sample_weight is passed.",
                'bootstrap': "Whether bootstrap samples are used when building trees. If False, the "
                             "whole datset is used to build each tree.",
                'oob_score': "whether to use out-of-bag samples to estimate the R^2 on unseen data.",
                'n_jobs': "int or None\nThe number of jobs to run in parallel for both fit and "
                          "predict. None` means 1 unless in a joblib.parallel_backend context. -1 "
                          "means using all processors.",
                'random_state': "int or None\nIf int, random_state is the seed used by the random "
                                "number generator; If None, the random number generator is the "
                                "RandomState instance used by np.random."}

GB_TOOL_TIPS = {'loss': "loss function to be optimized. ‘ls’ refers to least squares regression. "
                        "‘lad’ (least absolute deviation) is a highly robust loss function solely "
                        "based on order information of the input variables. ‘huber’ is a combination "
                        "of the two. ‘quantile’ allows quantile regression (use alpha to specify the "
                        "quantile).",
                'learning_rate': "float\nlearning rate shrinks the contribution of each tree by "
                                 "learning_rate. There is a trade-off between learning_rate and n_estimators.",
                'n_estimators': "int\nThe number of boosting stages to perform. Gradient boosting is "
                                "fairly robust to over-fitting so a large number usually results in "
                                "better performance.",
                'subsample': "float\nThe fraction of samples to be used for fitting the individual "
                             "base learners. If smaller than 1.0 this results in Stochastic Gradient "
                             "Boosting. subsample interacts with the parameter n_estimators. Choosing "
                             "subsample < 1.0 leads to a reduction of variance and an increase in bias.",
                'criterion': "The function to measure the quality of a split. Supported criteria are"
                             " “friedman_mse” for the mean squared error with improvement score by "
                             "Friedman, “mse” for mean squared error, and “mae” for the mean absolute"
                             " error. The default value of “friedman_mse” is generally the best as it "
                             "can provide a better approximation in some cases.",
                'max_depth': "int\nmaximum depth of the individual regression estimators. The maximum "
                             "depth limits the number of nodes in the tree. Tune this parameter for "
                             "best performance; the best value depends on the interaction of the input"
                             " variables.",
                'min_samples_split': "int, float\nThe minimum number of samples required to split an "
                                     "internal node:\n• If int, then consider min_samples_split as "
                                     "the minimum number.\n• If float, then min_samples_split is a "
                                     "fraction and ceil(min_samples_split * n_samples) are the minimum"
                                     " number of samples for each split.",
                'min_samples_leaf': "int, float\nThe minimum number of samples required to be at a "
                                    "leaf node. A split point at any depth will only be considered if "
                                    "it leaves at least min_samples_leaf training samples in each of "
                                    "the left and right branches. This may have the effect of "
                                    "smoothing the model, especially in regression.\n• If int, then "
                                    "consider min_samples_leaf as the minimum number.\n• If float, "
                                    "then min_samples_leaf is a fraction and ceil(min_samples_leaf * "
                                    "n_samples) are the minimum number of samples for each node.",
                'min_weight_fraction_leaf': "float\nThe minimum weighted fraction of the sum total of "
                                            "weights (of all the input samples) required to be at a "
                                            "leaf node. Samples have equal weight when sample_weight is"
                                            " not provided.",
                'max_features': "int, float, string, or None\nThe number of features to consider when"
                                " looking for the best split:\n• If int, then consider max_features"
                                " features at each split.\n• If float, then max_features is a "
                                "fraction and int(max_features * n_features) features are considered "
                                "at each split.\n• If “auto”, then max_features=n_features.\n• If "
                                "“sqrt”, then max_features=sqrt(n_features).\n• If “log2”, then max"
                                "_features=log2(n_features).\n• If None, then max_features=n_features."
                                "\nChoosing max_features < n_features leads to a reduction of variance"
                                " and an increase in bias.",
                'alpha': "float\nThe alpha-quantile of the huber loss function and the quantile loss "
                         "function. Only if loss='huber' or loss='quantile'.",
                'max_leaf_nodes': "int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
                                  "Best nodes are defined as relative reduction in impurity. If None "
                                  "then unlimited number of leaf nodes.",
                'min_impurity_decrease': "float\nA node will be split if this split induces a decrease "
                                         "of the impurity greater than or equal to this value.\nThe "
                                         "weighted impurity decrease equation is the following:\n"
                                         "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
                                         "                    - N_t_L / N_t * left_impurity)\nwhere N is"
                                         " the total number of samples, N_t is the number of samples at"
                                         " the current node, N_t_L is the number of samples in the left"
                                         " child, and N_t_R is the number of samples in the right child."
                                         "\nN, N_t, N_t_R and N_t_L all refer to the weighted sum, if "
                                         "sample_weight is passed.",
                'init': "If ‘zero’, the initial raw predictions are set to zero. By default a "
                        "DummyEstimator is used, predicting either the average target value "
                        "(for loss=’ls’), or a quantile for the other losses.",
                'random_state': "int or None\nIf int, random_state is the seed used by the random number"
                                " generator; If None, the random number generator is the RandomState "
                                "instance used by np.random.",
                'presort': "Whether to presort the data to speed up the finding of best splits in "
                           "fitting. Auto mode by default will use presorting on dense data and default "
                           "to normal sorting on sparse data. Setting presort to true on sparse data "
                           "will raise an error.",
                'validation_fraction': "float\nThe proportion of training data to set aside as "
                                       "validation set for early stopping. Must be between 0 and 1. "
                                       "Only used if n_iter_no_change is set to an integer.",
                'n_iter_no_change': "int or None\nn_iter_no_change is used to decide if early stopping "
                                    "will be used to terminate training when validation score is not "
                                    "improving. By default it is set to None to disable early stopping."
                                    " If set to a number, it will set aside validation_fraction size of"
                                    " the training data as validation and terminate training when "
                                    "validation score is not improving in all of the previous "
                                    "n_iter_no_change numbers of iterations.",
                'tol': "float\nTolerance for the early stopping. When the loss is not improving by at "
                        "least tol for n_iter_no_change iterations (if set to a number), the training "
                        "stops."}

DT_TOOL_TIPS = {'criterion': "The function to measure the quality of a split. Supported criteria are "
                             "“mse” for the mean squared error, which is equal to variance reduction "
                             "as feature selection criterion and minimizes the L2 loss using the mean "
                             "of each terminal node, “friedman_mse”, which uses mean squared error "
                             "with Friedman’s improvement score for potential splits, and “mae” for "
                             "the mean absolute error, which minimizes the L1 loss using the median of"
                             " each terminal node.",
                'splitter': "The strategy used to choose the split at each node. Supported strategies "
                            "are “best” to choose the best split and “random” to choose the best "
                            "random split.",
                'max_depth': "int, None\nThe maximum depth of the tree. If None, then nodes are expanded"
                             " until all leaves are pure or until all leaves contain less than "
                             "min_samples_split samples.",
                'min_samples_split': "int, float\nThe minimum number of samples required to split an "
                                     "internal node:\n• If int, then consider min_samples_split as the "
                                     "minimum number.\n• If float, then min_samples_split is a fraction"
                                     " and ceil(min_samples_split * n_samples) are the minimum number "
                                     "of samples for each split.",
                'min_samples_leaf': "int, float\nThe minimum number of samples required to be at a leaf"
                                    " node. A split point at any depth will only be considered if it "
                                    "leaves at least min_samples_leaf training samples in each of the "
                                    "left and right branches. This may have the effect of smoothing the"
                                    " model, especially in regression.\n• If int, then consider "
                                    "min_samples_leaf as the minimum number.\n• If float, then "
                                    "min_samples_leaf is a fraction and ceil(min_samples_leaf * "
                                    "n_samples) are the minimum number of samples for each node.",
                'min_weight_fraction_leaf': "float\nThe minimum weighted fraction of the sum total of "
                                            "weights (of all the input samples) required to be at a leaf"
                                            " node. Samples have equal weight when sample_weight is not"
                                            " provided.",
                'max_features': "int, float, string, or None\nThe number of features to consider when"
                                " looking for the best split:\n• If int, then consider max_features "
                                "features at each split.\n• If float, then max_features is a fraction"
                                " and int(max_features * n_features) features are considered at each "
                                "split.\n• If “auto”, then max_features=n_features.\n• If “sqrt”, "
                                "then max_features=sqrt(n_features).\n• If “log2”, "
                                "then max_features=log2(n_features).\n• If None, then "
                                "max_features=n_features.",
                'max_leaf_nodes': "int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
                                  "Best nodes are defined as relative reduction in impurity. If None "
                                  "then unlimited number of leaf nodes.",
                'min_impurity_decrease': "float\nA node will be split if this split induces a decrease "
                                         "of the impurity greater than or equal to this value.\nThe "
                                         "weighted impurity decrease equation is the following:\n"
                                         "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
                                         "                    - N_t_L / N_t * left_impurity)\nwhere N is"
                                         " the total number of samples, N_t is the number of samples at"
                                         " the current node, N_t_L is the number of samples in the left"
                                         " child, and N_t_R is the number of samples in the right child."
                                         "\nN, N_t, N_t_R and N_t_L all refer to the weighted sum, if "
                                         "sample_weight is passed.",
                'random_state': "int or None\nIf int, random_state is the seed used by the random number"
                                " generator; If None, the random number generator is the RandomState "
                                "instance used by np.random.",
                'presort': "Whether to presort the data to speed up the finding of best splits in "
                           "fitting. For the default settings of a decision tree on large datasets, "
                           "setting this to true may slow down the training process. When using either "
                           "a smaller dataset or a restricted depth, this may speed up the training."}

SVR_TOOL_TIPS = {'kernel': "string\n"
                           "Specifies the kernel type to be used in the algorithm. It must be one of ‘linear’, ‘poly’, "
                           "‘rbf’, ‘sigmoid’, ‘precomputed’ or a callable. If none is given, ‘rbf’ will be used. If "
                           "a callable is given it is used to precompute the kernel matrix.",
                 'degree': "int\n"
                           "Degree of the polynomial kernel function (‘poly’). Ignored by all other kernels.",
                 'gamma': "float\n"
                          "Kernel coefficient for ‘rbf’, ‘poly’ and ‘sigmoid’.\n\n"
                          "Current default is ‘auto’ which uses 1 / n_features, if gamma='scale' is passed then it "
                          "uses 1 / (n_features * X.var()) as value of gamma. The current default of gamma, ‘auto’, "
                          "will change to ‘scale’ in version 0.22. ‘auto_deprecated’, a deprecated version of ‘auto’ "
                          "is used as a default indicating that no explicit value of gamma was passed.",
                 'coef0': "float\n"
                          "Independent term in kernel function. It is only significant in ‘poly’ and ‘sigmoid’",
                 'tol': "float\n"
                        "Tolerance for stopping criterion.",
                 'C': "float\n"
                      "Penalty parameter C of the error term.",
                 'epsilon': "float\n"
                            "Epsilon in the epsilon-SVR model. It specifies the epsilon-tube within which no penalty is"
                            " associated in the training loss function with points predicted within a distance epsilon"
                            " from the actual value.",
                 'shrinking': "boolean\n"
                              "Whether to use the shrinking heuristic",
                 'cache_size': "float\n"
                               "Specify the size of the kernel cache (in MB)",
                 'max_iter': "int\n"
                             "Hard limit on iterations within solver, or -1 for no limit."}

DATA_SPLIT_TOOL_TIPS = {'test_size': "float, int, or None\n"
                                     "If float, should be between 0.0 and 1.0 and represent the proportion of the "
                                     "dataset to include in the test split. If int, represents the absolute number of "
                                     "test samples. If None, the value is set to the complement of the train size. If "
                                     "train_size is also None, it will be set to 0.25.",
                        'train_size': "float, int, or None\n"
                                      "If float, should be between 0.0 and 1.0 and represent the proportion of the "
                                      "dataset to include in the train split. If int, represents the absolute number "
                                      "of train samples. If None, the value is automatically set to the complement of "
                                      "the test size.",
                        'random_state': "int or None\n"
                                        "If int, random_state is the seed used by the random number generator; If None,"
                                        " the random number generator is the RandomState instance used by np.random.",
                        'shuffle': "boolean\n"
                                   "Whether or not to shuffle the data before splitting. If shuffle=False then stratify"
                                   " must be None."}


ALGORITHMS = {'Random Forest': {'regressor': RandomForestRegressor,
                                'tool_tips': RF_TOOL_TIPS,
                                'frame': RandomForestFrame},
              'Support Vector Machine': {'regressor': SVR,
                                         'tool_tips': SVR_TOOL_TIPS,
                                         'frame': SupportVectorRegressionFrame},
              'Gradient Boosting': {'regressor': GradientBoostingRegressor,
                                    'tool_tips': GB_TOOL_TIPS,
                                    'frame': GradientBoostingFrame},
              'Decision Tree': {'regressor': DecisionTreeRegressor,
                                'tool_tips': DT_TOOL_TIPS,
                                'frame': DecisionTreeFrame}}


class MachineLearningPlotData:
    def __init__(self, X, y, reg, do_training=True, **kwargs):
        self.reg = reg
        self.split_args = kwargs

        indices = list(range(len(y)))

        # split the data for training and testing
        split_data = train_test_split(X, indices, **kwargs)
        self.X = {'data': X, 'train': split_data[0], 'test': split_data[1]}
        self.indices = {'data': indices, 'train': split_data[2], 'test': split_data[3]}
        self.y = {'data': y, 'train': [y[i] for i in split_data[2]], 'test': [y[i] for i in split_data[3]]}
        self.x = {key: [i + 1 for i in range(len(data))] for key, data in self.y.items()}

        # Train model, then calculate predictions, residuals, and mse
        if do_training:
            self.reg.fit(self.X['train'], self.y['train'])
        self.predictions = {key: self.get_prediction(key) for key in self.y.keys()}
        self.residuals = {key: self.get_residual(key) for key in self.y.keys()}
        self.mse = {key: self.get_mse(key) for key in self.y.keys()}

    def get_prediction(self, key):
        return self.reg.predict(self.X[key])

    def get_mse(self, key):
        return np.mean(np.square(np.subtract(self.predictions[key], self.y[key])))

    def get_residual(self, key):
        return np.subtract(self.y[key], self.reg.predict(self.X[key]))

    @property
    def feature_importances(self):
        if hasattr(self.reg, 'feature_importances_'):
            return self.reg.feature_importances_
        return None


class FeatureImportanceFrame(wx.Frame):
    def __init__(self, options, x_variables, feature_importances, frame_title, plot_title):
        wx.Frame.__init__(self, None)

        self.title = frame_title

        self.plot = PlotFeatureImportance(self, options, x_variables, feature_importances, plot_title)

        self.set_properties()
        self.do_layout()

        self.Bind(wx.EVT_SIZE, self.on_resize)

    def set_properties(self):
        self.SetTitle(self.title)
        self.SetMinSize(get_window_size(0.35, 0.8))

    def do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_wrapper.Add(self.plot.layout, 1, wx.EXPAND, 0)

        set_msw_background_color(self)  # If windows, change the background color

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
        self.stats_data = group_data[group]['stats_data']
        self.options = options

        self.file_path = self.file_select_dlg()

        if self.file_path:

            self.__load_mlr_file()
            try:
                if self.is_valid:
                    self.__set_X_and_y_data()

                    if mvr:
                        self.mvr = mvr
                    else:
                        self.mvr = MultiVariableRegression(self.X, self.y)
                    self.multi_var_pred = self.mvr.predictions

                    data_keys = ['X', 'y', 'x_variables', 'y_variable', 'multi_var_pred', 'options', 'mrn', 'study_date', 'uid']
                    data = {key: getattr(self, key) for key in data_keys}
                    frame = ALGORITHMS[self.title]['frame']
                    self.ml_frame = frame(data, include_test_data=False)
                    self.__load_model()

                    self.ml_frame.run()
                else:
                    if self.stats_data is None:
                        msg = 'No data has been queried for Group %s.' % group
                    elif not self.is_mlr:
                        msg = 'Selected file is not a valid machine learning regression save file.'
                    elif not self.stats_data_has_y:
                        msg = "The model's dependent variable is not found in your queried data:\n%s" % self.y_variable
                    elif self.missing_x_variables:
                        msg = 'Your queried data is missing the following independent variables:\n%s' % \
                              ', '.join(self.missing_x_variables)
                    else:
                        msg = 'Unknown error.'

                    wx.MessageBox(msg, 'Model Loading Error', wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING)
            except Exception as e:
                msg = str(e)
                wx.MessageBox(msg, 'Model Loading Error', wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING)

    def file_select_dlg(self):
        with wx.FileDialog(self.parent, "Load a machine learning regression model", wildcard='*.mlr',
                           style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN) as dlg:
            dlg.SetDirectory(MODELS_DIR)
            if dlg.ShowModal() == wx.ID_OK:
                return dlg.GetPath()

    def __load_mlr_file(self):
        self.loaded_data = load_object_from_file(self.file_path)

        self.y_variable = self.loaded_data['y_variable']
        self.regression = self.loaded_data['regression']
        self.regressor = self.loaded_data['regressor']
        self.tool_tips = self.loaded_data['tool_tips']
        self.x_variables = self.loaded_data['x_variables']
        self.title = self.loaded_data['title']
        self.input_parameters = self.loaded_data['input_parameters']
        self.data_split = self.loaded_data['data_split']
        self.version = self.loaded_data['version']

    def __load_model(self):
        self.ml_frame.reg = self.regression
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
        self.X, self.y, self.mrn, self.uid, self.study_date = \
            self.stats_data.get_X_and_y(self.y_variable, self.x_variables, include_patient_info=True)

    @property
    def is_mlr(self):
        return 'title' in list(self.loaded_data) \
               and self.loaded_data['title'] in list(ALGORITHMS)

    @property
    def is_valid(self):
        return self.stats_data is not None and self.is_mlr and not self.missing_x_variables and self.stats_data_has_y

    @property
    def missing_x_variables(self):
        return [x for x in self.x_variables if x not in list(self.stats_data.data)]

    @property
    def stats_data_has_y(self):
        return self.y_variable in list(self.stats_data.data)