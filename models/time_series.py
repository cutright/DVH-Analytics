#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import wx
from models.plot import PlotTimeSeries
from db import sql_columns
from datetime import datetime
from dateutil import parser


class TimeSeriesFrame:
    def __init__(self, parent, dvh, data, *args, **kwds):
        self.parent = parent
        self.dvh = dvh
        self.data = data

        self.y_axis_options = sql_columns.numerical

        self.combo_box_y_axis = wx.ComboBox(self.parent, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.text_input_bin_size = wx.TextCtrl(self.parent, wx.ID_ANY, "10", style=wx.TE_PROCESS_ENTER)
        self.text_input_lookback_distance = wx.TextCtrl(self.parent, wx.ID_ANY, "1", style=wx.TE_PROCESS_ENTER)
        self.text_inputs_percentile = wx.TextCtrl(self.parent, wx.ID_ANY, "90", style=wx.TE_PROCESS_ENTER)
        self.button_update_plot = wx.Button(self.parent, wx.ID_ANY, "Update Plot")

        self.parent.Bind(wx.EVT_COMBOBOX, self.combo_box_y_axis_ticker, id=self.combo_box_y_axis.GetId())
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.update_plot_ticker, id=self.text_input_bin_size.GetId())
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.update_plot_ticker, id=self.text_input_lookback_distance.GetId())
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.update_plot_ticker, id=self.text_inputs_percentile.GetId())

        self.__set_properties()
        self.__do_layout()

        self.parent.Bind(wx.EVT_BUTTON, self.update_plot_ticker, id=self.button_update_plot.GetId())

        self.disable_buttons()

    def __set_properties(self):
        choices = list(self.y_axis_options)
        choices.sort()
        self.combo_box_y_axis.AppendItems(choices)
        self.combo_box_y_axis.SetLabelText('ROI Max Dose')

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self.parent, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_percentile = wx.BoxSizer(wx.VERTICAL)
        sizer_lookback_distance = wx.BoxSizer(wx.VERTICAL)
        sizer_histogram_bins = wx.BoxSizer(wx.VERTICAL)
        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)
        label_y_axis = wx.StaticText(self.parent, wx.ID_ANY, "Y Axis:")
        sizer_y_axis.Add(label_y_axis, 0, wx.LEFT, 5)
        sizer_y_axis.Add(self.combo_box_y_axis, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(sizer_y_axis, 1, wx.EXPAND, 0)
        label_histogram_bins = wx.StaticText(self.parent, wx.ID_ANY, "Histogram Bins:")
        sizer_histogram_bins.Add(label_histogram_bins, 0, wx.LEFT, 5)
        sizer_histogram_bins.Add(self.text_input_bin_size, 0, wx.ALL | wx.EXPAND, 5)
        label_lookback_distance = wx.StaticText(self.parent, wx.ID_ANY, "Lookback Distance:")
        sizer_lookback_distance.Add(label_lookback_distance, 0, wx.LEFT, 5)
        sizer_lookback_distance.Add(self.text_input_lookback_distance, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(sizer_lookback_distance, 1, wx.EXPAND, 0)
        label_percentile = wx.StaticText(self.parent, wx.ID_ANY, "Percentile:")
        sizer_percentile.Add(label_percentile, 0, wx.LEFT, 5)
        sizer_percentile.Add(self.text_inputs_percentile, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(sizer_percentile, 1, wx.EXPAND, 0)
        sizer_widgets.Add(sizer_histogram_bins, 1, wx.EXPAND, 0)
        sizer_widgets.Add(self.button_update_plot, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_widgets, 0, wx.BOTTOM | wx.EXPAND, 5)
        self.plot = PlotTimeSeries(self.parent)
        sizer_plot.Add(self.plot.layout)
        sizer_wrapper.Add(sizer_plot, 1, wx.EXPAND, 0)
        self.layout = sizer_wrapper

    def combo_box_y_axis_ticker(self, evt):
        if self.dvh and self.data['Plans']:
            self.update_plot()

    def update_plot(self):
        data_info = self.y_axis_options[self.combo_box_y_axis.GetValue()]
        table = data_info['table']
        var_name = data_info['var_name']

        if table == 'DVHs':
            y_data = getattr(self.dvh, var_name)
            uids = getattr(self.dvh, 'study_instance_uid')
            mrn_data = self.dvh.mrn
        else:
            y_data = getattr(self.data[table], var_name)
            uids = getattr(self.data[table], 'study_instance_uid')
            mrn_data = getattr(self.data[table], 'mrn')

        x_data = []
        for uid in uids:
            if uid in self.data['Plans'].study_instance_uid:
                index = self.data['Plans'].study_instance_uid.index(uid)
                x_data.append(self.data['Plans'].sim_study_date[index])
            else:
                x_data.append(datetime.now())

        sort_index = sorted(range(len(x_data)), key=lambda k: x_data[k])
        x_values_sorted, y_values_sorted, mrn_sorted = [], [], []

        for s in range(len(x_data)):
            x_values_sorted.append(parser.parse(x_data[sort_index[s]]))
            y_values_sorted.append(y_data[sort_index[s]])
            mrn_sorted.append(mrn_data[sort_index[s]])

        try:
            hist_bins = int(self.text_input_bin_size.GetValue())
        except ValueError:
            self.text_input_bin_size.SetValue('10')
            hist_bins = 10

        try:
            avg_len = int(self.text_input_lookback_distance.GetValue())
        except ValueError:
            self.text_input_lookback_distance.SetValue('1')
            avg_len = 1

        try:
            percentile = float(self.text_inputs_percentile.GetValue())
        except ValueError:
            self.text_inputs_percentile.SetValue('90')
            percentile = 90.

        self.plot.update_plot(x_values_sorted, y_values_sorted, mrn_sorted,
                              y_axis_label=self.combo_box_y_axis.GetValue(), avg_len=avg_len,
                              percentile=percentile, bin_size=hist_bins)

    def update_data(self, dvh, data):
        self.dvh = dvh
        self.data = data
        self.update_plot()

    def clear_data(self):
        self.plot.update_plot([], [], [], '')

    def enable_buttons(self):
        self.button_update_plot.Enable()

    def disable_buttons(self):
        self.button_update_plot.Disable()

    def enable_initial_buttons(self):
        self.button_update_plot.Enable()

    def update_plot_ticker(self, evt):
        self.update_plot()
