#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.roi_map.py
"""
Classes for viewing and editing the roi map, and updating the database with changes
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
import wx.html2
from datetime import datetime
from threading import Thread
from pubsub import pub
from os.path import join
from dvha.db.sql_connector import DVH_SQL, echo_sql_db
from dvha.dialogs.roi_map import (
    AddPhysician,
    AddPhysicianROI,
    AddVariation,
    MoveVariationDialog,
    RenamePhysicianDialog,
    RenamePhysicianROIDialog,
    RenameInstitutionalROIDialog,
    LinkPhysicianROI,
)
from dvha.models.data_table import DataTable
from dvha.models.plot import PlotROIMap
from dvha.options import Options
from dvha.paths import PREF_DIR
from dvha.tools.utilities import (
    get_selected_listctrl_items,
    MessageDialog,
    get_elapsed_time,
    get_window_size,
    set_frame_icon,
    set_msw_background_color,
    is_windows,
    delete_file,
)
from dvha.tools.roi_map_generator import ROIMapGenerator
from dvha.tools.roi_name_manager import clean_name
from time import sleep


class ROIMapFrame(wx.Frame):
    """
    Class to view and edit roi map
    """

    def __init__(self, roi_map):
        """
        :param roi_map: roi map object
        :type roi_map: DatabaseROIs
        """
        wx.Frame.__init__(self, None, title="ROI Map")
        set_frame_icon(self)

        self.is_edited = False

        self.roi_map = roi_map

        self.window_size = get_window_size(0.893, 0.762)
        self.SetSize(self.window_size)
        self.window = wx.SplitterWindow(self, wx.ID_ANY)
        self.window_tree = wx.Panel(
            self.window, wx.ID_ANY, style=wx.BORDER_SUNKEN
        )

        self.combo_box_tree_plot_data = wx.ComboBox(
            self.window_tree,
            wx.ID_ANY,
            choices=["All", "Linked", "Unlinked", "Branched"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )

        self.plot = PlotROIMap(self.window_tree, roi_map)
        self.window_editor = wx.Panel(
            self.window, wx.ID_ANY, style=wx.BORDER_SUNKEN
        )

        self.combo_box_physician = wx.ComboBox(
            self.window_editor,
            wx.ID_ANY,
            choices=self.roi_map.get_physicians(),
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_physician_roi = wx.ComboBox(
            self.window_editor,
            wx.ID_ANY,
            choices=[],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        roi_type_choices = Options().ROI_TYPES
        self.combo_box_roi_type = wx.ComboBox(
            self.window_editor,
            wx.ID_ANY,
            choices=roi_type_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.list_ctrl_variations = wx.ListCtrl(
            self.window_editor,
            wx.ID_ANY,
            style=wx.LC_NO_HEADER | wx.LC_REPORT | wx.BORDER_SUNKEN,
        )
        self.button_variation_select_all = wx.Button(
            self.window_editor, wx.ID_ANY, "Select All"
        )
        self.button_variation_deselect_all = wx.Button(
            self.window_editor, wx.ID_ANY, "Deselect All"
        )
        self.button_variation_add = wx.Button(
            self.window_editor, wx.ID_ANY, "Add"
        )
        self.button_variation_delete = wx.Button(
            self.window_editor, wx.ID_ANY, "Delete"
        )
        self.button_variation_move = wx.Button(
            self.window_editor, wx.ID_ANY, "Move"
        )

        self.button_variation_move.Disable()
        self.button_variation_delete.Disable()
        self.button_variation_deselect_all.Disable()

        self.button_physician = {
            "add": wx.Button(self.window_editor, wx.ID_ANY, "+"),
            "del": wx.Button(self.window_editor, wx.ID_ANY, "-"),
            "edit": wx.Button(self.window_editor, wx.ID_ANY, "Δ"),
        }
        self.button_physician_roi = {
            "add": wx.Button(self.window_editor, wx.ID_ANY, "+"),
            "del": wx.Button(self.window_editor, wx.ID_ANY, "-"),
            "edit": wx.Button(self.window_editor, wx.ID_ANY, "Δ"),
        }

        self.button_link_physician_roi = wx.Button(
            self.window_editor, wx.ID_ANY, "Link"
        )
        self.button_link_physician_roi.Disable()

        self.combo_box_uncategorized_ignored = wx.ComboBox(
            self.window_editor,
            wx.ID_ANY,
            choices=["Uncategorized", "Ignored"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_uncategorized_ignored_roi = wx.ComboBox(
            self.window_editor, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN
        )
        self.button_uncategorized_ignored_delete = wx.Button(
            self.window_editor, wx.ID_ANY, "Delete DVH"
        )
        self.button_uncategorized_ignored_ignore = wx.Button(
            self.window_editor, wx.ID_ANY, "Ignore DVH"
        )
        self.combo_box_physician_roi_merge = {
            "a": wx.ComboBox(
                self.window_editor,
                wx.ID_ANY,
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "b": wx.ComboBox(
                self.window_editor,
                wx.ID_ANY,
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
        }
        self.button_merge = wx.Button(self.window_editor, wx.ID_ANY, "Merge")

        self.list_ctrl_tg263 = wx.ListCtrl(
            self.window_editor,
            wx.ID_ANY,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN,
        )
        self.roi_map_gen = ROIMapGenerator()
        self.roi_map_gen.prep_data_for_roi_map_gui()
        self.data_table_tg263 = DataTable(
            self.list_ctrl_tg263, columns=self.roi_map_gen.keys
        )
        combo_map = {
            "anatomy": self.roi_map_gen.anatomic_groups,
            "target": self.roi_map_gen.target_types,
            "major": self.roi_map_gen.major_categories,
            "minor": self.roi_map_gen.minor_categories,
        }
        self.combo_box_tg263 = {
            key: wx.ComboBox(
                self.window_editor,
                wx.ID_ANY,
                choices=["All"] + choices,
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            )
            for key, choices in combo_map.items()
        }

        self.button_save_and_update = wx.Button(
            self.window_editor, wx.ID_ANY, "Save and Update Database"
        )
        self.button_cancel = wx.Button(
            self.window_editor, wx.ID_ANY, "Cancel Changes and Reload"
        )

        self.uncategorized_variations = {}

        self.columns = ["Variations"]
        self.data_table = DataTable(
            self.list_ctrl_variations, columns=self.columns, widths=[490]
        )

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.plot.update_roi_map_source_data(self.physician)

        self.physicians_to_delete = []

        self.run()

    def __set_properties(self):
        self.combo_box_uncategorized_ignored.SetSelection(0)
        self.button_uncategorized_ignored_ignore.SetMinSize((110, 20))

        self.combo_box_physician.SetValue("DEFAULT")
        self.update_physician_rois()
        self.update_variations()

        self.combo_box_physician.SetValue("DEFAULT")
        self.combo_box_tree_plot_data.SetValue("ALL")

        self.update_uncategorized_ignored_choices()

        self.window_tree.SetBackgroundColour("white")

        for button in self.button_physician.values():
            button.SetMaxSize((25, 25))
        for button in self.button_physician_roi.values():
            button.SetMaxSize((25, 25))

        self.update_physician_enable()
        self.update_merge_physician_rois()

        if (
            is_windows()
        ):  # combo_boxes here display a doubled bottom border on MSW
            combo_boxes = [
                self.combo_box_physician,
                self.combo_box_physician_roi,
                self.combo_box_roi_type,
                self.combo_box_uncategorized_ignored,
                self.combo_box_uncategorized_ignored_roi,
                self.combo_box_physician_roi_merge["a"],
                self.combo_box_physician_roi_merge["b"],
            ]
            for combo_box in combo_boxes:
                combo_box.SetMinSize((combo_box.GetSize()[0], 26))
            self.button_uncategorized_ignored_ignore.SetMinSize(
                (
                    self.button_uncategorized_ignored_ignore.GetSize()[0],
                    self.button_uncategorized_ignored_delete.GetSize()[1],
                )
            )

        self.data_table_tg263.set_data(
            self.roi_map_gen.tg_263, columns=self.roi_map_gen.keys
        )
        self.data_table_tg263.set_column_widths(auto=True)
        for combo_box in self.combo_box_tg263.values():
            combo_box.SetValue("All")

        # These combo_boxes get a height of 30 since adding TG263 combo_boxes?
        for combo_box in self.combo_box_physician_roi_merge.values():
            combo_box.SetMaxSize((1000, 26))
        self.combo_box_physician_roi.SetMaxSize((1000, 26))
        self.combo_box_roi_type.SetMaxSize((1000, 26))

        self.combo_box_roi_type.SetValue(
            self.roi_map.get_roi_type(self.physician, self.physician_roi)
        )

    def __do_bind(self):
        self.window_tree.Bind(
            wx.EVT_COMBOBOX,
            self.on_plot_data_type_change,
            id=self.combo_box_tree_plot_data.GetId(),
        )

        self.window_editor.Bind(
            wx.EVT_COMBOBOX,
            self.update_uncategorized_ignored_choices,
            id=self.combo_box_uncategorized_ignored.GetId(),
        )

        self.window_editor.Bind(
            wx.EVT_COMBOBOX,
            self.physician_ticker,
            id=self.combo_box_physician.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_COMBOBOX,
            self.physician_roi_ticker,
            id=self.combo_box_physician_roi.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_COMBOBOX,
            self.update_roi_type_in_map,
            id=self.combo_box_roi_type.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_COMBOBOX,
            self.uncategorized_ticker,
            id=self.combo_box_uncategorized_ignored.GetId(),
        )

        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.add_physician,
            id=self.button_physician["add"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.on_delete_physician,
            id=self.button_physician["del"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.on_edit_physician,
            id=self.button_physician["edit"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.on_link_physician_roi,
            id=self.button_link_physician_roi.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.add_physician_roi,
            id=self.button_physician_roi["add"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.on_delete_physician_roi,
            id=self.button_physician_roi["del"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.on_edit_physician_roi,
            id=self.button_physician_roi["edit"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.select_all_variations,
            id=self.button_variation_select_all.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.deselect_all_variations,
            id=self.button_variation_deselect_all.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.add_variation,
            id=self.button_variation_add.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.move_variations,
            id=self.button_variation_move.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.delete_variations,
            id=self.button_variation_delete.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.on_delete_dvh,
            id=self.button_uncategorized_ignored_delete.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.on_ignore_dvh,
            id=self.button_uncategorized_ignored_ignore.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON, self.on_merge, id=self.button_merge.GetId()
        )

        for combo_box in self.combo_box_tg263.values():
            self.window_editor.Bind(
                wx.EVT_COMBOBOX, self.update_tg263_table, id=combo_box.GetId()
            )
        self.window_editor.Bind(
            wx.EVT_LIST_COL_CLICK, self.sort_tg263_table, self.list_ctrl_tg263
        )

        self.window_editor.Bind(
            wx.EVT_BUTTON,
            self.save_and_update,
            id=self.button_save_and_update.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_BUTTON, self.on_cancel, id=self.button_cancel.GetId()
        )
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.window_editor.Bind(
            wx.EVT_COMBOBOX,
            self.update_merge_enable,
            id=self.combo_box_physician_roi_merge["a"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_COMBOBOX,
            self.update_merge_enable,
            id=self.combo_box_physician_roi_merge["b"].GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            self.update_button_variation_enable,
            id=self.list_ctrl_variations.GetId(),
        )
        self.window_editor.Bind(
            wx.EVT_LIST_ITEM_DESELECTED,
            self.update_button_variation_enable,
            id=self.list_ctrl_variations.GetId(),
        )

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_editor = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_merger = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi_merger_merge = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_b = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_a = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored = wx.StaticBoxSizer(
            wx.StaticBox(
                self.window_editor, wx.ID_ANY, "Uncategorized / Ignored"
            ),
            wx.HORIZONTAL,
        )
        sizer_uncategorized_ignored_ignore = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_delete = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_type = wx.BoxSizer(wx.VERTICAL)
        sizer_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_tree_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tree_plot_data = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_manager = wx.BoxSizer(wx.VERTICAL)
        sizer_variation_buttons = wx.BoxSizer(wx.VERTICAL)
        sizer_variation_table = wx.BoxSizer(wx.VERTICAL)
        sizer_map_editor = wx.StaticBoxSizer(
            wx.StaticBox(self.window_editor, wx.ID_ANY, "ROI Map Editor"),
            wx.VERTICAL,
        )
        sizer_variations = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_row = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi_row = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tg263 = wx.StaticBoxSizer(
            wx.StaticBox(
                self.window_editor, wx.ID_ANY, "TG-263 (for reference)"
            ),
            wx.VERTICAL,
        )
        sizer_tg263_filters = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tg263_col = {
            key: wx.BoxSizer(wx.VERTICAL) for key in list(self.combo_box_tg263)
        }
        sizer_tg263_table = wx.BoxSizer(wx.VERTICAL)
        sizer_save_cancel_buttons = wx.BoxSizer(wx.HORIZONTAL)

        label_physician = wx.StaticText(
            self.window_editor, wx.ID_ANY, "Physician:"
        )
        sizer_physician.Add(label_physician, 0, 0, 0)
        sizer_physician_row.Add(
            self.combo_box_physician, 1, wx.EXPAND | wx.RIGHT, 5
        )
        sizer_physician_row.Add(
            self.button_physician["add"], 0, wx.LEFT | wx.RIGHT, 5
        )
        sizer_physician_row.Add(self.button_physician["del"], 0, wx.RIGHT, 5)
        sizer_physician_row.Add(self.button_physician["edit"], 0, wx.RIGHT, 10)
        sizer_physician.Add(sizer_physician_row, 1, wx.EXPAND, 0)

        self.label_physician_roi = wx.StaticText(
            self.window_editor, wx.ID_ANY, "Institutional ROI:"
        )
        self.label_roi_type = wx.StaticText(
            self.window_editor, wx.ID_ANY, "ROI Type:"
        )

        sizer_physician_roi_select = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_select.Add(self.label_physician_roi, 0, 0, 0)
        sizer_physician_roi_select.Add(
            self.combo_box_physician_roi, 1, wx.EXPAND | wx.RIGHT, 5
        )

        sizer_roi_type_select = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_type_select.Add(self.label_roi_type, 0, 0, 0)
        sizer_roi_type_select.Add(
            self.combo_box_roi_type, 1, wx.EXPAND | wx.RIGHT, 5
        )

        sizer_physician_roi_spacer = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_spacer.Add((20, 15), 0, 0, 0)
        sizer_physician_roi_row.Add(
            self.button_link_physician_roi,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_physician_roi_row.Add(
            self.button_physician_roi["add"], 0, wx.LEFT | wx.RIGHT, 5
        )
        sizer_physician_roi_row.Add(
            self.button_physician_roi["del"], 0, wx.RIGHT, 5
        )
        sizer_physician_roi_row.Add(
            self.button_physician_roi["edit"], 0, wx.RIGHT, 10
        )
        sizer_physician_roi_spacer.Add(sizer_physician_roi_row)

        sizer_physician_roi.Add(
            sizer_physician_roi_select, 1, wx.EXPAND | wx.RIGHT, 5
        )
        sizer_physician_roi.Add(
            sizer_roi_type_select, 0, wx.EXPAND | wx.RIGHT, 5
        )
        sizer_physician_roi.Add(sizer_physician_roi_spacer, 0, wx.EXPAND, 0)

        sizer_map_editor.Add(sizer_physician, 0, wx.ALL | wx.EXPAND, 5)
        sizer_map_editor.Add(sizer_physician_roi, 0, wx.ALL | wx.EXPAND, 5)

        label_variations = wx.StaticText(
            self.window_editor, wx.ID_ANY, "Variations:"
        )
        label_variations_buttons = wx.StaticText(
            self.window_editor, wx.ID_ANY, " "
        )
        sizer_variation_table.Add(label_variations, 0, 0, 0)
        sizer_variation_table.Add(
            self.list_ctrl_variations, 1, wx.BOTTOM | wx.EXPAND, 15
        )
        sizer_variations.Add(sizer_variation_table, 1, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(label_variations_buttons, 0, 0, 0)
        sizer_variation_buttons.Add(
            self.button_variation_add,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            5,
        )
        sizer_variation_buttons.Add(
            self.button_variation_delete, 0, wx.EXPAND | wx.ALL, 5
        )
        sizer_variation_buttons.Add(
            self.button_variation_move, 0, wx.EXPAND | wx.ALL, 5
        )
        sizer_variation_buttons.Add(
            self.button_variation_select_all, 0, wx.EXPAND | wx.ALL, 5
        )
        sizer_variation_buttons.Add(
            self.button_variation_deselect_all, 0, wx.EXPAND | wx.ALL, 5
        )
        sizer_variations.Add(sizer_variation_buttons, 0, wx.EXPAND, 0)

        sizer_map_editor.Add(sizer_variations, 0, wx.EXPAND, 0)

        label_physician_roi_a = wx.StaticText(
            self.window_editor, wx.ID_ANY, "Merge Physician ROI A:"
        )
        sizer_physician_roi_a.Add(
            label_physician_roi_a, 0, wx.EXPAND | wx.LEFT, 5
        )
        sizer_physician_roi_a.Add(
            self.combo_box_physician_roi_merge["a"],
            1,
            wx.EXPAND | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_physician_roi_merger.Add(sizer_physician_roi_a, 1, wx.EXPAND, 0)
        label_physician_roi_b = wx.StaticText(
            self.window_editor, wx.ID_ANY, "Into Physician ROI B:"
        )
        sizer_physician_roi_b.Add(label_physician_roi_b, 0, wx.EXPAND, 0)
        sizer_physician_roi_b.Add(
            self.combo_box_physician_roi_merge["b"],
            1,
            wx.EXPAND | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_physician_roi_merger.Add(sizer_physician_roi_b, 1, wx.EXPAND, 0)
        sizer_physician_roi_merger_merge.Add((20, 16), 0, 0, 0)
        sizer_physician_roi_merger_merge.Add(self.button_merge, 0, wx.ALL, 5)
        sizer_physician_roi_merger.Add(
            sizer_physician_roi_merger_merge, 0, wx.ALL | wx.EXPAND, 0
        )
        sizer_map_editor.Add(sizer_physician_roi_merger, 0, wx.EXPAND, 0)

        sizer_save_cancel_buttons.Add(
            self.button_save_and_update, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 40
        )
        sizer_save_cancel_buttons.Add(
            self.button_cancel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 40
        )
        sizer_map_editor.Add((10, 10), 0, 0, 0)
        sizer_map_editor.Add(
            sizer_save_cancel_buttons, 0, wx.EXPAND | wx.ALL, 5
        )

        sizer_roi_manager.Add(sizer_map_editor, 1, wx.EXPAND, 0)
        sizer_editor.Add(sizer_roi_manager, 0, wx.EXPAND | wx.ALL, 5)

        label_tree_plot_data = wx.StaticText(
            self.window_tree, wx.ID_ANY, "Institutional Data to Display:"
        )
        sizer_tree_plot_data.Add(
            label_tree_plot_data, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5
        )
        sizer_tree_plot_data.Add(
            self.combo_box_tree_plot_data,
            0,
            wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT,
            5,
        )

        sizer_tree_input.Add(
            sizer_tree_plot_data, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5
        )

        sizer_tree.Add(sizer_tree_input, 0, wx.EXPAND, 0)
        sizer_tree.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.window_tree.SetSizer(sizer_tree)

        label_uncategorized_ignored = wx.StaticText(
            self.window_editor, wx.ID_ANY, "Type:"
        )
        label_uncategorized_ignored.SetMinSize((38, 16))
        sizer_uncategorized_ignored_type.Add(
            label_uncategorized_ignored,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            5,
        )
        sizer_uncategorized_ignored_type.Add(
            self.combo_box_uncategorized_ignored,
            1,
            wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_uncategorized_ignored.Add(
            sizer_uncategorized_ignored_type, 1, wx.EXPAND, 0
        )
        label_uncategorized_ignored_roi = wx.StaticText(
            self.window_editor, wx.ID_ANY, "ROI:"
        )
        label_uncategorized_ignored_roi.SetMinSize((30, 16))
        sizer_uncategorized_ignored_roi.Add(
            label_uncategorized_ignored_roi,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            5,
        )
        sizer_uncategorized_ignored_roi.Add(
            self.combo_box_uncategorized_ignored_roi,
            1,
            wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_uncategorized_ignored.Add(
            sizer_uncategorized_ignored_roi, 1, wx.EXPAND, 0
        )
        sizer_uncategorized_ignored_delete.Add((20, 16), 0, 0, 0)
        sizer_uncategorized_ignored_delete.Add(
            self.button_uncategorized_ignored_delete, 0, wx.ALL, 5
        )
        sizer_uncategorized_ignored.Add(
            sizer_uncategorized_ignored_delete, 0, wx.EXPAND, 0
        )
        sizer_uncategorized_ignored_ignore.Add((20, 16), 0, 0, 0)
        sizer_uncategorized_ignored_ignore.Add(
            self.button_uncategorized_ignored_ignore, 0, wx.ALL, 5
        )
        sizer_uncategorized_ignored.Add(
            sizer_uncategorized_ignored_ignore, 0, wx.EXPAND, 0
        )
        sizer_editor.Add(sizer_uncategorized_ignored, 0, wx.ALL | wx.EXPAND, 5)

        sizer_tg263_table.Add(self.list_ctrl_tg263, 1, wx.EXPAND, 0)

        label_tg263 = {
            key: wx.StaticText(
                self.window_editor, wx.ID_ANY, key.capitalize() + ":"
            )
            for key in list(self.combo_box_tg263)
        }
        for key in ["major", "minor", "anatomy", "target"]:
            sizer_tg263_col[key].Add(label_tg263[key])
            sizer_tg263_col[key].Add(
                self.combo_box_tg263[key], 0, wx.EXPAND, 0
            )
            sizer_tg263_filters.Add(sizer_tg263_col[key], 0, wx.EXPAND, 0)

        sizer_tg263.Add(sizer_tg263_filters, 0, 0, 0)
        sizer_tg263.Add(sizer_tg263_table, 1, wx.EXPAND, 0)
        sizer_editor.Add(sizer_tg263, 1, wx.EXPAND | wx.ALL, 5)

        self.window_editor.SetSizer(sizer_editor)
        self.window.SplitVertically(self.window_tree, self.window_editor)
        self.window.SetSashPosition(int(self.window_size[0] * 0.55))
        sizer_wrapper.Add(self.window, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Centre()

    def run(self):
        self.Show()

    @staticmethod
    def update_combo_box_choices(combo_box, choices, value):
        if not value:
            value = combo_box.GetValue()
        combo_box.Clear()
        combo_box.AppendItems(sorted(choices))
        combo_box.SetValue(value)

    def update_roi_map(self):
        self.plot.update_roi_map_source_data(
            self.physician,
            plot_type=self.plot_data_type,
            y_shift=self.combo_box_physician_roi.GetValue(),
        )

    @property
    def physician(self):
        return self.combo_box_physician.GetValue()

    @property
    def physician_roi(self):
        return self.combo_box_physician_roi.GetValue()

    @property
    def physician_roi_type(self):
        return self.combo_box_roi_type.GetValue()

    @property
    def plot_data_type(self):
        return self.combo_box_tree_plot_data.GetValue()

    def physician_ticker(self, evt):
        self.update_physician_roi_label()
        self.update_physician_enable()
        self.update_all(skip_physicians=True)

    def on_plot_data_type_change(self, evt):
        self.update_roi_map()

    def update_uncategorized_ignored_choices(self, *args):
        ignored_variations = (
            self.combo_box_uncategorized_ignored.GetValue() == "Ignored"
        )
        self.uncategorized_variations = self.get_uncategorized_variations(
            self.physician, ignored_variations=ignored_variations
        )
        choices = list(self.uncategorized_variations)
        choices.sort()
        if not choices:
            choices = ["None"]
            self.button_uncategorized_ignored_delete.Disable()
            self.button_uncategorized_ignored_ignore.Disable()
        else:
            self.button_uncategorized_ignored_delete.Enable()
            self.button_uncategorized_ignored_ignore.Enable()
        self.combo_box_uncategorized_ignored_roi.Clear()
        self.combo_box_uncategorized_ignored_roi.Append(choices)
        self.combo_box_uncategorized_ignored_roi.SetValue(choices[0])

    @staticmethod
    def get_uncategorized_variations(physician, ignored_variations=False):
        if echo_sql_db():
            with DVH_SQL() as cnx:
                physician = clean_name(physician).upper()
                condition = (
                    "physician_roi = '%s'"
                    % ["uncategorized", "ignored"][ignored_variations]
                )
                cursor_rtn = cnx.query(
                    "dvhs", "roi_name, study_instance_uid", condition
                )
                new_variations = {}
                for row in cursor_rtn:
                    variation = str(row[0])
                    study_instance_uid = str(row[1])
                    physician_db = cnx.get_unique_values(
                        "Plans",
                        "physician",
                        "study_instance_uid = '%s'" % study_instance_uid,
                    )
                    if physician_db and physician_db[0] == physician:
                        if variation not in list(new_variations):
                            new_variations[variation] = {
                                "roi_name": variation,
                                "study_instance_uid": [study_instance_uid],
                            }
                        else:
                            new_variations[variation][
                                "study_instance_uid"
                            ].append(study_instance_uid)
                return new_variations

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl_variations)

    def update_button_variation_enable(self, *args):
        if self.selected_indices:
            self.button_variation_move.Enable()
            self.button_variation_delete.Enable()
            self.button_variation_deselect_all.Enable()
        else:
            self.button_variation_move.Disable()
            self.button_variation_delete.Disable()
            self.button_variation_deselect_all.Disable()

        self.button_variation_select_all.Enable(self.variation_count > 0)

    def update_variations(self):
        self.data_table.set_data(self.variation_table_data, self.columns)
        self.update_button_variation_enable()

    def physician_roi_ticker(self, evt):
        self.update_variations()
        self.update_roi_map()
        self.update_roi_type_combo_box()

    def update_physicians(self, old_physicians=None):

        choices = list(self.roi_map.physicians)
        new = choices[0]
        if old_physicians:
            new = list(set(choices) - set(old_physicians))
            if new:
                new = clean_name(new[0]).upper()

        self.update_combo_box_choices(self.combo_box_physician, choices, new)
        self.update_physician_roi_label()
        self.update_physician_enable()

    def update_physician_rois(self, old_physician_rois=None):
        choices = self.roi_map.get_physician_rois(self.physician)
        new = choices[0]
        if old_physician_rois:
            new = list(set(choices) - set(old_physician_rois))
            if new:
                new = new[0]
        self.update_combo_box_choices(
            self.combo_box_physician_roi, choices, new
        )

    def update_roi_type_combo_box(self):
        roi_type = self.roi_map.get_roi_type(
            self.physician, self.physician_roi
        )
        self.combo_box_roi_type.SetValue(roi_type)

    def update_roi_type_in_map(self, evt):
        self.roi_map.set_roi_type(
            self.physician, self.physician_roi, self.physician_roi_type
        )
        self.is_edited = True

    @property
    def variations(self):
        variations = self.roi_map.get_variations(
            self.physician, self.physician_roi
        )
        variations = list(
            set(variations) - {self.physician_roi}
        )  # remove physician roi
        variations.sort()
        return variations

    @property
    def variation_table_data(self):
        return {"Variations": self.variations}

    def add_physician_roi(self, evt):
        old_physician_rois = self.roi_map.get_physician_rois(self.physician)
        dlg = AddPhysicianROI(
            self,
            self.physician,
            self.roi_map,
            institutional_mode=self.physician == "DEFAULT",
        )
        if dlg.res == wx.ID_OK:
            self.update_all(
                old_physician_rois=old_physician_rois, skip_physicians=True
            )
            self.is_edited = True

    def add_physician(self, evt):
        old_physicians = list(self.roi_map.physicians)
        dlg = AddPhysician(self.roi_map)
        if dlg.res == wx.ID_OK:
            self.update_all(old_physicians=old_physicians)
            self.is_edited = True

    @property
    def variation_count(self):
        return len(self.variations)

    @property
    def selected_values(self):
        return [
            self.list_ctrl_variations.GetItem(i, 0).GetText()
            for i in self.selected_indices
        ]

    def select_all_variations(self, evt):
        self.apply_global_selection()

    def deselect_all_variations(self, evt):
        self.apply_global_selection(on=0)

    def apply_global_selection(self, on=1):
        for i in range(self.variation_count):
            self.list_ctrl_variations.Select(i, on=on)

    def delete_variations(self, evt):
        self.is_edited = True
        self.roi_map.delete_variations(
            self.physician, self.physician_roi, self.selected_values
        )
        self.update_variations()
        self.update_roi_map()

    def add_variation(self, evt):
        self.is_edited = True
        AddVariation(self, self.physician, self.roi_map, self.physician_roi)
        self.update_variations()
        self.update_roi_map()

    def move_variations(self, evt):
        self.is_edited = True
        choices = [
            roi
            for roi in self.roi_map.get_physician_rois(self.physician)
            if roi != self.physician_roi
        ]
        MoveVariationDialog(
            self,
            self.selected_values,
            self.physician,
            self.physician_roi,
            choices,
            self.roi_map,
        )
        self.update_variations()
        self.update_roi_map()

    def on_delete_physician(self, evt):
        MessageDialog(
            self,
            "Delete Physician %s?" % self.physician,
            action_yes_func=self.delete_physician,
        )

    def delete_physician(self):
        self.is_edited = True
        self.roi_map.delete_physician(self.physician)
        self.physicians_to_delete.append(self.physician)
        self.update_all()

    def on_delete_physician_roi(self, evt):
        if self.physician == "DEFAULT":
            MessageDialog(
                self,
                "Delete Institutional ROI %s?" % self.physician_roi,
                action_yes_func=self.delete_institutional_roi,
            )
        else:
            MessageDialog(
                self,
                "Delete Physician ROI %s?" % self.physician_roi,
                action_yes_func=self.delete_physician_roi,
            )

    def delete_physician_roi(self):
        self.is_edited = True
        self.roi_map.delete_physician_roi(self.physician, self.physician_roi)
        self.update_all(skip_physicians=True)

    def delete_institutional_roi(self):
        self.is_edited = True
        self.roi_map.delete_institutional_roi(self.physician_roi)
        self.update_all(skip_physicians=True)

    def on_delete_dvh(self, evt):
        MessageDialog(
            self,
            "Delete all DVHs named %s for %s?" % (self.dvh, self.physician),
            message="Are you sure? This cannot be undone!",
            action_yes_func=self.delete_dvh,
        )

    def delete_dvh(self):
        with DVH_SQL() as cnx:
            for uid in self.dvh_uids:
                cnx.delete_dvh(self.dvh, uid)
        self.update_uncategorized_ignored_choices()

    def on_ignore_dvh(self, evt):
        msg_type = ["Unignore", "Ignore"][
            self.button_uncategorized_ignored_ignore.GetLabelText()
            == "Ignore DVH"
        ]
        MessageDialog(
            self,
            "%s all DVHs named %s for %s?"
            % (msg_type, self.dvh, self.physician),
            action_yes_func=self.ignore_dvh,
        )

    def ignore_dvh(self):
        unignore = (
            self.button_uncategorized_ignored_ignore.GetLabelText()
            == "Unignore DVH"
        )
        with DVH_SQL() as cnx:
            for uid in self.dvh_uids:
                cnx.ignore_dvh(self.dvh, uid, unignore=unignore)
        self.update_uncategorized_ignored_choices()

    @property
    def dvh(self):
        return self.combo_box_uncategorized_ignored_roi.GetValue()

    @property
    def dvh_uids(self):
        return self.uncategorized_variations[self.dvh]["study_instance_uid"]

    def update_all(
        self,
        old_physicians=None,
        old_physician_rois=None,
        skip_physicians=False,
    ):
        if not skip_physicians:
            self.update_physicians(old_physicians=old_physicians)
        self.update_physician_rois(old_physician_rois=old_physician_rois)
        self.update_variations()
        self.update_uncategorized_ignored_choices()
        self.update_merge_physician_rois()
        self.update_roi_map()

    def on_edit_physician(self, evt):
        current_physicians = list(self.roi_map.get_physicians())
        dlg = RenamePhysicianDialog(self.physician, self.roi_map)
        if dlg.res == wx.ID_OK:
            self.is_edited = True
            self.update_all(old_physicians=current_physicians)

    def on_edit_physician_roi(self, evt):
        current_physician_rois = self.roi_map.get_physician_rois(
            self.physician
        )
        if self.physician == "DEFAULT":
            dlg = RenameInstitutionalROIDialog(
                self.physician_roi, self.roi_map
            )
        else:
            dlg = RenamePhysicianROIDialog(
                self.physician, self.physician_roi, self.roi_map
            )
        if dlg.res == wx.ID_OK:
            self.is_edited = True
            self.update_all(
                old_physician_rois=current_physician_rois, skip_physicians=True
            )

    def update_physician_enable(self):
        self.button_physician["del"].Enable(self.physician != "DEFAULT")
        self.button_physician["edit"].Enable(self.physician != "DEFAULT")
        self.button_variation_add.Enable(self.physician != "DEFAULT")

    def update_physician_roi_label(self):
        label_text = ["Physician ROI:", "Institutional ROI:"][
            self.physician == "DEFAULT"
        ]
        self.label_physician_roi.SetLabelText(label_text)
        self.button_link_physician_roi.Enable(self.physician != "DEFAULT")

    def uncategorized_ticker(self, evt):
        if self.combo_box_uncategorized_ignored.GetValue() == "Uncategorized":
            self.button_uncategorized_ignored_ignore.SetLabelText("Ignore DVH")
        else:
            self.button_uncategorized_ignored_ignore.SetLabelText(
                "Unignore DVH"
            )
        self.update_uncategorized_ignored_choices()

    def update_merge_physician_rois(self):
        options = []
        if self.physician != "DEFAULT":
            options = self.roi_map.get_physician_rois(self.physician)
        if not options:
            options = [""]
        for combo_box in self.combo_box_physician_roi_merge.values():
            combo_box.Clear()
            combo_box.Append(options)
            combo_box.SetValue(options[0])
        self.update_merge_enable()

    @property
    def merge_a(self):
        return self.combo_box_physician_roi_merge["a"].GetValue()

    @property
    def merge_b(self):
        return self.combo_box_physician_roi_merge["b"].GetValue()

    def on_merge(self, evt):
        self.is_edited = True
        self.roi_map.merge_physician_rois(
            self.physician, [self.merge_a, self.merge_b], self.merge_b
        )
        self.update_all(skip_physicians=True)

    def update_merge_enable(self, *args):  # *args to catch wx.EVT_BUTTON
        self.combo_box_physician_roi_merge["a"].Enable(
            bool(self.merge_a and self.merge_b)
        )
        self.combo_box_physician_roi_merge["b"].Enable(
            bool(self.merge_a and self.merge_b)
        )
        self.button_merge.Enable(
            bool(self.merge_a)
            and bool(self.merge_b)
            and self.merge_a != self.merge_b
        )

    def on_link_physician_roi(self, evt):
        dlg = LinkPhysicianROI(
            self, self.physician, self.physician_roi, self.roi_map
        )
        if dlg.res == wx.ID_OK:
            self.is_edited = True
            self.update_roi_map()

    def update_tg263_table(self, *evt):
        filter_key_map = {
            "major": "Major Cat.",
            "minor": "Minor Cat.",
            "anatomy": "Anat. Group",
            "target": "Target Type",
        }
        data_filter = {
            col: self.combo_box_tg263[key].GetValue()
            for key, col in filter_key_map.items()
        }
        data = self.roi_map_gen.get_filtered_data(data_filter)
        self.data_table_tg263.set_data(data, columns=self.roi_map_gen.keys)
        self.data_table_tg263.set_column_widths(auto=True)

        self.update_tg263_combo_choices()

    def update_tg263_combo_choices(self):
        filter_key_map = {
            "major": "Major Cat.",
            "minor": "Minor Cat.",
            "anatomy": "Anat. Group",
            "target": "Target Type",
        }
        for key, col in filter_key_map.items():
            current_choice = self.combo_box_tg263[key].GetValue()
            new_choices = ["All"] + self.data_table_tg263.get_unique_values(
                col
            )
            self.combo_box_tg263[key].SetItems(new_choices)
            self.combo_box_tg263[key].SetValue(current_choice)

    def sort_tg263_table(self, evt):
        self.data_table_tg263.sort_table(evt)
        self.data_table_tg263.set_column_widths(auto=True)

    def save_and_update(self, evt):
        self.is_edited = False
        for physician in self.physicians_to_delete:
            rel_path = "physician_%s.roi" % physician
            abs_file_path = join(PREF_DIR, rel_path)
            delete_file(abs_file_path)

        RemapROIFrame(self.roi_map)

    def on_cancel(self, *args):
        self.roi_map.import_from_file()
        self.physicians_to_delete = []
        self.update_roi_map()
        self.update_physicians()

    def on_close(self, *args):
        if self.is_edited:
            MessageDialog(
                self,
                "Close without saving ROI Map?",
                action_yes_func=self.do_close,
            )
        else:
            self.do_close()

    def do_close(self):
        self.Destroy()
        self.roi_map.import_from_file()
        self.physicians_to_delete = []


class RemapROIWorker(Thread):
    """
    Create a thread to update the SQL DB with roi map changes
    """

    def __init__(self, roi_map, remap_all=False):
        """
        :param roi_map: roi map object
        :type roi_map: DatabaseROIs
        :param remap_all: If true, remap entire database
        :type remap_all: bool
        """
        Thread.__init__(self)

        self.roi_map = roi_map
        self.remap_all = remap_all
        self.start_time = datetime.now()

        self.start()  # start the thread

    def run(self):

        if self.remap_all:
            physician_to_map = self.roi_map.get_physicians()
            variations_to_update = {}
        else:
            physician_to_map = self.roi_map.physicians_to_remap
            variations_to_update = self.roi_map.variations_to_update

        with DVH_SQL() as cnx:

            physicians_in_db = cnx.get_unique_values("plans", "physician")
            physician_to_map = [
                p for p in physician_to_map if p in physicians_in_db
            ]

            physician_counter = 0
            physician_count = len(
                list(variations_to_update) + physician_to_map
            )

            # Partial physician remaps
            for physician, variations in variations_to_update.items():
                msg = [
                    "Physician (%s of %s): %s"
                    % (physician_counter + 1, physician_count, physician),
                    int(100 * physician_counter / physician_count),
                ]
                wx.CallAfter(
                    pub.sendMessage, "roi_map_update_gauge_1_info", msg=msg
                )
                variation_count = len(variations)
                variation_counter = 0

                for variation in variations:
                    variation_frac = variation_counter / variation_count
                    msg = [
                        "Physician (%s of %s): %s"
                        % (physician_counter + 1, physician_count, physician),
                        int(
                            100
                            * (
                                physician_counter / physician_count
                                + variation_frac / physician_count
                            )
                        ),
                    ]
                    wx.CallAfter(
                        pub.sendMessage, "roi_map_update_gauge_1_info", msg=msg
                    )
                    msg = [
                        "ROI Name (%s of %s): %s"
                        % (variation_counter + 1, variation_count, variation),
                        int(100 * variation_counter / variation_count),
                    ]
                    wx.CallAfter(
                        pub.sendMessage, "roi_map_update_gauge_2_info", msg=msg
                    )
                    msg = "Elapsed Time: %s" % get_elapsed_time(
                        self.start_time, datetime.now()
                    )
                    wx.CallAfter(
                        pub.sendMessage, "roi_map_update_elapsed_time", msg=msg
                    )
                    variation_counter += 1

                    self.update_variation(variation, physician, cnx)

                physician_counter += 1

            # Full Physician remaps
            for physician in physician_to_map:
                condition = "physician = '%s'" % physician
                uids = cnx.get_unique_values(
                    "Plans", "study_instance_uid", condition
                )
                if uids:
                    condition = "study_instance_uid in ('%s')" % "','".join(
                        uids
                    )
                    variations = cnx.get_unique_values(
                        "DVHs", "roi_name", condition
                    )
                    msg = [
                        "Physician (%s of %s): %s"
                        % (physician_counter + 1, physician_count, physician),
                        int(100 * physician_counter / physician_count),
                    ]
                    wx.CallAfter(
                        pub.sendMessage, "roi_map_update_gauge_1_info", msg=msg
                    )
                    variation_count = len(variations)
                    variation_counter = 0

                    for variation in variations:
                        variation_frac = variation_counter / variation_count
                        msg = [
                            "Physician (%s of %s): %s"
                            % (
                                physician_counter + 1,
                                physician_count,
                                physician,
                            ),
                            int(
                                100
                                * (
                                    physician_counter / physician_count
                                    + variation_frac / physician_count
                                )
                            ),
                        ]
                        wx.CallAfter(
                            pub.sendMessage,
                            "roi_map_update_gauge_1_info",
                            msg=msg,
                        )
                        msg = [
                            "ROI (%s of %s): %s"
                            % (
                                variation_counter + 1,
                                variation_count,
                                variation,
                            ),
                            int(100 * variation_frac),
                        ]
                        wx.CallAfter(
                            pub.sendMessage,
                            "roi_map_update_gauge_2_info",
                            msg=msg,
                        )
                        msg = "Elapsed Time: %s" % get_elapsed_time(
                            self.start_time, datetime.now()
                        )
                        wx.CallAfter(
                            pub.sendMessage,
                            "roi_map_update_elapsed_time",
                            msg=msg,
                        )
                        variation_counter += 1

                        self.update_variation(variation, physician, cnx)

                    physician_counter += 1

            msg = [
                "Physician (%s of %s): %s"
                % (physician_counter, physician_count, physician),
                100,
            ]
            wx.CallAfter(
                pub.sendMessage, "roi_map_update_gauge_1_info", msg=msg
            )
            msg = [
                "ROI (%s of %s): %s"
                % (variation_counter, variation_count, variation),
                100,
            ]
            wx.CallAfter(
                pub.sendMessage, "roi_map_update_gauge_2_info", msg=msg
            )
            sleep(0.2)

        wx.CallAfter(pub.sendMessage, "roi_map_close")

    def update_variation(self, variation, physician, cnx):

        new_physician_roi = self.roi_map.get_physician_roi(
            physician, variation
        )
        if new_physician_roi == "uncategorized":
            new_institutional_roi = "uncategorized"
        else:
            new_institutional_roi = self.roi_map.get_institutional_roi(
                physician, new_physician_roi
            )

        condition = "roi_name = '%s'" % variation
        roi_uids = cnx.get_unique_values(
            "DVHs", "study_instance_uid", condition
        )
        if roi_uids:
            condition = "physician = '%s' and study_instance_uid in ('%s')" % (
                physician,
                "','".join(roi_uids),
            )
            uids = cnx.get_unique_values(
                "Plans", "study_instance_uid", condition
            )

            if uids:
                for i, uid in enumerate(uids):
                    condition = (
                        "roi_name = '%s' and study_instance_uid = '%s'"
                        % (variation, uid)
                    )
                    cnx.update(
                        "dvhs", "physician_roi", new_physician_roi, condition
                    )
                    cnx.update(
                        "dvhs",
                        "institutional_roi",
                        new_institutional_roi,
                        condition,
                    )
                    roi_type = self.roi_map.get_roi_type(
                        physician, new_physician_roi
                    )
                    if new_physician_roi != "uncategorized":
                        cnx.update("dvhs", "roi_type", roi_type, condition)


class RemapROIFrame(wx.Frame):
    """
    Companion class for RemapROIWorker to to display progress, Automatically calls RemapROIWorker
    """

    def __init__(self, roi_map, remap_all=False):
        """
        :param roi_map: roi map object
        :type roi_map: DatabaseROIs
        :param remap_all: If true, remap entire database
        :type remap_all: bool
        """
        wx.Frame.__init__(
            self, None, title="Updating Database with ROI Map Changes"
        )
        set_msw_background_color(self)
        set_frame_icon(self)

        self.roi_map = roi_map

        self.gauge_physician = wx.Gauge(self, wx.ID_ANY, 100)
        self.gauge_roi = wx.Gauge(self, wx.ID_ANY, 100)

        self.start_time = None

        self.__set_properties()
        self.__do_layout()
        self.__do_subscribe()

        self.Show()

        RemapROIWorker(self.roi_map, remap_all=remap_all)

    def __set_properties(self):
        self.gauge_physician.SetMinSize((358, 17))
        self.gauge_roi.SetMinSize((358, 17))

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_progress = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_roi_name = wx.BoxSizer(wx.VERTICAL)
        sizer_physician = wx.BoxSizer(wx.VERTICAL)

        self.label_physician = wx.StaticText(self, wx.ID_ANY, "Physician:")
        sizer_physician.Add(self.label_physician, 0, 0, 0)
        sizer_physician.Add(self.gauge_physician, 0, wx.EXPAND, 0)

        self.label_roi_name = wx.StaticText(self, wx.ID_ANY, "ROI Name:")
        sizer_roi_name.Add(self.label_roi_name, 0, 0, 0)
        sizer_roi_name.Add(self.gauge_roi, 0, wx.EXPAND, 0)

        sizer_progress.Add(sizer_physician, 0, wx.ALL | wx.EXPAND, 5)
        sizer_progress.Add(sizer_roi_name, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_progress, 0, wx.ALL | wx.EXPAND, 5)

        self.label_elapsed_time = wx.StaticText(
            self, wx.ID_ANY, "Elapsed Time:"
        )
        sizer_wrapper.Add(self.label_elapsed_time, 0, wx.BOTTOM | wx.LEFT, 10)

        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Layout()
        self.Center()

    def __do_subscribe(self):
        pub.subscribe(self.update_gauge_1_info, "roi_map_update_gauge_1_info")
        pub.subscribe(self.update_gauge_2_info, "roi_map_update_gauge_2_info")
        pub.subscribe(self.update_elapsed_time, "roi_map_update_elapsed_time")
        pub.subscribe(self.close, "roi_map_close")

    def close(self):
        self.roi_map.write_to_file()
        self.roi_map.import_from_file()
        self.Destroy()

    def update_gauge_1_info(self, msg):
        wx.CallAfter(self.label_physician.SetLabelText, msg[0])
        wx.CallAfter(self.gauge_physician.SetValue, msg[1])

    def update_gauge_2_info(self, msg):
        wx.CallAfter(self.label_roi_name.SetLabelText, msg[0])
        wx.CallAfter(self.gauge_roi.SetValue, msg[1])

    def update_elapsed_time(self, msg):
        wx.CallAfter(self.label_elapsed_time.SetLabelText, msg)
