#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import wx


class PostImportCalculationsDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="Post-Import Calculations")

        choices = ["Default Post-Import", "PTV Distances", "PTV Overlap", "ROI Centroid", "ROI Spread",
                   "ROI Cross-Section", "OAR-PTV Centroid Distance", "Beam Complexities", "Plan Complexities",
                   "All (except age)", "Patient Ages"]
        self.combo_box_calculate = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.checkbox = wx.CheckBox(self, wx.ID_ANY, "Only Calculate Missing Values")
        self.text_ctrl_condition = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "Calculate")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.checkbox.SetValue(1)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper_inner = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_condition = wx.BoxSizer(wx.VERTICAL)
        sizer_calc_and_check = wx.BoxSizer(wx.HORIZONTAL)
        sizer_calculate = wx.BoxSizer(wx.VERTICAL)
        label_calculate = wx.StaticText(self, wx.ID_ANY, "Calculate:")
        sizer_calculate.Add(label_calculate, 0, wx.BOTTOM, 5)
        sizer_calculate.Add(self.combo_box_calculate, 0, 0, 0)
        sizer_calc_and_check.Add(sizer_calculate, 0, wx.EXPAND, 0)
        sizer_calc_and_check.Add(self.checkbox, 0, wx.LEFT | wx.TOP, 20)
        sizer_input.Add(sizer_calc_and_check, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        label_condition = wx.StaticText(self, wx.ID_ANY, "Condition:")
        sizer_condition.Add(label_condition, 0, wx.BOTTOM, 5)
        sizer_condition.Add(self.text_ctrl_condition, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_condition, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper_inner.Add(sizer_input, 0, wx.ALL | wx.EXPAND, 5)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper_inner.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_wrapper_inner, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()
