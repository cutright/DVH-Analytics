#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#

import wx
from dialogs.query import query_dlg
from dialogs.sql_settings import SQLSettingsDialog
from db import sql_columns
from models.datatable import DataTable
from models.plot import PlotStatDVH
from models.dvh import DVH
from models.endpoint import EndpointFrame
from models.rad_bio import RadBioFrame
from models.time_series import TimeSeriesFrame
from db.sql_settings import write_sql_connection_settings, validate_sql_connection
from db.sql_to_python import QuerySQL
from paths import LOGO_PATH
from utilties import get_study_instance_uids


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # Initial DVH object and data
        self.dvh = None
        self.data = {key: None for key in ['Plans', 'Beams', 'Rxs']}

        self.toolbar_keys = ['Open', 'Close', 'Save', 'Print', 'Export', 'Import', 'Settings', 'Database']
        self.toolbar_ids = {key: i+1000 for i, key in enumerate(self.toolbar_keys)}

        # sql_columns.py contains dictionaries of all queryable variables along with their
        # SQL columns and tables. Numerical categories include their units as well.
        self.categorical_columns = sql_columns.categorical
        self.numerical_columns = sql_columns.numerical

        # Keep track of currently select row in the query tables
        self.selected_index_categorical = None
        self.selected_index_numerical = None
        
        self.__add_menubar()
        self.__add_tool_bar()
        self.__add_layout_objects()
        self.__bind_layout_objects()
        self.__set_properties()
        self.__set_tooltips()
        self.__add_notebook_frames()
        self.__do_layout()

        for key in ['categorical', 'numerical']:
            self.disable_query_buttons(key)
        self.button_query_execute.Disable()
        self.__disable_notebook_tabs()

        columns = {'categorical': ['category_1', 'category_2', 'Filt. Type'],
                   'numerical': ['category', 'min', 'max', 'Filt. Type']}
        self.data_table_categorical = DataTable(self.table_categorical, columns=columns['categorical'])
        self.data_table_numerical = DataTable(self.table_numerical, columns=columns['numerical'])

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
        self.Bind(wx.EVT_TOOL, self.OnClose, id=self.toolbar_ids['Close'])

    def __add_menubar(self):

        self.frame_menubar = wx.MenuBar()

        file_menu = wx.Menu()
        file_menu.Append(wx.ID_NEW, '&New')
        menu_open = file_menu.Append(wx.ID_OPEN, '&Open\tCtrl+O')
        menu_close = file_menu.Append(wx.ID_ANY, '&Close\tCtrl+W')
        file_menu.Append(wx.ID_SAVE, '&Save')
        menu_about = file_menu.Append(wx.ID_ANY, '&About\tCtrl+A')
        file_menu.AppendSeparator()

        imp = wx.Menu()
        imp.Append(wx.ID_ANY, 'Import newsfeed list...')
        imp.Append(wx.ID_ANY, 'Import bookmarks...')
        imp.Append(wx.ID_ANY, 'Import mail...')

        file_menu.AppendSubMenu(imp, 'I&mport')

        qmi = file_menu.Append(wx.ID_ANY, '&Quit\tCtrl+Q')

        self.Bind(wx.EVT_MENU, self.OnQuit, qmi)
        self.Bind(wx.EVT_MENU, self.OnOpen, menu_open)
        self.Bind(wx.EVT_MENU, self.OnClose, menu_close)
        self.Bind(wx.EVT_MENU, self.OnAbout, menu_about)

        self.frame_menubar.Append(file_menu, '&File')
        self.SetMenuBar(self.frame_menubar)

    def __add_layout_objects(self):
        self.button_categorical = {'add': wx.Button(self, wx.ID_ANY, "Add Filter"),
                                   'del': wx.Button(self, wx.ID_ANY, "Delete Selected"),
                                   'edit': wx.Button(self, wx.ID_ANY, "Edit Selected")}
        self.button_numerical = {'add': wx.Button(self, wx.ID_ANY, "Add Filter"),
                                 'del': wx.Button(self, wx.ID_ANY, "Delete Selected"),
                                 'edit': wx.Button(self, wx.ID_ANY, "Edit Selected")}

        self.table_categorical = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT)
        self.table_numerical = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT)

        self.button_query_execute = wx.Button(self, wx.ID_ANY, "Query and Retrieve")

        self.notebook_main_view = wx.Notebook(self, wx.ID_ANY)
        self.tab_keys = ['Welcome', 'DVHs', 'Endpoints', 'Rad Bio', 'Time Series', 'Correlation', 'Regression']
        self.notebook_tab = {key: wx.Panel(self.notebook_main_view, wx.ID_ANY) for key in self.tab_keys}

        self.text_summary = wx.StaticText(self, wx.ID_ANY, "", style=wx.ALIGN_LEFT)

    def __bind_layout_objects(self):
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_select_categorical, self.table_categorical)
        self.Bind(wx.EVT_BUTTON, self.add_row_categorical, id=self.button_categorical['add'].GetId())
        self.Bind(wx.EVT_BUTTON, self.del_row_categorical, id=self.button_categorical['del'].GetId())
        self.Bind(wx.EVT_BUTTON, self.edit_row_categorical, id=self.button_categorical['edit'].GetId())
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.doubleclick_categorical, self.table_categorical)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_select_numerical, self.table_numerical)
        self.Bind(wx.EVT_BUTTON, self.add_row_numerical, id=self.button_numerical['add'].GetId())
        self.Bind(wx.EVT_BUTTON, self.del_row_numerical, id=self.button_numerical['del'].GetId())
        self.Bind(wx.EVT_BUTTON, self.edit_row_numerical, id=self.button_numerical['edit'].GetId())
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.doubleclick_numerical, self.table_numerical)

        self.Bind(wx.EVT_BUTTON, self.exec_query, id=self.button_query_execute.GetId())

    def __set_properties(self):
        self.SetTitle("DVH Analytics")

        self.frame_toolbar.Realize()

        self.table_categorical.AppendColumn("Category1", format=wx.LIST_FORMAT_LEFT, width=180)
        self.table_categorical.AppendColumn("Category2", format=wx.LIST_FORMAT_LEFT, width=150)
        self.table_categorical.AppendColumn("Filt. Type", format=wx.LIST_FORMAT_LEFT, width=80)

        self.table_numerical.AppendColumn("Category", format=wx.LIST_FORMAT_LEFT, width=150)
        self.table_numerical.AppendColumn("Min", format=wx.LIST_FORMAT_LEFT, width=90)
        self.table_numerical.AppendColumn("Max", format=wx.LIST_FORMAT_LEFT, width=90)
        self.table_numerical.AppendColumn("Filt. Type", format=wx.LIST_FORMAT_LEFT, width=80)

    def __set_tooltips(self):
        self.button_categorical['add'].SetToolTip("Add a categorical data filter.")
        self.button_categorical['del'].SetToolTip("Delete the currently selected category filter.")
        self.button_categorical['edit'].SetToolTip("Edit the currently selected category filter.")
        self.button_numerical['add'].SetToolTip("Add a numerical data filter.")
        self.button_numerical['del'].SetToolTip("Delete the currently selected numerical data filter.")
        self.button_numerical['edit'].SetToolTip("Edit the currently selected data filter.")
        self.button_query_execute.SetToolTip("Query the database with the filters entered below. At least one "
                                             "filter must be added.")

    def __add_notebook_frames(self):
        self.plot = PlotStatDVH(self.notebook_tab['DVHs'], self.dvh)
        self.endpoint = EndpointFrame(self.notebook_tab['Endpoints'], self.dvh)
        self.radbio = RadBioFrame(self.notebook_tab['Rad Bio'], self.dvh)
        self.time_series = TimeSeriesFrame(self.notebook_tab['Time Series'], self.dvh, self.data)

    def __do_layout(self):
        sizer_summary = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Summary"), wx.HORIZONTAL)
        sizer_query_numerical = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Query by Numerical Data"),
                                                  wx.VERTICAL)

        sizer_query_categorical = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Query by Categorical Data"),
                                                    wx.VERTICAL)

        sizer_categorical_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_numerical_buttons = wx.BoxSizer(wx.HORIZONTAL)

        for key in ['add', 'del', 'edit']:
            sizer_categorical_buttons.Add(self.button_categorical[key], 0, wx.ALL, 5)
            sizer_numerical_buttons.Add(self.button_numerical[key], 0, wx.ALL, 5)

        sizer_query_categorical.Add(sizer_categorical_buttons, 0, wx.EXPAND, 5)
        sizer_query_categorical.Add(self.table_categorical, 1, wx.ALL | wx.EXPAND, 10)

        sizer_query_numerical.Add(sizer_numerical_buttons, 0, wx.ALL | wx.EXPAND, 5)
        sizer_query_numerical.Add(self.table_numerical, 1, wx.ALL | wx.EXPAND, 10)

        sizer_summary.Add(self.text_summary)

        panel_left = wx.BoxSizer(wx.VERTICAL)
        panel_left.Add(sizer_query_categorical, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHAPED | wx.TOP, 5)
        panel_left.Add(sizer_query_numerical, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHAPED, 5)
        panel_left.Add(self.button_query_execute, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 15)
        panel_left.Add(sizer_summary, 1, wx.ALL | wx.EXPAND, 5)

        bitmap_logo = wx.StaticBitmap(self.notebook_tab['Welcome'], wx.ID_ANY,
                                      wx.Bitmap(LOGO_PATH, wx.BITMAP_TYPE_ANY))
        text_welcome = wx.StaticText(self.notebook_tab['Welcome'], wx.ID_ANY,
                                     "\n\nWelcome to DVH Analytics.\nIf you already have a database built, design "
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

        sizer_welcome = wx.BoxSizer(wx.VERTICAL)
        sizer_welcome.Add(bitmap_logo, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.TOP, 100)
        sizer_welcome.Add(text_welcome, 0, wx.ALIGN_CENTER | wx.ALL, 25)
        self.notebook_tab['Welcome'].SetSizer(sizer_welcome)

        sizer_dvhs = wx.BoxSizer(wx.VERTICAL)
        sizer_dvhs.Add(self.plot.layout, 0, wx.ALIGN_CENTER | wx.ALL, 25)
        self.notebook_tab['DVHs'].SetSizer(sizer_dvhs)

        sizer_endpoint = wx.BoxSizer(wx.VERTICAL)
        sizer_endpoint.Add(self.endpoint.layout, 0, wx.ALIGN_CENTER | wx.ALL, 25)
        self.notebook_tab['Endpoints'].SetSizer(sizer_endpoint)

        sizer_rad_bio = wx.BoxSizer(wx.VERTICAL)
        sizer_rad_bio.Add(self.radbio.layout, 0, wx.ALIGN_CENTER | wx.ALL, 25)
        self.notebook_tab['Rad Bio'].SetSizer(sizer_rad_bio)

        sizer_time_series = wx.BoxSizer(wx.VERTICAL)
        sizer_time_series.Add(self.time_series.layout, 0, wx.ALIGN_CENTER | wx.ALL, 25)
        self.notebook_tab['Time Series'].SetSizer(sizer_time_series)

        for key in self.tab_keys:
            self.notebook_main_view.AddPage(self.notebook_tab[key], key)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        hbox_main = wx.BoxSizer(wx.HORIZONTAL)
        hbox_main.Add(panel_left, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.TOP, 5)
        hbox_main.Add(self.notebook_main_view, 1, wx.BOTTOM | wx.EXPAND | wx.RIGHT | wx.TOP, 5)
        sizer_main_wrapper.Add(hbox_main, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_main_wrapper, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.SetSize((1400, 900))
        self.Centre()

    def __enable_notebook_tabs(self):
        for key in self.tab_keys:
            self.notebook_tab[key].Enable()
        self.__enable_initial_buttons_in_tabs()

    def __disable_notebook_tabs(self):
        for key in self.tab_keys:
            if key != 'Welcome':
                self.notebook_tab[key].Disable()

    def __enable_initial_buttons_in_tabs(self):
        self.endpoint.enable_initial_buttons()
        self.radbio.enable_initial_buttons()
        self.time_series.enable_initial_buttons()

    def enable_query_buttons(self, query_type):
        for key in ['del', 'edit']:
            {'categorical':  self.button_categorical[key],
             'numerical':  self.button_numerical[key]}[query_type].Enable()

    def disable_query_buttons(self, query_type):
        for key in ['del', 'edit']:
            {'categorical': self.button_categorical[key],
             'numerical': self.button_numerical[key]}[query_type].Disable()

    # --------------------------------------------------------------------------------------------------------------
    # Menu bar event functions
    # --------------------------------------------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------------------------------------------
    # Query event functions
    # --------------------------------------------------------------------------------------------------------------
    def on_item_select_categorical(self, evt):
        self.selected_index_categorical = self.table_categorical.GetFirstSelected()

    def on_item_select_numerical(self, evt):
        self.selected_index_numerical = self.table_numerical.GetFirstSelected()

    def add_row_categorical(self, evt):
        query_dlg(self, 'categorical')
        self.button_query_execute.Enable()
        if self.data_table_categorical.row_count == 1 and self.data_table_numerical == 0:
            self.button_query_execute.Enable()

    def add_row_numerical(self, evt):
        query_dlg(self, 'numerical')
        if self.data_table_numerical.row_count == 1 and self.data_table_categorical == 0:
            self.button_query_execute.Enable()

    def edit_row_categorical(self, evt):
        if self.selected_index_categorical is not None:
            query_dlg(self, 'categorical', title='Edit Categorical Filter', set_values=True)

    def edit_row_numerical(self, evt):
        if self.selected_index_numerical is not None:
            query_dlg(self, 'numerical', title='Edit Numerical Filter', set_values=True)

    def doubleclick_categorical(self, evt):
        self.selected_index_categorical = self.table_categorical.GetFirstSelected()
        self.edit_row_categorical(None)

    def doubleclick_numerical(self, evt):
        self.selected_index_numerical = self.table_numerical.GetFirstSelected()
        self.edit_row_numerical(None)

    def del_row_categorical(self, evt):
        self.data_table_categorical.delete_row(self.selected_index_categorical)
        self.selected_index_categorical = None
        if self.data_table_categorical.row_count == 0:
            self.disable_query_buttons('categorical')

    def del_row_numerical(self, evt):
        self.data_table_numerical.delete_row(self.selected_index_numerical)
        self.selected_index_numerical = None
        if self.data_table_numerical.row_count == 0:
            self.disable_query_buttons('numerical')

    def exec_query(self, evt):
        wait = wx.BusyCursor()
        uids, dvh_str = self.get_query()
        self.dvh = DVH(dvh_condition=dvh_str, uid=uids)
        self.endpoint.update_dvh(self.dvh)
        self.text_summary.SetLabelText(self.dvh.get_summary())
        self.plot.update_plot(self.dvh)
        del wait
        self.notebook_main_view.SetSelection(1)
        self.update_data()
        self.time_series.update_data(self.dvh, self.data)

        self.__enable_notebook_tabs()

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
                table = self.categorical_columns[category]['table']
                col = self.categorical_columns[category]['var_name']
                value = self.data_table_categorical.data['category_2'][i]
                if col not in queries_by_sql_column[table]:
                    queries_by_sql_column[table][col] = []
                operator = ['=', '!='][{'Include': 0, 'Exclude': 1}[self.data_table_categorical.data['Filt. Type'][i]]]
                queries_by_sql_column[table][col].append("%s %s '%s'" % (col, operator, value))

        # Range filter
        if self.data_table_numerical.row_count:
            for i, category in enumerate(self.data_table_numerical.data['category']):
                table = self.numerical_columns[category]['table']
                col = self.numerical_columns[category]['var_name']
                value_low = self.data_table_numerical.data['min'][i]
                value_high = self.data_table_numerical.data['max'][i]
                if col not in queries_by_sql_column[table]:
                    queries_by_sql_column[table][col] = []
                operator = ['BETWEEN', 'NOT BETWEEN'][{'Include': 0, 'Exclude': 1}[self.data_table_numerical.data['Filt. Type'][i]]]
                queries_by_sql_column[table][col].append("%s %s %s AND %s" % (col, operator, value_low, value_high))

        for table in queries:
            for col in queries_by_sql_column[table]:
                queries[table].append("(%s)" % ' OR '.join(queries_by_sql_column[table][col]))
            queries[table] = ' AND '.join(queries[table])

        print(queries)

        uids = get_study_instance_uids(plans=queries['Plans'], rxs=queries['Rxs'], beams=queries['Beams'])['common']

        print(queries['Plans'])

        return uids, queries['DVHs']

    def update_data(self):
        wait = wx.BusyCursor()
        tables = ['Plans', 'Rxs', 'Beams']
        if hasattr(self.dvh, 'study_instance_uid'):
            condition_str = "study_instance_uid in ('%s')" % "','".join(self.dvh.study_instance_uid)
            self.data = {key: QuerySQL(key, condition_str) for key in tables}
        else:
            self.data = {key: None for key in tables}
        del wait

    # --------------------------------------------------------------------------------------------------------------
    # Menu bar event functions
    # --------------------------------------------------------------------------------------------------------------
    def OnQuit(self, evt):
        self.Close()

    def OnOpen(self, evt):
        """ Open a file"""
        # wx.DirDialog()
        dlg = wx.DirDialog(self, "Choose input directory", "", wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            print(dlg.GetPath())
        dlg.Destroy()

    def OnClose(self, evt):
        dlg = wx.MessageDialog(self, "Clear all data and plots?", caption='Close',
                               style=wx.YES | wx.NO | wx.NO_DEFAULT | wx.CENTER | wx.ICON_EXCLAMATION)
        dlg.Center()
        res = dlg.ShowModal()
        if res == wx.ID_YES:
            self.dvh = None
            self.data_table_categorical.delete_all_rows()
            self.data_table_numerical.delete_all_rows()
            self.plot.clear_plot()
            self.endpoint.clear_data()
            self.time_series.clear_data()
            self.notebook_main_view.SetSelection(0)
            self.text_summary.SetLabelText("")
            self.__disable_notebook_tabs()
            for key in ['categorical', 'numerical']:
                self.disable_query_buttons(key)
            self.button_query_execute.Disable()
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


if __name__ == "__main__":
    app = DVHApp(0)
    app.MainLoop()
