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
from dvha.tools.utilities import get_window_size, get_selected_listctrl_items


class ProtocolsEditor(wx.Dialog):
    def __init__(self, roi_map):
        wx.Dialog.__init__(self, None)

        self.roi_map = roi_map
        self.protocols = Protocols()

        keys = ['protocol', 'fractionation']
        self.combo_box = {key: wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
                          for key in keys}
        self.label = {key: wx.StaticText(self, wx.ID_ANY, key.capitalize() + ':') for key in keys}

        button_map = {'add': '+', 'del': '-', 'edit': u"Δ"}
        self.buttons_combos = {key: {b_key: wx.Button(self, wx.ID_ANY, b_val)
                                     for b_key, b_val in button_map.items()}
                               for key in keys}

        keys = ['Add', 'Edit', 'Delete', 'Select All', 'Deselect All']
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

        self.update_protocols()

        for key in ['protocol', 'fractionation']:
            for button in self.buttons_combos[key].values():
                button.SetMaxSize((25, 25))

        self.button_constraints['Edit'].Disable()
        self.button_constraints['Delete'].Disable()

    def __do_bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.protocol_ticker, id=self.combo_box['protocol'].GetId())
        self.Bind(wx.EVT_COMBOBOX, self.update_table, id=self.combo_box['fractionation'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_select_all, id=self.button_constraints['Select All'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_deselect_all, id=self.button_constraints['Deselect All'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_delete_constraint, id=self.button_constraints['Delete'].GetId())
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.update_delete_constraint_enable, id=self.list_ctrl.GetId())
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.update_delete_constraint_enable, id=self.list_ctrl.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_delete_protocol, id=self.buttons_combos['protocol']['del'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_delete_fractionation, id=self.buttons_combos['fractionation']['del'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_add_constraint, id=self.button_constraints['Add'].GetId())

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_combos = {key: {'all': wx.BoxSizer(wx.VERTICAL),
                              'action': wx.BoxSizer(wx.HORIZONTAL)} for key in ['protocol', 'fractionation']}
        sizer_combos_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_constraints = wx.BoxSizer(wx.VERTICAL)
        sizer_actions = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dlg_buttons = wx.BoxSizer(wx.HORIZONTAL)

        for key in ['protocol', 'fractionation']:
            sizer_combos[key]['action'].Add(self.combo_box[key], 0, wx.LEFT | wx.RIGHT, 2)
            sizer_combos[key]['action'].Add(self.buttons_combos[key]['add'], 0, wx.LEFT | wx.RIGHT, 2)
            sizer_combos[key]['action'].Add(self.buttons_combos[key]['del'], 0, wx.LEFT | wx.RIGHT, 2)
            sizer_combos[key]['action'].Add(self.buttons_combos[key]['edit'], 0, wx.LEFT, 2)
            sizer_combos[key]['action'].Add((50, 20), 0, 0, 0)

            sizer_combos[key]['all'].Add(self.label[key], 0, 0, 0)
            sizer_combos[key]['all'].Add(sizer_combos[key]['action'], 0, 0, 0)
            sizer_combos_wrapper.Add(sizer_combos[key]['all'], 0, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_combos_wrapper, 0, wx.EXPAND, 0)

        sizer_actions.Add(self.button_constraints['Add'], 0, wx.RIGHT, 5)
        sizer_actions.Add(self.button_constraints['Edit'], 0, wx.RIGHT | wx.LEFT, 5)
        sizer_actions.Add(self.button_constraints['Delete'], 0, wx.RIGHT | wx.LEFT, 5)
        sizer_actions.Add(self.button_constraints['Select All'], 0, wx.RIGHT | wx.LEFT, 5)
        sizer_actions.Add(self.button_constraints['Deselect All'], 0,  wx.LEFT, 5)
        label_actions = wx.StaticText(self, wx.ID_ANY, "Constraints:")
        sizer_constraints.Add(label_actions, 0, 0, 0)
        sizer_constraints.Add(sizer_actions, 0, wx.ALL | wx.EXPAND, 5)
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

    @property
    def selected_protocol(self):
        return self.combo_box['protocol'].GetValue()

    @property
    def selected_fx(self):
        return self.combo_box['fractionation'].GetValue()

    def update_table(self, *evt):
        if self.selected_protocol and self.selected_fx:
            data, columns = self.protocols.get_column_data(self.selected_protocol, self.selected_fx)
            self.data_table.set_data(data, columns)

    def update_protocols(self, set_name=None):
        protocol_names = self.protocols.protocol_names
        if not protocol_names:
            self.clear_data()
        else:
            self.combo_box['protocol'].SetItems(protocol_names)
            selected_protocol = set_name if set_name is not None else protocol_names[0]
            self.combo_box['protocol'].SetValue(selected_protocol)
            self.update_fractionations()

    def update_fractionations(self):
        old_fx = self.selected_fx
        fxs = self.protocols.get_fractionations(self.selected_protocol)
        self.combo_box['fractionation'].SetItems(fxs)
        if not fxs:
            self.data_table.clear()
        else:
            new_fx = fxs[0] if old_fx not in fxs else old_fx
            self.combo_box['fractionation'].SetValue(new_fx)

    def protocol_ticker(self, *evt):
        self.update_fractionations()
        self.update_table()
        self.update_del_combos_enable()

    def on_select_all(self, *evt):
        self.data_table.apply_selection_to_all(True)

    def on_deselect_all(self, *evt):
        self.data_table.apply_selection_to_all(False)

    def on_delete_protocol(self, *evt):
        self.protocols.delete_protocol(self.selected_protocol)
        self.update_protocols()
        self.update_table()
        self.update_del_combos_enable()

    def on_delete_fractionation(self, *evt):
        self.protocols.delete_fractionation(self.selected_protocol, self.selected_fx)
        self.update_fractionations()
        self.update_table()
        self.update_del_combos_enable()

    def update_del_combos_enable(self):
        self.buttons_combos['protocol']['del'].Enable(bool(self.selected_protocol))
        self.buttons_combos['fractionation']['del'].Enable(bool(self.selected_fx))

    def on_delete_constraint(self, *evt):
        for index_and_row in self.data_table.selected_row_data_with_index:
            index, row = tuple(index_and_row)
            i = index
            while not self.data_table.data['Structure'][i]:
                i -= 1
            roi = self.data_table.data['Structure'][i]
            constraint_label = row[2].replace('cc', '').replace('Gy', '')
            if roi:
                self.protocols.delete_constraint(self.selected_protocol, self.selected_fx, roi, constraint_label)
        self.update_table()

    def on_add_constraint(self, *evt):
        AddProtocolROI(self, self.protocols, self.selected_protocol, self.selected_fx, self.roi_map)

    def update_delete_constraint_enable(self, *evt):
        selected = get_selected_listctrl_items(self.list_ctrl)
        count = len([i for i in selected if self.data_table.get_row(i)[-1]])
        self.button_constraints['Delete'].Enable(count > 0)
        self.button_constraints['Edit'].Enable(count == 1)

    def clear_data(self):
        for combo_box in self.combo_box.values():
            combo_box.SetItems([''])
        self.data_table.clear()


class AddProtocolROI(wx.Dialog):
    def __init__(self, parent, protocols, protocol_name, fractionation, roi_map):
        wx.Dialog.__init__(self, parent)

        self.parent = parent
        self.protocols = protocols
        self.protocol_name = protocol_name
        self.fractionation = fractionation
        self.roi_map = roi_map

        columns = ['Input Type', 'Input Value', 'Operator', 'Output Type', 'Output Value']
        keys = ['constraints', 'aliases']
        style = wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
        self.list_ctrl = {key: wx.ListCtrl(self, wx.ID_ANY, style=style) for key in keys}
        self.data_table = {key: DataTable(self.list_ctrl[key]) for key in keys}

        keys = ['Add', 'Delete', 'Help']
        self.button_constraint = {key: wx.Button(self, wx.ID_ANY, key) for key in keys}
        self.button_alias = {key: wx.Button(self, wx.ID_ANY, key) for key in ['Add', 'Remove']}
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.combo_box_alias = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)

        self.text_ctrl_structure = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ctrl_constraint = wx.TextCtrl(self, wx.ID_ANY, "")

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.ShowModal()
        self.Destroy()

    def __set_properties(self):
        self.SetTitle("New Constraints for %s: %sFx" % (self.protocol_name, self.fractionation))
        self.update_combo_box_aliases()

    def __do_bind(self):
        pass

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_structure = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Structure Name"), wx.VERTICAL)
        sizer_constraints_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Constraints"), wx.VERTICAL)
        sizer_constraints = wx.BoxSizer(wx.HORIZONTAL)
        sizer_aliases_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Aliases"), wx.VERTICAL)
        sizer_aliases = wx.BoxSizer(wx.VERTICAL)
        sizer_aliases_edit = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)

        sizer_structure.Add(self.text_ctrl_structure, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_structure, 0, wx.ALL | wx.EXPAND, 5)

        sizer_constraints.Add(self.text_ctrl_constraint, 1, wx.RIGHT, 5)
        sizer_constraints.Add(self.button_constraint['Add'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_constraints.Add(self.button_constraint['Delete'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_constraints.Add(self.button_constraint['Help'], 0, wx.LEFT, 5)
        sizer_constraints_wrapper.Add(sizer_constraints, 0, wx.ALL | wx.EXPAND, 5)
        sizer_constraints_wrapper.Add(self.list_ctrl['constraints'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_constraints_wrapper, 1, wx.ALL | wx.EXPAND, 5)

        label_alias = wx.StaticText(self, wx.ID_ANY, "Institutional ROI:")
        sizer_aliases.Add(label_alias, 0, 0, 0)
        sizer_aliases.Add(sizer_aliases_edit, 0, wx.ALL | wx.EXPAND, 0)
        sizer_aliases_wrapper.Add(sizer_aliases, 0, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_aliases_wrapper, 1, wx.EXPAND, 0)

        sizer_aliases_edit.Add(self.combo_box_alias, 1, wx.RIGHT, 5)
        sizer_aliases_edit.Add(self.button_alias['Add'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_aliases_edit.Add(self.button_alias['Remove'], 0, wx.LEFT, 5)
        sizer_aliases_wrapper.Add(self.list_ctrl['aliases'], 1, wx.ALL | wx.EXPAND, 5)

        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_main.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def update_combo_box_aliases(self):
        self.combo_box_alias.SetItems(self.roi_map.institutional_rois)
        self.combo_box_alias.SetValue(self.roi_map.institutional_rois[0])
