#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.control_chart.py
"""
Class for the Control Chart frame in the main view
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from pubsub import pub
from copy import deepcopy
from dvha.models.plot import PlotControlChart
from dvha.db import sql_columns
from dvha.dialogs.export import save_data_to_file


class ControlChartFrame:
    """
    Object to be passed into notebook panel for the Control Chart tab
    """

    def __init__(self, main_app_frame):

        self.main_app_frame = main_app_frame
        self.parent = main_app_frame.notebook_tab["Control Chart"]
        self.group_data = main_app_frame.group_data
        self.choices = []
        self.models = {grp: {} for grp in [1, 2]}

        self.group = 1

        self.y_axis_options = sql_columns.numerical

        self.combo_box_y_axis = wx.ComboBox(
            self.parent, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )

        self.limit_override = {
            key: wx.TextCtrl(self.parent, wx.ID_ANY, "")
            for key in ["UCL", "LCL"]
        }

        self.button_update = wx.Button(self.parent, wx.ID_ANY, "Update Plot")
        self.button_export = wx.Button(self.parent, wx.ID_ANY, "Export CSV")
        self.button_save_figure = wx.Button(
            self.parent, wx.ID_ANY, "Save Figure"
        )
        self.plot = PlotControlChart(self.parent, main_app_frame.options)

        self.__do_bind()
        self.__set_properties()
        self.__do_subscribe()
        self.__do_layout()

    def __do_bind(self):
        self.parent.Bind(
            wx.EVT_COMBOBOX,
            self.on_combo_box_y,
            id=self.combo_box_y_axis.GetId(),
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.save_figure, id=self.button_save_figure.GetId()
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.export_csv, id=self.button_export.GetId()
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.update_plot, id=self.button_update.GetId()
        )

    def __set_properties(self):
        self.combo_box_y_axis.SetMinSize(
            (300, self.combo_box_y_axis.GetSize()[1])
        )

    def __do_subscribe(self):
        pub.subscribe(self.set_model, "control_chart_set_model")

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        self.sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(
            wx.StaticBox(self.parent, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_lcl = wx.BoxSizer(wx.VERTICAL)
        sizer_ucl = wx.BoxSizer(wx.VERTICAL)

        label_y_axis = wx.StaticText(
            self.parent, wx.ID_ANY, "Charting Variable:"
        )
        sizer_y_axis.Add(label_y_axis, 0, wx.LEFT, 5)
        sizer_y_axis.Add(self.combo_box_y_axis, 0, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_y_axis, 0, wx.EXPAND, 0)

        label_lcl = wx.StaticText(self.parent, wx.ID_ANY, "LCL Override:")
        sizer_lcl.Add(label_lcl, 0, wx.LEFT, 5)
        sizer_lcl.Add(self.limit_override["LCL"], 0, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_lcl, 0, wx.EXPAND, 0)

        label_ucl = wx.StaticText(self.parent, wx.ID_ANY, "UCL Override:")
        sizer_ucl.Add(label_ucl, 0, wx.LEFT, 5)
        sizer_ucl.Add(self.limit_override["UCL"], 0, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_ucl, 0, wx.EXPAND, 0)

        sizer_buttons.Add(
            self.button_update, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 5
        )
        sizer_buttons.Add(
            self.button_export, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 5
        )
        sizer_buttons.Add(
            self.button_save_figure, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 5
        )

        sizer_widgets.Add(sizer_input, 1, wx.EXPAND, 0)
        sizer_widgets.Add(sizer_buttons, 0, 0, 0)

        sizer_wrapper.Add(sizer_widgets, 0, wx.EXPAND | wx.BOTTOM, 5)

        self.layout = sizer_wrapper

    def add_plot_to_layout(self):
        self.plot.init_layout()
        self.sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.update_plot()
        self.layout.Add(self.sizer_plot, 1, wx.EXPAND, 0)
        self.layout.Layout()

    def update_combo_box_y_choices(self):
        stats_data = self.group_data[self.group]["stats_data"]
        if stats_data:
            self.choices = stats_data.variables
            self.choices.sort()
            self.combo_box_y_axis.SetItems(self.choices)
            self.combo_box_y_axis.SetValue("ROI Max Dose")

    @property
    def y_axis(self):
        return self.combo_box_y_axis.GetValue()

    def on_combo_box_y(self, evt):
        self.update_plot()

    def update_plot_ticker(self, evt):
        self.update_plot()

    def update_plot(self, *evt):
        stats_data = self.group_data[self.group]["stats_data"]
        if stats_data is not None:
            dates = stats_data.sim_study_dates
            sort_index = sorted(range(len(dates)), key=lambda k: dates[k])
            dates_sorted = [dates[i] for i in sort_index]

            y_values_sorted = [
                stats_data.data[self.y_axis]["values"][i] for i in sort_index
            ]
            mrn_sorted = [stats_data.mrns[i] for i in sort_index]
            uid_sorted = [stats_data.uids[i] for i in sort_index]

            # remove data with no date
            if "None" in dates_sorted:
                final_index = dates_sorted.index("None")
                dates_sorted = dates_sorted[:final_index]
                y_values_sorted = y_values_sorted[:final_index]
                mrn_sorted = mrn_sorted[:final_index]
                uid_sorted = uid_sorted[:final_index]

            x = list(range(1, len(dates_sorted) + 1))

            self.plot.group = self.group
            self.plot.update_plot(
                x,
                y_values_sorted,
                mrn_sorted,
                uid_sorted,
                dates_sorted,
                y_axis_label=self.y_axis,
                cl_overrides=self.cl_overrides,
            )

            if (
                self.models[self.group]
                and self.y_axis in self.models[self.group].keys()
            ):
                model_data = self.models[self.group][self.y_axis]
                adj_data = self.plot.get_adjusted_control_chart(
                    stats_data=stats_data, **model_data
                )
                self.plot.update_adjusted_control_chart(**adj_data)

    def update_data(self, group_data):
        self.group_data = group_data
        self.update_combo_box_y_choices()
        self.update_plot()

    @property
    def variables(self):
        stats_data = self.group_data[self.group]["stats_data"]
        return list(stats_data)

    def initialize_y_axis_options(self):
        for i in range(len(self.choices))[::-1]:
            c = self.choices[i]
            if c[0:2] in {"D_", "V_"} or c in {"EUD", "NTCP or TCP"}:
                self.choices.pop(i)
        self.choices.sort()
        self.combo_box_y_axis.SetItems(self.choices)
        self.combo_box_y_axis.SetValue("ROI Max Dose")

    def clear_data(self):
        self.initialize_y_axis_options()

    def get_csv(self, selection=None):
        return self.plot.get_csv()

    def export_csv(self, evt):
        save_data_to_file(
            self.parent,
            "Export control chart data to CSV",
            self.plot.get_csv(),
        )

    def save_figure(self, *evt):
        title = "Save Control Chart"
        export_frame = self.main_app_frame.export_figure
        attr_dicts = None if export_frame is None else export_frame.attr_dicts
        self.plot.save_figure_dlg(self.parent, title, attr_dicts=attr_dicts)

    @property
    def has_data(self):
        return self.combo_box_y_axis.IsEnabled()

    def set_model(self, y_variable, x_variables, regression, group):
        self.models[group][y_variable] = {
            "y_variable": y_variable,
            "x_variables": x_variables,
            "regression": regression,
        }
        if self.y_axis == y_variable:
            wx.CallAfter(self.update_plot)

    def delete_model(self, y_variable):
        if y_variable in list(self.models):
            self.models.pop(y_variable)

    def get_save_data(self):
        return {"models": self.models}

    def load_save_data(self, saved_data):
        self.models = deepcopy(saved_data["models"])

    def get_limit_override(self, key):
        cl_override = self.limit_override[key].GetValue()
        if cl_override != "":
            try:
                cl = float(cl_override)
                return cl
            except Exception:
                self.limit_override[key].SetValue("")

    @property
    def cl_overrides(self):
        return {
            key: self.get_limit_override(key)
            for key in self.limit_override.keys()
        }
