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
from datetime import datetime
from dateutil import parser
from dvha.db import sql_columns
from dvha.dialogs.export import save_data_to_file
from dvha.models.plot import PlotTimeSeries


class TimeSeriesFrame:
    """
    Object to be passed into notebook panel for the Time Series tab
    """
    def __init__(self, parent, dvh, data, options):
        """
        :param parent:  notebook panel in main view
        :type parent: Panel
        :param dvh: dvh data object
        :type dvh: DVH
        :param data: data object containing Plans, Beams, and Rxs data
        :type data: dict
        :param options: user options containing visual preferences
        :type options: Options
        """
        self.parent = parent
        self.options = options
        self.dvh = dvh
        self.data = data
        self.custom_data = {}

        self.y_axis_options = sql_columns.numerical

        self.combo_box_y_axis = wx.ComboBox(self.parent, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.text_input_bin_size = wx.TextCtrl(self.parent, wx.ID_ANY, "10", style=wx.TE_PROCESS_ENTER)
        self.text_input_lookback_distance = wx.TextCtrl(self.parent, wx.ID_ANY, "1", style=wx.TE_PROCESS_ENTER)
        self.text_inputs_percentile = wx.TextCtrl(self.parent, wx.ID_ANY, "90", style=wx.TE_PROCESS_ENTER)
        self.button_update_plot = wx.Button(self.parent, wx.ID_ANY, "Update Plot")
        self.button_export_csv = wx.Button(self.parent, wx.ID_ANY, "Export")

        self.parent.Bind(wx.EVT_COMBOBOX, self.combo_box_y_axis_ticker, id=self.combo_box_y_axis.GetId())
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.update_plot_ticker, id=self.text_input_bin_size.GetId())
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.update_plot_ticker, id=self.text_input_lookback_distance.GetId())
        self.parent.Bind(wx.EVT_TEXT_ENTER, self.update_plot_ticker, id=self.text_inputs_percentile.GetId())

        self.__set_properties()
        self.__do_layout()

        self.parent.Bind(wx.EVT_BUTTON, self.update_plot_ticker, id=self.button_update_plot.GetId())
        self.parent.Bind(wx.EVT_BUTTON, self.export_csv, id=self.button_export_csv.GetId())

        self.disable_buttons()

        self.save_attr = ['combo_box_y_axis', 'text_input_lookback_distance',
                          'text_inputs_percentile', 'text_input_bin_size']

    def __set_properties(self):
        self.choices = list(self.y_axis_options)
        self.choices.sort()
        self.combo_box_y_axis.AppendItems(self.choices)
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
        sizer_widgets.Add(self.button_export_csv, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_widgets, 0, wx.BOTTOM | wx.EXPAND, 5)

        self.plot = PlotTimeSeries(self.parent, self.options)
        sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_plot, 1, wx.EXPAND, 0)

        self.layout = sizer_wrapper

    def combo_box_y_axis_ticker(self, evt):
        if self.dvh and self.data['Plans']:
            self.update_plot()

    def update_plot(self):
        data = self.get_plot_data()
        self.plot.update_plot(**data)

    def get_plot_data(self, y_axis_selection=None):
        if y_axis_selection is None:
            y_axis_selection = self.combo_box_y_axis.GetValue()
        uids = self.dvh.study_instance_uid
        mrn_data = self.dvh.mrn
        if y_axis_selection.split('_')[0] in {'D', 'V'}:
            y_data = self.dvh.endpoints['data'][y_axis_selection]
        elif y_axis_selection in ['EUD', 'NTCP or TCP']:
            y_data = getattr(self.dvh, y_axis_selection.lower().replace(' ', '_'))
        elif y_axis_selection in self.custom_data.keys():
            y_data = self.custom_data[y_axis_selection]['y']
            uids = self.custom_data[y_axis_selection]['uid']
            mrn_data = self.custom_data[y_axis_selection]['mrn']
        else:
            data_info = self.y_axis_options[y_axis_selection]
            table = data_info['table']
            var_name = data_info['var_name']

            if table == 'DVHs':
                y_data = getattr(self.dvh, var_name)
            else:
                y_data = getattr(self.data[table], var_name)
                uids = getattr(self.data[table], 'study_instance_uid')
                mrn_data = getattr(self.data[table], 'mrn')

        x_data = []
        for uid in uids:
            if uid in self.data['Plans'].study_instance_uid:
                index = self.data['Plans'].study_instance_uid.index(uid)
                x = self.data['Plans'].sim_study_date[index]
                if x and x != 'None':
                    x_data.append(x)
                else:
                    x_data.append(str(datetime.now()))
            else:
                x_data.append(str(datetime.now()))

        sort_index = sorted(range(len(x_data)), key=lambda k: x_data[k])
        x_values_sorted, y_values_sorted, mrn_sorted, uid_sorted = [], [], [], []

        for s in range(len(x_data)):
            x_values_sorted.append(parser.parse(x_data[sort_index[s]]))
            y_values_sorted.append(y_data[sort_index[s]])
            mrn_sorted.append(mrn_data[sort_index[s]])
            uid_sorted.append(uids[sort_index[s]])

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

        y_axis = self.combo_box_y_axis.GetValue()
        try:
            units = self.y_axis_options[y_axis]['units']
        except:
            units = ''
        if units:
            y_axis = "%s (%s)" % (y_axis, units)

        return {'x': x_values_sorted,
                'y': y_values_sorted,
                'mrn': mrn_sorted,
                'uid': uid_sorted,
                'y_axis_label': y_axis,
                'avg_len': avg_len,
                'percentile': percentile,
                'bin_size': hist_bins}

    def update_data(self, dvh, data):
        self.dvh = dvh
        self.data = data
        self.update_plot()

    def clear_data(self):
        self.plot.clear_plot()
        self.combo_box_y_axis.SetLabelText('ROI Max Dose')

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
        if self.dvh:
            if self.dvh.endpoints['defs']:
                for choice in self.dvh.endpoints['defs']['label']:
                    if choice not in self.choices:
                        self.choices.append(choice)

                for i in range(len(self.choices))[::-1]:
                    if self.choices[i][0:2] in {'D_', 'V_'}:
                        if self.choices[i] not in self.dvh.endpoints['defs']['label']:
                            self.choices.pop(i)

            if self.dvh.eud and 'EUD' not in self.choices:
                self.choices.append('EUD')
            if self.dvh.ntcp_or_tcp and 'NTCP or TCP' not in self.choices:
                self.choices.append('NTCP or TCP')

            self.choices.sort()

            self.combo_box_y_axis.SetItems(self.choices)
            if current_choice not in self.choices:
                current_choice = 'ROI Max Dose'
            self.combo_box_y_axis.SetValue(current_choice)

    def initialize_y_axis_options(self):
        for i in range(len(self.choices))[::-1]:
            c = self.choices[i]
            if c[0:2] in {'D_', 'V_'} or c in {'EUD', 'NTCP or TCP'} or 'Date' in c:
                self.choices.pop(i)
        self.choices.sort()
        self.combo_box_y_axis.SetItems(self.choices)
        self.combo_box_y_axis.SetValue('ROI Max Dose')

    def get_save_data(self):
        return {attr: getattr(self, attr).GetValue() for attr in self.save_attr}

    def load_save_data(self, save_data):
        for attr in self.save_attr:
            getattr(self, attr).SetValue(save_data[attr])

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

        uids = self.dvh.study_instance_uid
        mrns = self.dvh.mrn
        dates = self.dvh.sim_study_date

        # Collect y-data (as in y-axis data from time series), organize into dict for printing to rows
        y_data = {}
        for y_axis in selection:
            data = self.get_plot_data(y_axis_selection=y_axis)
            column = []
            for uid in uids:
                if uid in data['uid']:
                    index = data['uid'].index(uid)
                    column.append(data['y'][index])
                else:
                    column.append('None')
            y_data[y_axis] = column

        # Collect data into a list of row data
        csv = ['MRN,Study Instance UID,Date,%s' % ','.join(selection)]
        for i, uid in enumerate(uids):
            row = [mrns[i], uid, str(dates[i])]
            for y_axis in selection:
                row.append(str(y_data[y_axis][i]))
            csv.append(','.join(row))

        return '\n'.join(csv)

    def export_csv(self, evt):
        save_data_to_file(self.parent, "Export Time Series data to CSV", self.plot.get_csv())

    @property
    def has_data(self):
        return self.button_export_csv.IsEnabled()

    def add_custom_data(self, option, data):
        self.combo_box_y_axis.AppendItems([option])
        self.custom_data[option] = data
