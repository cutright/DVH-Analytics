#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import wx


class EndpointFrame:
    def __init__(self, parent, *args, **kwds):
        self.button_add = wx.Button(parent, wx.ID_ANY, "Add Endpoint")
        self.button_del = wx.Button(parent, wx.ID_ANY, "Delete Endpoint")
        self.button_edit = wx.Button(parent, wx.ID_ANY, "Edit Endpoint")
        self.table_endpoint = wx.ListCtrl(parent, wx.ID_ANY,
                                          style=wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.table_endpoint.SetMinSize((1046, 800))

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        # self.SetTitle("frame")
        self.table_endpoint.AppendColumn("MRN", format=wx.LIST_FORMAT_LEFT, width=150)
        self.table_endpoint.AppendColumn("ROI Name", format=wx.LIST_FORMAT_LEFT, width=250)
        self.table_endpoint.AppendColumn("EP1", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_endpoint.AppendColumn("EP2", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_endpoint.AppendColumn("EP3", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_endpoint.AppendColumn("EP4", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_endpoint.AppendColumn("EP5", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_endpoint.AppendColumn("EP6", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_endpoint.AppendColumn("EP7", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_endpoint.AppendColumn("EP8", format=wx.LIST_FORMAT_LEFT, width=-1)

    def __do_layout(self):
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6.Add(self.button_add, 0, wx.ALL, 5)
        sizer_6.Add(self.button_del, 0, wx.ALL, 5)
        sizer_6.Add(self.button_edit, 0, wx.ALL, 5)
        sizer_5.Add(sizer_6, 0, wx.ALL | wx.EXPAND, 5)
        sizer_5.Add(self.table_endpoint, 1, wx.EXPAND, 0)
        sizer_4.Add(sizer_5, 1, wx.ALL | wx.EXPAND, 20)
        self.layout = sizer_4
