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
from dateutil.parser import parse as date_parser
from dvha.db import sql_columns
from dvha.dialogs.export import save_data_to_file
from dvha.models.plot import PlotTimeSeries


class TimeSeriesFrame:
    """
    Object to be passed into notebook panel for the Time Series tab
    """

    def __init__(self, main_app_frame):

        self.main_app_frame = main_app_frame
        self.parent = main_app_frame.notebook_tab["Time Series"]
        self.options = main_app_frame.options
        self.stats_data = {
            grp: data["stats_data"]
            for grp, data in main_app_frame.group_data.items()
        }

        self.combo_box_y_axis = wx.ComboBox(
            self.parent, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.text_input_bin_size = wx.TextCtrl(
            self.parent, wx.ID_ANY, "10", style=wx.TE_PROCESS_ENTER
        )
        self.text_input_lookback_distance = wx.TextCtrl(
            self.parent, wx.ID_ANY, "1", style=wx.TE_PROCESS_ENTER
        )
        self.text_inputs_percentile = wx.TextCtrl(
            self.parent, wx.ID_ANY, "90", style=wx.TE_PROCESS_ENTER
        )
        self.button_update_plot = wx.Button(
            self.parent, wx.ID_ANY, "Update Plot"
        )
        self.button_export_csv = wx.Button(
            self.parent, wx.ID_ANY, "Export CSV"
        )
        self.button_save_figure = wx.Button(
            self.parent, wx.ID_ANY, "Save Figure"
        )

        self.parent.Bind(
            wx.EVT_COMBOBOX,
            self.combo_box_y_axis_ticker,
            id=self.combo_box_y_axis.GetId(),
        )
        self.parent.Bind(
            wx.EVT_TEXT_ENTER,
            self.update_plot_ticker,
            id=self.text_input_bin_size.GetId(),
        )
        self.parent.Bind(
            wx.EVT_TEXT_ENTER,
            self.update_plot_ticker,
            id=self.text_input_lookback_distance.GetId(),
        )
        self.parent.Bind(
            wx.EVT_TEXT_ENTER,
            self.update_plot_ticker,
            id=self.text_inputs_percentile.GetId(),
        )

        self.__set_properties()
        self.__do_layout()

        self.parent.Bind(
            wx.EVT_BUTTON,
            self.update_plot_ticker,
            id=self.button_update_plot.GetId(),
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.export_csv, id=self.button_export_csv.GetId()
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.save_figure, id=self.button_save_figure.GetId()
        )

        self.disable_buttons()

        self.layout_save_attr = [
            "combo_box_y_axis",
            "text_input_lookback_distance",
            "text_inputs_percentile",
            "text_input_bin_size",
        ]

    def __set_properties(self):
        self.combo_box_y_axis.AppendItems(self.choices)
        self.combo_box_y_axis.SetLabelText("ROI Max Dose")

    @property
    def choices(self):
        if self.stats_data[1]:
            choices = self.stats_data[1].variables
            if self.stats_data[2]:
                choices.extend(self.stats_data[2].variables)
                choices = list(set(choices))
        else:
            choices = list(sql_columns.numerical)
        choices.sort()
        return choices

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        self.sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(
            wx.StaticBox(self.parent, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_percentile = wx.BoxSizer(wx.VERTICAL)
        sizer_lookback_distance = wx.BoxSizer(wx.VERTICAL)
        sizer_histogram_bins = wx.BoxSizer(wx.VERTICAL)
        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.BoxSizer(wx.HORIZONTAL)

        label_y_axis = wx.StaticText(self.parent, wx.ID_ANY, "Y Axis:")
        sizer_y_axis.Add(label_y_axis, 0, wx.LEFT, 5)
        sizer_y_axis.Add(self.combo_box_y_axis, 0, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_y_axis, 1, wx.EXPAND, 0)

        label_histogram_bins = wx.StaticText(
            self.parent, wx.ID_ANY, "Hist. Bins:"
        )
        sizer_histogram_bins.Add(label_histogram_bins, 0, wx.LEFT, 5)
        sizer_histogram_bins.Add(
            self.text_input_bin_size, 0, wx.ALL | wx.EXPAND, 5
        )

        label_lookback_distance = wx.StaticText(
            self.parent, wx.ID_ANY, "Avg. Len:"
        )
        sizer_lookback_distance.Add(label_lookback_distance, 0, wx.LEFT, 5)
        sizer_lookback_distance.Add(
            self.text_input_lookback_distance, 0, wx.ALL | wx.EXPAND, 5
        )
        sizer_input.Add(sizer_lookback_distance, 1, wx.EXPAND, 0)

        label_percentile = wx.StaticText(self.parent, wx.ID_ANY, "Percentile:")
        sizer_percentile.Add(label_percentile, 0, wx.LEFT, 5)
        sizer_percentile.Add(
            self.text_inputs_percentile, 0, wx.ALL | wx.EXPAND, 5
        )
        sizer_input.Add(sizer_percentile, 1, wx.EXPAND, 0)
        sizer_input.Add(sizer_histogram_bins, 1, wx.EXPAND, 0)
        sizer_buttons.Add(self.button_update_plot, 0, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_export_csv, 0, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_save_figure, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(sizer_input, 0, wx.ALL | wx.EXPAND, 0)
        sizer_widgets.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_widgets, 0, wx.BOTTOM | wx.EXPAND, 5)

        self.plot = PlotTimeSeries(self.parent, self.options)

        self.layout = sizer_wrapper

    def add_plot_to_layout(self):
        self.plot.init_layout()
        self.sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.layout.Add(self.sizer_plot, 1, wx.EXPAND, 0)
        self.layout.Layout()

    def combo_box_y_axis_ticker(self, evt):
        self.update_plot()

    def update_plot(self):
        data = self.get_plot_data()
        self.plot.update_plot(data)

    def get_plot_data(self, y_axis_selection=None):
        if y_axis_selection is None:
            y_axis_selection = self.combo_box_y_axis.GetValue()
        data = {}
        for grp, stats_data in self.stats_data.items():
            if stats_data:
                y_data = stats_data.data[y_axis_selection]["values"]
                x_data = stats_data.sim_study_dates

                sort_index = sorted(
                    range(len(x_data)), key=lambda k: x_data[k]
                )
                x_values_sorted, y_values_sorted, mrn_sorted, uid_sorted = (
                    [],
                    [],
                    [],
                    [],
                )

                for s in range(len(x_data)):
                    try:
                        x = date_parser(x_data[sort_index[s]])
                    except Exception:
                        continue
                    x_values_sorted.append(x)
                    y_values_sorted.append(y_data[sort_index[s]])
                    mrn_sorted.append(stats_data.mrns[sort_index[s]])
                    uid_sorted.append(stats_data.uids[sort_index[s]])

                data[grp] = {
                    "x": x_values_sorted,
                    "y": y_values_sorted,
                    "mrn": mrn_sorted,
                    "uid": uid_sorted,
                    "y_axis_label": stats_data.get_axis_title(
                        y_axis_selection
                    ),
                    "avg_len": self.avg_len,
                    "percentile": self.percentile,
                    "bin_size": self.hist_bins,
                    "group": [grp] * len(x_values_sorted),
                }
            else:
                data[grp] = {
                    "x": [],
                    "y": [],
                    "mrn": [],
                    "uid": [],
                    "y_axis_label": [],
                    "avg_len": [],
                    "percentile": [],
                    "bin_size": [],
                    "group": [],
                }
        return data

    @property
    def hist_bins(self):
        try:
            hist_bins = int(self.text_input_bin_size.GetValue())
        except ValueError:
            self.text_input_bin_size.SetValue("10")
            hist_bins = 10
        return hist_bins

    @property
    def avg_len(self):
        try:
            avg_len = int(self.text_input_lookback_distance.GetValue())
        except ValueError:
            self.text_input_lookback_distance.SetValue("1")
            avg_len = 1
        return avg_len

    @property
    def percentile(self):
        try:
            percentile = float(self.text_inputs_percentile.GetValue())
        except ValueError:
            self.text_inputs_percentile.SetValue("90")
            percentile = 90.0
        return percentile

    def update_data(self, group_data):
        self.stats_data = {
            grp: data["stats_data"] for grp, data in group_data.items()
        }
        self.initialize_y_axis_options()
        self.update_plot()

    def clear_data(self):
        self.plot.clear_plot()
        self.initialize_y_axis_options()
        self.combo_box_y_axis.SetLabelText("ROI Max Dose")

    def enable_buttons(self):
        self.button_update_plot.Enable()

    def disable_buttons(self):
        self.button_update_plot.Disable()

    def enable_initial_buttons(self):
        self.button_update_plot.Enable()

    def update_plot_ticker(self, evt):
        self.update_plot()

    def update_y_axis_options(self):
        current_choice = self.combo_box_y_axis.GetValue()
        self.combo_box_y_axis.SetItems(self.choices)
        if current_choice not in self.choices:
            current_choice = "ROI Max Dose"
        self.combo_box_y_axis.SetValue(current_choice)

    def initialize_y_axis_options(self):
        self.combo_box_y_axis.SetItems(self.choices)
        self.combo_box_y_axis.SetValue("ROI Max Dose")

    def get_save_data(self):
        return {
            attr: getattr(self, attr).GetValue()
            for attr in self.layout_save_attr
        }

    def load_save_data(self, save_data):
        for attr in list(save_data):
            getattr(self, attr).SetValue(save_data[attr])
        self.update_y_axis_options()

    def get_csv(self, selection=None):
        """
        :param selection: variables to be included
        :type selection: list
        :return: csv data
        :rtype: str
        """

        # get_csv may be called from Time Series tab or DVHA app menu or tool bar
        # if selection is None, get_csv was called from Time Series tab, only export data in plot
        if selection is None:
            return self.plot.get_csv()

        # if selection is not None, export being called from DVHA app menu or tool bar

        csv = []
        for grp in [1, 2]:
            if self.stats_data[grp]:
                uids = self.stats_data[grp].uids
                mrns = self.stats_data[grp].mrns
                dates = self.stats_data[grp].sim_study_dates

                # Collect y-data (as in y-axis data from time series), organize into dict for printing to rows
                y_data = {}
                for y_axis in selection:
                    data = self.get_plot_data(y_axis_selection=y_axis)[grp]
                    column = []
                    for uid in uids:
                        if uid in data["uid"]:
                            index = data["uid"].index(uid)
                            column.append(data["y"][index])
                        else:
                            column.append("None")
                    y_data[y_axis] = column

                if grp == 2:
                    csv.insert(0, "Group 1")
                    csv.append("\nGroup 2")

                # Collect data into a list of row data
                csv.append(
                    "MRN,Study Instance UID,Date,%s" % ",".join(selection)
                )
                for i, uid in enumerate(uids):
                    row = [mrns[i], uid, str(dates[i])]
                    for y_axis in selection:
                        row.append(str(y_data[y_axis][i]))
                    csv.append(",".join(row))

        return "\n".join(csv)

    def export_csv(self, evt):
        save_data_to_file(
            self.parent, "Export Time Series data to CSV", self.plot.get_csv()
        )

    def save_figure(self, *evt):
        title = "Save Time Series Figure"
        export_frame = self.main_app_frame.export_figure
        attr_dicts = None if export_frame is None else export_frame.attr_dicts
        self.plot.save_figure_dlg(self.parent, title, attr_dicts=attr_dicts)

    @property
    def has_data(self):
        return self.button_export_csv.IsEnabled()
