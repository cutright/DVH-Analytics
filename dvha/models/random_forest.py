#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.rad_bio.py
"""
Class to view and calculate Random Forest
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
import numpy as np
# from threading import Thread
# from pubsub import pub
from sklearn.ensemble import RandomForestRegressor
from dvha.models.plot import PlotRandomForest
from dvha.tools.utilities import set_msw_background_color


class RandomForestFrame(wx.Frame):
    """
    View random forest predictions for provided data
    """
    def __init__(self, X, y, x_variables, y_variable, multi_var_pred, options, mrn, study_date):
        """
        :param X:
        :param y: data to be modeled
        :type y: list
        :param x_variables:
        :param y_variable:
        :param options: user options
        :type options: Options
        """
        wx.Frame.__init__(self, None)

        set_msw_background_color(self)  # If windows, change the background color

        self.X, self.y = X, y
        self.x_variables, self.y_variable = x_variables, y_variable

        self.plot = PlotRandomForest(self, options, X, y, multi_var_pred, mrn, study_date)

        self.SetSize((1000, 750))
        self.spin_ctrl_trees = wx.SpinCtrl(self, wx.ID_ANY, "100", min=1, max=1000)
        self.spin_ctrl_features = wx.SpinCtrl(self, wx.ID_ANY, "2", min=2, max=len(x_variables))
        self.button_update = wx.Button(self, wx.ID_ANY, "Calculate")

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()

        self.Show()

        self.on_update(None)

    def __set_properties(self):
        self.SetTitle("Random Forest")
        self.spin_ctrl_trees.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                             wx.FONTWEIGHT_NORMAL, 0, ".SF NS Text"))
        self.spin_ctrl_trees.SetToolTip("n_estimators")
        self.spin_ctrl_features.SetToolTip("Maximum number of features when splitting")

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_update, id=self.button_update.GetId())

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_input_and_plot = wx.BoxSizer(wx.VERTICAL)
        sizer_hyper_parameters = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Hyper-parameters:"), wx.HORIZONTAL)
        sizer_features = wx.BoxSizer(wx.HORIZONTAL)
        sizer_trees = wx.BoxSizer(wx.HORIZONTAL)

        label_trees = wx.StaticText(self, wx.ID_ANY, "Number of Trees:")
        sizer_trees.Add(label_trees, 0, wx.ALL, 5)
        sizer_trees.Add(self.spin_ctrl_trees, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(sizer_trees, 1, wx.EXPAND, 0)

        label_features = wx.StaticText(self, wx.ID_ANY, "Max feature count:")
        sizer_features.Add(label_features, 0, wx.ALL, 5)
        sizer_features.Add(self.spin_ctrl_features, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(sizer_features, 1, wx.EXPAND, 0)

        sizer_hyper_parameters.Add(self.button_update, 0, wx.ALL, 5)

        sizer_input_and_plot.Add(sizer_hyper_parameters, 0, wx.EXPAND, 0)

        sizer_input_and_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_input_and_plot, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Center()
        self.Layout()

    def on_update(self, evt):
        y_pred, mse, importance = get_random_forest(self.X, self.y, n_estimators=self.spin_ctrl_trees.GetValue(),
                                                    max_features=self.spin_ctrl_features.GetValue())
        self.plot.update_data(y_pred, importance, self.x_variables, self.y_variable)


# class RandomForestWorker(Thread):
#     """
#     Thread to calculate random forest apart
#     """
#     def __init__(self, X, y, n_estimators=None, max_features=None):
#         """
#         :param X: independent data matrix
#         :type X: numpy.array
#         :param y: numpy.array
#         :param n_estimators:
#         :param max_features:
#         """
#         Thread.__init__(self)
#         self.X, self.y = X, y
#
#         self.kwargs = {}
#         if n_estimators is not None:
#             self.kwargs['n_estimators'] = n_estimators
#         if max_features is not None:
#             self.kwargs['max_features'] = max_features
#         self.start()  # start the thread
#
#     def run(self):
#         y_predict, mse = get_random_forest(self.X, self.y, **self.kwargs)
#         msg = {'y_predict': y_predict, 'mse': mse}
#         wx.CallAfter(pub.sendMessage, "random_forest_complete", msg=msg)


def get_random_forest(X, y, n_estimators=100, max_features=None):
    """
    Get random forest predictions and the mean square error with sklearn
    :param X: independent data
    :type X: numpy.array
    :param y: dependent data
    :type y: list
    :param n_estimators:
    :type n_estimators: int
    :param max_features:
    :type max_features: int
    :return: predicted values, mean square error
    :rtype: tuple
    """
    if max_features is None:
        max_features = len(X[0, :])
    regressor = RandomForestRegressor(n_estimators=n_estimators, max_features=max_features)
    regressor.fit(X, y)
    y_pred = regressor.predict(X)

    mse = np.mean(np.square(np.subtract(y_pred, y)))

    return y_pred, mse, regressor.feature_importances_
