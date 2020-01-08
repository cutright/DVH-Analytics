#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dialogs.export.py
"""
GUI tools to export text data to a file
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
import wx.adv
from dvha.models.data_table import DataTable
from dvha.paths import DATA_DIR
from dvha.tools.utilities import get_selected_listctrl_items, save_object_to_file


def save_data_to_file(frame, title, data, wildcard="CSV files (*.csv)|*.csv", data_type='string', initial_dir=DATA_DIR):
    """
    from https://wxpython.org/Phoenix/docs/html/wx.FileDialog.html
    :param frame: GUI parent
    :param title: title for the file dialog window
    :type title: str
    :param data: text data or pickle-able object to be written
    :param wildcard: restrict visible files and intended file extension
    :type wildcard: str
    :param data_type: either 'string' or 'pickle'
    :type data_type: str
    """

    with wx.FileDialog(frame, title, initial_dir, wildcard=wildcard,
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return

        pathname = fileDialog.GetPath()

        if data_type == 'string':
            try:
                with open(pathname, 'w') as file:
                    file.write(data)
            except IOError:
                wx.LogError("Cannot save current data in file '%s'." % pathname)

        if data_type == 'pickle':
            save_object_to_file(data, pathname)


class ExportCSVDialog(wx.Dialog):
    """
    Allow user to select available data for export to CSV into one file.
    This class leverages the get_csv functions built-into each of the data types / tabs
    """
    def __init__(self, app):
        """
        :param app: easier to pass main frame pointer than several links to each data type
        :type app: DVHAMainFrame
        """
        wx.Dialog.__init__(self, None)

        self.app = app

        # Each of these objects shoudl have a has_data property, if False, those UI elements in this class will
        # be disabled (i.e., don't allow user to export empty tables
        self.enabled = {'DVHs': self.app.group_data[1]['dvh'].has_data,
                        'DVHs Summary': self.app.group_data[1]['dvh'].has_data,
                        'Endpoints': self.app.endpoint.has_data,
                        'Radbio': self.app.radbio.has_data,
                        'Charting Variables': self.app.time_series.has_data}

        checkbox_keys = ['DVHs', 'DVHs Summary', 'Endpoints', 'Radbio', 'Charting Variables']
        self.checkbox = {key: wx.CheckBox(self, wx.ID_ANY, key) for key in checkbox_keys}

        # set to a dictionary because previous versions had a tree with Regression
        self.list_ctrl = {'Charting Variables': wx.ListCtrl(self, wx.ID_ANY,
                                                            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)}

        time_series_column = "Variables"
        time_series_variables = self.app.time_series.combo_box_y_axis.GetItems()
        time_series_data = {time_series_column: time_series_variables}
        self.data_table_time_series = DataTable(self.list_ctrl['Charting Variables'],
                                                columns=[time_series_column], widths=[400])
        self.data_table_time_series.set_data(time_series_data, [time_series_column])

        # set to a dictionary because previous versions had a table with Regression
        self.button_select_data = {'Charting Variables': {'Select': wx.Button(self, wx.ID_ANY, "Select All"),
                                                          'Deselect': wx.Button(self, wx.ID_ANY, "Deselect All")}}

        self.button_save = wx.Button(self, wx.ID_OK, "Save")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_select_all = wx.Button(self, wx.ID_ANY, 'Select All')
        self.button_deselect_all = wx.Button(self, wx.ID_ANY, 'Deselect All')

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Export Data to CSV")
        self.button_select_all.SetToolTip('Only data objects with data will be enabled.')
        self.validate_ui_objects()

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_select_all, id=self.button_select_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_deselect_all, id=self.button_deselect_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_time_series_select_all,
                  id=self.button_select_data['Charting Variables']['Select'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_time_series_deselect_all,
                  id=self.button_select_data['Charting Variables']['Deselect'].GetId())

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_data = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Data Selection"), wx.VERTICAL)
        sizer_time_series = wx.BoxSizer(wx.VERTICAL)
        sizer_time_series_listctrl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time_series_checkboxes = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time_series_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_radbio = wx.BoxSizer(wx.VERTICAL)
        sizer_endpoints = wx.BoxSizer(wx.VERTICAL)
        sizer_dvhs = wx.BoxSizer(wx.VERTICAL)
        sizer_dvhs_checkboxes = wx.BoxSizer(wx.HORIZONTAL)

        keys = ['DVHs', 'Endpoints', 'Radbio']
        static_line = {key: wx.StaticLine(self, wx.ID_ANY) for key in keys}

        sizer_dvhs_checkboxes.Add(self.checkbox['DVHs'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_dvhs_checkboxes.Add(self.checkbox['DVHs Summary'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_dvhs.Add(sizer_dvhs_checkboxes, 1, wx.EXPAND, 0)
        sizer_dvhs.Add(static_line['DVHs'], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_dvhs, 0, wx.ALL | wx.EXPAND, 5)

        sizer_endpoints.Add(self.checkbox['Endpoints'], 0, wx.ALL, 5)
        sizer_endpoints.Add(static_line['Endpoints'], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_endpoints, 0, wx.ALL | wx.EXPAND, 5)

        sizer_radbio.Add(self.checkbox['Radbio'], 0, wx.ALL, 5)
        sizer_radbio.Add(static_line['Radbio'], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_radbio, 0, wx.ALL | wx.EXPAND, 5)

        sizer_time_series_checkboxes.Add(self.checkbox['Charting Variables'], 1, wx.EXPAND, 0)
        sizer_time_series_buttons.Add(self.button_select_data['Charting Variables']['Select'],
                                      0, wx.ALL | wx.EXPAND, 5)
        sizer_time_series_buttons.Add(self.button_select_data['Charting Variables']['Deselect'],
                                      0, wx.ALL | wx.EXPAND, 5)
        sizer_time_series_checkboxes.Add(sizer_time_series_buttons, 1, wx.EXPAND, 0)
        sizer_time_series.Add(sizer_time_series_checkboxes, 0, wx.ALL | wx.EXPAND, 5)
        sizer_time_series_listctrl.Add((20, 20), 0, 0, 0)
        sizer_time_series_listctrl.Add(self.list_ctrl['Charting Variables'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_time_series.Add(sizer_time_series_listctrl, 0, wx.ALL | wx.EXPAND, 5)
        sizer_data.Add(sizer_time_series, 0, wx.ALL | wx.EXPAND, 5)

        sizer_main.Add(sizer_data, 0, wx.ALL | wx.EXPAND, 5)

        sizer_main_buttons.Add(self.button_select_all, 0, wx.ALL, 5)
        sizer_main_buttons.Add(self.button_deselect_all, 0, wx.ALL, 5)

        sizer_main_buttons.Add(self.button_save, 0, wx.ALL, 5)
        sizer_main_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_main.Add(sizer_main_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def set_checkbox_values(self, value):
        for checkbox in self.checkbox.values():
            checkbox.SetValue(value)

    def on_select_all(self, evt):
        self.set_checkbox_values(True)
        self.validate_ui_objects(allow_enable=False)

    def on_deselect_all(self, evt):
        self.set_checkbox_values(False)
        self.validate_ui_objects(allow_enable=False)

    def on_time_series_select_all(self, evt):
        self.data_table_time_series.apply_selection_to_all(1)

    def on_time_series_deselect_all(self, evt):
        self.data_table_time_series.apply_selection_to_all(0)

    def validate_ui_objects(self, allow_enable=True):
        tables = {'Charting Variables': self.data_table_time_series}
        for key, data_table in tables.items():
            state = data_table.has_data
            if not state or (state and allow_enable):
                self.list_ctrl[key].Enable(state)
                self.button_select_data[key]['Select'].Enable(state)
                self.button_select_data[key]['Deselect'].Enable(state)

        for key, value in self.enabled.items():
            if not value or (value and allow_enable):
                self.checkbox[key].SetValue(value)
                self.checkbox[key].Enable(value)

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            save_data_to_file(self, 'Export CSV Data', self.csv)
        self.Destroy()

    def is_checked(self, key):
        return self.checkbox[key].GetValue()

    def on_dvh_check(self, evt):
        if not self.is_checked('DVHs'):
            self.checkbox['DVHs Summary'].SetValue(False)

    @property
    def csv(self):
        csv_data = []

        csv_key = ['DVHs', 'Endpoints', 'Radbio', 'Charting Variables']
        csv_obj = [None, self.app.endpoint, self.app.radbio, self.app.time_series, self.app.control_chart]
        for i, key in enumerate(csv_key):
            if self.is_checked(key) or (key == 'DVHs' and self.is_checked('DVHs Summary')):
                csv_data.append('%s\n' % key)
                if key == 'DVHs':  # DVHs has a summary and plot data for export
                    csv_data.append(self.app.plot.get_csv(include_summary=self.is_checked('DVHs Summary'),
                                                          include_dvhs=self.is_checked('DVHs')))
                else:
                    if key == 'Charting Variables':
                        selection_indices = get_selected_listctrl_items(self.list_ctrl['Charting Variables'])
                        y_choices = self.app.time_series.combo_box_y_axis.GetItems()
                        selection = [y for i, y in enumerate(y_choices) if i in selection_indices]
                    else:
                        selection = None
                    csv_data.append(csv_obj[i].get_csv(selection=selection))
                csv_data.append('\n\n')

        return '\n'.join(csv_data)
