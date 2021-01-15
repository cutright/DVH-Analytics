#!/usr/bin/env python
# -*- coding: utf-8 -*-

# main.py
"""
The main file DVH Analytics
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import logging, logging.handlers
import sys, threading, traceback, os

logger = logging.getLogger("dvha")
logger.setLevel(logging.DEBUG)

import wx
from datetime import datetime
import webbrowser
from pubsub import pub
from dvha.db import sql_columns
from dvha.db.sql_to_python import QuerySQL
from dvha.db.sql_connector import echo_sql_db, initialize_db
from dvha.dialogs.main import (
    query_dlg,
    UserSettings,
    About,
    PythonLibraries,
    do_sqlite_backup,
)
from dvha.dialogs.database import SQLSettingsDialog
from dvha.dialogs.export import (
    ExportCSVDialog,
    ExportFigure,
    ExportPGSQLProgressFrame,
)
from dvha.models.import_dicom import ImportDicomFrame
from dvha.models.database_editor import DatabaseEditorFrame
from dvha.models.data_table import DataTable
from dvha.models.plot import PlotStatDVH
from dvha.models.dvh import DVH
from dvha.models.endpoint import EndpointFrame
from dvha.models.queried_data import QueriedDataFrame
from dvha.models.rad_bio import RadBioFrame
from dvha.models.time_series import TimeSeriesFrame
from dvha.models.correlation import CorrelationFrame
from dvha.models.machine_learning import (
    MachineLearningModelViewer,
    ALGORITHMS,
    MachineLearningSetupDlg,
)
from dvha.models.regression import RegressionFrame, LoadMultiVarModelFrame
from dvha.models.control_chart import ControlChartFrame
from dvha.models.roi_map import ROIMapFrame
from dvha.models.stats_data_editor import StatsDataEditor
from dvha.options import Options, DefaultOptions
from dvha.paths import LOGO_PATH, DATA_DIR, ICONS, MODELS_DIR, APP_DIR
from dvha.tools.errors import (
    MemoryErrorDialog,
    PlottingMemoryError,
    ErrorDialog,
)
from dvha.tools.roi_name_manager import DatabaseROIs
from dvha.tools.stats import StatsData, sync_variables_in_stats_data_objects
from dvha.tools.utilities import (
    get_study_instance_uids,
    scale_bitmap,
    is_windows,
    is_linux,
    is_mac,
    get_window_size,
    save_object_to_file,
    load_object_from_file,
    set_msw_background_color,
    initialize_directories,
    set_frame_icon,
    main_is_frozen,
    apply_resolution_limits,
)
from dvha.db.sql_columns import all_columns as sql_column_info


class DVHAMainFrame(wx.Frame):
    def __init__(self, *args, **kwds):

        self.allow_window_size_save = False

        #############################################################################
        # The following block of code for logging adapted from dicompyler
        #############################################################################
        # Initialize logging
        logger = logging.getLogger("dvha")

        # Configure the exception hook to process threads as well
        self.InstallThreadExcepthook()

        # Remap the exception hook so that we can log and display exceptions
        def LogExcepthook(*exc_info):
            # Log the exception
            text = "".join(traceback.format_exception(*exc_info))
            logger.error("Unhandled exception: %s", text)
            pub.sendMessage("logging.exception", msg=text)

        sys.excepthook = LogExcepthook

        # Modify the logging system from pydicom to capture important messages
        pydicom_logger = logging.getLogger("pydicom")
        for l in pydicom_logger.handlers:
            pydicom_logger.removeHandler(l)

        # Add file logger
        logpath = os.path.join(APP_DIR, "logs")
        if not os.path.exists(logpath):
            os.makedirs(logpath)
        self.fh = logging.handlers.RotatingFileHandler(
            os.path.join(logpath, "dvha.log"), maxBytes=524288, backupCount=7
        )
        self.fh.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        self.fh.setLevel(logging.WARNING)
        logger.addHandler(self.fh)
        pydicom_logger.addHandler(self.fh)

        # Add console logger if not frozen
        if not main_is_frozen():
            self.ch = logging.StreamHandler()
            self.ch.setFormatter(
                logging.Formatter("%(levelname)s: %(message)s")
            )
            self.ch.setLevel(logging.WARNING)
            logger.addHandler(self.ch)
            pydicom_logger.addHandler(self.ch)
        # Otherwise if frozen, send stdout/stderror to /dev/null since
        # logging the messages seems to cause instability due to recursion
        else:
            devnull = open(os.devnull, "w")
            sys.stdout = devnull
            sys.stderr = devnull
        #############################################################################
        # End logging code block from dicompyler
        #############################################################################

        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.active_tab = "Welcome"

        self.sizer_dvhs = wx.BoxSizer(wx.VERTICAL)

        set_msw_background_color(
            self
        )  # If windows, change the background color

        self.options = Options()
        self.SetMinSize(self.options.MIN_RESOLUTION_MAIN)

        # Initial DVH object and data
        self.save_data = {}
        self.group_data = {
            1: {
                "dvh": None,
                "data": {key: None for key in ["Plans", "Beams", "Rxs"]},
                "stats_data": None,
            },
            2: {
                "dvh": None,
                "data": {key: None for key in ["Plans", "Beams", "Rxs"]},
                "stats_data": None,
            },
        }

        self.toolbar_keys = [
            "Open",
            "Close",
            "Save",
            "Export",
            "Image",
            "Import",
            "Database",
            "ROI Map",
            "AI",
            "Settings",
        ]
        self.toolbar_ids = {
            key: i + 1000 for i, key in enumerate(self.toolbar_keys)
        }

        # sql_columns.py contains dictionaries of all queryable variables along with their
        # SQL columns and tables. Numerical categories include their units as well.
        self.categorical_columns = sql_columns.categorical
        self.numerical_columns = sql_columns.numerical

        # Keep track of currently selected row in the query tables
        self.selected_index_categorical = None
        self.selected_index_numerical = None

        # Load ROI Map now and pass to other objects for continuity
        # TODO: Need a method to address multiple users editing roi_map at the same time
        self.roi_map = DatabaseROIs()

        self.query_filters = None
        self.reset_query_filters()

        self.__add_menubar()
        self.__add_tool_bar()
        self.__add_layout_objects()
        self.__bind_layout_objects()

        columns = {
            "categorical": ["category_1", "category_2", "Filter Type"],
            "numerical": ["category", "min", "max", "Filter Type"],
        }
        self.data_table_categorical = DataTable(
            self.table_categorical, columns=columns["categorical"]
        )
        self.data_table_numerical = DataTable(
            self.table_numerical, columns=columns["numerical"]
        )

        self.do_plot_refresh = {
            "DVHs": False,
            "Time Series": False,
            "Correlation": False,
            "Regression": False,
            "Control Chart": False,
        }

        self.__set_properties()
        self.__set_tooltips()
        self.__add_notebook_frames()
        self.__do_layout()
        self.disable_query_buttons("categorical")
        self.disable_query_buttons("numerical")
        self.button_query_execute.Disable()

        self.Bind(wx.EVT_CLOSE, self.on_quit)
        self.tool_bar_windows = {
            key: None for key in ["import", "database", "roi_map"]
        }
        self.loaded_mvr_ml_frames = []
        self.user_settings = None
        self.export_figure = None

        wx.CallAfter(self.__catch_failed_sql_connection_on_app_launch)

        self.correlation_error_displayed = False

        self.__do_subscribe()

        # Temporary dicompyler-core check until released on PyPI
        from dicompylercore import __version__ as dicompylercore_version

        if dicompylercore_version != "0.5.6":
            msg = (
                "dicompyler-core >= 0.5.6 is required for non-HFS imports. Please upgrade dicompyler-core with\n\n"
                "pip install --upgrade git+https://github.com/dicompyler/dicompyler-core.git\n\nand relaunch DVHA"
            )
            caption = "dicompyler-core Version Warning"
            ErrorDialog(self, msg, caption)

        if self.options.SHOW_NEW_PTV_CALC_WARNING:
            msg = (
                "As of DVHA v0.8.9, there are new PTV Distance calculations. "
                "Go to Data -> Database Administrator. Click Calculate for PTV Distances to ensure "
                "all of your data is calculated consistently across studies/patients.\n\n"
                "This warning will only show once. Must perform for each of your databases separately."
            )
            caption = "New PTV Distance Calculations"
            ErrorDialog(self, msg, caption)
            self.options.set_option("SHOW_NEW_PTV_CALC_WARNING", False)

        self.ml_views = []

    def __add_tool_bar(self):
        self.frame_toolbar = wx.ToolBar(
            self, -1, style=wx.TB_HORIZONTAL | wx.TB_TEXT
        )
        self.SetToolBar(self.frame_toolbar)

        description = {
            "Open": "Open previously queried data",
            "Close": "Clear queried data",
            "Save": "Save queried data",
            # 'Print': "Print a report",
            "Export": "Export data to CSV",
            "Image": "Export a plot to SVG/HTML",
            "Import": "DICOM import wizard",
            "Settings": "User Settings",
            "Database": "Database Administrator Tools",
            "ROI Map": "Define ROI name aliases",
            "AI": "Modeling with Scikit-Learn",
        }

        for key in self.toolbar_keys:
            bitmap = wx.Bitmap(ICONS[key], wx.BITMAP_TYPE_ANY)
            if is_windows() or is_linux():
                bitmap = scale_bitmap(bitmap, 30, 30)
            self.frame_toolbar.AddTool(
                self.toolbar_ids[key],
                key,
                bitmap,
                wx.NullBitmap,
                wx.ITEM_NORMAL,
                description[key],
                "",
            )

            if key in {"Close", "Image", "ROI Map", "AI"}:
                separator_count = (
                    4 if is_windows() else 1
                )  # MSW separator is very thin compared to mac
                for _ in range(separator_count):
                    self.frame_toolbar.AddSeparator()

        self.Bind(wx.EVT_TOOL, self.on_save, id=self.toolbar_ids["Save"])
        self.Bind(wx.EVT_TOOL, self.on_open, id=self.toolbar_ids["Open"])
        self.Bind(wx.EVT_TOOL, self.on_export, id=self.toolbar_ids["Export"])
        self.Bind(
            wx.EVT_TOOL, self.on_export_figure, id=self.toolbar_ids["Image"]
        )
        self.Bind(
            wx.EVT_TOOL,
            self.on_toolbar_database,
            id=self.toolbar_ids["Database"],
        )
        self.Bind(
            wx.EVT_TOOL,
            self.on_toolbar_settings,
            id=self.toolbar_ids["Settings"],
        )
        self.Bind(
            wx.EVT_TOOL,
            self.on_toolbar_roi_map,
            id=self.toolbar_ids["ROI Map"],
        )
        self.Bind(wx.EVT_TOOL, self.on_toolbar_ml, id=self.toolbar_ids["AI"])
        self.Bind(wx.EVT_TOOL, self.on_close, id=self.toolbar_ids["Close"])
        self.Bind(
            wx.EVT_TOOL, self.on_toolbar_import, id=self.toolbar_ids["Import"]
        )

    def __add_menubar(self):

        self.frame_menubar = wx.MenuBar()

        file_menu = wx.Menu()
        menu_open = file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O")
        menu_import = file_menu.Append(wx.ID_OPEN, "&Import DICOM\tCtrl+I")
        menu_save = file_menu.Append(wx.ID_ANY, "&Save\tCtrl+S")
        menu_close = file_menu.Append(wx.ID_ANY, "&Close")

        load_model = wx.Menu()
        load_model_mvr = load_model.Append(
            wx.ID_ANY, "Multi-Variable Regression"
        )
        load_model_ml = load_model.Append(wx.ID_ANY, "Machine Learning")

        export = wx.Menu()
        export_csv = export.Append(wx.ID_ANY, "Data to csv\tCtrl+E")
        export_figure = export.Append(wx.ID_ANY, "&Plot to file\tCtrl+P")
        export_pgsql = export.Append(wx.ID_ANY, "PGSQL to SQLite")
        export_db_to_json = export.Append(wx.ID_ANY, "Database to JSON")
        file_menu.AppendSeparator()

        qmi = file_menu.Append(wx.ID_ANY, "&Quit\tCtrl+Q")

        self.data_menu = wx.Menu()

        self.data_views = {
            key: None for key in ["DVHs", "Plans", "Rxs", "Beams"]
        }
        menu_db_admin = self.data_menu.Append(
            wx.ID_ANY, "Database Administrator"
        )
        self.data_menu.AppendSubMenu(load_model, "Load &Model")
        self.data_menu.AppendSubMenu(export, "&Export")
        menu_db_backup = self.data_menu.Append(wx.ID_ANY, "Backup SQLite DB")
        self.data_menu.AppendSeparator()
        self.data_menu_items = {
            "DVHs": self.data_menu.Append(wx.ID_ANY, "Show DVHs\tCtrl+1"),
            "Plans": self.data_menu.Append(wx.ID_ANY, "Show Plans\tCtrl+2"),
            "Rxs": self.data_menu.Append(wx.ID_ANY, "Show Rxs\tCtrl+3"),
            "Beams": self.data_menu.Append(wx.ID_ANY, "Show Beams\tCtrl+4"),
            "StatsData1": self.data_menu.Append(
                wx.ID_ANY, "Show Stats Data: Group 1\tCtrl+5"
            ),
            "StatsData2": self.data_menu.Append(
                wx.ID_ANY, "Show Stats Data: Group 2\tCtrl+6"
            ),
        }

        settings_menu = wx.Menu()
        menu_pref = settings_menu.Append(wx.ID_PREFERENCES)
        menu_sql = settings_menu.Append(
            wx.ID_ANY, "&Database Connection\tCtrl+D"
        )
        menu_sql_2 = settings_menu.Append(wx.ID_ANY, "&Database Connection 2")
        menu_roi_map = settings_menu.Append(wx.ID_ANY, "&ROI Map\tCtrl+R")

        help_menu = wx.Menu()
        menu_github = help_menu.Append(wx.ID_ANY, "GitHub Page")
        menu_dvha_edit = help_menu.Append(wx.ID_ANY, "DVHA DICOM Editor")
        menu_python_libraries = help_menu.Append(
            wx.ID_ANY, "Python Libraries Used"
        )
        menu_report_issue = help_menu.Append(wx.ID_ANY, "Report an Issue")
        menu_about = help_menu.Append(wx.ID_ANY, "&About")

        self.Bind(wx.EVT_MENU, self.on_quit, qmi)
        self.Bind(wx.EVT_MENU, self.on_open, menu_open)
        self.Bind(wx.EVT_MENU, self.on_toolbar_import, menu_import)
        self.Bind(wx.EVT_MENU, self.on_load_mvr_model, load_model_mvr)
        self.Bind(wx.EVT_MENU, self.on_load_ml_model, load_model_ml)
        self.Bind(wx.EVT_MENU, self.on_close, menu_close)
        self.Bind(wx.EVT_MENU, self.on_export, export_csv)
        self.Bind(wx.EVT_MENU, self.on_export_figure, export_figure)
        self.Bind(wx.EVT_MENU, self.on_export_pgsql, export_pgsql)
        self.Bind(wx.EVT_MENU, self.on_export_db_to_json, export_db_to_json)
        self.Bind(wx.EVT_MENU, self.on_save, menu_save)
        self.Bind(wx.EVT_MENU, self.on_pref, menu_pref)
        self.Bind(wx.EVT_MENU, self.on_githubpage, menu_github)
        self.Bind(wx.EVT_MENU, self.on_report_issue, menu_report_issue)
        self.Bind(wx.EVT_MENU, self.on_dvha_edit, menu_dvha_edit)
        self.Bind(wx.EVT_MENU, PythonLibraries, menu_python_libraries)
        self.Bind(wx.EVT_MENU, About, menu_about)
        self.Bind(wx.EVT_MENU, self.on_sql, menu_sql)
        self.Bind(wx.EVT_MENU, self.on_sql_2, menu_sql_2)
        self.Bind(wx.EVT_MENU, self.on_toolbar_roi_map, menu_roi_map)
        if is_mac():
            menu_user_settings = settings_menu.Append(
                wx.ID_ANY, "&Preferences\tCtrl+,"
            )
            self.Bind(wx.EVT_MENU, self.on_pref, menu_user_settings)
        menu_win_pos = settings_menu.Append(wx.ID_ANY, "Reset Windows")
        self.Bind(wx.EVT_MENU, self.on_reset_windows, menu_win_pos)

        self.Bind(wx.EVT_MENU, self.on_toolbar_database, menu_db_admin)
        self.Bind(wx.EVT_MENU, self.on_sqlite_backup, menu_db_backup)
        self.Bind(wx.EVT_MENU, self.on_view_dvhs, self.data_menu_items["DVHs"])
        self.Bind(
            wx.EVT_MENU, self.on_view_plans, self.data_menu_items["Plans"]
        )
        self.Bind(wx.EVT_MENU, self.on_view_rxs, self.data_menu_items["Rxs"])
        self.Bind(
            wx.EVT_MENU, self.on_view_beams, self.data_menu_items["Beams"]
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_view_stats_data_1,
            self.data_menu_items["StatsData1"],
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_view_stats_data_2,
            self.data_menu_items["StatsData2"],
        )

        self.frame_menubar.Append(file_menu, "&File")
        self.frame_menubar.Append(self.data_menu, "&Data")
        self.frame_menubar.Append(settings_menu, "&Settings")
        self.frame_menubar.Append(help_menu, "&Help")
        self.SetMenuBar(self.frame_menubar)

    def __add_layout_objects(self):
        self.button_categorical = {
            "add": wx.Button(self, wx.ID_ANY, "Add Filter"),
            "del": wx.Button(self, wx.ID_ANY, "Delete Selected"),
            "edit": wx.Button(self, wx.ID_ANY, "Edit Selected"),
        }
        self.button_numerical = {
            "add": wx.Button(self, wx.ID_ANY, "Add Filter"),
            "del": wx.Button(self, wx.ID_ANY, "Delete Selected"),
            "edit": wx.Button(self, wx.ID_ANY, "Edit Selected"),
        }

        self.table_categorical = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT
        )
        self.table_numerical = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT
        )

        self.radio_button_query_group = wx.RadioBox(
            self, wx.ID_ANY, "Query Group", choices=["1", "2"]
        )
        self.button_query_execute = wx.Button(
            self, wx.ID_ANY, "Query and Retrieve Group 1"
        )

        self.notebook_main_view = wx.Notebook(self, wx.ID_ANY)
        self.tab_keys = [
            "Welcome",
            "DVHs",
            "Endpoints",
            "Rad Bio",
            "Time Series",
            "Correlation",
            "Regression",
            "Control Chart",
        ]
        self._created_tabs = []
        self.notebook_tab = {
            key: wx.Panel(self.notebook_main_view, wx.ID_ANY)
            for key in self.tab_keys
        }

        # self.text_summary = wx.StaticText(
        #     self, wx.ID_ANY, "", style=wx.ALIGN_LEFT
        # )
        self.text_summary = wx.TextCtrl(
            self, wx.ID_ANY, style=wx.TE_MULTILINE | wx.TE_READONLY
        )

    def __bind_layout_objects(self):
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            self.on_item_select_categorical,
            self.table_categorical,
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.add_row_categorical,
            id=self.button_categorical["add"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.del_row_categorical,
            id=self.button_categorical["del"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.edit_row_categorical,
            id=self.button_categorical["edit"].GetId(),
        )
        self.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED,
            self.doubleclick_categorical,
            self.table_categorical,
        )

        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            self.on_item_select_numerical,
            self.table_numerical,
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.add_row_numerical,
            id=self.button_numerical["add"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.del_row_numerical,
            id=self.button_numerical["del"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.edit_row_numerical,
            id=self.button_numerical["edit"].GetId(),
        )
        self.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED,
            self.doubleclick_numerical,
            self.table_numerical,
        )

        self.Bind(
            wx.EVT_RADIOBOX,
            self.on_group_select,
            id=self.radio_button_query_group.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.exec_query_button,
            id=self.button_query_execute.GetId(),
        )

        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_MOVE, self.on_move)

        self.notebook_main_view.Bind(
            wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_selection
        )

    def __set_properties(self):
        self.SetTitle("DVH Analytics")

        self.frame_toolbar.Realize()

        widths = [180, 150, 80]
        self.table_categorical.AppendColumn(
            "Category1", format=wx.LIST_FORMAT_LEFT, width=widths[0]
        )
        self.table_categorical.AppendColumn(
            "Category2", format=wx.LIST_FORMAT_LEFT, width=widths[1]
        )
        self.table_categorical.AppendColumn(
            "Filter Type", format=wx.LIST_FORMAT_LEFT, width=widths[2]
        )
        self.data_table_categorical.widths = widths

        widths = [150, 90, 90, 80]
        self.table_numerical.AppendColumn(
            "Category", format=wx.LIST_FORMAT_LEFT, width=widths[0]
        )
        self.table_numerical.AppendColumn(
            "Min", format=wx.LIST_FORMAT_LEFT, width=widths[1]
        )
        self.table_numerical.AppendColumn(
            "Max", format=wx.LIST_FORMAT_LEFT, width=widths[2]
        )
        self.table_numerical.AppendColumn(
            "Filter Type", format=wx.LIST_FORMAT_LEFT, width=widths[3]
        )
        self.data_table_numerical.widths = widths

    def __set_tooltips(self):
        self.button_categorical["add"].SetToolTip(
            "Add a categorical data filter."
        )
        self.button_categorical["del"].SetToolTip(
            "Delete the currently selected category filter."
        )
        self.button_categorical["edit"].SetToolTip(
            "Edit the currently selected category filter."
        )
        self.button_numerical["add"].SetToolTip("Add a numerical data filter.")
        self.button_numerical["del"].SetToolTip(
            "Delete the currently selected numerical data filter."
        )
        self.button_numerical["edit"].SetToolTip(
            "Edit the currently selected data filter."
        )
        self.button_query_execute.SetToolTip(
            "Query the database with the filters entered above. At least one "
            "filter must be added."
        )

    def __add_notebook_frames(self):
        self.plot = PlotStatDVH(
            self.notebook_tab["DVHs"], self.group_data, self.options
        )
        self.time_series = TimeSeriesFrame(self)
        self.correlation = CorrelationFrame(self)
        self.regression = RegressionFrame(self)
        self.control_chart = ControlChartFrame(self)
        self.radbio = RadBioFrame(self)
        self.endpoint = EndpointFrame(self)

        self.plot_frames = {
            "DVHs": self.plot,
            "Time Series": self.time_series,
            "Correlation": self.correlation,
            "Regression": self.regression,
            "Control Chart": self.control_chart,
        }

    def __do_layout(self):
        sizer_summary = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Summary"), wx.HORIZONTAL
        )
        sizer_query_numerical = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Query by Numerical Data"),
            wx.VERTICAL,
        )

        sizer_query_categorical = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Query by Categorical Data"),
            wx.VERTICAL,
        )

        sizer_categorical_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_numerical_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_query_exec_buttons = wx.BoxSizer(wx.HORIZONTAL)

        for key in ["add", "del", "edit"]:
            sizer_categorical_buttons.Add(
                self.button_categorical[key], 0, wx.ALL, 5
            )
            sizer_numerical_buttons.Add(
                self.button_numerical[key], 0, wx.ALL, 5
            )

        sizer_query_categorical.Add(
            sizer_categorical_buttons, 0, wx.ALL | wx.EXPAND, 5
        )
        sizer_query_categorical.Add(
            self.table_categorical, 1, wx.ALL | wx.EXPAND, 10
        )

        sizer_query_numerical.Add(
            sizer_numerical_buttons, 0, wx.ALL | wx.EXPAND, 5
        )
        sizer_query_numerical.Add(
            self.table_numerical, 1, wx.ALL | wx.EXPAND, 10
        )

        sizer_summary.Add(self.text_summary, 1, wx.EXPAND | wx.ALL, 5)

        panel_left = wx.BoxSizer(wx.VERTICAL)
        panel_left.Add(
            sizer_query_categorical,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHAPED | wx.TOP,
            5,
        )
        panel_left.Add(
            sizer_query_numerical,
            0,
            wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHAPED,
            5,
        )
        sizer_query_exec_buttons.Add(self.radio_button_query_group, 0, 0, 0)
        sizer_query_exec_buttons.Add(
            self.button_query_execute, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10
        )
        panel_left.Add(
            sizer_query_exec_buttons, 0, wx.EXPAND | wx.RIGHT | wx.LEFT, 5
        )
        panel_left.Add(sizer_summary, 1, wx.ALL | wx.EXPAND, 5)

        bitmap_logo = wx.StaticBitmap(
            self.notebook_tab["Welcome"],
            wx.ID_ANY,
            wx.Bitmap(LOGO_PATH, wx.BITMAP_TYPE_ANY),
        )
        text_welcome = wx.StaticText(
            self.notebook_tab["Welcome"],
            wx.ID_ANY,
            "\n\nWelcome to DVH Analytics.\nIf you already have a database built, design "
            "a query with the filters to the left.\n\n\n\nDVH Analytics is a software "
            "application to help radiation oncology departments build an in-house database "
            "of treatment planning data for the purpose of historical comparisons and "
            "statistical analysis. This code is still in development. Please contact the "
            "developer if you are interested in testing or collaborating.\n\nThe application "
            "builds a SQL database of DVHs and various planning parameters from DICOM files "
            "(i.e., Plan, Structure, Dose). Since the data is extracted directly from DICOM "
            "files, we intend to accommodate an array of treatment planning system vendors.",
            style=wx.ALIGN_CENTER,
        )

        text_welcome_size = get_window_size(0.417, 0.476)
        text_welcome.SetMinSize(text_welcome_size)
        text_welcome.Wrap(text_welcome_size[1])

        sizer_welcome = wx.BoxSizer(wx.VERTICAL)
        sizer_welcome.Add(
            bitmap_logo, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT | wx.TOP, 100
        )
        sizer_welcome.Add(text_welcome, 0, wx.ALIGN_CENTER | wx.ALL, 25)
        self.notebook_tab["Welcome"].SetSizer(sizer_welcome)

        self.notebook_tab["DVHs"].SetSizer(self.sizer_dvhs)

        sizer_endpoint = wx.BoxSizer(wx.VERTICAL)
        sizer_endpoint.Add(self.endpoint.layout, 0, wx.ALL, 25)
        self.notebook_tab["Endpoints"].SetSizer(sizer_endpoint)

        sizer_rad_bio = wx.BoxSizer(wx.VERTICAL)
        sizer_rad_bio.Add(self.radbio.layout, 0, wx.ALL, 25)
        self.notebook_tab["Rad Bio"].SetSizer(sizer_rad_bio)

        sizer_time_series = wx.BoxSizer(wx.VERTICAL)
        sizer_time_series.Add(
            self.time_series.layout, 1, wx.EXPAND | wx.ALL, 25
        )
        self.notebook_tab["Time Series"].SetSizer(sizer_time_series)

        sizer_correlation = wx.BoxSizer(wx.VERTICAL)
        sizer_correlation.Add(
            self.correlation.layout, 1, wx.EXPAND | wx.ALL, 25
        )
        self.notebook_tab["Correlation"].SetSizer(sizer_correlation)

        sizer_regression = wx.BoxSizer(wx.VERTICAL)
        sizer_regression.Add(self.regression.layout, 1, wx.EXPAND | wx.ALL, 25)
        self.notebook_tab["Regression"].SetSizer(sizer_regression)

        sizer_control_chart = wx.BoxSizer(wx.VERTICAL)
        sizer_control_chart.Add(
            self.control_chart.layout, 1, wx.EXPAND | wx.ALL, 25
        )
        self.notebook_tab["Control Chart"].SetSizer(sizer_control_chart)

        for key in self.tab_keys:
            self.notebook_main_view.AddPage(self.notebook_tab[key], key)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        hbox_main = wx.BoxSizer(wx.HORIZONTAL)
        hbox_main.Add(
            panel_left, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.TOP, 5
        )
        hbox_main.Add(
            self.notebook_main_view,
            1,
            wx.BOTTOM | wx.EXPAND | wx.RIGHT | wx.TOP,
            5,
        )
        sizer_main_wrapper.Add(hbox_main, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_main_wrapper, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()

        self.__apply_size_and_position()

    def __apply_size_and_position(self):
        if self.options.window_sizes["main"] is not None:
            size = self.options.window_sizes["main"]
        else:
            size = get_window_size(0.833, 0.875)
            size = apply_resolution_limits(size, self.options)

        self.SetSize(size)
        self.options.apply_window_position(self, "main")

        self.allow_window_size_save = True

    def __enable_initial_buttons_in_tabs(self):
        self.endpoint.enable_initial_buttons()
        self.radbio.enable_initial_buttons()
        self.time_series.enable_initial_buttons()

    def __disable_add_filter_buttons(self):
        self.button_categorical["add"].Disable()
        self.button_numerical["add"].Disable()

    def __enable_add_filter_buttons(self):
        self.button_categorical["add"].Enable()
        self.button_numerical["add"].Enable()

    def enable_query_buttons(self, query_type):
        for key in ["del", "edit"]:
            {
                "categorical": self.button_categorical[key],
                "numerical": self.button_numerical[key],
            }[query_type].Enable()

    def disable_query_buttons(self, query_type):
        for key in ["del", "edit"]:
            {
                "categorical": self.button_categorical[key],
                "numerical": self.button_numerical[key],
            }[query_type].Disable()

    def update_all_query_buttons(self):
        tables = {
            "numerical": self.data_table_numerical,
            "categorical": self.data_table_categorical,
        }
        for key, table in tables.items():
            if table.data is not None:
                [self.disable_query_buttons, self.enable_query_buttons][
                    table.row_count > 0
                ](key)
            else:
                self.disable_query_buttons(key)

        if (
            self.data_table_numerical.row_count
            + self.data_table_categorical.row_count
            > 0
        ):
            self.button_query_execute.Enable()
        else:
            self.button_query_execute.Disable()

        # Force user to populate group 1 first
        if self.selected_group == 2 and self.group_data[1]["dvh"] is None:
            self.button_query_execute.Disable()

    def __catch_failed_sql_connection_on_app_launch(self):
        if self.options.DB_TYPE_GRPS[1] == "pgsql":
            if not echo_sql_db():
                wx.MessageBox(
                    "Invalid credentials!",
                    "Echo SQL Database",
                    wx.OK | wx.ICON_WARNING,
                )
                self.on_sql()
        else:  # if using sqlite
            initialize_db()

    def __do_subscribe(self):
        pub.subscribe(self.raise_error_dialog, "import_status_raise_error")
        pub.subscribe(self.call_sqlite_backup, "backup_sqlite_db")
        pub.subscribe(
            self.correlation_patients_removed, "correlation_patients_removed"
        )

    def raise_error_dialog(self, msg):
        MemoryErrorDialog(self, msg)

    # --------------------------------------------------------------------------------------------------------------
    # Menu bar event functions
    # --------------------------------------------------------------------------------------------------------------
    def on_save(self, evt):
        if self.save_data:
            dlg = wx.FileDialog(
                self,
                "Save your session data to file",
                "",
                wildcard="*.dvha",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
            dlg.SetDirectory(DATA_DIR)
            if dlg.ShowModal() == wx.ID_OK:
                self.save_data_obj()
                save_object_to_file(self.save_data, dlg.GetPath())
            dlg.Destroy()
        else:
            wx.MessageBox(
                "There is no data to save. Please query/open some data first.",
                "Save Error",
                wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
            )

    def on_open(self, evt):
        dlg = wx.FileDialog(
            self,
            "Open saved data",
            "",
            wildcard="*.dvha",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.close()
            self.load_data_obj(dlg.GetPath())

        dlg.Destroy()

    def on_load_mvr_model(self, *evt):
        with wx.FileDialog(
            self,
            "Load a multi-variable linear regression model",
            "",
            wildcard="*.mvr",
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN,
        ) as dlg:
            dlg.SetDirectory(MODELS_DIR)
            if dlg.ShowModal() == wx.ID_OK:
                model_file_path = dlg.GetPath()
                dlg.Destroy()
                self.loaded_mvr_ml_frames.append(
                    LoadMultiVarModelFrame(
                        self,
                        model_file_path,
                        self.group_data,
                        self.selected_group,
                        self.options,
                    )
                )

    def on_load_ml_model(self, *evt):
        if self.group_data[self.selected_group]["stats_data"]:
            self.loaded_mvr_ml_frames.append(
                MachineLearningModelViewer(
                    self, self.group_data, self.selected_group, self.options
                )
            )
        else:
            wx.MessageBox(
                "No data as been queried for Group %s." % self.selected_group,
                "Error",
                wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
            )

    @property
    def selected_group(self):
        return self.radio_button_query_group.GetSelection() + 1

    def save_data_obj(self):
        self.save_data["group_data"] = self.group_data
        self.save_data["query_filters"] = self.query_filters
        self.save_data["time_stamp"] = datetime.now()
        self.save_data["version"] = DefaultOptions().VERSION
        # data_table_categorical and data_table_numerical saved after query to ensure these data reflect
        # the rest of the saved data
        self.save_data["endpoint"] = self.endpoint.get_save_data()
        self.save_data["time_series"] = self.time_series.get_save_data()
        self.save_data["radbio"] = self.radbio.get_save_data()
        self.save_data["regression"] = self.regression.get_save_data()
        self.save_data["control_chart"] = self.control_chart.get_save_data()

    def load_data_obj(self, abs_file_path):
        self.save_data = load_object_from_file(abs_file_path)
        self.group_data = self.save_data["group_data"]

        # .load_save_data loses column widths?
        self.radio_button_query_group.SetSelection(0)
        self.data_table_categorical.load_save_data(
            self.save_data["main_categorical_1"]
        )
        self.data_table_numerical.load_save_data(
            self.save_data["main_numerical_1"]
        )

        self.control_chart.load_save_data(self.save_data["control_chart"])

        self.radio_button_query_group.SetSelection(0)
        self.exec_query(load_saved_dvh_data=True, group=1)

        if "main_categorical_2" in self.save_data.keys():
            self.radio_button_query_group.SetSelection(1)
            self.on_group_select()
            self.data_table_categorical.load_save_data(
                self.save_data["main_categorical_2"]
            )
            self.data_table_numerical.load_save_data(
                self.save_data["main_numerical_2"]
            )
            self.update_all_query_buttons()

            self.exec_query(load_saved_dvh_data=True, group=2)

        self.update_all_query_buttons()

        self.endpoint.load_save_data(self.save_data["endpoint"])
        if self.endpoint.has_data:
            self.endpoint.enable_buttons()

        self.radbio.load_save_data(self.save_data["radbio"])

        self.endpoint.update_endpoints_in_dvh()

        self.group_data[1]["stats_data"].update_endpoints_and_radbio()
        if self.group_data[2]["stats_data"]:
            self.group_data[2]["stats_data"].update_endpoints_and_radbio()

        self.time_series.load_save_data(self.save_data["time_series"])
        self.time_series.update_plot()

        self.regression.update_combo_box_choices()
        self.regression.load_save_data(self.save_data["regression"])

        self.control_chart.update_combo_box_y_choices()

    def on_toolbar_settings(self, evt):
        self.on_pref()

    def on_toolbar_import(self, evt):
        self.check_db_then_call(
            ImportDicomFrame, "import", self.roi_map, self.options
        )

    def on_toolbar_database(self, evt):
        self.check_db_then_call(
            DatabaseEditorFrame, "database", self.roi_map, self.options
        )

    def on_toolbar_roi_map(self, evt):
        self.check_db_then_call(ROIMapFrame, "roi_map", self.roi_map)

    def on_toolbar_ml(self, evt):
        if self.group_data[self.selected_group]["dvh"] is not None:
            dlg = MachineLearningSetupDlg(
                self.group_data[self.selected_group]["stats_data"],
                self.options,
            )
            res = dlg.ShowModal()
            if res == wx.ID_OK:
                frame = ALGORITHMS[dlg.ml_alg]["frame"]
                self.ml_views.append(
                    frame(self, dlg.ml_input_data, alg_type=dlg.alg_type)
                )
            dlg.Destroy()
        else:
            wx.MessageBox(
                "There is no data to use! Please query some data first.",
                "Data Error",
                wx.OK | wx.ICON_WARNING,
            )

    def on_sqlite_backup(self, *evt):
        wx.CallAfter(do_sqlite_backup, self, self.options)

    def call_sqlite_backup(self):
        if self.options.AUTO_SQL_DB_BACKUP:
            self.on_sqlite_backup()

    def check_db_then_call(self, func, window_type, *parameters):
        if not echo_sql_db():
            self.on_sql()

        if echo_sql_db():
            if self.tool_bar_windows[window_type]:
                self.tool_bar_windows[window_type].Raise()
            else:
                self.tool_bar_windows[window_type] = func(*parameters)
        else:
            wx.MessageBox(
                "Connection to SQL database could not be established.",
                "Connection Error",
                wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
            )

    def on_export_pgsql(self, evt):
        if self.options.DB_TYPE_GRPS[1] == "pgsql":
            dlg = wx.FileDialog(
                self,
                "Export your PGSQL DB to SQLite",
                "",
                wildcard="*.db",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
            dlg.SetDirectory(DATA_DIR)
            if dlg.ShowModal() == wx.ID_OK:
                ExportPGSQLProgressFrame(dlg.GetPath())
        else:
            wx.MessageBox(
                "This is for PostgreSQL only. Your main (Group 1) connection is SQLite. "
                "Use Data->Backup SQLite DB instead.",
                "DB Export Error",
                wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
            )

    def on_export_db_to_json(self, evt):
        dlg = wx.FileDialog(
            self,
            "Export your entire DB to JSON",
            "",
            wildcard="*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        dlg.SetDirectory(DATA_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            ExportPGSQLProgressFrame(dlg.GetPath(), export_to_json=True)

    # --------------------------------------------------------------------------------------------------------------
    # Query event functions
    # --------------------------------------------------------------------------------------------------------------
    def on_item_select_categorical(self, evt):
        self.selected_index_categorical = (
            self.table_categorical.GetFirstSelected()
        )

    def on_item_select_numerical(self, evt):
        self.selected_index_numerical = self.table_numerical.GetFirstSelected()

    def add_row_categorical(self, evt):
        query_dlg(self, "categorical")
        self.button_query_execute.Enable()
        self.update_all_query_buttons()

    def add_row_numerical(self, evt):
        query_dlg(self, "numerical")
        self.update_all_query_buttons()

    def edit_row_categorical(self, *args):
        if self.selected_index_categorical is not None:
            query_dlg(self, "categorical", set_values=True)

    def edit_row_numerical(self, *args):
        if self.selected_index_numerical is not None:
            query_dlg(self, "numerical", set_values=True)

    def doubleclick_categorical(self, evt):
        self.selected_index_categorical = (
            self.table_categorical.GetFirstSelected()
        )
        self.edit_row_categorical()

    def doubleclick_numerical(self, evt):
        self.selected_index_numerical = self.table_numerical.GetFirstSelected()
        self.edit_row_numerical()

    def del_row_categorical(self, evt):
        self.data_table_categorical.delete_row(self.selected_index_categorical)
        self.selected_index_categorical = None
        self.update_all_query_buttons()

    def del_row_numerical(self, evt):
        self.data_table_numerical.delete_row(self.selected_index_numerical)
        self.selected_index_numerical = None
        self.update_all_query_buttons()

    def exec_query_button(self, evt):
        self.exec_query()

    def exec_query(self, load_saved_dvh_data=False, group=None):

        # Used to make sure Correlation calculation error of patient removal is only displayed once after a query
        self.correlation_error_displayed = False

        wx.BeginBusyCursor()
        if group is not None:
            self.radio_button_query_group.SetSelection(group - 1)
        group = self.selected_group

        # TODO: retain group 1 endpoint defs after query of group 2
        self.endpoint.clear_data()

        if group == 1:
            self.plot.clear_plot()
            self.time_series.clear_data()
            self.regression.clear(self.group_data)
            self.control_chart.clear_data()
            self.radbio.clear_data()

        if not load_saved_dvh_data:
            try:
                uids, dvh_str = self.get_query()
                self.group_data[group]["dvh"] = DVH(
                    dvh_condition=dvh_str,
                    uid=uids,
                    dvh_bin_width=self.options.dvh_bin_width,
                    group=group,
                )
            except MemoryError:
                msg = (
                    "Querying memory error. Try querying less data. At least %s DVHs returned.\n"
                    "NOTE: Threshold of this error is dependent on your computer."
                    % self.group_data[group]["dvh"].count
                )
                MemoryErrorDialog(self, msg)
                self.close()
                return

        count = self.group_data[group]["dvh"].count
        min_dvh_count = 3
        if count >= min_dvh_count:
            try:
                self.endpoint.update_dvh(self.group_data)
                self.set_summary_text(group)
                self.plot.update_plot(
                    self.group_data[1]["dvh"], dvh_2=self.group_data[2]["dvh"]
                )
                wx.EndBusyCursor()
                self.update_data(
                    load_saved_dvh_data=load_saved_dvh_data,
                    group_2_only=bool(group - 1),
                )

                if group == 1:
                    self.notebook_main_view.SetSelection(1)
                    self.__enable_initial_buttons_in_tabs()

                self.save_data[
                    "main_categorical_%s" % group
                ] = self.data_table_categorical.get_save_data()
                self.save_data[
                    "main_numerical_%s" % group
                ] = self.data_table_numerical.get_save_data()

                if group == 2:
                    self.regression.group = 2
                    self.control_chart.group = 2
                    self.update_stats_data_plots()

            except PlottingMemoryError as e:
                wx.EndBusyCursor()
                self.on_plotting_memory_error(str(e))
        else:
            wx.EndBusyCursor()
            msg = (
                "%s DVHs returned. Please modify query or import more data."
                % ["Less than %s" % min_dvh_count, "No"][count == 0]
            )
            wx.MessageBox(
                msg, "Query Error", wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING
            )
            self.group_data[group]["dvh"] = None

    def get_query(self):

        # Used to accumulate lists of query strings for each table
        # Will assume each item in list is complete query for that SQL column
        queries = {"Plans": [], "Rxs": [], "Beams": [], "DVHs": []}

        # Used to group queries by variable, will combine all queries of same variable with an OR operator
        # e.g., queries_by_sql_column['Plans'][key] = list of strings, where key is sql column
        queries_by_sql_column = {
            "Plans": {},
            "Rxs": {},
            "Beams": {},
            "DVHs": {},
        }
        operator_by_sql_column = {
            "Plans": {},
            "Rxs": {},
            "Beams": {},
            "DVHs": {},
        }

        # Categorical filter
        if self.data_table_categorical.row_count:
            for i, category in enumerate(
                self.data_table_categorical.data["category_1"]
            ):
                table = self.categorical_columns[category]["table"]
                col = self.categorical_columns[category]["var_name"]
                value = self.data_table_categorical.data["category_2"][i]
                if col not in queries_by_sql_column[table]:
                    queries_by_sql_column[table][col] = []
                    operator_by_sql_column[table][col] = []
                operator = ["=", "!="][
                    {"Include": 0, "Exclude": 1}[
                        self.data_table_categorical.data["Filter Type"][i]
                    ]
                ]
                queries_by_sql_column[table][col].append(
                    "%s %s '%s'" % (col, operator, value)
                )
                operator_by_sql_column[table][col].append(
                    self.data_table_categorical.data["Filter Type"][i]
                )

        # Range filter
        if self.data_table_numerical.row_count:
            for i, category in enumerate(
                self.data_table_numerical.data["category"]
            ):
                table = self.numerical_columns[category]["table"]
                col = self.numerical_columns[category]["var_name"]
                value_low = self.data_table_numerical.data["min"][i]
                value_high = self.data_table_numerical.data["max"][i]
                if "date" in col:
                    value_low = "'%s'" % value_low
                    value_high = "'%s'" % value_high
                    if self.options.DB_TYPE_GRPS[1] == "pgsql":
                        value_low = value_low + "::date"
                        value_high = value_high + "::date"
                if col not in queries_by_sql_column[table]:
                    queries_by_sql_column[table][col] = []
                    operator_by_sql_column[table][col] = []
                operator = ["BETWEEN", "NOT BETWEEN"][
                    {"Include": 0, "Exclude": 1}[
                        self.data_table_numerical.data["Filter Type"][i]
                    ]
                ]
                queries_by_sql_column[table][col].append(
                    "%s %s %s AND %s" % (col, operator, value_low, value_high)
                )
                operator_by_sql_column[table][col].append(
                    self.data_table_numerical.data["Filter Type"][i]
                )

        for table in queries:
            for col in queries_by_sql_column[table]:
                includes = [
                    item
                    for i, item in enumerate(queries_by_sql_column[table][col])
                    if operator_by_sql_column[table][col][i]
                ]
                excludes = [
                    item
                    for i, item in enumerate(queries_by_sql_column[table][col])
                    if not operator_by_sql_column[table][col][i]
                ]

                includes_str = (
                    "(%s)" % " OR ".join(includes) if includes else None
                )
                excludes_str = (
                    "(%s)" % " AND ".join(excludes) if excludes else None
                )

                queries[table].append(
                    "(%s)"
                    % " AND ".join(
                        [item for item in [includes_str, excludes_str] if item]
                    )
                )
            queries[table] = " AND ".join(queries[table])

        uids = get_study_instance_uids(
            plans=queries["Plans"], rxs=queries["Rxs"], beams=queries["Beams"]
        )["common"]

        return uids, queries["DVHs"]

    def update_data(self, load_saved_dvh_data=False, group_2_only=False):
        wx.BeginBusyCursor()
        tables = ["Plans", "Rxs", "Beams"]
        for grp, grp_data in self.group_data.items():
            if not (grp == 1 and group_2_only) or grp == 2:
                if hasattr(grp_data["dvh"], "study_instance_uid"):
                    if not load_saved_dvh_data:
                        condition_str = (
                            "study_instance_uid in ('%s')"
                            % "','".join(grp_data["dvh"].study_instance_uid)
                        )
                        grp_data["data"] = {
                            key: QuerySQL(key, condition_str) for key in tables
                        }
                        grp_data["stats_data"] = StatsData(
                            grp_data["dvh"], grp_data["data"], group=grp
                        )
                else:
                    grp_data["data"] = {key: None for key in tables}
                    grp_data["stats_data"] = None

        if self.group_data[2]["stats_data"]:
            sync_variables_in_stats_data_objects(
                self.group_data[1]["stats_data"],
                self.group_data[2]["stats_data"],
            )
        self.time_series.update_data(self.group_data)
        self.control_chart.update_data(self.group_data)
        self.correlation.set_data(self.group_data)
        self.regression.update_combo_box_choices()
        self.radbio.update_dvh_data(self.group_data)

        wx.EndBusyCursor()

    # --------------------------------------------------------------------------------------------------------------
    # Menu bar event functions
    # --------------------------------------------------------------------------------------------------------------
    def close_windows(self):

        pub.sendMessage("import_dicom_cancel")

        for view in self.data_views.values():
            if hasattr(view, "Destroy"):
                try:
                    view.Destroy()
                except RuntimeError:
                    pass

        if self.user_settings is not None:
            self.user_settings.Close()

        if self.export_figure is not None:
            self.export_figure.Close()

        for window in self.tool_bar_windows.values():
            if window and hasattr(window, "Destroy"):
                window.Destroy()

        for view in self.ml_views:
            if hasattr(view, "Destroy"):
                try:
                    view.Destroy()
                except RuntimeError:
                    pass

        self.regression.close_mvr_frames()

    def on_quit(self, evt):
        self.close_windows()
        self.Destroy()

    def on_close(self, *evt):
        if self.group_data[1]["dvh"]:
            dlg = wx.MessageDialog(
                self,
                "Clear all data and plots?",
                caption="Close",
                style=wx.YES
                | wx.NO
                | wx.NO_DEFAULT
                | wx.CENTER
                | wx.ICON_EXCLAMATION,
            )
            dlg.Center()
            res = dlg.ShowModal()
            if res == wx.ID_YES:
                self.close()
                self.radio_button_query_group.SetSelection(0)
            dlg.Destroy()

    def close(self):
        self.group_data = {
            1: {
                "dvh": None,
                "data": {key: None for key in ["Plans", "Beams", "Rxs"]},
                "stats_data": None,
            },
            2: {
                "dvh": None,
                "data": {key: None for key in ["Plans", "Beams", "Rxs"]},
                "stats_data": None,
            },
        }
        self.data_table_categorical.delete_all_rows()
        self.data_table_numerical.delete_all_rows()
        self.plot.clear_plot()
        self.endpoint.clear_data()
        self.radbio.clear_data()
        self.time_series.clear_data()
        self.notebook_main_view.SetSelection(0)
        self.text_summary.SetValue("")
        self.disable_query_buttons("categorical")
        self.disable_query_buttons("numerical")
        self.button_query_execute.Disable()
        self.time_series.initialize_y_axis_options()
        self.regression.clear(self.group_data)
        self.control_chart.initialize_y_axis_options()
        self.control_chart.plot.clear_plot()
        self.control_chart.group = 1
        self.close_windows()
        self.reset_query_filters()

    def on_export(self, evt):
        if self.group_data[1]["dvh"] is not None:
            ExportCSVDialog(self)
        else:
            wx.MessageBox(
                "There is no data to export! Please query some data first.",
                "Export Error",
                wx.OK | wx.ICON_WARNING,
            )

    @staticmethod
    def on_githubpage(evt):
        webbrowser.open_new_tab("http://dvhanalytics.com/")

    @staticmethod
    def on_dvha_edit(evt):
        webbrowser.open_new_tab(
            "https://github.com/cutright/DVHA-DICOM-Editor"
        )

    @staticmethod
    def on_report_issue(evt):
        webbrowser.open_new_tab(
            "https://github.com/cutright/DVH-Analytics/issues"
        )

    def on_pref(self, *args):
        if self.user_settings is None:
            self.user_settings = UserSettings(self)
            self.user_settings.Show()
        else:
            self.user_settings.Raise()

    def on_sql(self, *args):
        self.open_sql_setting(group=1)

    def on_sql_2(self, *args):
        self.open_sql_setting(group=2)

    def open_sql_setting(self, group):
        SQLSettingsDialog(self.options, group)
        [self.__disable_add_filter_buttons, self.__enable_add_filter_buttons][
            echo_sql_db(group=self.selected_group)
        ]()

    def on_export_figure(self, evt):
        if self.save_data:
            if self.export_figure is None:
                try:
                    self.export_figure = ExportFigure(self)
                except Exception:
                    self.options.save_fig_param = (
                        DefaultOptions().save_fig_param
                    )
                    self.export_figure = ExportFigure(self)
                self.export_figure.Show()
            else:
                self.export_figure.Raise()
        else:
            wx.MessageBox(
                "There is no data to save. Please query/open some data first.",
                "Save Error",
                wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
            )

    def on_view_dvhs(self, evt):
        self.view_table_data("DVHs")

    def on_view_plans(self, evt):
        self.view_table_data("Plans")

    def on_view_rxs(self, evt):
        self.view_table_data("Rxs")

    def on_view_beams(self, evt):
        self.view_table_data("Beams")

    def on_view_stats_data_1(self, evt):
        self.view_table_data("StatsData1")

    def on_view_stats_data_2(self, evt):
        self.view_table_data("StatsData2")

    def view_table_data(self, key):
        if key == "DVHs":
            data = {grp: self.group_data[grp]["dvh"] for grp in [1, 2]}
        elif "StatsData" in key:
            data = {grp: self.group_data[grp]["stats_data"] for grp in [1, 2]}
        else:
            data = {grp: self.group_data[grp]["data"][key] for grp in [1, 2]}

        if data[1]:

            if self.get_menu_item_status(key) == "Show":
                if "StatsData" in key:
                    group = int(key[-1])
                    if group == 1 or data[2] is not None:
                        self.data_views[key] = StatsDataEditor(
                            self.group_data,
                            group,
                            self.data_menu,
                            self.data_menu_items[key].GetId(),
                            self.time_series,
                            self.regression,
                            self.control_chart,
                        )
                    else:
                        self.no_queried_data_dlg()
                else:
                    if key == "DVHs":
                        columns = [c for c in data[1].keys]
                    elif key == "Rxs":
                        columns = [
                            "plan_name",
                            "fx_dose",
                            "rx_percent",
                            "fxs",
                            "rx_dose",
                            "fx_grp_number",
                            "fx_grp_count",
                            "fx_grp_name",
                            "normalization_method",
                            "normalization_object",
                        ]
                    else:
                        columns = [
                            obj["var_name"]
                            for obj in sql_column_info.values()
                            if obj["table"] == key
                        ]

                    for starter_column in ["study_instance_uid", "mrn"]:
                        if starter_column in columns:
                            columns.pop(columns.index(starter_column))
                        columns.insert(0, starter_column)

                    self.data_views[key] = QueriedDataFrame(
                        data,
                        columns,
                        key,
                        self.data_menu,
                        self.data_menu_items[key].GetId(),
                    )
            else:
                self.data_views[key].on_close()
                self.data_views[key] = None
        else:
            self.no_queried_data_dlg()

    def no_queried_data_dlg(self):
        dlg = wx.MessageDialog(
            self,
            "Please query/open some data first.",
            "ERROR!",
            wx.ICON_ERROR | wx.OK_DEFAULT,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def get_menu_item_status(self, key):
        show_hide = ["Hide", "Show"][
            "Show"
            in self.data_menu.GetLabel(self.data_menu_items[key].GetId())
        ]
        return show_hide

    def redraw_plots(self):
        if self.group_data[1]["dvh"]:
            if self.active_tab in self.do_plot_refresh.keys():
                self.do_plot_refresh[self.active_tab] = False
            if self.active_tab == "DVHs":
                self.plot.redraw_plot()
            elif self.active_tab in self.plot_frames.keys():
                self.plot_frames[self.active_tab].plot.redraw_plot()
            # self.plot.redraw_plot()
            # self.time_series.plot.redraw_plot()
            # self.correlation.plot.redraw_plot()
            # self.regression.plot.redraw_plot()
            # self.control_chart.plot.redraw_plot()

    def apply_plot_options(self):
        self.plot.apply_options()
        self.time_series.plot.apply_options()
        self.correlation.plot.apply_options()
        self.regression.apply_plot_options()  # applies to MVR frames too
        self.control_chart.plot.apply_options()

        for frame in self.loaded_mvr_ml_frames:
            try:
                frame.apply_plot_options()
            except RuntimeError:
                pass

    def update_stats_data_plots(self):
        if self.group_data[1]["dvh"]:
            self.time_series.update_plot()
            self.time_series.update_y_axis_options()
            self.regression.update_plot()
            self.control_chart.update_plot()

    def on_resize(self, *evt):
        try:
            if self.allow_window_size_save:
                self.options.set_window_size(self, "main")
            self.Refresh()
            self.Layout()
            for key in self.do_plot_refresh.keys():
                self.do_plot_refresh[key] = True
            wx.CallAfter(self.redraw_plots)
        except RuntimeError:
            pass

    def on_reset_windows(self, *evt):
        defaults = DefaultOptions()
        for key in ["MIN_RESOLUTION_MAIN", "MAX_INIT_RESOLUTION_MAIN"]:
            self.options.set_option(key, getattr(defaults, key))
        self.options.clear_positions()
        self.options.clear_window_sizes()
        self.__apply_size_and_position()

    def on_move(self, *evt):
        try:
            self.options.save_window_position(self, "main")
        except Exception:
            pass

    def on_plotting_memory_error(self, plot_type):
        plot_type = [" (Plot type: %s)" % plot_type, ""][plot_type is None]
        msg = (
            "Plotting memory error%s. Try querying less data. At least %s DVHs returned.\n"
            "NOTE: Threshold of this error is dependent on your computer."
            % (plot_type, self.group_data[1]["dvh"].count)
        )
        MemoryErrorDialog(self, msg)
        self.close()

    def correlation_patients_removed(self, msg):
        if not self.correlation_error_displayed:
            msg = (
                "These MRN(s) were removed from some or all of the Correlation calculations:\n%s"
                % ", ".join(list(msg["mrns"]))
            )
            caption = "Non-numerical data detected."
            wx.CallAfter(ErrorDialog, self, msg, caption)
            self.correlation_error_displayed = True

    def reset_query_filters(self):
        self.query_filters = {key: None for key in [1, 2]}

    def on_group_select(self, *evt):
        group = self.selected_group
        other = 3 - group

        self.button_query_execute.SetLabelText(
            "Query and Retrieve Group %s" % group
        )

        self.query_filters[other] = {
            "main_categorical": self.data_table_categorical.get_save_data(),
            "main_numerical": self.data_table_numerical.get_save_data(),
        }
        if self.query_filters[group] is not None:
            self.data_table_categorical.load_save_data(
                self.query_filters[group]["main_categorical"]
            )
            self.data_table_numerical.load_save_data(
                self.query_filters[group]["main_numerical"]
            )
        else:
            self.data_table_categorical.delete_all_rows()
            self.data_table_numerical.delete_all_rows()

        self.update_all_query_buttons()

        self.set_summary_text(group)

        if self.group_data[2]["stats_data"]:
            self.regression.group = group
            self.regression.update_plot()
            self.control_chart.group = group
            self.control_chart.update_plot()

    def set_summary_text(self, group):
        if self.group_data[group]["dvh"]:
            text = self.group_data[group]["dvh"].get_summary()
        else:
            text = ""
        self.text_summary.SetValue(text)

    def InstallThreadExcepthook(self):
        """Workaround for sys.excepthook thread bug from Jonathan Ellis
        (http://bugs.python.org/issue1230540).
        Call once from __main__ before creating any threads.
        If using psyco, call psyco.cannotcompile(threading.Thread.run)
        since this replaces a new-style class method."""

        run_old = threading.Thread.run

        def Run(*args, **kwargs):
            try:
                run_old(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                sys.excepthook(*sys.exc_info())

        threading.Thread.run = Run

    def on_page_selection(self, event):
        index = event.GetSelection()
        key = self.tab_keys[index]
        self.active_tab = key
        if key not in self._created_tabs:
            self._created_tabs.append(key)
            if key in self.plot_frames.keys():
                self.do_plot_refresh[key] = False
                if key == "DVHs":
                    self.plot.init_layout()
                    self.sizer_dvhs.Add(
                        self.plot.layout, 1, wx.EXPAND | wx.ALL, 25
                    )
                    self.notebook_tab["DVHs"].Layout()
                else:
                    self.plot_frames[key].add_plot_to_layout()
        elif key in self.do_plot_refresh and self.do_plot_refresh[key]:
            self.do_plot_refresh[key] = False
            if key == "DVHs":
                self.plot.redraw_plot()
            elif key in self.plot_frames.keys():
                self.plot_frames[key].plot.redraw_plot()
        event.Skip()


class MainApp(wx.App):
    def OnInit(self):
        initialize_directories()
        if is_windows():
            from dvha.tools.windows_reg_edit import (
                set_ie_emulation_level,
                set_ie_lockdown_level,
            )

            set_ie_emulation_level()
            set_ie_lockdown_level()
        self.SetAppName("DVH Analytics")
        self.frame = DVHAMainFrame(None, wx.ID_ANY, "")
        set_frame_icon(self.frame)
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

    def OnExit(self):
        self.frame.options.save()
        for window in wx.GetTopLevelWindows():
            wx.CallAfter(window.Close)
        return super().OnExit()

    def InitLocale(self):
        # https://docs.wxpython.org/MigrationGuide.html#possible-locale-mismatch-on-windows
        if is_windows():
            return
        super().InitLocale()


def start():
    app = MainApp(0)
    app.MainLoop()
