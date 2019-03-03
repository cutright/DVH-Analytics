#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#

import wx
from dialogs.query import QueryCategoryDialog, QueryRangeDialog
from dialogs.sql_settings import SQLSettingsDialog
from categories import Categories
from models.widgets import DataTable, PlotStatDVH
from db.sql_connector import DVH_SQL
from models.dvh import DVH
from models.endpoint import EndpointFrame
from db.sql_settings import write_sql_connection_settings, validate_sql_connection


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((1400, 900))

        self.dvh_data = None

        self.toolbar_keys = ['Open', 'Close', 'Save', 'Print', 'Export', 'Import', 'Settings', 'Database']
        self.toolbar_ids = {key: i+1000 for i, key in enumerate(self.toolbar_keys)}

        # Get queryable variables
        categories = Categories()
        self.selector_categories = categories.selector
        self.range_categories = categories.range
        self.selected_index_categorical = None
        self.selected_index_numerical = None
        
        self.__add_menubar()
        self.__add_tool_bar()
        self.__add_layout_objects()
        self.__set_properties()
        self.__do_layout()

        self.data_table_categorical = DataTable(self.table_categorical,
                                                columns=['category_1', 'category_2', 'not'])
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_select_categorical, self.table_categorical)
        self.Bind(wx.EVT_BUTTON, self.add_row_categorical, id=self.button_categorical_add.GetId())
        self.Bind(wx.EVT_BUTTON, self.del_row_categorical, id=self.button_categorical_del.GetId())
        self.Bind(wx.EVT_BUTTON, self.edit_row_categorical, id=self.button_categorical_edit.GetId())

        self.data_table_numerical = DataTable(self.table_numerical,
                                              columns=['category', 'min', 'max', 'not'])
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_select_categorical, self.table_categorical)
        self.Bind(wx.EVT_BUTTON, self.add_row_numerical, id=self.button_numerical_add.GetId())
        self.Bind(wx.EVT_BUTTON, self.del_row_numerical, id=self.button_numerical_del.GetId())
        self.Bind(wx.EVT_BUTTON, self.edit_row_numerical, id=self.button_numerical_edit.GetId())

        self.Bind(wx.EVT_BUTTON, self.exec_query, id=self.button_query_execute.GetId())

    def __add_tool_bar(self):
        self.frame_toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL | wx.TB_TEXT)
        self.SetToolBar(self.frame_toolbar)

        files = {'Open': "icons/iconfinder_Open_1493293.png",
                 'Close': "icons/iconfinder_Close_1493281.png",
                 'Save': "icons/iconfinder_Save_1493294.png",
                 'Print': "icons/iconfinder_Print_1493286.png",
                 'Export': "icons/iconfinder_csv_file_database_extension_data_3876336.png",
                 'Import': "icons/iconfinder_wizard_43606.png",
                 'Settings': "icons/iconfinder_Settings_1493289.png",
                 'Database': "icons/iconfinder_data_115746.png"}

        description = {'Open': "Open previously queried data",
                       'Close': "Clear queried data",
                       'Save': "Save queried data",
                       'Print': "Print a report",
                       'Export': "Export data to CSV",
                       'Import': "DICOM import wizard",
                       'Settings': "Program preferences",
                       'Database': "Change SQL database connection settings"}

        for key in self.toolbar_keys:
            self.frame_toolbar.AddTool(self.toolbar_ids[key], key, wx.Bitmap(files[key], wx.BITMAP_TYPE_ANY),
                                       wx.NullBitmap, wx.ITEM_NORMAL, description[key], "")

            if key in {'Export', 'Database'}:
                self.frame_toolbar.AddSeparator()

        self.Bind(wx.EVT_TOOL, self.on_toolbar_database, id=self.toolbar_ids['Database'])

    def __add_menubar(self):

        self.frame_menubar = wx.MenuBar()

        fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_NEW, '&New')
        menuOpen = fileMenu.Append(wx.ID_OPEN, '&Open\tCtrl+O')
        fileMenu.Append(wx.ID_SAVE, '&Save')
        menuAbout = fileMenu.Append(wx.ID_ANY, '&About\tCtrl+A')
        fileMenu.AppendSeparator()

        imp = wx.Menu()
        imp.Append(wx.ID_ANY, 'Import newsfeed list...')
        imp.Append(wx.ID_ANY, 'Import bookmarks...')
        imp.Append(wx.ID_ANY, 'Import mail...')

        fileMenu.AppendSubMenu(imp, 'I&mport')

        qmi = fileMenu.Append(wx.ID_ANY, '&Quit\tCtrl+Q')

        self.Bind(wx.EVT_MENU, self.OnQuit, qmi)
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)

        self.frame_menubar.Append(fileMenu, '&File')
        self.SetMenuBar(self.frame_menubar)

    def __add_layout_objects(self):
        self.button_categorical_add = wx.Button(self, wx.ID_ANY, "Add Filter")
        self.button_categorical_del = wx.Button(self, wx.ID_ANY, "Delete Selected")
        self.button_categorical_edit = wx.Button(self, wx.ID_ANY, "Edit Selected")
        self.table_categorical = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT)
        self.button_numerical_add = wx.Button(self, wx.ID_ANY, "Add Filter")
        self.button_numerical_del = wx.Button(self, wx.ID_ANY, "Delete Selected")
        self.button_numerical_edit = wx.Button(self, wx.ID_ANY, "Edit Selected")
        self.table_numerical = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT)
        self.button_query_execute = wx.Button(self, wx.ID_ANY, "Query and Retrieve")
        self.notebook_main_view = wx.Notebook(self, wx.ID_ANY)
        self.notebook_welcome = wx.Panel(self.notebook_main_view, wx.ID_ANY)
        self.notebook_dvhs = wx.Panel(self.notebook_main_view, wx.ID_ANY)
        self.notebook_endpoints = wx.Panel(self.notebook_main_view, wx.ID_ANY)
        self.notebook_rad_bio = wx.Panel(self.notebook_main_view, wx.ID_ANY)
        self.notebook_roi_viewer = wx.Panel(self.notebook_main_view, wx.ID_ANY)
        self.notebook_time_series = wx.Panel(self.notebook_main_view, wx.ID_ANY)
        self.notebook_correlation = wx.Panel(self.notebook_main_view, wx.ID_ANY)
        self.notebook_regression = wx.Panel(self.notebook_main_view, wx.ID_ANY)

        self.text_summary = wx.StaticText(self, wx.ID_ANY, "", style=wx.ALIGN_LEFT)

    def __bind_layout_objects(self):
        self.Bind(wx.EVT_BUTTON, self.add_row_categorical, id=self.button_categorical_add.GetId())
        self.Bind(wx.EVT_BUTTON, self.del_row_categorical, id=self.button_categorical_del.GetId())
        self.Bind(wx.EVT_BUTTON, self.edit_row_categorical, id=self.button_categorical_edit.GetId())

    def __set_properties(self):
        self.SetTitle("DVH Analytics")
        self.frame_toolbar.Realize()
        self.button_categorical_add.SetToolTip("Add a categorical data filter.")
        self.button_categorical_del.SetToolTip("Delete the currently selected category filter.")
        self.button_categorical_edit.SetToolTip("Edit the currently selected category filter.")
        self.table_categorical.AppendColumn("Category1", format=wx.LIST_FORMAT_LEFT, width=150)
        self.table_categorical.AppendColumn("Category2", format=wx.LIST_FORMAT_LEFT, width=180)
        self.table_categorical.AppendColumn("Apply Not", format=wx.LIST_FORMAT_LEFT, width=80)
        self.button_numerical_add.SetToolTip("Add a numerical data filter.")
        self.button_numerical_del.SetToolTip("Delete the currently selected numerical data filter.")
        self.button_numerical_edit.SetToolTip("Edit the currently selected data filter.")
        self.table_numerical.AppendColumn("Category", format=wx.LIST_FORMAT_LEFT, width=150)
        self.table_numerical.AppendColumn("Min", format=wx.LIST_FORMAT_LEFT, width=90)
        self.table_numerical.AppendColumn("Max", format=wx.LIST_FORMAT_LEFT, width=90)
        self.table_numerical.AppendColumn("Apply Not", format=wx.LIST_FORMAT_LEFT, width=80)
        self.button_query_execute.SetToolTip("Query the database with the filters entered below. At least one "
                                             "filter must be added.")

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        hbox_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_welcome = wx.BoxSizer(wx.VERTICAL)
        panel_left = wx.BoxSizer(wx.VERTICAL)
        sizer_summary = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Summary"), wx.HORIZONTAL)
        sizer_query_numerical = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Query by Numerical Data"),
                                                  wx.VERTICAL)
        sizer_numerical_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_query_categorical = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Query by Categorical Data"),
                                                    wx.VERTICAL)
        sizer_categorical_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_categorical_buttons.Add(self.button_categorical_add, 0, wx.ALL, 5)
        sizer_categorical_buttons.Add(self.button_categorical_del, 0, wx.ALL, 5)
        sizer_categorical_buttons.Add(self.button_categorical_edit, 0, wx.ALL, 5)
        sizer_query_categorical.Add(sizer_categorical_buttons, 0, wx.EXPAND, 0)
        sizer_query_categorical.Add(self.table_categorical, 1, wx.ALL | wx.EXPAND, 5)
        panel_left.Add(sizer_query_categorical, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHAPED | wx.TOP, 5)
        sizer_numerical_buttons.Add(self.button_numerical_add, 0, wx.ALL, 5)
        sizer_numerical_buttons.Add(self.button_numerical_del, 0, wx.ALL, 5)
        sizer_numerical_buttons.Add(self.button_numerical_edit, 0, wx.ALL, 5)
        sizer_query_numerical.Add(sizer_numerical_buttons, 0, wx.ALL | wx.EXPAND, 5)
        sizer_query_numerical.Add(self.table_numerical, 1, wx.ALL | wx.EXPAND, 5)
        panel_left.Add(sizer_query_numerical, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHAPED, 5)
        panel_left.Add(self.button_query_execute, 0, wx.ALL | wx.EXPAND, 30)

        # sizer_summary.Add((0, 0), 0, 0, 0)
        sizer_summary.Add(self.text_summary)
        panel_left.Add(sizer_summary, 1, wx.ALL | wx.EXPAND, 5)
        hbox_main.Add(panel_left, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.TOP, 5)
        bitmap_logo = wx.StaticBitmap(self.notebook_welcome, wx.ID_ANY,
                                      wx.Bitmap("/Users/nightowl/PycharmProjects/DVH-Analytics-Desktop/logo.png",
                                                wx.BITMAP_TYPE_ANY))
        sizer_welcome.Add(bitmap_logo, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.TOP, 100)
        text_welcome = wx.StaticText(self.notebook_welcome, wx.ID_ANY,
                                     "Welcome to DVH Analytics.  If you already have a database built, design "
                                     "a query with the filters to the left.\n\n\n\nDVH Analytics is a software "
                                     "application to help radiation oncology departments build an in-house database "
                                     "of treatment planning data for the purpose of historical comparisons and "
                                     "statistical analysis. This code is still in development. Please contact the "
                                     "developer if you are interested in testing or collaborating.\n\nThe application "
                                     "builds a SQL database of DVHs and various planning parameters from DICOM files "
                                     "(i.e., Plan, Structure, Dose). Since the data is extracted directly from DICOM "
                                     "files, we intend to accommodate an array of treatment planning system vendors.",
                                     style=wx.ALIGN_CENTER)
        text_welcome.SetMinSize((700, 500))
        text_welcome.Wrap(500)
        sizer_welcome.Add(text_welcome, 0, wx.ALIGN_CENTER | wx.ALL, 50)
        self.notebook_welcome.SetSizer(sizer_welcome)

        sizer_dvhs = wx.BoxSizer(wx.VERTICAL)
        self.plot = PlotStatDVH(self.notebook_dvhs, x_axis_label='Dose (cGy)', y_axis_label='Relative Volume')
        sizer_dvhs.Add(self.plot.layout, 0, wx.ALIGN_CENTER | wx.ALL, 50)
        self.notebook_dvhs.SetSizer(sizer_dvhs)

        sizer_endpoint = wx.BoxSizer(wx.VERTICAL)
        self.endpoint = EndpointFrame(self.notebook_endpoints)
        sizer_endpoint.Add(self.endpoint.layout, 0, wx.ALIGN_CENTER | wx.ALL, 50)
        self.notebook_endpoints.SetSizer(sizer_endpoint)

        self.notebook_main_view.AddPage(self.notebook_welcome, "Welcome")
        self.notebook_main_view.AddPage(self.notebook_dvhs, "DVHs")
        self.notebook_main_view.AddPage(self.notebook_endpoints, "Endpoints")
        self.notebook_main_view.AddPage(self.notebook_rad_bio, "Rad Bio")
        self.notebook_main_view.AddPage(self.notebook_roi_viewer, "ROI Viewer")
        self.notebook_main_view.AddPage(self.notebook_time_series, "Time Series")
        self.notebook_main_view.AddPage(self.notebook_correlation, "Correlation")
        self.notebook_main_view.AddPage(self.notebook_regression, "Regression")
        hbox_main.Add(self.notebook_main_view, 1, wx.BOTTOM | wx.EXPAND | wx.RIGHT | wx.TOP, 5)
        sizer_main_wrapper.Add(hbox_main, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_main_wrapper, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()

    @staticmethod
    def on_toolbar_database(evt):
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

    def on_item_select_categorical(self, evt):
        self.selected_index_categorical = self.table_categorical.GetFirstSelected()

    def add_row_categorical(self, evt):
        dlg = QueryCategoryDialog(title='Add Categorical Filter')
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            new_row = [dlg.select_category_1.get_value(),
                       dlg.select_category_2.get_value(),
                       dlg.check_box_not.GetValue()]
            self.data_table_categorical.append_row(new_row)
        dlg.Destroy()

    def del_row_categorical(self, evt):
        self.data_table_categorical.delete_row(self.selected_index_categorical)
        self.selected_index_categorical = None

    def edit_row_categorical(self, evt):
        query = QueryCategoryDialog(title='Edit Categorical Filter')
        query.set_values(self.data_table_categorical.get_row(self.selected_index_categorical))
        res = query.ShowModal()
        if res == wx.ID_OK:
            self.data_table_categorical.edit_row(query.get_values(), self.selected_index_categorical)
        query.Destroy()

    def on_item_select_numerical(self, evt):
        self.selected_index_numerical = self.table_numerical.GetFirstSelected()

    def add_row_numerical(self, evt):
        dlg = QueryRangeDialog()
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            new_row = [dlg.select_category.get_value(),
                       dlg.validated_text('min'),
                       dlg.validated_text('max'),
                       dlg.check_box_not.GetValue()]
            self.data_table_numerical.append_row(new_row)
        dlg.Destroy()

    def del_row_numerical(self, evt):
        self.data_table_numerical.delete_row(self.selected_index_numerical)
        self.selected_index_numerical = None

    def edit_row_numerical(self, evt):
        query = QueryRangeDialog(title='Edit Numerical Filter')
        query.set_values(self.data_table_numerical.get_row(self.selected_index_numerical))
        res = query.ShowModal()
        if res == wx.ID_OK:
            self.data_table_numerical.edit_row(query.get_values(), self.selected_index_numerical)
        query.Destroy()

    def exec_query(self, evt):
        # condition = "physician_roi = '%s'" % 'brainstem'
        wait = wx.BusyCursor()
        uids, dvh_str = self.get_query()
        self.dvh_data = DVH(dvh_condition=dvh_str, uid=uids)
        self.text_summary.SetLabelText(self.dvh_data.get_summary())
        self.plot.update_plot(self.dvh_data, x_axis_label='Dose (cGy)', y_axis_label='Relative Volume')
        del wait
        self.notebook_main_view.SetSelection(1)

    def get_query(self):

        # Used to accumulate lists of query strings for each table
        # Will assume each item in list is complete query for that SQL column
        queries = {'Plans': [], 'Rxs': [], 'Beams': [], 'DVHs': []}

        # Used to group queries by variable, will combine all queries of same variable with an OR operator
        # e.g., queries_by_sql_column['Plans'][key] = list of strings, where key is sql column
        queries_by_sql_column = {'Plans': {}, 'Rxs': {}, 'Beams': {}, 'DVHs': {}}

        # Categorical filter
        if self.data_table_categorical.row_count:
            for i, category in enumerate(self.data_table_categorical.data['category_1']):
                table = self.selector_categories[category]['table']
                col = self.selector_categories[category]['var_name']
                value = self.data_table_categorical.data['category_2'][i]
                if col not in queries_by_sql_column[table]:
                    queries_by_sql_column[table][col] = []
                operator = ['=', '!='][bool(self.data_table_categorical.data['not'][i])]
                queries_by_sql_column[table][col].append("%s %s '%s'" % (col, operator, value))

        # Range filter
        if self.data_table_numerical.row_count:
            for i, category in enumerate(self.data_table_numerical.data['category']):
                table = self.range_categories[category]['table']
                col = self.range_categories[category]['var_name']
                value_low = self.data_table_numerical.data['min'][i]
                value_high = self.data_table_numerical.data['max'][i]
                if col not in queries_by_sql_column[table]:
                    queries_by_sql_column[table][col] = []
                operator = ['BETWEEN', 'NOT BETWEEN'][bool(self.data_table_numerical.data['not'][i])]
                queries_by_sql_column[table][col].append("%s %s %s AND %s" % (col, operator, value_low, value_high))

        for table in queries:
            for col in queries_by_sql_column[table]:
                queries[table].append("(%s)" % ' OR '.join(queries_by_sql_column[table][col]))
            queries[table] = ' AND '.join(queries[table])

        uids = get_study_instance_uids(plans=queries['Plans'], rxs=queries['Rxs'], beams=queries['Beams'])['common']

        return uids, queries['DVHs']

    def OnQuit(self, evt):
        self.Close()

    def OnOpen(self, evt):
        """ Open a file"""
        # wx.DirDialog()
        dlg = wx.DirDialog(self, "Choose input directory", "", wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            print(dlg.GetPath())
        dlg.Destroy()

    def OnAbout(self, evt):
        dlg = wx.MessageDialog(self, "DVH Analytics \n in wxPython", "About Sample Editor", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()


class DVHApp(wx.App):
    def OnInit(self):
        self.frame = MainFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True


def get_study_instance_uids(**kwargs):
    cnx = DVH_SQL()
    uids = {table: cnx.get_unique_values(table, 'study_instance_uid', condition) for table, condition in kwargs.items()}
    cnx.close()

    complete_list = flatten_list_of_lists(list(uids.values()), remove_duplicates=True)

    uids['common'] = [uid for uid in complete_list if is_uid_in_all_keys(uid, uids)]
    uids['unique'] = complete_list

    return uids


def is_uid_in_all_keys(uid, uids):
    is_uid_in_table = {table: uid in table_uids for table, table_uids in uids.items()}
    return all([list(is_uid_in_table.values())])


def flatten_list_of_lists(some_list, remove_duplicates=False, sort=False):
    data = [item for sublist in some_list for item in sublist]
    if sort:
        data.sort()
    if remove_duplicates:
        return list(set(data))
    return data


if __name__ == "__main__":
    app = DVHApp(0)
    app.MainLoop()
