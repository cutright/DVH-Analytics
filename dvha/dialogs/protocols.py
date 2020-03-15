#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dialogs.protocols.py
"""
Dialogs used to edit DVH Constraint Protocols
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from dvha.models.data_table import DataTable
from dvha.models.dvh import Protocols
from dvha.tools.utilities import get_window_size


class ProtocolsEditor(wx.Dialog):
    def __init__(self, *evt):
        wx.Dialog.__init__(self, None)

        self.protocols = Protocols()

        keys = ['protocol', 'fractionation']
        self.combo_box = {key: wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
                          for key in keys}
        self.label = {key: wx.StaticText(self, wx.ID_ANY, key.capitalize() + ':') for key in keys}

        button_map = {'add': '+', 'del': '-', 'edit': u"Δ"}
        self.buttons_combos = {key: {b_key: wx.Button(self, wx.ID_ANY, b_val)
                                     for b_key, b_val in button_map.items()}
                               for key in keys}

        keys = ['Add', 'Delete', 'Select All', 'Deselect All']
        self.button_constraints = {key: wx.Button(self, wx.ID_ANY, key) for key in keys}

        button_id_map = {'Save': wx.ID_ANY, 'OK': wx.ID_OK, 'Cancel': wx.ID_CANCEL}
        self.button_dlg = {key: wx.Button(self, wxid, key) for key, wxid in button_id_map.items()}

        self.list_ctrl = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.data_table = DataTable(self.list_ctrl, widths=[250, 100, 100, 100])

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.update_table()

        self.ShowModal()
        self.Destroy()

    def __set_properties(self):
        self.SetMinSize(get_window_size(0.4, 0.7))
        self.SetTitle("Protocol Editor")

        protocol_names = self.protocols.protocol_names
        self.combo_box['protocol'].SetItems(protocol_names)
        self.combo_box['protocol'].SetValue(protocol_names[0])

        fractionations = self.protocols.get_fractionations(protocol_names[0])
        self.combo_box['fractionation'].SetItems(fractionations)
        self.combo_box['fractionation'].SetValue(fractionations[0])

        for key in ['protocol', 'fractionation']:
            for button in self.buttons_combos[key].values():
                button.SetMaxSize((25, 25))

    def __do_bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.update_table, id=self.combo_box['protocol'].GetId())
        self.Bind(wx.EVT_COMBOBOX, self.update_table, id=self.combo_box['fractionation'].GetId())

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_combos = {key: {'all': wx.BoxSizer(wx.VERTICAL),
                              'action': wx.BoxSizer(wx.HORIZONTAL)} for key in ['protocol', 'fractionation']}
        sizer_constraints = wx.BoxSizer(wx.VERTICAL)
        sizer_actions = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dlg_buttons = wx.BoxSizer(wx.HORIZONTAL)

        for key in ['protocol', 'fractionation']:
            sizer_combos[key]['action'].Add(self.combo_box[key], 0, wx.LEFT | wx.RIGHT, 5)
            sizer_combos[key]['action'].Add(self.buttons_combos[key]['add'], 0, wx.LEFT | wx.RIGHT, 5)
            sizer_combos[key]['action'].Add(self.buttons_combos[key]['del'], 0, wx.LEFT | wx.RIGHT, 5)
            sizer_combos[key]['action'].Add(self.buttons_combos[key]['edit'], 0, wx.LEFT, 5)

            sizer_combos[key]['all'].Add(self.label[key], 0, 0, 0)
            sizer_combos[key]['all'].Add(sizer_combos[key]['action'], 0, 0, 0)
            sizer_main.Add(sizer_combos[key]['all'], 0, wx.ALL | wx.EXPAND, 5)

        sizer_actions.Add(self.button_constraints['Add'], 0, 0, 0)
        sizer_actions.Add(self.button_constraints['Delete'], 0, 0, 0)
        sizer_actions.Add(self.button_constraints['Select All'], 0, 0, 0)
        sizer_actions.Add(self.button_constraints['Deselect All'], 0, 0, 0)
        label_actions = wx.StaticText(self, wx.ID_ANY, "Constraints:")
        sizer_constraints.Add(label_actions, 0, 0, 0)
        sizer_constraints.Add(sizer_actions, 0, wx.ALL | wx.EXPAND, 5)
        label_note = wx.StaticText(self, wx.ID_ANY, "NOTE: All doses in Gy and volumes in cc, unless in percentage")
        sizer_constraints.Add(label_note, 0, wx.ALL, 5)
        sizer_constraints.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_constraints, 1, wx.ALL | wx.EXPAND, 5)

        sizer_dlg_buttons.Add(self.button_dlg['Save'], 0, wx.RIGHT, 5)
        sizer_dlg_buttons.Add(self.button_dlg['OK'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_dlg_buttons.Add(self.button_dlg['Cancel'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_main.Add(sizer_dlg_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def update_table(self, *evt):
        data, columns = self.protocols.get_column_data(self.combo_box['protocol'].GetValue(),
                                                       self.combo_box['fractionation'].GetValue())
        self.data_table.set_data(data, columns)
