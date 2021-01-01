#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.queried_data.py
"""
Class for viewing SQL table data of the current query
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from dvha.models.data_table import DataTable
from dvha.dialogs.export import save_data_to_file
from dvha.tools.utilities import (
    get_window_size,
    set_msw_background_color,
    set_frame_icon,
)


class QueriedDataFrame(wx.Frame):
    """
    Generate a simple table to view data of the current query for a specified SQL table
    """

    def __init__(self, data_obj, columns, data_key, menu, menu_item_id):
        """
        :param data_obj: object containing data to be viewed for each group
        :type data_obj: dict
        :param columns: columns to be displayed in table
        :type columns: list
        :param data_key: either 'DVHs', 'Plans', 'Beams', 'Rxs', or 'StatsData'
        :type data_key: str
        :param menu: a link to the main app menu, used to toggle Show/Hide status
        :type menu: Menu
        :param menu_item_id: the ID of the menu item associated with the specified data_obj
        """
        wx.Frame.__init__(self, None, title="%s Data" % data_key[0:-1])

        self.data = data_obj
        self.columns = columns
        self.sql_table = data_key
        self.menu = menu
        self.menu_item_id = menu_item_id

        self.list_ctrl = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.BORDER_SUNKEN
            | wx.LC_HRULES
            | wx.LC_REPORT
            | wx.LC_VRULES,
        )

        self.button_export = wx.Button(self, wx.ID_ANY, "Export to CSV")
        self.radio_button_query_group = wx.RadioBox(
            self, wx.ID_ANY, "Query Group", choices=["1", "2"]
        )

        self.data_table = DataTable(self.list_ctrl)
        self.data_table.set_data(self.table_data, self.columns)

        if not self.data[2]:
            self.radio_button_query_group.Disable()

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetSize(get_window_size(0.714, 0.762))
        set_msw_background_color(self)
        set_frame_icon(self)

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_export, id=self.button_export.GetId())
        self.Bind(wx.EVT_LIST_COL_CLICK, self.sort_table, self.list_ctrl)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(
            wx.EVT_RADIOBOX,
            self.on_group_select,
            id=self.radio_button_query_group.GetId(),
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_widgets = wx.BoxSizer(wx.HORIZONTAL)
        sizer_button = wx.BoxSizer(wx.HORIZONTAL)
        sizer_button.Add(self.button_export, 0, wx.TOP, 15)
        sizer_widgets.Add(sizer_button, 0, wx.ALL, 10)
        sizer_widgets.Add(self.radio_button_query_group, 0, wx.ALL, 10)
        sizer_wrapper.Add(sizer_widgets, 0, 0, 0)
        sizer_wrapper.Add(
            self.list_ctrl, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10
        )
        self.SetSizer(sizer_wrapper)
        self.Center()

    @property
    def table_data(self):
        return {
            column: getattr(self.selected_data, column)
            for column in self.columns
        }

    @property
    def selected_group(self):
        return self.radio_button_query_group.GetSelection() + 1

    @property
    def selected_data(self):
        return self.data[self.selected_group]

    def run(self):
        self.toggle_data_menu_item()
        self.Show()

    def on_close(self, *args):
        self.toggle_data_menu_item()
        self.Destroy()

    def on_export(self, *args):
        save_data_to_file(
            self,
            "Export Group %s %s to CSV"
            % (self.selected_group, self.sql_table),
            self.data_table.get_csv(),
        )

    def toggle_data_menu_item(self):
        short_cut = ["DVHs", "Plans", "Rxs", "Beams"].index(self.sql_table) + 1
        show_hide = ["Show", "Hide"][
            "Show" in self.menu.GetLabel(self.menu_item_id)
        ]
        self.menu.SetLabel(
            self.menu_item_id,
            "%s %s\tCtrl+%s" % (show_hide, self.sql_table, short_cut),
        )

    def sort_table(self, evt):
        self.data_table.sort_table(evt)

    def on_group_select(self, *evt):
        self.data_table.clear()
        self.data_table.set_data(self.table_data, self.columns)
