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
from pubsub import pub
from dvha.db.sql_connector import DVH_SQL
from dvha.models.data_table import DataTable
from dvha.paths import DATA_DIR
from dvha.tools.threading_progress import ProgressFrame
from dvha.tools.utilities import (
    get_selected_listctrl_items,
    save_object_to_file,
    set_msw_background_color,
    set_frame_icon,
)


def save_data_to_file(
    frame,
    title,
    data,
    wildcard="CSV files (*.csv)|*.csv",
    data_type="string",
    initial_dir=DATA_DIR,
):
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

    with wx.FileDialog(
        frame,
        title,
        defaultDir=initial_dir,
        wildcard=wildcard,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as fileDialog:

        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return

        pathname = fileDialog.GetPath()

        if data_type == "string":
            try:
                with open(pathname, "w", encoding="utf-8") as file:
                    file.write(data)
            except IOError:
                wx.LogError(
                    "Cannot save current data in file '%s'." % pathname
                )

        elif data_type == "pickle":
            save_object_to_file(data, pathname)

        elif data_type == "function":
            data(pathname)

        return pathname


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
        self.enabled = {
            "DVHs": self.app.group_data[1]["dvh"].has_data,
            "DVHs Summary": self.app.group_data[1]["dvh"].has_data,
            "Endpoints": self.app.endpoint.has_data,
            "Radbio": self.app.radbio.has_data,
            "Charting Variables": self.app.time_series.has_data,
        }

        checkbox_keys = [
            "DVHs",
            "DVHs Summary",
            "Endpoints",
            "Radbio",
            "Charting Variables",
        ]
        self.checkbox = {
            key: wx.CheckBox(self, wx.ID_ANY, key) for key in checkbox_keys
        }

        # set to a dictionary because previous versions had a tree with Regression
        self.list_ctrl = {
            "Charting Variables": wx.ListCtrl(
                self,
                wx.ID_ANY,
                style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES,
            )
        }

        time_series_column = "Variables"
        time_series_variables = (
            self.app.time_series.combo_box_y_axis.GetItems()
        )
        time_series_data = {time_series_column: time_series_variables}
        self.data_table_time_series = DataTable(
            self.list_ctrl["Charting Variables"],
            columns=[time_series_column],
            widths=[400],
        )
        self.data_table_time_series.set_data(
            time_series_data, [time_series_column]
        )

        # set to a dictionary because previous versions had a table with Regression
        self.button_select_data = {
            "Charting Variables": {
                "Select": wx.Button(self, wx.ID_ANY, "Select All"),
                "Deselect": wx.Button(self, wx.ID_ANY, "Deselect All"),
            }
        }

        self.button_save = wx.Button(self, wx.ID_OK, "Save")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_select_all = wx.Button(self, wx.ID_ANY, "Select All")
        self.button_deselect_all = wx.Button(self, wx.ID_ANY, "Deselect All")

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Export Data to CSV")
        self.button_select_all.SetToolTip(
            "Only data objects with data will be enabled."
        )
        self.validate_ui_objects()

    def __do_bind(self):
        self.Bind(
            wx.EVT_BUTTON,
            self.on_select_all,
            id=self.button_select_all.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_deselect_all,
            id=self.button_deselect_all.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_time_series_select_all,
            id=self.button_select_data["Charting Variables"]["Select"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_time_series_deselect_all,
            id=self.button_select_data["Charting Variables"][
                "Deselect"
            ].GetId(),
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_data = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Data Selection"), wx.VERTICAL
        )
        sizer_time_series = wx.BoxSizer(wx.VERTICAL)
        sizer_time_series_listctrl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time_series_checkboxes = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time_series_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_radbio = wx.BoxSizer(wx.VERTICAL)
        sizer_endpoints = wx.BoxSizer(wx.VERTICAL)
        sizer_dvhs = wx.BoxSizer(wx.VERTICAL)
        sizer_dvhs_checkboxes = wx.BoxSizer(wx.HORIZONTAL)

        keys = ["DVHs", "Endpoints", "Radbio"]
        static_line = {key: wx.StaticLine(self, wx.ID_ANY) for key in keys}

        sizer_dvhs_checkboxes.Add(
            self.checkbox["DVHs"], 1, wx.ALL | wx.EXPAND, 5
        )
        sizer_dvhs_checkboxes.Add(
            self.checkbox["DVHs Summary"], 1, wx.ALL | wx.EXPAND, 5
        )
        sizer_dvhs.Add(sizer_dvhs_checkboxes, 1, wx.EXPAND, 0)
        sizer_dvhs.Add(static_line["DVHs"], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_dvhs, 0, wx.ALL | wx.EXPAND, 5)

        sizer_endpoints.Add(self.checkbox["Endpoints"], 0, wx.ALL, 5)
        sizer_endpoints.Add(static_line["Endpoints"], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_endpoints, 0, wx.ALL | wx.EXPAND, 5)

        sizer_radbio.Add(self.checkbox["Radbio"], 0, wx.ALL, 5)
        sizer_radbio.Add(static_line["Radbio"], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_radbio, 0, wx.ALL | wx.EXPAND, 5)

        sizer_time_series_checkboxes.Add(
            self.checkbox["Charting Variables"], 1, wx.EXPAND, 0
        )
        sizer_time_series_buttons.Add(
            self.button_select_data["Charting Variables"]["Select"],
            0,
            wx.ALL | wx.EXPAND,
            5,
        )
        sizer_time_series_buttons.Add(
            self.button_select_data["Charting Variables"]["Deselect"],
            0,
            wx.ALL | wx.EXPAND,
            5,
        )
        sizer_time_series_checkboxes.Add(
            sizer_time_series_buttons, 1, wx.EXPAND, 0
        )
        sizer_time_series.Add(
            sizer_time_series_checkboxes, 0, wx.ALL | wx.EXPAND, 5
        )
        sizer_time_series_listctrl.Add((20, 20), 0, 0, 0)
        sizer_time_series_listctrl.Add(
            self.list_ctrl["Charting Variables"], 1, wx.ALL | wx.EXPAND, 5
        )
        sizer_time_series.Add(
            sizer_time_series_listctrl, 0, wx.ALL | wx.EXPAND, 5
        )
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
        tables = {"Charting Variables": self.data_table_time_series}
        for key, data_table in tables.items():
            state = data_table.has_data
            if not state or (state and allow_enable):
                self.list_ctrl[key].Enable(state)
                self.button_select_data[key]["Select"].Enable(state)
                self.button_select_data[key]["Deselect"].Enable(state)

        for key, value in self.enabled.items():
            if not value or (value and allow_enable):
                self.checkbox[key].SetValue(value)
                self.checkbox[key].Enable(value)

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            save_data_to_file(self, "Export CSV Data", self.csv)
        self.Destroy()

    def is_checked(self, key):
        return self.checkbox[key].GetValue()

    def on_dvh_check(self, evt):
        if not self.is_checked("DVHs"):
            self.checkbox["DVHs Summary"].SetValue(False)

    @property
    def csv(self):
        csv_data = []

        csv_key = ["DVHs", "Endpoints", "Radbio", "Charting Variables"]
        csv_obj = [
            None,
            self.app.endpoint,
            self.app.radbio,
            self.app.time_series,
            self.app.control_chart,
        ]
        for i, key in enumerate(csv_key):
            if self.is_checked(key) or (
                key == "DVHs" and self.is_checked("DVHs Summary")
            ):
                csv_data.append("%s\n" % key)
                if (
                    key == "DVHs"
                ):  # DVHs has a summary and plot data for export
                    csv_data.append(
                        self.app.plot.get_csv(
                            include_summary=self.is_checked("DVHs Summary"),
                            include_dvhs=self.is_checked("DVHs"),
                        )
                    )
                else:
                    if key == "Charting Variables":
                        selection_indices = get_selected_listctrl_items(
                            self.list_ctrl["Charting Variables"]
                        )
                        y_choices = (
                            self.app.time_series.combo_box_y_axis.GetItems()
                        )
                        selection = [
                            y
                            for i, y in enumerate(y_choices)
                            if i in selection_indices
                        ]
                    else:
                        selection = None
                    csv_data.append(csv_obj[i].get_csv(selection=selection))
                csv_data.append("\n\n")

        return "\n".join(csv_data)


class ExportFigure(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(
            self, parent, style=wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.CAPTION
        )

        self.parent = parent
        self.options = parent.options
        self.plots = {
            "DVHs": parent.plot,
            "Time Series": parent.time_series.plot,
            "Regression": parent.regression.plot,
            "Control Chart": parent.control_chart.plot,
        }

        button_keys = {"Export": wx.ID_ANY, "Dismiss": wx.ID_CANCEL}
        self.button = {
            key: wx.Button(self, button_id, key)
            for key, button_id in button_keys.items()
        }

        self.__set_input_widgets()
        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.getter = {
            int: self.get_text_ctrl_int,
            float: self.get_text_ctrl_float,
            str: self.get_combo_box,
        }

        set_msw_background_color(self)
        set_frame_icon(self)

    def __set_input_widgets(self):
        self.input = {key: [] for key in self.options.save_fig_param.keys()}
        self.label = {key: [] for key in self.options.save_fig_param.keys()}
        self.text_ctrl = {}
        self.combo_box = {}
        for obj_type, attr_dict in self.options.save_fig_param.items():
            for attr, value in attr_dict.items():
                self.label[obj_type].append(
                    wx.StaticText(
                        self, wx.ID_ANY, attr.replace("_", " ").title() + ":"
                    )
                )
                if type(value) is str:
                    color_options = ["none"] + list(plot_colors.cnames)
                    self.input[obj_type].append(
                        wx.ComboBox(
                            self,
                            wx.ID_ANY,
                            choices=color_options,
                            style=wx.CB_DROPDOWN | wx.TE_READONLY,
                        )
                    )
                    self.input[obj_type][-1].SetValue(value)
                    self.combo_box[obj_type + "_" + attr] = self.input[
                        obj_type
                    ][-1]
                else:
                    if "alpha" in attr:
                        self.input[obj_type].append(
                            wx.SpinCtrlDouble(
                                self,
                                wx.ID_ANY,
                                "0",
                                min=0,
                                max=1,
                                inc=0.1,
                                style=wx.SP_ARROW_KEYS,
                            )
                        )
                        self.input[obj_type][-1].SetIncrement(0.1)
                        self.input[obj_type][-1].SetValue(str(value))
                    elif "width" in attr and obj_type == "legend":
                        self.input[obj_type].append(
                            wx.SpinCtrl(
                                self,
                                wx.ID_ANY,
                                "0",
                                min=0,
                                max=20,
                                style=wx.SP_ARROW_KEYS,
                            )
                        )
                        self.input[obj_type][-1].SetValue(str(value))
                    else:
                        self.input[obj_type].append(
                            wx.TextCtrl(self, wx.ID_ANY, str(value))
                        )
                    self.text_ctrl[obj_type + "_" + attr] = self.input[
                        obj_type
                    ][-1]

        self.label_plot = wx.StaticText(self, wx.ID_ANY, "Plot:")
        self.combo_plot = wx.ComboBox(
            self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.TE_READONLY
        )

        self.include_range = wx.CheckBox(self, wx.ID_ANY, "Apply Range Edits")

    def __set_properties(self):
        self.SetTitle("Export Figure")

        self.combo_plot.SetItems(sorted(list(self.plots)))
        self.combo_plot.SetValue("DVHs")

        range_init = (
            self.options.apply_range_edits
            if hasattr(self.options, "apply_range_edits")
            else False
        )
        self.include_range.SetValue(range_init)
        self.include_range.SetToolTip(
            "Check this to alter the ranges from the current view. Leave a range field blank "
            "to use the current view's value.\n"
            "NOTE: These range edits do not apply to Machine Learning plot saves."
        )
        self.on_checkbox()  # Disable Range input objects by default

    def __do_bind(self):
        self.Bind(
            wx.EVT_BUTTON, self.on_export, id=self.button["Export"].GetId()
        )
        self.Bind(wx.EVT_BUTTON, self.on_dismiss, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_checkbox, id=self.include_range.GetId()
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_input = {
            key: wx.StaticBoxSizer(
                wx.StaticBox(self, wx.ID_ANY, key.capitalize()), wx.VERTICAL
            )
            for key in ["figure", "legend"]
        }
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        sizer_input["figure"].Add(self.include_range, 0, 0, 0)

        for obj_type in ["figure", "legend"]:
            for i, input_obj in enumerate(self.input[obj_type]):
                sizer_input[obj_type].Add(
                    self.label[obj_type][i],
                    0,
                    wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
                    3,
                )
                sizer_input[obj_type].Add(
                    input_obj, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 3
                )
            sizer_main.Add(sizer_input[obj_type], 0, wx.EXPAND | wx.ALL, 5)

        sizer_main.Add(self.label_plot, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer_main.Add(self.combo_plot, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        sizer_buttons.Add(
            self.button["Export"], 1, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, 5
        )
        sizer_buttons.Add(
            self.button["Dismiss"], 1, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, 5
        )
        sizer_main.Add(
            sizer_buttons, 1, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, 5
        )

        sizer_wrapper.Add(sizer_main, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.SetMinSize(self.GetSize())
        self.SetMaxSize(self.GetSize())
        self.Layout()

        self.options.apply_window_position(self, "export_figure")

    @property
    def plot(self):
        return self.plots[self.combo_plot.GetValue()]

    @property
    def save_plot_function(self):
        return partial(self.plot.save_figure, self.attr_dicts)

    def on_export(self, *evt):
        self.validate_input()
        self.plot.save_figure_dlg(
            self,
            "Save %s Figure" % self.combo_plot.GetValue(),
            attr_dicts=self.attr_dicts,
        )

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

    def get_attr_dict(self, obj_type, save_mode=False):
        return {
            key: self.getter[type(value)](obj_type + "_" + key)
            for key, value in self.options.save_fig_param[obj_type].items()
            if save_mode
            or (
                "range" not in key
                or ("range" in key and self.include_range.GetValue())
            )
        }

    @property
    def attr_dicts(self):
        return {key: self.get_attr_dict(key) for key in self.input.keys()}

    @property
    def save_attr_dicts(self):
        return {
            key: self.get_attr_dict(key, save_mode=True)
            for key in self.input.keys()
            if self.get_attr_dict(key, save_mode=True) is not None
        }

    def on_dismiss(self, *evt):
        wx.CallAfter(self.on_close)

    def on_close(self, *evt):
        self.validate_input()
        self.options.save_window_position(self, "export_figure")
        self.save_options()
        self.parent.export_figure = None
        self.Destroy()

    def save_options(self):
        self.options.save_fig_param = self.save_attr_dicts
        self.options.apply_range_edits = self.include_range.GetValue()
        self.options.save()

    def on_checkbox(self, *evt):
        for i, obj in enumerate(self.input["figure"]):
            if "Range" in self.label["figure"][i].GetLabel():
                self.label["figure"][i].Enable(self.include_range.GetValue())
                obj.Enable(self.include_range.GetValue())

    def validate_input(self):
        """If any TextCtrl is invalid, set to stored options"""
        for key, obj in self.text_ctrl.items():
            if obj.GetValue() == "":
                obj_type, attr = key[: key.find("_")], key[key.find("_") + 1 :]
                stored_value = self.options.save_fig_param[obj_type][attr]
                new_value = self.getter[type(stored_value)](key)
                if new_value is None:
                    obj.SetValue(str(stored_value))


class ExportPGSQLProgressFrame(ProgressFrame):
    """Create a window to display value generation progress and begin SaveWorker"""

    def __init__(self, file_path, export_to_json=False):
        func_call = self.func_call_json if export_to_json else self.func_call
        ProgressFrame.__init__(
            self, [file_path], func_call, title="Exporting PGSQL DB to SQLite"
        )

    def func_call(self, file_path):
        with DVH_SQL() as cnx:
            cnx.export_to_sqlite(file_path, callback=self.callback)

    def func_call_json(self, file_path):
        with DVH_SQL() as cnx:
            cnx.save_to_json(file_path, callback=self.callback)

    @staticmethod
    def callback(table, iteration, total_count):
        msg = {
            "label": "Exporting Table: %s (%s of %s)"
            % (table, iteration + 1, total_count),
            "gauge": (float(iteration) / total_count),
        }
        wx.CallAfter(pub.sendMessage, "progress_update", msg=msg)
