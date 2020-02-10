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
    def __init__(self, parent, group_data, options):
        """
        :param parent:  notebook panel in main view
        :type parent: Panel
        :param group_data: dvh, table, and stats data
        :type group_data: dict
        :param options: user options containing visual preferences
        :type options: Options
        """
        self.parent = parent
        self.group_data = group_data
        self.choices = []
        self.models = {grp: {} for grp in [1, 2]}

        self.group = 1

        self.y_axis_options = sql_columns.numerical

        self.combo_box_y_axis = wx.ComboBox(self.parent, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)

        self.button_export = wx.Button(self.parent, wx.ID_ANY, "Export")
        self.button_save_plot = wx.Button(self.parent, wx.ID_ANY, "Save Plot")
        self.plot = PlotControlChart(self.parent, options)

        self.__do_bind()
        self.__set_properties()
        self.__do_subscribe()
        self.__do_layout()

    def __do_bind(self):
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box_y, id=self.combo_box_y_axis.GetId())
        self.parent.Bind(wx.EVT_BUTTON, self.on_save_plot, id=self.button_save_plot.GetId())
        self.parent.Bind(wx.EVT_BUTTON, self.export_csv, id=self.button_export.GetId())

    def __set_properties(self):
        self.combo_box_y_axis.SetMinSize((300, self.combo_box_y_axis.GetSize()[1]))

    def __do_subscribe(self):
        pub.subscribe(self.set_model, "control_chart_set_model")

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self.parent, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)

        label_y_axis = wx.StaticText(self.parent, wx.ID_ANY, "Charting Variable:")
        sizer_y_axis.Add(label_y_axis, 0, wx.LEFT, 5)
        sizer_y_axis.Add(self.combo_box_y_axis, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(sizer_y_axis, 0, wx.EXPAND, 0)

        sizer_widgets.Add(self.button_export, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(self.button_save_plot, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_widgets, 0, wx.EXPAND | wx.BOTTOM, 5)
        sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_plot, 1, wx.EXPAND, 0)

        self.layout = sizer_wrapper

    def update_combo_box_y_choices(self):
        stats_data = self.group_data[self.group]['stats_data']
        if stats_data:
            self.choices = stats_data.trending_variables
            self.choices.sort()
            self.combo_box_y_axis.SetItems(self.choices)
            self.combo_box_y_axis.SetValue('ROI Max Dose')

    @property
    def y_axis(self):
        return self.combo_box_y_axis.GetValue()

    def on_combo_box_y(self, evt):
        self.update_plot()

    def update_plot_ticker(self, evt):
        self.update_plot()

    def update_plot(self):
        stats_data = self.group_data[self.group]['stats_data']
        dates = stats_data.sim_study_dates
        sort_index = sorted(range(len(dates)), key=lambda k: dates[k])
        dates_sorted = [dates[i] for i in sort_index]

        y_values_sorted = [stats_data.data[self.y_axis]['values'][i] for i in sort_index]
        mrn_sorted = [stats_data.mrns[i] for i in sort_index]
        uid_sorted = [stats_data.uids[i] for i in sort_index]

        # remove data with no date
        if 'None' in dates_sorted:
            final_index = dates_sorted.index('None')
            dates_sorted = dates_sorted[:final_index]
            y_values_sorted = y_values_sorted[:final_index]
            mrn_sorted = mrn_sorted[:final_index]
            uid_sorted = uid_sorted[:final_index]

        x = list(range(1, len(dates_sorted)+1))

        self.plot.group = self.group
        self.plot.update_plot(x, y_values_sorted, mrn_sorted, uid_sorted, dates_sorted, y_axis_label=self.y_axis)

        if self.models[self.group] and self.y_axis in self.models[self.group].keys():
            model_data = self.models[self.group][self.y_axis]
            adj_data = self.plot.get_adjusted_control_chart(stats_data=stats_data, **model_data)
            self.plot.update_adjusted_control_chart(**adj_data)

    def update_data(self, group_data):
        self.group_data = group_data
        self.update_combo_box_y_choices()
        self.update_plot()

    @property
    def variables(self):
        stats_data = self.group_data[self.group]['stats_data']
        return list(stats_data)

    # def update_endpoints_and_radbio(self):
    #     if self.dvhs:
    #         if self.dvhs.endpoints['defs']:
    #             for var in self.dvhs.endpoints['defs']['label']:
    #                 if var not in self.variables:
    #                     self.stats_data[var] = {'units': '',
    #                                             'values': self.dvhs.endpoints['data'][var]}
    #
    #             for var in self.variables:
    #                 if var[0:2] in {'D_', 'V_'}:
    #                     if var not in self.dvhs.endpoints['defs']['label']:
    #                         self.stats_data.pop(var)
    #
    #         if self.dvhs.eud:
    #             self.stats_data['EUD'] = {'units': 'Gy',
    #                                       'values': self.dvhs.eud}
    #         if self.dvhs.ntcp_or_tcp:
    #             self.stats_data['NTCP or TCP'] = {'units': '',
    #                                               'values': self.dvhs.ntcp_or_tcp}

    def initialize_y_axis_options(self):
        for i in range(len(self.choices))[::-1]:
            c = self.choices[i]
            if c[0:2] in {'D_', 'V_'} or c in {'EUD', 'NTCP or TCP'}:
                self.choices.pop(i)
        self.choices.sort()
        self.combo_box_y_axis.SetItems(self.choices)
        self.combo_box_y_axis.SetValue('ROI Max Dose')

    def clear_data(self):
        self.initialize_y_axis_options()

    def get_csv(self, selection=None):
        return self.plot.get_csv()

    def export_csv(self, evt):
        save_data_to_file(self.parent, "Export control chart data to CSV", self.plot.get_csv())

    def on_save_plot(self, evt):
        save_data_to_file(self.parent, 'Save control chart', self.plot.html_str,
                          wildcard="HTML files (*.html)|*.html")

    @property
    def has_data(self):
        return self.combo_box_y_axis.IsEnabled()

    def set_model(self, y_variable, x_variables, regression, group):
        self.models[group][y_variable] = {'y_variable': y_variable,
                                          'x_variables': x_variables,
                                          'regression': regression}
        if self.y_axis == y_variable:
            wx.CallAfter(self.update_plot)

    def delete_model(self, y_variable):
        if y_variable in list(self.models):
            self.models.pop(y_variable)

    def get_save_data(self):
        return {'models': self.models}

    def load_save_data(self, saved_data):
        self.models = deepcopy(saved_data['models'])
