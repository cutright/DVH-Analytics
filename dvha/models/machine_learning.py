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
from sklearn.tree import DecisionTreeRegressor
from dvha.dialogs.export import save_data_to_file
from dvha.models.plot import PlotMachineLearning


class MachineLearningFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None)

        self.data = None
        self.regressor = None
        self.reg = None

        self.input = {}
        self.defaults = {}
        self.getters = {}

        self.button_calculate = wx.Button(self, wx.ID_ANY, "Calculate")
        self.button_export_data = wx.Button(self, wx.ID_ANY, "Export Data")
        self.button_save_plot = wx.Button(self, wx.ID_ANY, "Save Plot")

        self.__do_bind()

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_calculate, id=self.button_calculate.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_export, id=self.button_export_data.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_save_plot, id=self.button_save_plot.GetId())

    def do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_side_bar = wx.BoxSizer(wx.VERTICAL)
        sizer_actions = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Actions"), wx.VERTICAL)
        sizer_param = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Parameters"), wx.VERTICAL)

        sizer_input = {variable: wx.BoxSizer(wx.VERTICAL) for variable in self.input.keys()}

        variables = list(self.input)
        variables.sort()
        for variable in variables:
            sizer_input[variable].Add(wx.StaticText(self, wx.ID_ANY, "%s:" % variable), 0, 0, 0)
            sizer_input[variable].Add(self.input[variable], 0, 0, 0)
            sizer_param.Add(sizer_input[variable], 1, wx.EXPAND, 0)

        sizer_side_bar.Add(sizer_param, 1, wx.ALL | wx.EXPAND, 5)

        sizer_actions.Add(self.button_calculate, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_actions.Add(self.button_export_data, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_actions.Add(self.button_save_plot, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_side_bar.Add(sizer_actions, 0, wx.ALL | wx.EXPAND, 5)

        sizer_wrapper.Add(sizer_side_bar, 0, wx.EXPAND, 0)

        sizer_wrapper.Add(self.plot.layout, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def get_param(self, variable):
        try:
            return self.getters[variable](self.input[variable].GetValue())
        except:
            return self.defaults[variable]

    def set_defaults(self):
        for variable, input_obj in self.input.items():
            self.input[variable].SetValue(self.to_str_for_gui(self.defaults[variable]))

    @property
    def input_parameters(self):
        return {variable: self.get_param(variable) for variable in self.input.keys()
                if self.get_param(variable) != self.defaults[variable]}

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

    def to_float_str_or_none(self, str_value):
        try:
            return self.to_float_or_none(str_value)
        except:
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

    def on_calculate(self, evt):
        self.reg = self.regressor(**self.input_parameters)
        self.reg.fit(self.data['X'], self.data['y'])
        y_pred = self.reg.predict(self.data['X'])

        mse = np.mean(np.square(np.subtract(y_pred, self.data['y'])))

        self.plot.update_data(y_pred, self.reg.feature_importances_, self.data['x_variables'], self.data['y_variable'],
                              mse, self.data['uid'])

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


class RandomForestFrame(MachineLearningFrame):
    def __init__(self, data):
        MachineLearningFrame.__init__(self)

        self.data = data
        self.regressor = RandomForestRegressor

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
                        'min_samples_split': self.to_int,
                        'min_samples_leaf': self.to_int,
                        'min_weight_fraction_leaf': self.to_float,
                        'max_features': self.to_float_str_or_none,
                        'max_leaf_nodes': self.to_int_or_none,
                        'min_impurity_decrease': self.to_float,
                        'bootstrap': self.to_bool,
                        'oob_score': self.to_bool,
                        'n_jobs': self.to_int_or_none,
                        'random_state': self.to_int_or_none}

        plot_data = {key: data[key]
                     for key in {'options', 'X', 'y', 'multi_var_pred', 'mrn', 'study_date', 'multi_var_mse'}}
        self.plot = PlotMachineLearning(self, **plot_data)

        self.__set_properties()
        self.do_layout()

        self.Show()

        self.on_calculate(None)

    def __set_properties(self):
        self.SetTitle("Random Forest")
        self.SetSize((1200, 850))
        self.set_defaults()
        self.input['n_estimators'].SetToolTip("int\nThe number of trees in the forest.")
        self.input['criterion'].SetToolTip(u"The function to measure the quality of a split. Supported criteria are "
                                           u"“mse” for the mean squared error, which is equal to variance reduction as"
                                           u" feature selection criterion, and “mae” for the mean absolute error.")
        self.input['max_depth'].SetToolTip("int, None\nThe maximum depth of the tree. If None, then nodes are expanded"
                                           " until all leaves are pure or until all leaves contain less than min_"
                                           "samples_split samples.")
        self.input['min_samples_split'].SetToolTip(u"int, float\nThe minimum number of samples required to split an "
                                                   u"internal node:\n• If int, then consider min_samples_split as the "
                                                   u"minimum number.\n• If float, then min_samples_split is a fraction "
                                                   u"and ceil(min_samples_split * n_samples) are the minimum number "
                                                   u"of samples for each split.")
        self.input['min_samples_leaf'].SetToolTip(u"int, float\nThe minimum number of samples required to be at a leaf"
                                                  u" node. A split point at any depth will only be considered if it "
                                                  u"leaves at least min_samples_leaf training samples in each of the "
                                                  u"left and right branches. This may have the effect of smoothing "
                                                  u"the model, especially in regression.\n• If int, then consider min_"
                                                  u"samples_leaf as the minimum number.\n• If float, then min_samples_"
                                                  u"leaf is a fraction and ceil(min_samples_leaf * n_samples) are the "
                                                  u"minimum number of samples for each node.")
        self.input['min_weight_fraction_leaf'].SetToolTip("float\nThe minimum weighted fraction of the sum total of "
                                                          "weights (of all the input samples) required to be at a leaf"
                                                          " node. Samples have equal weight when sample_weight is not"
                                                          " provided.")
        self.input['max_features'].SetToolTip(u"int, float, string, or None\nThe number of features to consider when "
                                              u"looking for the best split:\n•\tIf int, then consider max_features "
                                              u"features at each split.\n•\tIf float, then max_features is a fraction"
                                              u" and int(max_features * n_features) features are considered at each "
                                              u"split.\n•\tIf “auto”, then max_features=n_features.\n•\tIf “sqrt”, "
                                              u"then max_features=sqrt(n_features).\n•\tIf “log2”, then max_"
                                              u"features=log2(n_features).\n•\tIf None, then max_features=n_features.")
        self.input['max_leaf_nodes'].SetToolTip("int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
                                                "Best nodes are defined as relative reduction in impurity. If None "
                                                "then unlimited number of leaf nodes.")
        self.input['min_impurity_decrease'].SetToolTip("float\nA node will be split if this split induces a decrease "
                                                       "of the impurity greater than or equal to this value.\nThe "
                                                       "weighted impurity decrease equation is the following:\n"
                                                       "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
                                                       "                    - N_t_L / N_t * left_impurity)\n"
                                                       "where N is the total number of samples, N_t is the number of "
                                                       "samples at the current node, N_t_L is the number of samples "
                                                       "in the left child, and N_t_R is the number of samples in the "
                                                       "right child.\nN, N_t, N_t_R and N_t_L all refer to the "
                                                       "weighted sum, if sample_weight is passed.")
        self.input['bootstrap'].SetToolTip("Whether bootstrap samples are used when building trees. If False, the "
                                           "whole datset is used to build each tree.")
        self.input['oob_score'].SetToolTip("whether to use out-of-bag samples to estimate the R^2 on unseen data.")
        self.input['n_jobs'].SetToolTip("int or None\nThe number of jobs to run in parallel for both fit and "
                                        "predict. None` means 1 unless in a joblib.parallel_backend context. -1 "
                                        "means using all processors.")
        self.input['random_state'].SetToolTip("int or None\nIf int, random_state is the seed used by the random "
                                              "number generator; If None, the random number generator is the "
                                              "RandomState instance used by np.random.")


class GradientBoostingFrame(MachineLearningFrame):
    def __init__(self,data):
        MachineLearningFrame.__init__(self)

        self.data = data
        self.regressor = GradientBoostingRegressor

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
                      'init': wx.ComboBox(self, wx.ID_ANY, choices=["DummyEstimator", "zero"], style=wx.CB_DROPDOWN),
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
                        'min_samples_split': self.to_float,
                        'min_samples_leaf': self.to_float,
                        'min_weight_fraction_leaf': self.to_float,
                        'max_features': self.to_float_str_or_none,
                        'alpha': self.to_float,
                        'max_leaf_nodes': self.to_int_or_none,
                        'min_impurity_decrease': self.to_float,
                        'init': self.to_str,
                        'random_state': self.to_int_or_none,
                        'presort': self.to_bool_or_str,
                        'validation_fraction': self.to_float,
                        'n_iter_no_change': self.to_int_or_none,
                        'tol': self.to_float}

        plot_data = {key: data[key]
                     for key in {'options', 'X', 'y', 'multi_var_pred', 'mrn', 'study_date', 'multi_var_mse'}}
        self.plot = PlotMachineLearning(self, **plot_data)

        self.__set_properties()
        self.do_layout()

        self.Show()

        self.on_calculate(None)

    def __set_properties(self):
        self.SetTitle("Gradient Boosting")
        self.SetSize((750, 1000))
        self.set_defaults()
        self.input['loss'].SetToolTip(u"loss function to be optimized. ‘ls’ refers to least squares regression. "
                                      u"‘lad’ (least absolute deviation) is a highly robust loss function solely "
                                      u"based on order information of the input variables. ‘huber’ is a combination "
                                      u"of the two. ‘quantile’ allows quantile regression (use alpha to specify the "
                                      u"quantile).")
        self.input['learning_rate'].SetToolTip("float\nlearning rate shrinks the contribution of each tree by "
                                               "learning_rate. There is a trade-off between learning_rate and n_"
                                               "estimators.")
        self.input['n_estimators'].SetToolTip("int\nThe number of boosting stages to perform. Gradient boosting is "
                                              "fairly robust to over-fitting so a large number usually results in "
                                              "better performance.")
        self.input['subsample'].SetToolTip("float\nThe fraction of samples to be used for fitting the individual "
                                           "base learners. If smaller than 1.0 this results in Stochastic Gradient "
                                           "Boosting. subsample interacts with the parameter n_estimators. Choosing "
                                           "subsample < 1.0 leads to a reduction of variance and an increase in bias.")
        self.input['criterion'].SetToolTip(u"The function to measure the quality of a split. Supported criteria are"
                                           u" “friedman_mse” for the mean squared error with improvement score by "
                                           u"Friedman, “mse” for mean squared error, and “mae” for the mean absolute"
                                           u" error. The default value of “friedman_mse” is generally the best as it "
                                           u"can provide a better approximation in some cases.")
        self.input['max_depth'].SetToolTip("int\nmaximum depth of the individual regression estimators. The maximum "
                                           "depth limits the number of nodes in the tree. Tune this parameter for "
                                           "best performance; the best value depends on the interaction of the input"
                                           " variables.")
        self.input['min_samples_split'].SetToolTip(u"int, float\nThe minimum number of samples required to split an "
                                                   u"internal node:\n•\tIf int, then consider min_samples_split as "
                                                   u"the minimum number.\n•\tIf float, then min_samples_split is a "
                                                   u"fraction and ceil(min_samples_split * n_samples) are the minimum"
                                                   u" number of samples for each split.")
        self.input['min_samples_leaf'].SetToolTip(u"int, float\nThe minimum number of samples required to be at a "
                                                  u"leaf node. A split point at any depth will only be considered if "
                                                  u"it leaves at least min_samples_leaf training samples in each of "
                                                  u"the left and right branches. This may have the effect of "
                                                  u"smoothing the model, especially in regression.\n•\tIf int, then "
                                                  u"consider min_samples_leaf as the minimum number.\n•\tIf float, "
                                                  u"then min_samples_leaf is a fraction and ceil(min_samples_leaf * "
                                                  u"n_samples) are the minimum number of samples for each node.")
        self.input['min_weight_fraction_leaf'].SetToolTip("float\nThe minimum weighted fraction of the sum total of "
                                                          "weights (of all the input samples) required to be at a "
                                                          "leaf node. Samples have equal weight when sample_weight is"
                                                          " not provided.")
        self.input['max_features'].SetToolTip(u"int, float, string, or None\nThe number of features to consider when"
                                              u" looking for the best split:\n•\tIf int, then consider max_features"
                                              u" features at each split.\n•\tIf float, then max_features is a "
                                              u"fraction and int(max_features * n_features) features are considered "
                                              u"at each split.\n•\tIf “auto”, then max_features=n_features.\n•\tIf "
                                              u"“sqrt”, then max_features=sqrt(n_features).\n•\tIf “log2”, then max"
                                              u"_features=log2(n_features).\n•\tIf None, then max_features=n_features."
                                              u"\nChoosing max_features < n_features leads to a reduction of variance"
                                              u" and an increase in bias.")
        self.input['alpha'].SetToolTip("float\nThe alpha-quantile of the huber loss function and the quantile loss "
                                       "function. Only if loss='huber' or loss='quantile'.")
        self.input['max_leaf_nodes'].SetToolTip("int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
                                                "Best nodes are defined as relative reduction in impurity. If None "
                                                "then unlimited number of leaf nodes.")
        self.input['min_impurity_decrease'].SetToolTip("float\nA node will be split if this split induces a decrease "
                                                       "of the impurity greater than or equal to this value.\nThe "
                                                       "weighted impurity decrease equation is the following:\n"
                                                       "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
                                                       "                    - N_t_L / N_t * left_impurity)\nwhere N is"
                                                       " the total number of samples, N_t is the number of samples at"
                                                       " the current node, N_t_L is the number of samples in the left"
                                                       " child, and N_t_R is the number of samples in the right child."
                                                       "\nN, N_t, N_t_R and N_t_L all refer to the weighted sum, if "
                                                       "sample_weight is passed.")
        self.input['init'].SetToolTip(u"If ‘zero’, the initial raw predictions are set to zero. By default a "
                                      u"DummyEstimator is used, predicting either the average target value "
                                      u"(for loss=’ls’), or a quantile for the other losses.")
        self.input['random_state'].SetToolTip("int or None\nIf int, random_state is the seed used by the random number"
                                              " generator; If None, the random number generator is the RandomState "
                                              "instance used by np.random.")
        self.input['presort'].SetToolTip("Whether to presort the data to speed up the finding of best splits in "
                                         "fitting. Auto mode by default will use presorting on dense data and default "
                                         "to normal sorting on sparse data. Setting presort to true on sparse data "
                                         "will raise an error.")
        self.input['validation_fraction'].SetToolTip("float\nThe proportion of training data to set aside as "
                                                     "validation set for early stopping. Must be between 0 and 1. "
                                                     "Only used if n_iter_no_change is set to an integer.")
        self.input['n_iter_no_change'].SetToolTip("int or None\nn_iter_no_change is used to decide if early stopping "
                                                  "will be used to terminate training when validation score is not "
                                                  "improving. By default it is set to None to disable early stopping."
                                                  " If set to a number, it will set aside validation_fraction size of"
                                                  " the training data as validation and terminate training when "
                                                  "validation score is not improving in all of the previous "
                                                  "n_iter_no_change numbers of iterations.")
        self.input['tol'].SetToolTip("float\nTolerance for the early stopping. When the loss is not improving by at "
                                     "least tol for n_iter_no_change iterations (if set to a number), the training "
                                     "stops.")


class DecisionTreeFrame(MachineLearningFrame):
    def __init__(self, data):
        MachineLearningFrame.__init__(self)

        self.data = data
        self.regressor = DecisionTreeRegressor

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
                        'min_samples_split': self.to_float,
                        'min_samples_leaf': self.to_float,
                        'min_weight_fraction_leaf': self.to_float,
                        'max_features': self.to_float_str_or_none,
                        'max_leaf_nodes': self.to_int_or_none,
                        'min_impurity_decrease': self.to_float,
                        'random_state': self.to_int_or_none,
                        'presort': self.to_bool}

        plot_data = {key: data[key]
                     for key in {'options', 'X', 'y', 'multi_var_pred', 'mrn', 'study_date', 'multi_var_mse'}}
        self.plot = PlotMachineLearning(self, **plot_data)

        self.__set_properties()
        self.do_layout()

        self.Show()

        self.on_calculate(None)

    def __set_properties(self):
        self.SetTitle("Decision Tree")
        self.SetSize((750, 750))
        self.set_defaults()
        self.input['criterion'].SetToolTip(u"The function to measure the quality of a split. Supported criteria are "
                                           u"“mse” for the mean squared error, which is equal to variance reduction "
                                           u"as feature selection criterion and minimizes the L2 loss using the mean "
                                           u"of each terminal node, “friedman_mse”, which uses mean squared error "
                                           u"with Friedman’s improvement score for potential splits, and “mae” for "
                                           u"the mean absolute error, which minimizes the L1 loss using the median of"
                                           u" each terminal node.")
        self.input['splitter'].SetToolTip(u"The strategy used to choose the split at each node. Supported strategies "
                                          u"are “best” to choose the best split and “random” to choose the best "
                                          u"random split.")
        self.input['max_depth'].SetToolTip("int, None\nThe maximum depth of the tree. If None, then nodes are expanded"
                                           " until all leaves are pure or until all leaves contain less than "
                                           "min_samples_split samples.")
        self.input['min_samples_split'].SetToolTip(u"int, float\nThe minimum number of samples required to split an "
                                                   u"internal node:\n• If int, then consider min_samples_split as the "
                                                   u"minimum number.\n• If float, then min_samples_split is a fraction"
                                                   u" and ceil(min_samples_split * n_samples) are the minimum number "
                                                   u"of samples for each split.")
        self.input['min_samples_leaf'].SetToolTip(u"int, float\nThe minimum number of samples required to be at a leaf"
                                                  u" node. A split point at any depth will only be considered if it "
                                                  u"leaves at least min_samples_leaf training samples in each of the "
                                                  u"left and right branches. This may have the effect of smoothing the"
                                                  u" model, especially in regression.\n• If int, then consider "
                                                  u"min_samples_leaf as the minimum number.\n• If float, then "
                                                  u"min_samples_leaf is a fraction and ceil(min_samples_leaf * "
                                                  u"n_samples) are the minimum number of samples for each node.")
        self.input['min_weight_fraction_leaf'].SetToolTip("float\nThe minimum weighted fraction of the sum total of "
                                                          "weights (of all the input samples) required to be at a leaf"
                                                          " node. Samples have equal weight when sample_weight is not"
                                                          " provided.")
        self.input['max_features'].SetToolTip(u"int, float, string, or None\nThe number of features to consider when"
                                              u" looking for the best split:\n•\tIf int, then consider max_features "
                                              u"features at each split.\n•\tIf float, then max_features is a fraction"
                                              u" and int(max_features * n_features) features are considered at each "
                                              u"split.\n•\tIf “auto”, then max_features=n_features.\n•\tIf “sqrt”, "
                                              u"then max_features=sqrt(n_features).\n•\tIf “log2”, "
                                              u"then max_features=log2(n_features).\n•\tIf None, then "
                                              u"max_features=n_features.")
        self.input['max_leaf_nodes'].SetToolTip("int or None\nGrow a tree with max_leaf_nodes in best-first fashion. "
                                                "Best nodes are defined as relative reduction in impurity. If None "
                                                "then unlimited number of leaf nodes.")
        self.input['min_impurity_decrease'].SetToolTip("float\nA node will be split if this split induces a decrease "
                                                       "of the impurity greater than or equal to this value.\nThe "
                                                       "weighted impurity decrease equation is the following:\n"
                                                       "N_t / N * (impurity - N_t_R / N_t * right_impurity\n"
                                                       "                    - N_t_L / N_t * left_impurity)\nwhere N is"
                                                       " the total number of samples, N_t is the number of samples at"
                                                       " the current node, N_t_L is the number of samples in the left"
                                                       " child, and N_t_R is the number of samples in the right child."
                                                       "\nN, N_t, N_t_R and N_t_L all refer to the weighted sum, if "
                                                       "sample_weight is passed.")
        self.input['random_state'].SetToolTip("int or None\nIf int, random_state is the seed used by the random number"
                                              " generator; If None, the random number generator is the RandomState "
                                              "instance used by np.random.")
        self.input['presort'].SetToolTip("Whether to presort the data to speed up the finding of best splits in "
                                         "fitting. For the default settings of a decision tree on large datasets, "
                                         "setting this to true may slow down the training process. When using either "
                                         "a smaller dataset or a restricted depth, this may speed up the training.")
