#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.time_series.py
"""
Class for viewing and editing the roi map, and updating the database with changes
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from dvha.dialogs.export import save_data_to_file
from dvha.models.plot import PlotCorrelation


class CorrelationFrame:
    """
    Object to be passed into notebook panel for the Time Series tab
    """
    def __init__(self, parent, stats_data, options):
        """
        :param parent:  notebook panel in main view
        :type parent: Panel
        :param stats_data: object containing queried data applicable/parsed for statistical analysis
        :type stats_data: StatsData
        :param options: user options containing visual preferences
        :type options: Options
        """
        self.parent = parent
        self.options = options
        self.stats_data = stats_data

        self.__do_layout()

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_plot = wx.BoxSizer(wx.HORIZONTAL)

        self.plot = PlotCorrelation(self.parent, self.options)
        sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_plot, 1, wx.EXPAND, 0)

        self.layout = sizer_wrapper

    def update_data(self, stats_data):
        self.plot.update_plot_data(stats_data)

    def clear_data(self):
        pass

    def get_csv(self, selection=None):
        pass

    def export_csv(self, evt):
        save_data_to_file(self.parent, "Export Correlation data to CSV", self.plot.get_csv())

