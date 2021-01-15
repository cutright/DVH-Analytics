#!/usr/bin/env python
# -*- coding: utf-8 -*-

# paths.py
"""
A collection of directories and paths updated with the script directory and user's home folder for the OS
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import sys
from os import environ
from os.path import join, dirname, expanduser, pathsep

SCRIPT_DIR = dirname(__file__)
PARENT_DIR = getattr(
    sys, "_MEIPASS", dirname(SCRIPT_DIR)
)  # PyInstaller compatibility
RESOURCES_DIR = join(SCRIPT_DIR, "resources")
ICONS_DIR = join(RESOURCES_DIR, "icons")
WIN_APP_ICON = join(ICONS_DIR, "dvha_new.ico")
LOGO_PATH = join(RESOURCES_DIR, "logo.png")
APPS_DIR = join(expanduser("~"), "Apps")
APP_DIR = join(APPS_DIR, "dvh_analytics")
PREF_DIR = join(APP_DIR, "preferences")
DATA_DIR = join(APP_DIR, "data")
INBOX_DIR = join(DATA_DIR, "inbox")
IMPORTED_DIR = join(DATA_DIR, "imported")
REVIEW_DIR = join(DATA_DIR, "review")
BACKUP_DIR = join(DATA_DIR, "backup")
TEMP_DIR = join(DATA_DIR, "temp")
MODELS_DIR = join(DATA_DIR, "models")
DIRECTORIES = {
    key[:-4]: value for key, value in locals().items() if key.endswith("_DIR")
}

OPTIONS_PATH = join(PREF_DIR, ".options")
OPTIONS_CHECKSUM_PATH = join(PREF_DIR, ".options_checksum")
SQL_CNF_PATH = join(PREF_DIR, "sql_connection.cnf")
LICENSE_PATH = join(RESOURCES_DIR, "LICENSE.txt")
CREATE_PGSQL_TABLES = join(SCRIPT_DIR, "db", "create_tables.sql")
CREATE_SQLITE_TABLES = join(SCRIPT_DIR, "db", "create_tables_sqlite.sql")
TG263_CSV = join(
    SCRIPT_DIR, "resources", "TG263_Nomenclature_Worksheet_20170815.csv"
)
PIP_LIST_PATH = join(SCRIPT_DIR, "resources", "pip_list")

ICONS = {
    "Open": "iconfinder_Open_1493293.png",
    "Close": "iconfinder_Close_1493281.png",
    "Save": "iconfinder_Save_1493294.png",
    "Print": "iconfinder_Print_1493286.png",
    "Export": "iconfinder_csv_file_database_extension_data_3876336.png",
    "Import": "iconfinder_import_4168538.png",
    "Settings": "iconfinder_Settings_1493289.png",
    "Database": "iconfinder_data_115746_black_edit.png",
    "ROI Map": "iconfinder_icon-map_211858.png",
    "ok-green": "iconfinder_ok-green_53916.png",
    "ko-red": "iconfinder_ko-red_53948.png",
    "custom_Y": "icon_custom_Y.png",
    "custom_X": "icon_custom_X.png",
    "rtplan": "iconfinder_Clipboard-Plan_379537_zoom.png",
    "rtstruct": "iconfinder_Education-Filled_7_3672892.png",
    "rtdose": "iconfinder_package-supported_24220.png",
    "other": "error.png",
    "studies": "iconfinder_User_Customers_1218712.png",
    "study": "iconfinder_Travel-Filled-07_3671983.png",
    "plan": "iconfinder_Clipboard-Plan_379537_zoom.png",
    "patient": "iconfinder_User_Yuppie_3_1218716.png",
    "Image": "iconfinder_m-52_4230522.png",
    "AI": "neural-network_clipart2769230_edit.png",
}
for key, value in ICONS.items():
    ICONS[key] = join(ICONS_DIR, value)


def set_phantom_js_path_environment():
    """Edit the PATH environment for PhantomJS (for Bokeh's .svg export)"""
    phantom_js_path = getattr(sys, "_MEIPASS", APP_DIR)
    if phantom_js_path not in environ["PATH"]:
        environ["PATH"] += pathsep + phantom_js_path
