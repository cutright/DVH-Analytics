#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import wx
from dialogs.database.sql_settings import SQLSettingsDialog
from dialogs.database.change_or_delete_patient import ChangePatientIdentifierDialog, DeletePatientDialog
from dialogs.database.reimport import ReimportDialog
from dialogs.database.edit_db import EditDatabaseDialog
from dialogs.database.post_import_calculations import PostImportCalculationsDialog
from db.sql_settings import write_sql_connection_settings, validate_sql_connection
from db.sql_to_python import get_database_tree
from db.sql_connector import DVH_SQL
from models.datatable import DataTable


class DatabaseEditorDialog(wx.Frame):
    def __init__(self, *args, **kwds):
        wx.Frame.__init__(self, None, title='Database Administrator')

        self.db_tree = self.get_db_tree()

        self.SetSize((1330, 820))
        self.button_sql_connection = wx.Button(self, wx.ID_ANY, "SQL Connection")
        self.button_rebuild_db = wx.Button(self, wx.ID_ANY, "Rebuild Database")
        self.button_post_import_calc = wx.Button(self, wx.ID_ANY, "Post-Import Calculations")
        self.button_edit_db = wx.Button(self, wx.ID_ANY, "Edit Database")
        self.button_reimport = wx.Button(self, wx.ID_ANY, "Reimport from DICOM")
        self.button_delete_study = wx.Button(self, wx.ID_ANY, "Delete Study")
        self.button_change_mrn_uid = wx.Button(self, wx.ID_ANY, "Change MRN/UID")
        self.window_db_editor = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_3D)
        self.window_pane_db_tree = wx.ScrolledWindow(self.window_db_editor, wx.ID_ANY,
                                                     style=wx.BORDER_SUNKEN | wx.TAB_TRAVERSAL)
        self.tree_ctrl_db = wx.TreeCtrl(self.window_pane_db_tree, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE)
        self.window_pane_query = wx.Panel(self.window_db_editor, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.TAB_TRAVERSAL)
        self.text_ctrl_condition = wx.TextCtrl(self.window_pane_query, wx.ID_ANY, "")
        self.button_query = wx.Button(self.window_pane_query, wx.ID_ANY, "Query")
        self.button_download = wx.Button(self.window_pane_query, wx.ID_ANY, "Download")
        self.list_ctrl_query_results = wx.ListCtrl(self.window_pane_query, wx.ID_ANY,
                                                   style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.data_query_results = DataTable(self.list_ctrl_query_results, columns=['mrn', 'study_instance_uid'])
        self.combo_box_query_table = wx.ComboBox(self.window_pane_query, wx.ID_ANY, choices=list(self.db_tree),
                                                 style=wx.CB_DROPDOWN | wx.CB_READONLY)

        self.Bind(wx.EVT_BUTTON, self.OnSQLSettings, id=self.button_sql_connection.GetId())
        # self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeAdd, self.tree_ctrl_db, id=self.tree_ctrl_db.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnQuery, id=self.button_query.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnPostImportCalc, id=self.button_post_import_calc.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnEditDB, id=self.button_edit_db.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnReimport, id=self.button_reimport.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnDeletePatient, id=self.button_delete_study.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnChangePatientIdentifier, id=self.button_change_mrn_uid.GetId())

        self.__set_properties()
        self.__do_layout()

        self.selected_columns = {table: {c: False for c in list(self.db_tree[table])} for table in list(self.db_tree)}
        self.selected_tables = {table: False for table in list(self.db_tree)}

        self.window_db_editor.SetSashPosition(250)
        self.tree_ctrl_db.Expand(self.db_tree_root)

        self.allow_tree_select_change = True

        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Database Administrator")
        self.window_pane_db_tree.SetScrollRate(10, 10)
        # self.list_ctrl_query_results.AppendColumn("A", format=wx.LIST_FORMAT_LEFT, width=-1)
        # self.list_ctrl_query_results.AppendColumn("B", format=wx.LIST_FORMAT_LEFT, width=-1)
        # self.list_ctrl_query_results.AppendColumn("C", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.window_db_editor.SetMinimumPaneSize(20)

        self.db_tree_root = self.tree_ctrl_db.AddRoot('DVH Analytics')
        self.table_nodes = {table: self.tree_ctrl_db.AppendItem(self.db_tree_root, table) for table in self.db_tree}
        self.column_nodes = {table: {} for table in self.db_tree}
        for table in self.db_tree:
            for column in self.db_tree[table]:
                self.column_nodes[table][column] = self.tree_ctrl_db.AppendItem(self.table_nodes[table], column)

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_query = wx.BoxSizer(wx.VERTICAL)
        sizer_query_table = wx.StaticBoxSizer(wx.StaticBox(self.window_pane_query, wx.ID_ANY, "Query Results"),
                                              wx.VERTICAL)
        sizer_condition_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_download_button = wx.BoxSizer(wx.VERTICAL)
        sizer_query_button = wx.BoxSizer(wx.VERTICAL)
        sizer_condition = wx.BoxSizer(wx.VERTICAL)
        sizer_combo_box = wx.BoxSizer(wx.VERTICAL)
        sizer_db_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dialog_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dialog_buttons.Add(self.button_sql_connection, 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button_rebuild_db, 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button_post_import_calc, 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button_edit_db, 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button_reimport, 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button_delete_study, 0, wx.ALL, 5)
        sizer_dialog_buttons.Add(self.button_change_mrn_uid, 0, wx.ALL, 5)
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
        sizer_query_button.Add(self.button_query, 0, wx.ALL, 5)
        sizer_condition_buttons.Add(sizer_query_button, 0, wx.ALL, 5)
        label_spacer_2 = wx.StaticText(self.window_pane_query, wx.ID_ANY, "")
        sizer_download_button.Add(label_spacer_2, 0, wx.BOTTOM, 5)
        sizer_download_button.Add(self.button_download, 0, wx.ALL, 5)
        sizer_condition_buttons.Add(sizer_download_button, 0, wx.ALL, 5)
        sizer_query.Add(sizer_condition_buttons, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_query_table.Add(self.list_ctrl_query_results, 1, wx.EXPAND, 0)
        sizer_query.Add(sizer_query_table, 1, wx.ALL | wx.EXPAND, 5)
        self.window_pane_query.SetSizer(sizer_query)
        self.window_db_editor.SplitVertically(self.window_pane_db_tree, self.window_pane_query)
        sizer_wrapper.Add(self.window_db_editor, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    @staticmethod
    def OnSQLSettings(evt):
        dlg = SQLSettingsDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            new_config = {key: dlg.input[key].GetValue() for key in dlg.keys if dlg.input[key].GetValue()}
            if validate_sql_connection(new_config):
                write_sql_connection_settings(new_config)
            else:
                print("Invalid SQL config")
                print(new_config)
        dlg.Destroy()

    def OnTreeAdd(self, evt):
        self.update_selected_tree_items()

    # def UnselectOtherTables(self, selected_table):
    #     self.allow_tree_select_change = False
    #     for table, node in self.table_nodes.items():
    #         if table != selected_table:
    #             self.tree_ctrl_db.UnselectItem(node)
    #     self.allow_tree_select_change = True

    def OnQuery(self, evt):
        self.update_selected_tree_items()
        table = self.combo_box_query_table.GetValue()
        columns = [c for c, sel in self.selected_columns[table].items() if sel and c not in {'mrn', 'study_instance_uid'}]
        columns.sort()

        if not columns:
            columns = [c for c in self.db_tree[table] if c not in {'mrn', 'study_instance_uid'}]

        columns.insert(0, 'study_instance_uid')
        columns.insert(0, 'mrn')

        wait = wx.BusyCursor()
        cnx = DVH_SQL()
        data = cnx.query(table, ','.join(columns), bokeh_cds=True)
        self.data_query_results.set_data(data, columns)
        cnx.close()
        del wait

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

    def OnChangePatientIdentifier(self, evt):
        dlg = ChangePatientIdentifierDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            pass
        dlg.Destroy()

    def OnDeletePatient(self, evt):
        dlg = DeletePatientDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            pass
        dlg.Destroy()

    def OnReimport(self, evt):
        dlg = ReimportDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            pass
        dlg.Destroy()

    def OnEditDB(self, evt):
        dlg = EditDatabaseDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            pass
        dlg.Destroy()

    def OnPostImportCalc(self, evt):
        dlg = PostImportCalculationsDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            pass
        dlg.Destroy()
