#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.database_editor.py
"""
Class for the Database Editor accessible from the main view
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics


import wx
from dvha.dialogs.database import ChangePatientIdentifierDialog, DeletePatientDialog, ReimportDialog, EditDatabaseDialog,\
    CalculationsDialog, DeleteAllData, RebuildDB, SQLErrorDialog
from dvha.db.sql_to_python import get_database_tree
from dvha.db.sql_connector import DVH_SQL, SQLError
from dvha.models.data_table import DataTable
from dvha.dialogs.export import save_data_to_file
from dvha.tools.utilities import set_msw_background_color, get_window_size, set_frame_icon
from dvha.models.roi_map import RemapROIFrame


class DatabaseEditorFrame(wx.Frame):
    """
    Various viewing and editing tools for the SQL database. This object is called on Database toolbar click.
    """
    def __init__(self, roi_map, options):
        """
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        """
        wx.Frame.__init__(self, None, title='Database Administrator')
        set_frame_icon(self)

        set_msw_background_color(self)  # If windows, change the background color

        self.roi_map = roi_map
        self.options = options
        self.db_tree = self.get_db_tree()

        self.SetSize(get_window_size(0.792, 0.781))

        self.window_db_editor = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_3D)
        self.window_pane_db_tree = wx.ScrolledWindow(self.window_db_editor, wx.ID_ANY,
                                                     style=wx.BORDER_SUNKEN | wx.TAB_TRAVERSAL)
        self.tree_ctrl_db = wx.TreeCtrl(self.window_pane_db_tree, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE)
        self.window_pane_query = wx.Panel(self.window_db_editor, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.TAB_TRAVERSAL)
        self.text_ctrl_condition = wx.TextCtrl(self.window_pane_query, wx.ID_ANY, "")
        self.list_ctrl_query_results = wx.ListCtrl(self.window_pane_query, wx.ID_ANY,
                                                   style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.data_query_results = DataTable(self.list_ctrl_query_results, columns=['mrn', 'study_instance_uid'])
        self.combo_box_query_table = wx.ComboBox(self.window_pane_query, wx.ID_ANY, choices=list(self.db_tree),
                                                 style=wx.CB_DROPDOWN | wx.CB_READONLY)

        self.button = {'delete_all_data': wx.Button(self, wx.ID_ANY, "Delete All Data"),
                       'rebuild_db': wx.Button(self, wx.ID_ANY, "Rebuild Database"),
                       # 'calculations': wx.Button(self, wx.ID_ANY, "Calculations"),
                       'edit_db': wx.Button(self, wx.ID_ANY, "Edit Database"),
                       'reimport': wx.Button(self, wx.ID_ANY, "Reimport from DICOM"),
                       'delete_study': wx.Button(self, wx.ID_ANY, "Delete Study"),
                       'change_mrn_uid': wx.Button(self, wx.ID_ANY, "Change MRN/UID"),
                       'query': wx.Button(self.window_pane_query, wx.ID_ANY, "Query"),
                       'clear': wx.Button(self.window_pane_query, wx.ID_ANY, "Clear"),
                       'export_csv': wx.Button(self.window_pane_query, wx.ID_ANY, "Export"),
                       'remap_roi_names': wx.Button(self, wx.ID_ANY, "Remap ROI Names")}

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()

        self.selected_columns = {table: {c: False for c in list(self.db_tree[table])} for table in list(self.db_tree)}
        self.selected_tables = {table: False for table in list(self.db_tree)}

        self.window_db_editor.SetSashPosition(250)
        self.tree_ctrl_db.Expand(self.db_tree_root)

        self.allow_tree_select_change = True

        self.Show()

    def __set_properties(self):
        self.SetTitle("Database Administrator")
        self.window_pane_db_tree.SetScrollRate(10, 10)
        self.window_db_editor.SetMinimumPaneSize(20)

        self.db_tree_root = self.tree_ctrl_db.AddRoot('DVH Analytics')
        self.table_nodes = {table: self.tree_ctrl_db.AppendItem(self.db_tree_root, table) for table in self.db_tree}
        self.column_nodes = {table: {} for table in self.db_tree}
        for table in self.db_tree:
            for column in self.db_tree[table]:
                self.column_nodes[table][column] = self.tree_ctrl_db.AppendItem(self.table_nodes[table], column)
        self.combo_box_query_table.SetValue('Plans')

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_query = wx.BoxSizer(wx.VERTICAL)
        sizer_query_table = wx.StaticBoxSizer(wx.StaticBox(self.window_pane_query, wx.ID_ANY, "Query Results"),
                                              wx.VERTICAL)
        sizer_condition_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_download_button = wx.BoxSizer(wx.VERTICAL)
        sizer_clear_button = wx.BoxSizer(wx.VERTICAL)
        sizer_query_button = wx.BoxSizer(wx.VERTICAL)
        sizer_condition = wx.BoxSizer(wx.VERTICAL)
        sizer_combo_box = wx.BoxSizer(wx.VERTICAL)
        sizer_db_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dialog_buttons = wx.BoxSizer(wx.HORIZONTAL)

        # sizer_dialog_buttons.Add(self.button['calculations'], 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button['edit_db'], 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button['reimport'], 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button['delete_study'], 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button['change_mrn_uid'], 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button['rebuild_db'], 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button['delete_all_data'], 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button['remap_roi_names'], 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_dialog_buttons, 0, wx.ALL, 5)

        sizer_db_tree.Add(self.tree_ctrl_db, 1, wx.EXPAND, 0)
        self.window_pane_db_tree.SetSizer(sizer_db_tree)

        label_table = wx.StaticText(self.window_pane_query, wx.ID_ANY, "Table:")
        sizer_combo_box.Add(label_table, 0, wx.BOTTOM | wx.TOP, 5)
        sizer_combo_box.Add(self.combo_box_query_table, 0, 0, 0)
        sizer_condition_buttons.Add(sizer_combo_box, 0, wx.ALL | wx.EXPAND, 5)

        label_condition = wx.StaticText(self.window_pane_query, wx.ID_ANY, "Condition:")
        sizer_condition.Add(label_condition, 0, wx.BOTTOM | wx.TOP, 5)
        sizer_condition.Add(self.text_ctrl_condition, 0, wx.ALL | wx.EXPAND, 0)
        sizer_condition_buttons.Add(sizer_condition, 1, wx.ALL | wx.EXPAND, 5)

        label_spacer_1 = wx.StaticText(self.window_pane_query, wx.ID_ANY, "")
        sizer_query_button.Add(label_spacer_1, 0, wx.BOTTOM, 5)
        sizer_query_button.Add(self.button['query'], 0, wx.ALL, 5)
        sizer_condition_buttons.Add(sizer_query_button, 0, wx.ALL, 5)

        label_spacer_2 = wx.StaticText(self.window_pane_query, wx.ID_ANY, "")
        sizer_download_button.Add(label_spacer_2, 0, wx.BOTTOM, 5)
        sizer_download_button.Add(self.button['export_csv'], 0, wx.TOP | wx.BOTTOM, 5)
        sizer_condition_buttons.Add(sizer_download_button, 0, wx.ALL, 5)

        label_spacer_3 = wx.StaticText(self.window_pane_query, wx.ID_ANY, "")
        sizer_clear_button.Add(label_spacer_3, 0, wx.BOTTOM, 5)
        sizer_clear_button.Add(self.button['clear'], 0, wx.ALL, 5)
        sizer_condition_buttons.Add(sizer_clear_button, 0, wx.ALL, 5)

        sizer_query.Add(sizer_condition_buttons, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        sizer_query_table.Add(self.list_ctrl_query_results, 1, wx.EXPAND, 0)
        sizer_query.Add(sizer_query_table, 1, wx.ALL | wx.EXPAND, 5)

        self.window_pane_query.SetSizer(sizer_query)
        self.window_db_editor.SplitVertically(self.window_pane_db_tree, self.window_pane_query)
        sizer_wrapper.Add(self.window_db_editor, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def __do_bind(self):
        # self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeAdd, self.tree_ctrl_db, id=self.tree_ctrl_db.GetId())

        # All buttons are bound to a function based on their key prepended with 'on_'
        # For example, query button calls on_query when clicked
        for key, button in self.button.items():
            self.Bind(wx.EVT_BUTTON, getattr(self, 'on_' + key), id=button.GetId())

        self.Bind(wx.EVT_LIST_COL_CLICK, self.sort_query_results, self.list_ctrl_query_results)

    def on_tree_add(self, evt):
        self.update_selected_tree_items()

    # def UnselectOtherTables(self, selected_table):
    #     self.allow_tree_select_change = False
    #     for table, node in self.table_nodes.items():
    #         if table != selected_table:
    #             self.tree_ctrl_db.UnselectItem(node)
    #     self.allow_tree_select_change = True

    def on_query(self, evt):
        self.update_selected_tree_items()
        table = self.combo_box_query_table.GetValue()
        columns = [c for c, sel in self.selected_columns[table].items()
                   if sel and c not in {'mrn', 'study_instance_uid'}]
        columns.sort()

        if not columns:
            columns = [c for c in self.db_tree[table] if c not in {'mrn', 'study_instance_uid'}]

        columns.insert(0, 'study_instance_uid')
        columns.insert(0, 'mrn')

        condition = self.text_ctrl_condition.GetValue()

        wait = wx.BusyInfo("Querying data\nPlease wait...")
        with DVH_SQL() as cnx:
            try:
                data = cnx.query(table, ','.join(columns), condition, bokeh_cds=True)
                self.data_query_results.set_data(data, columns)
            except SQLError as e:
                SQLErrorDialog(self, e)
                self.data_query_results.clear()
        del wait

    def on_clear(self, evt):
        self.data_query_results.clear()

    @staticmethod
    def get_db_tree():
        tree = get_database_tree()
        for table in list(tree):
            tree[table] = [column for column in tree[table] if 'string' not in column]
        return tree

    def update_selected_tree_items(self):
        for table, table_item in self.table_nodes.items():
            self.selected_tables[table] = self.tree_ctrl_db.IsSelected(table_item)
            for column, column_item in self.column_nodes[table].items():
                self.selected_columns[table][column] = self.tree_ctrl_db.IsSelected(column_item)

    def on_change_mrn_uid(self, evt):
        self.change_or_delete_dlg(ChangePatientIdentifierDialog)

    def on_delete_study(self, evt):
        # TODO: Needs an Are you sure? dialog
        self.change_or_delete_dlg(DeletePatientDialog)

    def change_or_delete_dlg(self, class_type):
        selected_data = self.data_query_results.selected_row_data
        if selected_data:
            class_type(mrn=selected_data[0][0], study_instance_uid=selected_data[0][1])
        else:
            class_type()

    def on_reimport(self, evt):
        selected_data = self.data_query_results.selected_row_data
        if selected_data:
            ReimportDialog(self.roi_map, self.options, mrn=selected_data[0][0], study_instance_uid=selected_data[0][1])
        else:
            ReimportDialog(self.roi_map, self.options)

    @staticmethod
    def on_edit_db(evt):
        EditDatabaseDialog()

    @staticmethod
    def on_calculations(evt):
        CalculationsDialog()

    def on_rebuild_db(self, evt):
        RebuildDB(self, self.roi_map, self.options)

    def on_delete_all_data(self, evt):
        DeleteAllData(self)

    def on_export_csv(self, evt):
        save_data_to_file(self, "Export Data Table to CSV", self.data_query_results.get_csv())

    def on_remap_roi_names(self, evt):
        RemapROIFrame(self.roi_map, remap_all=True)

    def sort_query_results(self, evt):
        self.data_query_results.sort_table(evt)
