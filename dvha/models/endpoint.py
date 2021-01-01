#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.endpoint.py
"""
Class for the Endpoint frame in the main view
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from copy import deepcopy
from dvha.models.data_table import DataTable
from dvha.dialogs.main import AddEndpointDialog, DelEndpointDialog
from dvha.dialogs.export import save_data_to_file
from dvha.tools.stats import sync_variables_in_stats_data_objects
from dvha.tools.utilities import get_window_size


class EndpointFrame:
    """
    Object to be passed into notebook panel for the Endpoint tab
    """

    def __init__(self, main_app_frame):

        self.main_app_frame = main_app_frame
        self.parent = main_app_frame.notebook_tab["Endpoints"]
        self.group_data = main_app_frame.group_data
        self.time_series = main_app_frame.time_series
        self.regression = main_app_frame.regression
        self.control_chart = main_app_frame.control_chart
        self.group_data = main_app_frame.group_data
        self.initial_columns = ["MRN", "Tx Site", "ROI Name", "Volume (cc)"]
        self.widths = [150, 150, 250, 100]

        self.button = {
            "add": wx.Button(self.parent, wx.ID_ANY, "Add Endpoint"),
            "del": wx.Button(self.parent, wx.ID_ANY, "Delete Endpoint"),
            "exp": wx.Button(self.parent, wx.ID_ANY, "Export"),
        }

        self.table = {
            key: wx.ListCtrl(
                self.parent,
                wx.ID_ANY,
                style=wx.BORDER_SUNKEN
                | wx.LC_HRULES
                | wx.LC_REPORT
                | wx.LC_VRULES,
            )
            for key in [1, 2]
        }
        for table in self.table.values():
            table.SetMinSize(get_window_size(0.623, 0.28))
        self.data_table = {key: DataTable(self.table[key]) for key in [1, 2]}

        self.endpoint_defs = DataTable(
            None,
            columns=[
                "label",
                "output_type",
                "input_type",
                "input_value",
                "units_in",
                "units_out",
            ],
        )

        for key in [1, 2]:
            if self.group_data[key]["dvh"]:
                self.group_data[key]["dvh"].endpoints[
                    "data"
                ] = self.data_table[key].data
                self.group_data[key]["dvh"].endpoints[
                    "defs"
                ] = self.endpoint_defs.data

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()

        self.disable_buttons()

    def __do_bind(self):
        self.parent.Bind(
            wx.EVT_BUTTON,
            self.add_ep_button_click,
            id=self.button["add"].GetId(),
        )
        self.parent.Bind(
            wx.EVT_BUTTON,
            self.del_ep_button_click,
            id=self.button["del"].GetId(),
        )
        self.parent.Bind(
            wx.EVT_BUTTON, self.on_export_csv, id=self.button["exp"].GetId()
        )

    def __set_properties(self):
        for table in self.table.values():
            for i, column in enumerate(self.initial_columns):
                table.AppendColumn(
                    column, format=wx.LIST_FORMAT_LEFT, width=self.widths[i]
                )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        for key in list(self.button):
            hbox.Add(self.button[key], 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 5)
        for grp in [1, 2]:
            vbox.Add(
                wx.StaticText(self.parent, wx.ID_ANY, "Query Group %s:" % grp),
                0,
                wx.EXPAND | wx.BOTTOM,
                5,
            )
            vbox.Add(self.table[grp], 1, wx.EXPAND, 0)
            vbox.Add((10, 10), 0, 0, 0)
        sizer_wrapper.Add(vbox, 1, wx.ALL | wx.EXPAND, 20)
        self.layout = sizer_wrapper

    def calculate_endpoints(self):

        columns = {key: [c for c in self.initial_columns] for key in [1, 2]}
        if self.data_table[1].data:
            current_labels = [
                key
                for key in list(self.data_table[1].data)
                if key not in columns
            ]
        else:
            current_labels = []

        eps = {
            grp: {
                "MRN": group_data["dvh"].mrn,
                "Tx Site": group_data["dvh"].get_plan_values("tx_site"),
                "ROI Name": group_data["dvh"].roi_name,
                "Volume (cc)": group_data["dvh"].volume,
            }
            for grp, group_data in self.group_data.items()
            if group_data["dvh"]
        }

        ep_defs = self.endpoint_defs.data
        for group, ep in eps.items():
            if ep_defs:
                for i, ep_name in enumerate(ep_defs["label"]):

                    if ep_name not in columns[group]:
                        columns[group].append(ep_name)

                        if ep_name in current_labels:
                            ep[ep_name] = deepcopy(
                                self.data_table[group].data[ep_name]
                            )

                        else:
                            endpoint_input = ep_defs["input_type"][i]
                            endpoint_output = ep_defs["output_type"][i]

                            x = float(ep_defs["input_value"][i])
                            if endpoint_input == "relative":
                                x /= 100.0

                            dvh = self.group_data[group]["dvh"]
                            if "V" in ep_name:
                                ep[ep_name] = dvh.get_volume_of_dose(
                                    x,
                                    volume_scale=endpoint_output,
                                    dose_scale=endpoint_input,
                                )
                            else:
                                ep[ep_name] = dvh.get_dose_to_volume(
                                    x,
                                    dose_scale=endpoint_output,
                                    volume_scale=endpoint_input,
                                )

        for group, ep in eps.items():
            self.data_table[group].set_data(ep, columns[group])
            self.data_table[group].set_column_width(0, 150)
            self.data_table[group].set_column_width(1, 150)
            self.data_table[group].set_column_width(2, 200)

    def add_ep_button_click(self, evt):
        # TODO: Track down duplicate table refreshes/calculations
        dlg = AddEndpointDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK and dlg.is_endpoint_valid:
            self.endpoint_defs.append_row(dlg.endpoint_row)
            self.calculate_endpoints()
            self.enable_buttons()
            self.update_endpoints_in_dvh()
        dlg.Destroy()
        self.update_endpoints_and_radbio_in_group_data()
        self.regression.update_combo_box_choices()
        self.control_chart.update_combo_box_y_choices()
        self.time_series.update_y_axis_options()

    def del_ep_button_click(self, evt):
        dlg = DelEndpointDialog(self.data_table[1].columns)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            for value in dlg.selected_values:
                for data_table in self.data_table.values():
                    if data_table.columns and value in data_table.columns:
                        data_table.delete_column(value)
                endpoint_def_row = self.endpoint_defs.data["label"].index(
                    value
                )
                self.update_endpoints_in_dvh()
                self.endpoint_defs.delete_row(endpoint_def_row)
                self.update_endpoints_and_radbio_in_group_data()

            self.time_series.update_y_axis_options()
        dlg.Destroy()

        for group in self.group_data.values():
            if group["stats_data"]:
                group["stats_data"].update_endpoints_and_radbio()
        self.regression.update_combo_box_choices()
        self.control_chart.update_combo_box_y_choices()

        for data_table in self.data_table.values():
            if data_table.column_count == 3:
                self.button["del"].Disable()
                self.button["exp"].Disable()

    def update_dvh(self, group_data):
        self.group_data = group_data
        self.update_endpoints_in_dvh()

    def update_endpoints_and_radbio_in_group_data(self):
        for grp, data in self.group_data.items():
            if data["stats_data"]:
                data["stats_data"].update_endpoints_and_radbio()
                if grp == 2:
                    sync_variables_in_stats_data_objects(
                        self.group_data[1]["stats_data"],
                        self.group_data[2]["stats_data"],
                    )

    def update_endpoints_in_dvh(self):
        for group in [1, 2]:
            if self.group_data[group]["dvh"]:
                self.group_data[group]["dvh"].endpoints[
                    "data"
                ] = self.data_table[group].data
                self.group_data[group]["dvh"].endpoints[
                    "defs"
                ] = self.endpoint_defs.data

    def clear_data(self):
        for data_table in self.data_table.values():
            data_table.delete_all_rows()
        self.endpoint_defs.delete_all_rows(
            force_delete_data=True
        )  # no attached layout, force delete

        for data_table in self.data_table.values():
            if data_table.data:
                for column in list(data_table.data):
                    if column not in self.initial_columns:
                        data_table.delete_column(column)

    def enable_buttons(self):
        for key in list(self.button):
            self.button[key].Enable()

    def disable_buttons(self):
        for key in list(self.button):
            self.button[key].Disable()

    def enable_initial_buttons(self):
        self.button["add"].Enable()

    def get_csv(self, selection=None):
        uid = {
            1: {
                "title": "Study Instance UID",
                "data": self.group_data[1]["dvh"].uid,
            }
        }
        csv = self.data_table[1].get_csv(extra_column_data=uid)
        if self.group_data[2]["dvh"]:
            uid = {
                1: {
                    "title": "Study Instance UID",
                    "data": self.group_data[2]["dvh"].uid,
                }
            }
            csv = "Group 1\n%s\n\nGroup 2\n%s" % (
                csv,
                self.data_table[2].get_csv(extra_column_data=uid),
            )

        return csv

    def on_export_csv(self, evt):
        save_data_to_file(
            self.parent, "Export Endpoints to CSV", self.get_csv()
        )

    def get_save_data(self):
        return {
            "data_table_1": self.data_table[1].get_save_data(),
            "data_table_2": self.data_table[2].get_save_data(),
            "endpoint_defs": self.endpoint_defs.get_save_data(),
        }

    def load_save_data(self, save_data):
        self.data_table[1].load_save_data(
            save_data["data_table_1"], ignore_layout=True
        )
        self.data_table[2].load_save_data(
            save_data["data_table_2"], ignore_layout=True
        )
        self.endpoint_defs.load_save_data(
            save_data["endpoint_defs"], ignore_layout=True
        )
        self.calculate_endpoints()

    @property
    def has_data(self):
        if self.endpoint_defs.data and self.endpoint_defs.data["label"]:
            return True
        return False
