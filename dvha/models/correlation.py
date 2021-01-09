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
from dvha.dialogs.main import SelectFromListDialog
from dvha.tools.errors import ErrorDialog
from dvha.tools.utilities import get_window_size


class CorrelationFrame:
    """
    Object to be passed into notebook panel for the Time Series tab
    """

    def __init__(self, main_app):

        self.main_app = main_app
        self.parent = main_app.notebook_tab["Correlation"]
        self.options = main_app.options
        self.stats_data = main_app.group_data[1]["stats_data"]
        self.stats_data_2 = main_app.group_data[2]["stats_data"]

        self.selections = main_app.options.CORRELATION_MATRIX_VARS

        self.__define_gui_objects()
        self.__do_bind()
        self.__do_layout()

    def __define_gui_objects(self):
        self.button_var_select = wx.Button(
            self.parent, wx.ID_ANY, "Select Variables"
        )
        self.button_var_default = wx.Button(
            self.parent, wx.ID_ANY, "Default Variables"
        )
        self.button_export_csv = wx.Button(
            self.parent, wx.ID_ANY, "Export CSV"
        )
        self.button_save_figure = wx.Button(
            self.parent, wx.ID_ANY, "Save Figure"
        )
        self.plot = PlotCorrelation(self.parent, self.options)

    def __do_bind(self):
        self.parent.Bind(
            wx.EVT_BUTTON,
            self.on_var_select,
            id=self.button_var_select.GetId(),
        )
        self.parent.Bind(
            wx.EVT_BUTTON,
            self.on_var_default,
            id=self.button_var_default.GetId(),
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.export_csv, id=self.button_export_csv.GetId()
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.save_figure, id=self.button_save_figure.GetId()
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_plot = wx.BoxSizer(wx.HORIZONTAL)

        sizer_buttons.Add(self.button_var_select, 0, wx.RIGHT, 5)
        sizer_buttons.Add(self.button_var_default, 0, wx.RIGHT, 5)
        sizer_buttons.Add(self.button_export_csv, 0, wx.RIGHT, 5)
        sizer_buttons.Add(self.button_save_figure, 0, wx.RIGHT, 5)

        # self.sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)

        sizer_wrapper.Add(sizer_buttons, 0, wx.BOTTOM, 5)

        self.layout = sizer_wrapper

    def add_plot_to_layout(self):
        self.plot.init_layout()
        self.sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.layout.Add(self.sizer_plot, 1, wx.EXPAND, 0)
        self.update_plot_data()
        self.layout.Layout()

    def on_var_select(self, evt):
        categories = [
            c for c in list(self.stats_data.data) if "date" not in c.lower()
        ]
        categories.sort()
        size = get_window_size(1, 0.8)
        dlg = SelectFromListDialog(
            "Correlation Matrix",
            "Variables",
            categories,
            size=(350, size[1]),
            column_width=300,
            selections=self.selections,
        )
        res = dlg.ShowModal()

        if res == wx.ID_OK:
            self.selections = dlg.selected_values
            self.update_plot_data()
        dlg.Destroy()

    def on_var_default(self, evt):
        self.selections = self.options.CORRELATION_MATRIX_VARS
        self.update_plot_data()

    def set_data(self, group_data):
        self.stats_data = group_data[1]["stats_data"]
        self.stats_data_2 = group_data[2]["stats_data"]
        self.update_plot_data()

    def update_plot_data(self):
        try:
            self.plot.update_plot_data(
                self.stats_data,
                stats_data_2=self.stats_data_2,
                included_vars=self.selections,
            )
        except Exception as e:
            msg = (
                "Correlation calculation failed. Perhaps more data is needed?\n%s"
                % str(e)
            )
            ErrorDialog(self.parent, msg, "Correlation Error")

    # TODO: are these 2 functions purposeful?
    def clear_data(self):
        pass

    def get_csv(self, selection=None):
        pass

    def export_csv(self, evt):
        save_data_to_file(
            self.parent, "Export Correlation data to CSV", self.plot.get_csv()
        )

    def save_figure(self, *evt):
        self.plot.save_figure_dlg(self.parent, "Save Correlation Figure")
