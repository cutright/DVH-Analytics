#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import wx


class EditDatabaseDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="Edit Database Values")

        # self.SetSize((570, 250))
        self.combo_box_table = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.combo_box_column = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.text_ctrl_value = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ctrl_condition = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "Update")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        # self.SetTitle("frame")
        # end wxGlade
        pass

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper_inner = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_condition = wx.BoxSizer(wx.VERTICAL)
        sizer_table_column_value = wx.BoxSizer(wx.HORIZONTAL)
        sizer_value = wx.BoxSizer(wx.VERTICAL)
        sizer_column = wx.BoxSizer(wx.VERTICAL)
        sizer_table = wx.BoxSizer(wx.VERTICAL)
        label_table = wx.StaticText(self, wx.ID_ANY, "Table:")
        sizer_table.Add(label_table, 0, 0, 0)
        sizer_table.Add(self.combo_box_table, 0, wx.EXPAND, 0)
        sizer_table_column_value.Add(sizer_table, 0, wx.ALL | wx.EXPAND, 5)
        label_column = wx.StaticText(self, wx.ID_ANY, "Column:")
        sizer_column.Add(label_column, 0, 0, 0)
        sizer_column.Add(self.combo_box_column, 0, 0, 0)
        sizer_table_column_value.Add(sizer_column, 0, wx.ALL | wx.EXPAND, 5)
        label_value = wx.StaticText(self, wx.ID_ANY, "Value:")
        sizer_value.Add(label_value, 0, 0, 0)
        sizer_value.Add(self.text_ctrl_value, 0, wx.EXPAND, 0)
        sizer_table_column_value.Add(sizer_value, 1, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_table_column_value, 1, wx.EXPAND, 0)
        label_condition = wx.StaticText(self, wx.ID_ANY, "Condition:")
        sizer_condition.Add(label_condition, 0, wx.BOTTOM | wx.RIGHT | wx.TOP, 5)
        sizer_condition.Add(self.text_ctrl_condition, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_condition, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper_inner.Add(sizer_input, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper_inner.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_wrapper_inner, 0, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()
