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
from functools import partial
import matplotlib.colors as plot_colors
from dvha.models.data_table import DataTable
from dvha.paths import DATA_DIR
from dvha.tools.errors import ErrorDialog
from dvha.tools.utilities import get_selected_listctrl_items, save_object_to_file,\
    set_msw_background_color, set_frame_icon


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
    :param initial_dir: start the FileDialog at this directory
    :type initial_dir: str
    """

    with wx.FileDialog(frame, title, defaultDir=initial_dir,  wildcard=wildcard,
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return

        pathname = fileDialog.GetPath()

        if data_type == 'string':
            try:
                with open(pathname, 'w', encoding="utf-8") as file:
                    file.write(data)
            except IOError:
                wx.LogError("Cannot save current data in file '%s'." % pathname)

        elif data_type == 'pickle':
            save_object_to_file(data, pathname)

        elif data_type == 'function':
            data(pathname)


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


class ExportFigure(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent)

        self.parent = parent
        self.options = parent.options
        self.plots = {'DVHs': parent.plot,
                      'Time Series': parent.time_series.plot,
                      'Regression': parent.regression.plot,
                      'Control Chart': parent.control_chart.plot}

        keys_tc = ['y_range_start', 'y_range_end', 'x_range_start', 'plot_height', 'plot_width']
        self.text_ctrl = {key: wx.TextCtrl(self, wx.ID_ANY, str(self.options.save_fig_param[key])) for key in keys_tc}
        self.label = {key: wx.StaticText(self, wx.ID_ANY, key.replace('_', ' ').title() + ':') for key in keys_tc}

        self.keys_cb = ['background_fill_color', 'border_fill_color', 'plot', 'format']
        self.combo_box = {key: wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.TE_READONLY)
                          for key in self.keys_cb}
        for key in self.keys_cb:
            self.label[key] = wx.StaticText(self, wx.ID_ANY, key.replace('_', ' ').title() + ':')

        self.button_keys = ['Export', 'Dismiss']
        self.button = {'Export': wx.Button(self, wx.ID_ANY, 'Export'),
                       'Dismiss': wx.Button(self, wx.ID_CANCEL, 'Dismiss')}

        self.keys = keys_tc + self.keys_cb
        self.fig_attr_keys = keys_tc + ['background_fill_color', 'border_fill_color']

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        set_msw_background_color(self)
        set_frame_icon(self)

    def __set_properties(self):
        self.SetTitle("Export Figure")

        self.combo_box['plot'].SetItems(sorted(list(self.plots)))
        self.combo_box['plot'].SetValue('DVHs')

        self.combo_box['format'].SetItems(['HTML', 'SVG'])
        self.combo_box['format'].SetValue('SVG')

        color_options = ['none'] + list(plot_colors.cnames)
        for key in ['background_fill_color', 'border_fill_color']:
            self.combo_box[key].SetItems(color_options)
            self.combo_box[key].SetValue(self.options.save_fig_param[key])

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_export, id=self.button['Export'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_dismiss, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        for key in self.keys:
            input_obj = self.combo_box[key] if key in self.keys_cb else self.text_ctrl[key]
            sizer_input.Add(self.label[key], 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
            sizer_input.Add(input_obj, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer_main.Add(sizer_input, 0, wx.EXPAND | wx.ALL, 5)

        for key in self.button_keys:
            sizer_buttons.Add(self.button[key], 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 0, wx.EXPAND | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Layout()
        self.Center()

    @property
    def plot(self):
        return self.plots[self.combo_box['plot'].GetValue()]

    @property
    def export_title(self):
        return "Save %s plot as .%s" % (self.combo_box['plot'].GetValue(), self.format.lower())

    @property
    def wildcard(self):
        ext = self.combo_box['format'].GetValue()
        return "%s files (*.%s)|*.%s" % (ext.upper(), ext.lower(), ext.lower())

    @property
    def format(self):
        return self.combo_box['format'].GetValue()

    @property
    def save_plot_function(self):
        return partial(self.plot.save_figure, self.format.lower(), self.fig_attr_dict)

    def on_export(self, *evt):
        try:
            save_data_to_file(self, self.export_title, self.save_plot_function, initial_dir="",
                              data_type='function', wildcard=self.wildcard)
        except Exception as e:
            ErrorDialog(self, str(e), "Save Error")

    def get_text_ctrl_float(self, key):
        value = self.text_ctrl[key].GetValue()
        try:
            return float(value)
        except ValueError:
            return None

    def get_text_ctrl_int(self, key):
        value = self.text_ctrl[key].GetValue()
        try:
            return int(float(value))
        except ValueError:
            return None

    def get_combo_box(self, key):
        return self.combo_box[key].GetValue()

    @property
    def y_range_start(self):
        return self.get_text_ctrl_float('y_range_start')

    @property
    def x_range_start(self):
        return self.get_text_ctrl_float('x_range_start')

    @property
    def y_range_end(self):
        return self.get_text_ctrl_float('y_range_end')

    @property
    def plot_height(self):
        return self.get_text_ctrl_int('plot_height')

    @property
    def plot_width(self):
        return self.get_text_ctrl_int('plot_width')

    @property
    def background_fill_color(self):
        return self.get_combo_box('background_fill_color')

    @property
    def border_fill_color(self):
        return self.get_combo_box('border_fill_color')

    @property
    def fig_attr_dict(self):
        return {key: getattr(self, key) for key in self.fig_attr_keys}

    def on_dismiss(self, *evt):
        wx.CallAfter(self.on_close)

    def on_close(self, *evt):
        self.save_options()
        self.parent.export_figure = None
        self.Destroy()

    def save_options(self):
        self.options.save_fig_param = self.fig_attr_dict
        self.options.save()
