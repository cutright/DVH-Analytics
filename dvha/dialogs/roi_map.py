#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dialogs.roi_map.py
"""
GUI tools to edit the ROI Name map
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from dvha.models.data_table import DataTable
from dvha.tools.errors import ROIVariationErrorDialog
from dvha.tools.utilities import get_selected_listctrl_items
from dvha.tools.roi_name_manager import ROIVariationError, clean_name


class AddPhysician(wx.Dialog):
    """
    Create a new physician in the ROI map with ability to copy the initial map from a current physician
    """
    def __init__(self, roi_map, initial_physician=None):
        """
        :param roi_map: the roi_map object
        :type roi_map: DatabaseROIs
        :param initial_physician: optionally set the new physician name in the text_ctrl
        :type initial_physician: str
        """
        wx.Dialog.__init__(self, None)

        self.roi_map = roi_map
        self.initial_physician = initial_physician

        self.text_ctrl_physician = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_box_copy_from = wx.ComboBox(self, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN)
        self.checkbox_variations = wx.CheckBox(self, wx.ID_ANY, "Include Variations")
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.res = None

        self.Bind(wx.EVT_TEXT, self.update_enable, id=self.text_ctrl_physician.GetId())

        self.run()

    def __set_properties(self):
        self.SetTitle("Add Physician to ROI Map")
        self.checkbox_variations.SetValue(1)
        if self.initial_physician:
            self.text_ctrl_physician.SetValue(self.initial_physician)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_copy_from = wx.BoxSizer(wx.VERTICAL)
        sizer_new_physician = wx.BoxSizer(wx.VERTICAL)

        label_new_physician = wx.StaticText(self, wx.ID_ANY, "New Physician:")
        sizer_new_physician.Add(label_new_physician, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_new_physician.Add(self.text_ctrl_physician, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_widgets.Add(sizer_new_physician, 1, wx.EXPAND | wx.TOP, 10)

        label_copy_from = wx.StaticText(self, wx.ID_ANY, "Copy From:")
        sizer_copy_from.Add(label_copy_from, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_copy_from.Add(self.combo_box_copy_from, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_widgets.Add(sizer_copy_from, 1, wx.EXPAND | wx.TOP, 10)
        sizer_widgets.Add(self.checkbox_variations, 0, wx.EXPAND | wx.ALL, 10)
        sizer_wrapper.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 10)

        sizer_ok_cancel.Add(self.button_ok, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def action(self):
        self.roi_map.copy_physician(self.text_ctrl_physician.GetValue(),
                                    copy_from=self.combo_box_copy_from.GetValue(),
                                    include_variations=self.checkbox_variations.GetValue())

    def run(self):
        self.res = self.ShowModal()
        if self.res == wx.ID_OK:
            self.action()
        self.Destroy()

    def update_enable(self, evt):
        invalid_choices = set(self.roi_map.get_physicians())
        new = clean_name(self.text_ctrl_physician.GetValue()).upper()
        self.button_ok.Enable(new not in invalid_choices)


# TODO: Disable ability to use Variation Manager on 'DEFAULT' physician
class RoiManager(wx.Dialog):
    """
    Dialog accessible from the DICOM import GUI to allow user to easily update the ROI map with new plans
    """
    def __init__(self, parent, roi_map, physician, physician_roi):
        """
        :param parent: GUI parent
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        :param physician: initial physician value
        :type physician: str
        :param physician_roi: initial physician roi
        :type physician_roi: str
        """
        wx.Dialog.__init__(self, parent)
        self.parent = parent
        self.roi_map = roi_map
        self.initial_physician = physician
        self.initial_physician_roi = physician_roi

        self.combo_box_physician = wx.ComboBox(self, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_physician_roi = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.list_ctrl_variations = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_NO_HEADER | wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.button_select_all = wx.Button(self, wx.ID_ANY, "Select All")
        self.button_deselect_all = wx.Button(self, wx.ID_ANY, "Deselect All")
        self.button_add = wx.Button(self, wx.ID_ANY, "Add")
        self.button_delete = wx.Button(self, wx.ID_ANY, "Delete")
        self.button_move = wx.Button(self, wx.ID_ANY, "Move")
        self.button_dismiss = wx.Button(self, wx.ID_CANCEL, "Dismiss")

        self.button_move.Disable()
        self.button_delete.Disable()
        self.button_deselect_all.Disable()

        self.button_add_physician = wx.Button(self, wx.ID_ANY, "Add")
        self.button_add_physician_roi = wx.Button(self, wx.ID_ANY, "Add")

        self.columns = ['Variations']
        self.data_table = DataTable(self.list_ctrl_variations, columns=self.columns, widths=[400])

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()

        self.run()

    def __set_properties(self):
        self.SetTitle("ROI Manager")
        self.combo_box_physician.SetValue(self.initial_physician)
        self.update_physician_rois()
        self.combo_box_physician_roi.SetValue(self.initial_physician_roi)
        self.update_variations()

    def __do_bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.physician_ticker, id=self.combo_box_physician.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.physician_roi_ticker, id=self.combo_box_physician_roi.GetId())
        self.Bind(wx.EVT_BUTTON, self.add_physician, id=self.button_add_physician.GetId())
        self.Bind(wx.EVT_BUTTON, self.add_physician_roi, id=self.button_add_physician_roi.GetId())
        self.Bind(wx.EVT_BUTTON, self.select_all, id=self.button_select_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.deselect_all, id=self.button_deselect_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.add_variation, id=self.button_add.GetId())
        self.Bind(wx.EVT_BUTTON, self.move_variations, id=self.button_move.GetId())
        self.Bind(wx.EVT_BUTTON, self.delete_variations, id=self.button_delete.GetId())
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.update_button_enable, id=self.list_ctrl_variations.GetId())
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.update_button_enable, id=self.list_ctrl_variations.GetId())

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_variation_buttons = wx.BoxSizer(wx.VERTICAL)
        sizer_variation_table = wx.BoxSizer(wx.VERTICAL)
        sizer_select = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_variations = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_row_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician = wx.BoxSizer(wx.VERTICAL)

        label_physician = wx.StaticText(self, wx.ID_ANY, "Physician:")
        sizer_physician.Add(label_physician, 0, wx.LEFT, 5)
        sizer_physician_row = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_row.Add(self.combo_box_physician, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_row.Add(self.button_add_physician, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer_physician.Add(sizer_physician_row, 1, wx.EXPAND, 0)
        sizer_select.Add(sizer_physician, 0, wx.ALL | wx.EXPAND, 5)

        label_physician_roi = wx.StaticText(self, wx.ID_ANY, "Physician ROI:")
        sizer_physician_roi.Add(label_physician_roi, 0, wx.LEFT, 5)
        sizer_physician_roi_row_2.Add(self.combo_box_physician_roi, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_row_2.Add(self.button_add_physician_roi, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer_physician_roi.Add(sizer_physician_roi_row_2, 0, wx.EXPAND, 0)
        sizer_select.Add(sizer_physician_roi, 0, wx.ALL | wx.EXPAND, 5)

        label_variations = wx.StaticText(self, wx.ID_ANY, "Variations:")
        label_variations_buttons = wx.StaticText(self, wx.ID_ANY, " ")
        sizer_variation_table.Add(label_variations, 0, 0, 0)
        sizer_variation_table.Add(self.list_ctrl_variations, 1, wx.ALL | wx.EXPAND, 0)
        sizer_variations.Add(sizer_variation_table, 0, wx.ALL, 5)
        sizer_variation_buttons.Add(label_variations_buttons, 0, 0, 0)
        sizer_variation_buttons.Add(self.button_add, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer_variation_buttons.Add(self.button_delete, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(self.button_move, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(self.button_select_all, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(self.button_deselect_all, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variations.Add(sizer_variation_buttons, 0, wx.EXPAND | wx.ALL, 5)
        sizer_select.Add(sizer_variations, 0, wx.ALL | wx.EXPAND, 5)

        sizer_wrapper.Add(sizer_select, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_dismiss, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer_wrapper.Add(sizer_buttons, 0, wx.ALIGN_CENTER | wx.ALL, 0)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def run(self):
        self.ShowModal()
        self.Destroy()

    def update_physicians(self, old_physicians=None):

        choices = self.roi_map.get_physicians()
        new = choices[0]
        if old_physicians:
            new = list(set(choices) - set(old_physicians))
            if new:
                new = clean_name(new[0]).upper()

        self.update_combo_box_choices(self.combo_box_physician, choices, new)

    def update_physician_rois(self, old_physician_rois=None):
        choices = self.roi_map.get_physician_rois(self.physician)
        new = choices[0]
        if old_physician_rois:
            new = list(set(choices) - set(old_physician_rois))
            if new:
                new = clean_name(new[0])

        self.update_combo_box_choices(self.combo_box_physician_roi, choices, new)

    @staticmethod
    def update_combo_box_choices(combo_box, choices, value):
        if not value:
            value = combo_box.GetValue()
        combo_box.Clear()
        combo_box.AppendItems(choices)
        combo_box.SetValue(value)

    def update_variations(self):
        self.data_table.set_data(self.variation_table_data, self.columns)
        self.update_button_enable(None)

    def physician_ticker(self, evt):
        self.update_physician_rois()
        self.update_variations()

    def physician_roi_ticker(self, evt):
        self.update_variations()

    @property
    def physician(self):
        return self.combo_box_physician.GetValue()

    @property
    def physician_roi(self):
        return self.combo_box_physician_roi.GetValue()

    @property
    def variations(self):
        variations = self.roi_map.get_variations(self.combo_box_physician.GetValue(),
                                                 self.combo_box_physician_roi.GetValue())
        variations = list(set(variations) - {self.combo_box_physician_roi.GetValue()})  # remove physician roi
        variations.sort()
        return variations

    @property
    def variation_table_data(self):
        return {'Variations': self.variations}

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl_variations)

    @property
    def selected_values(self):
        return [self.list_ctrl_variations.GetItem(i, 0).GetText() for i in self.selected_indices]

    @property
    def variation_count(self):
        return len(self.variations)

    def select_all(self, evt):
        self.apply_global_selection()

    def deselect_all(self, evt):
        self.apply_global_selection(on=0)

    def apply_global_selection(self, on=1):
        for i in range(self.variation_count):
            self.list_ctrl_variations.Select(i, on=on)

    def delete_variations(self, evt):
        self.roi_map.delete_variations(self.physician, self.physician_roi, self.selected_values)
        self.update_variations()

    def add_variation(self, evt):
        dlg = AddVariationDialog(self.parent, self.physician, self.physician_roi, self.roi_map)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            try:
                self.roi_map.add_variation(self.physician, self.physician_roi, dlg.text_ctrl_variation.GetValue())
                self.update_variations()
            except ROIVariationError as e:
                ROIVariationErrorDialog(self.parent, e)
        dlg.Destroy()

    def move_variations(self, evt):
        choices = [roi for roi in self.roi_map.get_physician_rois(self.physician) if roi != self.physician_roi]
        MoveVariationDialog(self, self.selected_values, self.physician, self.physician_roi, choices, self.roi_map)
        self.update_variations()

    def update_button_enable(self, evt):
        if self.selected_indices:
            self.button_move.Enable()
            self.button_delete.Enable()
            self.button_deselect_all.Enable()
        else:
            self.button_move.Disable()
            self.button_delete.Disable()
            self.button_deselect_all.Disable()

    def add_physician_roi(self, evt):
        old_physician_rois = self.roi_map.get_physician_rois(self.physician)
        AddPhysicianROI(self.parent, self.physician, self.roi_map)
        self.update_physician_rois(old_physician_rois=old_physician_rois)

    def add_physician(self, evt):
        old_physicians = self.roi_map.get_physicians()
        AddPhysician(self.roi_map)
        self.update_physicians(old_physicians=old_physicians)


class AddVariationDialog(wx.Dialog):
    """
    Add a new variation for a specified physician and physician roi
    """
    def __init__(self, parent, physician, physician_roi, roi_map):
        """
        :param parent: GUI parent
        :param physician: physician associated with new variation
        :type physician: str
        :param physician_roi: physician roi associated with new variation
        :type physician_roi: str
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        """
        wx.Dialog.__init__(self, parent)
        self.physician = physician
        self.physician_roi = physician_roi
        self.roi_map = roi_map
        self.text_ctrl_variation = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "Add")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()

    def __do_bind(self):
        self.Bind(wx.EVT_TEXT, self.enable_add_button, id=self.text_ctrl_variation.GetId())

    def __set_properties(self):
        self.SetTitle("Add Variation to %s for %s" % (self.physician_roi, self.physician))
        self.text_ctrl_variation.SetMinSize((300, 22))
        self.button_ok.SetToolTip("If Add is disabled, requested variation is already in use by %s." % self.physician)

    def __do_layout(self):
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_variation = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)

        label_variation = wx.StaticText(self, wx.ID_ANY, "New variation:")
        sizer_variation.Add(label_variation, 0, 0, 0)
        sizer_variation.Add(self.text_ctrl_variation, 0, wx.EXPAND, 0)
        sizer_frame.Add(sizer_variation, 0, wx.EXPAND, 0)

        sizer_buttons.Add(self.button_ok, 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_cancel, 1, wx.ALL | wx.EXPAND, 5)
        sizer_frame.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_frame)
        sizer_frame.Fit(self)
        self.Layout()
        self.Center()

    def enable_add_button(self, evt):
        if self.roi_map.is_variation_used(self.physician, self.text_ctrl_variation.GetValue()):
            self.button_ok.Disable()
        else:
            self.button_ok.Enable()


class MoveVariationDialog(wx.Dialog):
    """
    Move provided variations to a new physician roi within the same physician map
    """
    def __init__(self, parent, variations, physician, old_physician_roi, choices, roi_map):
        """
        :param parent: GUI parent
        :param variations: the roi variations to be moved
        :type variations: list
        :param physician: the associated physician
        :type physician: str
        :param old_physician_roi: current physician roi of the provided variations
        :type old_physician_roi: str
        :param choices: the allowed physician rois that the variations may be moved to
        :type choices: list
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        """
        wx.Dialog.__init__(self, parent)
        self.variations = variations
        self.physician = physician
        self.old_physician_roi = old_physician_roi
        self.choices = choices
        self.roi_map = roi_map
        self.combo_box = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Move Variations")
        self.combo_box.SetValue(self.choices[0])

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        label_physician_roi = wx.StaticText(self, wx.ID_ANY, "Move to Physician ROI:")
        sizer_input.Add(label_physician_roi, 0, 0, 0)
        sizer_input.Add(self.combo_box, 0, 0, 0)
        sizer_wrapper.Add(sizer_input, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sizer_buttons.Add(self.button_ok, 0, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        for variation in self.variations:
            self.roi_map.delete_variation(self.physician, self.old_physician_roi, variation)
            self.roi_map.add_variation(self.physician, self.combo_box.GetValue(), variation)


class AddPhysicianROI(wx.Dialog):
    """
    Add a new physician roi to the specified physician
    """
    def __init__(self, parent, physician, roi_map, institutional_mode=False):
        """
        :param parent: GUI parent
        :param physician: physician of interest
        :type physician: str
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        :param institutional_mode: If True, this dialog adds an institutional roi instead
        :type institutional_mode: bool
        """
        wx.Dialog.__init__(self, parent)
        self.SetSize((500, 135))

        self.institutional_mode = institutional_mode

        self.physician = physician
        self.roi_map = roi_map
        self.institutional_rois = self.roi_map.get_unused_institutional_rois(physician)
        self.text_ctrl_physician_roi = wx.TextCtrl(self, wx.ID_ANY, "")

        if not self.institutional_mode:
            self.combo_box_institutional_roi = wx.ComboBox(self, wx.ID_ANY, choices=self.institutional_rois,
                                                           style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_ok = wx.Button(self, wx.ID_OK, "Add")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.res = None

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()

        self.run()

    def __do_bind(self):
        self.Bind(wx.EVT_TEXT, self.update_enable, id=self.text_ctrl_physician_roi.GetId())

    def __set_properties(self):
        if not self.institutional_mode:
            self.SetTitle("Add Physician ROI for %s" % self.physician)
            self.text_ctrl_physician_roi.SetToolTip("New entry must be unique from all other institutional, physician, "
                                                    "or variation ROIs for this physician.")
            self.combo_box_institutional_roi.SetToolTip("If the institutional ROI you’re looking for isn’t here, it may"
                                                        " already be assigned.")
            if 'uncategorized' in self.institutional_rois:
                self.combo_box_institutional_roi.SetValue('uncategorized')

            self.button_ok.SetToolTip("If Add is disabled, new entry is already used in institutional ROIs, "
                                      "physician ROIs, or ROI variations for %s." % self.physician)
        else:
            self.SetTitle("Add Institutional ROI")
            self.text_ctrl_physician_roi.SetToolTip("New entry must be unique from all other institutional ROIs.")
            self.button_ok.SetToolTip("If Add is disabled, new entry is already used in institutional ROIs")

        self.SetMinSize((300, 100))

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        if not self.institutional_mode:
            sizer_institutional_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)

        label_physician_roi = wx.StaticText(self, wx.ID_ANY, "New %s ROI:" %
                                            ['Physician', 'Institutional'][self.institutional_mode])
        sizer_physician_roi.Add(label_physician_roi, 0, 0, 0)
        sizer_physician_roi.Add(self.text_ctrl_physician_roi, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_physician_roi, 1, wx.ALL | wx.EXPAND, 5)

        if not self.institutional_mode:
            label_institutional_roi = wx.StaticText(self, wx.ID_ANY, "Linked Institutional ROI:")
            sizer_institutional_roi.Add(label_institutional_roi, 0, 0, 0)
            sizer_institutional_roi.Add(self.combo_box_institutional_roi, 0, wx.EXPAND, 0)
            sizer_input.Add(sizer_institutional_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_input, 0, wx.EXPAND, 0)

        sizer_buttons.Add(self.button_ok, 1, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 1, wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 0, wx.ALIGN_RIGHT, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def run(self):
        self.res = self.ShowModal()
        if self.res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        if not self.institutional_mode:
            self.roi_map.add_physician_roi(self.physician,
                                           self.combo_box_institutional_roi.GetValue(),
                                           self.text_ctrl_physician_roi.GetValue())
        else:
            self.roi_map.add_institutional_roi(self.text_ctrl_physician_roi.GetValue())

    def update_enable(self, evt):
        if not self.institutional_mode:
            invalid_choices = set(self.roi_map.get_physician_rois(self.physician) +
                                  self.roi_map.get_all_variations_of_physician(self.physician))
        else:
            invalid_choices = self.roi_map.get_institutional_rois()

        new = clean_name(self.text_ctrl_physician_roi.GetValue())
        self.button_ok.Enable(new not in invalid_choices)


class AddROIType(wx.Dialog):
    """
    Add a new roi type (e.g., External, PTV, ORGAN, etc.)
    """
    def __init__(self, parent):
        """
        :param parent: GUI parent
        """
        wx.Dialog.__init__(self, parent)
        self.SetSize((250, 135))
        self.text_ctrl_roi_type = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "Add")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Add New ROI Type")

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        label_roi_type = wx.StaticText(self, wx.ID_ANY, "New ROI Type:")
        sizer_physician_roi.Add(label_roi_type, 0, 0, 0)
        sizer_physician_roi.Add(self.text_ctrl_roi_type, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_physician_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_input, 0, wx.EXPAND, 0)
        sizer_buttons.Add(self.button_ok, 1, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 1, wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 0, wx.ALIGN_CENTER, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        pass


class ChangePlanROIName(wx.Dialog):
    """
    Change the roi name of a parsed plan in the DICOM importer
    """
    # TODO: implement ChangePlanROIName
    def __init__(self, tree_ctrl_roi, tree_item, mrn, study_instance_uid, parsed_dicom_data):
        """
        :param tree_ctrl_roi: the roi tree from the DICOM importer view
        :param tree_item: the tree_ctrl_roi item to be edited
        :param mrn: the patient's mrn for the plan of interest
        :type mrn: str
        :param study_instance_uid: the study instance uid of the plan of interest (should be plan_uid now?)
        :type study_instance_uid: str
        :param parsed_dicom_data: parsed dicom data object for plan of interest
        :type parsed_dicom_data: DICOM_Parser
        """
        wx.Dialog.__init__(self, None, title='Edit %s' % tree_ctrl_roi.GetItemText(tree_item))

        self.tree_ctrl_roi = tree_ctrl_roi
        self.tree_item = tree_item
        self.roi = tree_ctrl_roi.GetItemText(tree_item)
        self.initial_mrn = mrn
        self.initial_study_instance_uid = study_instance_uid

        self.parsed_dicom_data = parsed_dicom_data

        invalid_options = [''] + parsed_dicom_data.roi_names
        self.invalid_options = [clean_name(name) for name in invalid_options]

        self.text_input_label = 'Change ROI name to:'

        self.text_ctrl = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, 'OK')
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.text_ctrl.SetMinSize((365, 22))
        self.button_ok.Disable()

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)

        label_text_input = wx.StaticText(self, wx.ID_ANY, self.text_input_label)
        sizer_input.Add(label_text_input, 0, wx.EXPAND | wx.ALL, 5)
        sizer_input.Add(self.text_ctrl, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        sizer_wrapper.Add(sizer_input, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 10)

        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def __do_bind(self):
        self.Bind(wx.EVT_TEXT, self.text_ticker, id=self.text_ctrl.GetId())

    def text_ticker(self, evt):
        [self.button_ok.Disable, self.button_ok.Enable][self.new_name not in self.invalid_options]()

    @property
    def roi_key(self):
        return self.parsed_dicom_data.get_roi_key(self.roi)

    @property
    def new_name(self):
        return clean_name(self.text_ctrl.GetValue())

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        # TODO: data doesn't propagate everywhere needed?
        key = self.parsed_dicom_data.get_roi_key(self.roi)
        self.parsed_dicom_data.set_roi_name(key, self.new_name)
        self.tree_ctrl_roi.SetItemText(self.tree_item, self.new_name)


class RenamerBaseClass(wx.Dialog):
    """
    Simple base class used for renaming (e.g., renaming a physician in the roi map)
    """
    def __init__(self, title, text_input_label, invalid_options, lower_case=True):
        """
        :param title: title of the dialog window
        :type title: str
        :param text_input_label: label to be displayed above text_ctrl
        :type text_input_label: str
        :param invalid_options: if text_ctrl is in invalid options, OK button will be disabled
        :type invalid_options: list
        :param lower_case: final value of text_input_label will be forced to either all lower or upper case
        :type lower_case: bool
        """
        wx.Dialog.__init__(self, None, title=title)

        self.invalid_options = invalid_options
        self.lower_case = lower_case

        self.text_input_label = text_input_label

        self.text_ctrl = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, 'OK')
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.res = None

        self.run()

    def __set_properties(self):
        self.text_ctrl.SetMinSize((365, 22))
        self.button_ok.Disable()

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)

        label_text_input = wx.StaticText(self, wx.ID_ANY, self.text_input_label)
        sizer_input.Add(label_text_input, 0, wx.EXPAND | wx.ALL, 5)
        sizer_input.Add(self.text_ctrl, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        sizer_wrapper.Add(sizer_input, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 10)

        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def __do_bind(self):
        self.Bind(wx.EVT_TEXT, self.text_ticker, id=self.text_ctrl.GetId())

    def text_ticker(self, evt):
        [self.button_ok.Disable, self.button_ok.Enable][self.new_name not in self.invalid_options]()

    @property
    def new_name(self):
        new = clean_name(self.text_ctrl.GetValue())  # clean name will result in lower-case
        if self.lower_case:
            return new
        else:
            return new.upper()

    def run(self):
        self.res = self.ShowModal()
        if self.res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        pass


class RenamePhysicianDialog(RenamerBaseClass):
    """
    Dialog for renaming a physician in the roi map
    """
    def __init__(self, physician, roi_map):
        """
        :param physician: physician to be renamed
        :type physician: str
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        """
        self.physician = physician
        self.roi_map = roi_map
        RenamerBaseClass.__init__(self, 'Rename %s' % physician,
                                  'New Physician Name:', roi_map.get_physicians(), lower_case=False)

    def action(self):
        self.roi_map.rename_physician(self.new_name, self.physician)


class RenamePhysicianROIDialog(RenamerBaseClass):
    """
    Dialog to rename a physician roi for a given physician
    """
    def __init__(self, physician, physician_roi, roi_map):
        """
        :param physician: physician of the physician roi to be renamed
        :type physician: str
        :param physician_roi: physician roi to be renamed
        :type physician_roi: str
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        """
        self.physician = physician
        self.physician_roi = physician_roi
        self.roi_map = roi_map
        RenamerBaseClass.__init__(self, 'Rename %s for %s' % (physician_roi, physician),
                                  'New Physician ROI name:', roi_map.get_physician_rois(physician))

    def action(self):
        self.roi_map.rename_physician_roi(self.new_name, self.physician, self.physician_roi)


class RenameInstitutionalROIDialog(RenamerBaseClass):
    """
    Dialog to rename an institutional roi
    """
    def __init__(self, institutional_roi, roi_map):
        """
        :param institutional_roi: institutional roi to be renamed
        :type institutional_roi: str
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        """
        self.institutional_roi = institutional_roi
        self.roi_map = roi_map
        RenamerBaseClass.__init__(self, 'Rename %s' % institutional_roi,
                                  'New Institutional ROI name:', roi_map.get_institutional_rois())

    def action(self):
        self.roi_map.rename_institutional_roi(self.new_name, self.institutional_roi)


class LinkPhysicianROI(wx.Dialog):
    """
    Dialog to change which institutional roi a specified physician roi is linked
    """
    def __init__(self, parent, physician, physician_roi, roi_map):
        """
        :param parent: GUI parent
        :param physician: physician for the specified physician roi
        :type physician: str
        :param physician_roi: physician roi of interest
        :type physician_roi: str
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        """
        wx.Dialog.__init__(self, parent)
        self.SetMinSize((500, 135))

        self.physician = physician
        self.physician_roi = physician_roi
        self.roi_map = roi_map
        self.institutional_rois = self.roi_map.get_institutional_rois()
        self.institutional_roi = self.roi_map.get_institutional_roi(self.physician, self.physician_roi)
        choices = self.roi_map.get_unused_institutional_rois(self.physician)
        if self.institutional_roi not in choices:
            choices.append(self.institutional_roi)
            choices.sort()
        self.combo_box_institutional_roi = wx.ComboBox(self, wx.ID_ANY, choices=choices,
                                                       style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.res = None

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Change Institutional ROI for %s" % self.physician_roi)
        tip = "If the institutional ROI you’re looking for isn’t here, it may already be assigned."
        self.combo_box_institutional_roi.SetToolTip(tip)
        self.button_ok.SetToolTip(tip)
        if 'uncategorized' in self.institutional_rois:
            self.combo_box_institutional_roi.SetValue('uncategorized')

        self.combo_box_institutional_roi.SetValue(self.institutional_roi)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_institutional_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)

        sizer_input.Add(sizer_physician_roi, 1, wx.ALL | wx.EXPAND, 5)

        label_institutional_roi = wx.StaticText(self, wx.ID_ANY, "Linked Institutional ROI:")
        sizer_institutional_roi.Add(label_institutional_roi, 0, 0, 0)
        sizer_institutional_roi.Add(self.combo_box_institutional_roi, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_institutional_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_input, 0, wx.EXPAND, 0)

        sizer_buttons.Add(self.button_ok, 1, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 1, wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 0, wx.ALIGN_RIGHT, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def run(self):
        self.res = self.ShowModal()
        if self.res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        self.roi_map.set_linked_institutional_roi(self.combo_box_institutional_roi.GetValue(),
                                                  self.physician, self.physician_roi)
