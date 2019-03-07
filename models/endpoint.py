#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import wx
from models.datatable import DataTable
from dialogs.endpoint import EndpointDialog
from copy import deepcopy


ENDPOINT_DEF_COLUMNS = ['label', 'output_type', 'input_type', 'input_value', 'units_in', 'units_out']


class EndpointFrame:
    def __init__(self, parent, dvh, *args, **kwds):

        self.parent = parent
        self.dvh = dvh

        self.button_add = wx.Button(self.parent, wx.ID_ANY, "Add Endpoint")
        self.button_del = wx.Button(self.parent, wx.ID_ANY, "Delete Endpoint")
        self.button_edit = wx.Button(self.parent, wx.ID_ANY, "Edit Endpoint")

        self.parent.Bind(wx.EVT_BUTTON, self.add_ep_button_click, id=self.button_add.GetId())

        self.table = wx.ListCtrl(self.parent, wx.ID_ANY,
                                 style=wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.table.SetMinSize((1046, 800))
        self.data_table = DataTable(self.table, columns=['mrn', 'roi_name', 'ep1'])

        self.endpoint_defs = DataTable(None, columns=ENDPOINT_DEF_COLUMNS)

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.table.AppendColumn("MRN", format=wx.LIST_FORMAT_LEFT, width=150)
        self.table.AppendColumn("ROI Name", format=wx.LIST_FORMAT_LEFT, width=250)
        self.table.AppendColumn("EP1", format=wx.LIST_FORMAT_LEFT, width=-1)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.button_add, 0, wx.ALL, 5)
        hbox.Add(self.button_del, 0, wx.ALL, 5)
        hbox.Add(self.button_edit, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 5)
        vbox.Add(self.table, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(vbox, 1, wx.ALL | wx.EXPAND, 20)
        self.layout = sizer_wrapper

    @property
    def ep_count(self):
        return len(self.endpoint_defs['label'])

    def calculate_endpoints(self):

        columns = ['mrn', 'roi_name']
        if self.data_table.data:
            current_labels = [key for key in list(self.data_table.data) if key not in columns]
        else:
            current_labels = []

        ep = {'mrn': self.dvh.mrn,
              'roi_name': self.dvh.roi_name}

        ep_defs = self.endpoint_defs.data
        for i, ep_name in enumerate(ep_defs['label']):

            if ep_name not in columns:
                columns.append(ep_name)

                if ep_name in current_labels:
                    ep[ep_name] = deepcopy(self.data_table.data[ep_name])

                else:
                    endpoint_input = ['absolute', 'relative']['%' in ep_defs['units_in'][i]]
                    endpoint_output = ['absolute', 'relative']['%' in ep_defs['units_out'][i]]

                    x = float(ep_defs['input_value'][i])
                    if endpoint_input == 'relative':
                        x /= 100.

                    if 'V' in ep_name:
                        ep[ep_name] = self.dvh.get_volume_of_dose(x, volume_scale=endpoint_input,
                                                                  dose_scale=endpoint_output)

                    else:
                        ep[ep_name] = self.dvh.get_dose_to_volume(x, dose_scale=endpoint_input,
                                                                  volume_scale=endpoint_output)

        self.data_table.set_data(ep, columns)
        self.data_table.set_column_width(0, 150)
        self.data_table.set_column_width(1, 250)

    def add_ep_button_click(self, evt):
        dlg = EndpointDialog(title='Add Endpoint')
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            if dlg.is_endpoint_valid:
                self.endpoint_defs.append_row(dlg.endpoint_row)
                self.calculate_endpoints()
        dlg.Destroy()

    def update_dvh(self, dvh):
        self.dvh = dvh

    def clear_data(self):
        self.data_table.delete_all_rows()
        self.endpoint_defs.delete_all_rows()
