#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.import_dicom.py
"""
Classes for the DICOM import GUI and threading
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
import wx.adv
from wx.lib.agw.customtreectrl import (
    CustomTreeCtrl,
    TR_AUTO_CHECK_CHILD,
    TR_AUTO_CHECK_PARENT,
    TR_DEFAULT_STYLE,
)
from datetime import date as datetime_obj, datetime
from dateutil.parser import parse as parse_date
from os import listdir, remove
from os.path import isdir, join
from pubsub import pub
from multiprocessing import Pool
from threading import Thread
from queue import Queue
from functools import partial
from dvha.db import update as db_update
from dvha.db.sql_connector import DVH_SQL, write_test as sql_write_test
from dvha.models.dicom_tree_builder import (
    DicomTreeBuilder,
    PreImportFileSetParserWorker,
)
from dvha.db.dicom_parser import DICOM_Parser, PreImportData
from dvha.dialogs.main import DatePicker
from dvha.dialogs.roi_map import (
    AddPhysician,
    AddPhysicianROI,
    DelPhysicianROI,
    AssignVariation,
    DelVariation,
    AddROIType,
    RoiManager,
    ChangePlanROIName,
)
from dvha.models.data_table import DataTable
from dvha.models.roi_map import RemapROIFrame
from dvha.paths import ICONS, TEMP_DIR
from dvha.tools.dicom_dose_sum import DoseGrid
from dvha.tools.errors import ErrorDialog, push_to_log
from dvha.tools.roi_name_manager import clean_name
from dvha.tools.utilities import (
    datetime_to_date_string,
    get_elapsed_time,
    move_files_to_new_path,
    rank_ptvs_by_D95,
    set_msw_background_color,
    is_windows,
    get_tree_ctrl_image,
    remove_empty_sub_folders,
    get_window_size,
    set_frame_icon,
    PopupMenu,
    MessageDialog,
    get_new_uids_by_directory,
    edit_study_uid,
)
from dvha.tools.threading_progress import ProgressFrame


class ImportDicomFrame(wx.Frame):
    """
    Class used to generate the DICOM import GUI
    """

    def __init__(self, roi_map, options, inbox=None, auto_parse=False):
        """
        :param roi_map: roi_map object
        :type roi_map: DatabaseROIs
        :param options: user options object
        :type options: Options
        :param inbox: set the inbox, defaults to value in options if None
        """
        wx.Frame.__init__(self, None, title="Import DICOM")
        set_frame_icon(self)

        set_msw_background_color(
            self
        )  # If windows, change the background color

        self.options = options
        self.auto_parse = auto_parse
        self.inbox = inbox

        with DVH_SQL() as cnx:
            cnx.initialize_database()

        self.SetSize(get_window_size(0.804, 0.762))

        self.parsed_dicom_data = {}
        self.selected_uid = None

        self.roi_map = roi_map
        self.selected_roi = None

        self.start_path = self.options.INBOX_DIR

        self.checkbox = {}
        keys = [
            "birth_date",
            "sim_study_date",
            "physician",
            "tx_site",
            "rx_dose",
        ]
        for key in keys:
            self.checkbox["%s_1" % key] = wx.CheckBox(
                self, wx.ID_ANY, "Apply to all studies"
            )
            self.checkbox["%s_2" % key] = wx.CheckBox(
                self, wx.ID_ANY, "Only if missing"
            )
        self.global_plan_over_rides = {
            key: {"value": None, "only_if_missing": False} for key in keys
        }

        self.text_ctrl_directory = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )

        with DVH_SQL() as cnx:
            tx_sites = cnx.get_unique_values("Plans", "tx_site")

        self.input = {
            "mrn": wx.TextCtrl(self, wx.ID_ANY, ""),
            "study_instance_uid": wx.TextCtrl(self, wx.ID_ANY, ""),
            "birth_date": wx.TextCtrl(
                self, wx.ID_ANY, "", style=wx.TE_READONLY
            ),
            "sim_study_date": wx.TextCtrl(
                self, wx.ID_ANY, "", style=wx.TE_READONLY
            ),
            "physician": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=self.roi_map.get_physicians(),
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "tx_site": wx.ComboBox(
                self, wx.ID_ANY, choices=tx_sites, style=wx.CB_DROPDOWN
            ),
            "rx_dose": wx.TextCtrl(self, wx.ID_ANY, ""),
        }
        # 'fx_grp': wx.ComboBox(self, wx.ID_ANY, choices=['1'], style=wx.CB_DROPDOWN | wx.CB_READONLY)}

        self.input["physician"].SetValue("")
        self.input["tx_site"].SetValue("")
        # self.input['fx_grp'].SetValue('1')
        self.button_edit_sim_study_date = wx.Button(self, wx.ID_ANY, "Edit")
        self.button_edit_birth_date = wx.Button(self, wx.ID_ANY, "Edit")

        self.button_apply_plan_data = wx.Button(self, wx.ID_ANY, "Apply")
        self.button_delete_study = wx.Button(
            self, wx.ID_ANY, "Delete Study in Database with this UID"
        )
        self.button_delete_study.Disable()
        self.button_add_physician = wx.Button(self, wx.ID_ANY, "Add")

        self.button_browse = wx.Button(self, wx.ID_ANY, u"Browse…")
        self.checkbox_subfolders = wx.CheckBox(
            self, wx.ID_ANY, "Search within sub-folders"
        )
        self.checkbox_keep_in_inbox = wx.CheckBox(
            self, wx.ID_ANY, "Leave files in inbox"
        )
        self.checkbox_copy_misc_files = wx.CheckBox(
            self, wx.ID_ANY, "Copy images/misc DICOM"
        )
        self.panel_study_tree = wx.Panel(
            self, wx.ID_ANY, style=wx.BORDER_SUNKEN
        )
        self.button_import = wx.Button(self, wx.ID_ANY, "Import")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_save_roi_map = wx.Button(self, wx.ID_ANY, "Save ROI Map")
        self.button_preprocess = wx.Button(
            self, wx.ID_ANY, "Pre-Process DICOM"
        )

        self.panel_roi_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.input_roi = {
            "physician": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=[],
                style=wx.CB_DROPDOWN | wx.CB_READONLY,
            ),
            "type": wx.ComboBox(
                self,
                wx.ID_ANY,
                choices=self.options.ROI_TYPES,
                style=wx.CB_DROPDOWN,
            ),
        }
        self.input_roi["type"].SetValue("")
        self.button_roi_manager = wx.Button(self, wx.ID_ANY, "ROI Manager")

        self.button_save_roi_type_in_map = wx.Button(
            self, wx.ID_ANY, "Store in ROI Map"
        )

        self.enable_inputs(False)
        self.disable_roi_inputs()

        styles = TR_AUTO_CHECK_CHILD | TR_AUTO_CHECK_PARENT | TR_DEFAULT_STYLE
        self.tree_ctrl_import = CustomTreeCtrl(
            self.panel_study_tree, wx.ID_ANY, agwStyle=styles
        )
        self.tree_ctrl_import.SetBackgroundColour(wx.WHITE)

        self.tree_ctrl_roi = CustomTreeCtrl(
            self.panel_roi_tree, wx.ID_ANY, agwStyle=TR_DEFAULT_STYLE
        )
        self.tree_ctrl_roi.SetBackgroundColour(wx.WHITE)
        self.tree_ctrl_roi_root = self.tree_ctrl_roi.AddRoot(
            "RT Structures (right-click an ROI to edit)", ct_type=0
        )

        self.checkbox_include_uncategorized = wx.CheckBox(
            self, wx.ID_ANY, "Import uncategorized ROIs"
        )
        self.checkbox_auto_sum_dose = wx.CheckBox(
            self, wx.ID_ANY, "Sum all dose grids in a study"
        )

        self.allow_input_roi_apply = False

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()
        self.__do_subscribe()

        self.is_all_data_parsed = False
        self.dicom_importer = None

        self.incomplete_studies = []

        self.PreprocessDicom = None

        self.run()

    def __do_subscribe(self):
        """After DICOM directory is scanned and sorted, parse_dicom_data will be called"""
        pub.subscribe(self.parse_dicom_data, "parse_dicom_data")
        pub.subscribe(
            self.set_pre_import_parsed_dicom_data,
            "set_pre_import_parsed_dicom_data",
        )
        pub.subscribe(self.pre_import_complete, "pre_import_complete")
        pub.subscribe(self.pre_import_canceled, "pre_import_canceled")
        pub.subscribe(self.build_dicom_file_tree, "build_dicom_file_tree")

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_browse, id=self.button_browse.GetId())

        self.Bind(
            wx.EVT_TREE_SEL_CHANGED,
            self.on_file_tree_select,
            id=self.tree_ctrl_import.GetId(),
        )
        self.Bind(
            wx.EVT_TREE_SEL_CHANGED,
            self.on_roi_tree_select,
            id=self.tree_ctrl_roi.GetId(),
        )
        self.Bind(
            wx.EVT_TREE_ITEM_RIGHT_CLICK,
            self.on_roi_tree_right_click,
            id=self.tree_ctrl_roi.GetId(),
        )

        for input_obj in self.input.values():
            self.Bind(wx.EVT_TEXT, self.on_text_change, id=input_obj.GetId())

        self.Bind(
            wx.EVT_BUTTON,
            self.on_delete_study,
            id=self.button_delete_study.GetId(),
        )

        self.Bind(
            wx.EVT_COMBOBOX,
            self.on_text_change,
            id=self.input["physician"].GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.on_text_change,
            id=self.input["tx_site"].GetId(),
        )

        self.Bind(
            wx.EVT_BUTTON,
            self.on_apply_plan,
            id=self.button_apply_plan_data.GetId(),
        )

        self.Bind(
            wx.EVT_COMBOBOX,
            self.on_apply_roi,
            id=self.input_roi["type"].GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.on_apply_roi,
            id=self.input_roi["physician"].GetId(),
        )

        for key in [
            "birth_date",
            "sim_study_date",
            "physician",
            "tx_site",
            "rx_dose",
        ]:
            self.Bind(
                wx.EVT_CHECKBOX,
                self.on_check_apply_all,
                id=self.checkbox["%s_1" % key].GetId(),
            )
            self.Bind(
                wx.EVT_CHECKBOX,
                self.on_check_apply_all,
                id=self.checkbox["%s_2" % key].GetId(),
            )

        self.Bind(
            wx.EVT_BUTTON,
            self.on_edit_birth_date,
            id=self.button_edit_birth_date.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_edit_sim_study_date,
            id=self.button_edit_sim_study_date.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_add_physician,
            id=self.button_add_physician.GetId(),
        )

        self.Bind(wx.EVT_BUTTON, self.on_import, id=self.button_import.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=self.button_cancel.GetId())
        self.Bind(
            wx.EVT_BUTTON,
            self.on_save_roi_map,
            id=self.button_save_roi_map.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_preprocess,
            id=self.button_preprocess.GetId(),
        )

        self.Bind(
            wx.EVT_BUTTON,
            self.on_roi_manager,
            id=self.button_roi_manager.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.on_physician_roi_change,
            id=self.input_roi["physician"].GetId(),
        )

        self.Bind(wx.EVT_CLOSE, self.on_cancel)

        self.Bind(
            wx.EVT_BUTTON,
            self.on_save_roi_type_in_map,
            id=self.button_save_roi_type_in_map.GetId(),
        )

    def __set_properties(self):

        self.checkbox_subfolders.SetFont(
            wx.Font(
                11,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        value = (
            self.options.SEARCH_SUBFOLDERS
            if hasattr(self.options, "SEARCH_SUBFOLDERS")
            else 1
        )
        self.checkbox_subfolders.SetValue(value)

        self.checkbox_keep_in_inbox.SetFont(
            wx.Font(
                11,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        self.checkbox_keep_in_inbox.SetToolTip(
            "Successfully imported DICOM files will either be copied or moved into "
            "your Imported Directory. Check this box to copy. Uncheck this box to "
            "remove these files from the inbox."
        )
        value = (
            self.options.KEEP_IN_INBOX
            if hasattr(self.options, "KEEP_IN_INBOX")
            else 0
        )
        self.checkbox_keep_in_inbox.SetValue(value)

        self.checkbox_copy_misc_files.SetFont(
            wx.Font(
                11,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        self.checkbox_copy_misc_files.SetToolTip(
            "Uncheck to only copy DICOM-RT Dose, Structure and Plan files to DVH imported directory."
        )

        value = (
            self.options.COPY_MISC_FILES
            if hasattr(self.options, "COPY_MISC_FILES")
            else 0
        )
        self.checkbox_copy_misc_files.SetValue(value)

        self.checkbox_include_uncategorized.SetFont(
            wx.Font(
                11,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        self.checkbox_auto_sum_dose.SetFont(
            wx.Font(
                11,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        value = (
            self.options.IMPORT_UNCATEGORIZED
            if hasattr(self.options, "IMPORT_UNCATEGORIZED")
            else 0
        )
        self.checkbox_include_uncategorized.SetValue(value)
        value = (
            self.options.AUTO_SUM_DOSE
            if hasattr(self.options, "AUTO_SUM_DOSE")
            else 1
        )
        self.checkbox_auto_sum_dose.SetValue(value)

        self.checkbox_auto_sum_dose.SetToolTip(
            "If multiple dose grids are found for one patient, dose grids will be "
            "summed and composite DVHs will be stored. "
            "This is typically recommended."
        )

        for checkbox in self.checkbox.values():
            checkbox.SetFont(
                wx.Font(
                    11,
                    wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                    0,
                    "",
                )
            )

        self.image_list = wx.ImageList(16, 16)
        self.tree_ctrl_images = {
            "yes": self.image_list.Add(get_tree_ctrl_image(ICONS["ok-green"])),
            "no": self.image_list.Add(get_tree_ctrl_image(ICONS["ko-red"])),
        }
        self.tree_ctrl_roi.AssignImageList(self.image_list)

        self.button_cancel.SetToolTip(
            "Cancel and do not save ROI Map changes since last save."
        )
        self.button_import.SetToolTip(
            "Save ROI Map changes and import checked studies."
        )
        self.button_save_roi_map.SetToolTip("Save ROI Map changes.")

    def __do_layout(self):
        labels = {
            "mrn": "MRN:",
            "study_instance_uid": "Study Instance UID:",
            "birth_date": "Birthdate:",
            "sim_study_date": "Sim Study Date:",
            "physician": "Physician:",
            "tx_site": "Tx Site:",
            "rx_dose": "Rx Dose (Gy):",
            "physician_roi": "Physician's ROI Label:",
            "roi_type": "ROI Type:",
        }
        self.label = {
            key: wx.StaticText(self, wx.ID_ANY, label)
            for key, label in labels.items()
        }

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_warning = wx.BoxSizer(wx.HORIZONTAL)
        sizer_warning_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_map_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_map = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "ROI Mapping for Selected Study"),
            wx.VERTICAL,
        )
        sizer_selected_roi = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Map for Selected ROI"), wx.VERTICAL
        )
        sizer_roi_type = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plan_data_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plan_data = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Plan Data for Selected Study"),
            wx.VERTICAL,
        )
        sizer_rx = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_rx_fx_grp_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rx_input = wx.BoxSizer(wx.VERTICAL)
        # sizer_fx_grp_input = wx.BoxSizer(wx.VERTICAL)
        sizer_checkbox_rx = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tx_site = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_tx_site_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_physician_input = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_input_and_button = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sim_study_date = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_sim_study_date_text_button = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sim_study_date_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_birth_date = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_birth_date_text_button = wx.BoxSizer(wx.HORIZONTAL)
        sizer_birth_date_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_uid = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_mrn = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_browse_and_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_studies = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Studies"), wx.VERTICAL
        )
        sizer_studies_checkboxes = wx.BoxSizer(wx.HORIZONTAL)
        sizer_progress = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dicom_import_directory = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "DICOM Import Directory"),
            wx.VERTICAL,
        )
        sizer_directory = wx.BoxSizer(wx.VERTICAL)
        sizer_import_checkboxes = wx.BoxSizer(wx.HORIZONTAL)
        sizer_browse = wx.BoxSizer(wx.HORIZONTAL)
        sizer_browse.Add(self.text_ctrl_directory, 1, wx.ALL | wx.EXPAND, 5)
        sizer_browse.Add(self.button_browse, 0, wx.ALL, 5)
        sizer_directory.Add(sizer_browse, 1, wx.EXPAND, 0)
        sizer_import_checkboxes.Add(self.checkbox_subfolders, 0, wx.LEFT, 10)
        sizer_import_checkboxes.Add(
            self.checkbox_keep_in_inbox, 0, wx.LEFT, 10
        )
        sizer_directory.Add(sizer_import_checkboxes, 1, wx.EXPAND, 0)
        sizer_directory.Add(self.checkbox_copy_misc_files, 0, wx.LEFT, 10)
        sizer_dicom_import_directory.Add(sizer_directory, 1, wx.EXPAND, 0)
        sizer_browse_and_tree.Add(
            sizer_dicom_import_directory, 0, wx.ALL | wx.EXPAND, 10
        )
        label_note = wx.StaticText(
            self,
            wx.ID_ANY,
            "NOTE: Only the latest files for a plan-set will be used/shown.",
        )
        label_note.SetFont(
            wx.Font(
                10,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        sizer_studies.Add(label_note, 0, wx.ALL, 5)
        sizer_tree.Add(self.tree_ctrl_import, 1, wx.EXPAND, 0)
        self.panel_study_tree.SetSizer(sizer_tree)
        sizer_studies.Add(self.panel_study_tree, 1, wx.ALL | wx.EXPAND, 5)
        sizer_studies_checkboxes.Add(
            self.checkbox_include_uncategorized, 0, wx.RIGHT, 10
        )
        sizer_studies_checkboxes.Add(self.checkbox_auto_sum_dose, 0, 0, 0)
        sizer_studies.Add(sizer_studies_checkboxes, 0, wx.LEFT | wx.EXPAND, 10)
        self.label_progress = wx.StaticText(self, wx.ID_ANY, "")
        self.label_progress.SetFont(
            wx.Font(
                11,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        sizer_progress.Add(self.label_progress, 1, wx.ALL, 10)
        sizer_studies.Add(sizer_progress, 0, wx.EXPAND | wx.RIGHT, 5)
        sizer_browse_and_tree.Add(
            sizer_studies, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 10
        )
        sizer_main.Add(sizer_browse_and_tree, 1, wx.EXPAND, 0)

        sizer_mrn.Add(self.label["mrn"], 0, 0, 0)
        sizer_mrn.Add(self.input["mrn"], 0, wx.EXPAND, 0)

        sizer_plan_data.Add(sizer_mrn, 1, wx.ALL | wx.EXPAND, 5)
        sizer_uid.Add(self.label["study_instance_uid"], 0, 0, 0)
        sizer_uid.Add(self.input["study_instance_uid"], 0, wx.EXPAND, 0)
        sizer_uid.Add(self.button_delete_study, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        sizer_plan_data.Add(sizer_uid, 1, wx.ALL | wx.EXPAND, 5)
        sizer_birth_date.Add(self.label["birth_date"], 0, 0, 0)
        sizer_birth_date_text_button.Add(self.input["birth_date"], 0, 0, 0)
        sizer_birth_date_text_button.Add(
            self.button_edit_birth_date, 0, wx.LEFT, 10
        )
        sizer_birth_date_checkbox.Add(
            self.checkbox["birth_date_1"], 0, wx.RIGHT, 20
        )
        sizer_birth_date_checkbox.Add(self.checkbox["birth_date_2"], 0, 0, 0)
        sizer_birth_date.Add(sizer_birth_date_text_button, 0, 0, 0)
        sizer_birth_date.Add(sizer_birth_date_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_birth_date, 1, wx.ALL | wx.EXPAND, 5)

        sizer_sim_study_date.Add(self.label["sim_study_date"], 0, 0, 0)
        sizer_sim_study_date_text_button.Add(
            self.input["sim_study_date"], 0, 0, 0
        )
        sizer_sim_study_date_text_button.Add(
            self.button_edit_sim_study_date, 0, wx.LEFT, 10
        )
        sizer_sim_study_date_checkbox.Add(
            self.checkbox["sim_study_date_1"], 0, wx.RIGHT, 20
        )
        sizer_sim_study_date_checkbox.Add(
            self.checkbox["sim_study_date_2"], 0, 0, 0
        )
        sizer_sim_study_date.Add(sizer_sim_study_date_text_button, 0, 0, 0)
        sizer_sim_study_date.Add(
            sizer_sim_study_date_checkbox, 1, wx.EXPAND, 0
        )
        sizer_plan_data.Add(sizer_sim_study_date, 1, wx.ALL | wx.EXPAND, 5)

        sizer_physician_input.Add(self.label["physician"], 0, 0, 0)
        sizer_physician_input_and_button.Add(self.input["physician"], 0, 0, 0)
        sizer_physician_input_and_button.Add(
            self.button_add_physician, 0, wx.LEFT, 5
        )
        sizer_physician_checkbox.Add(
            self.checkbox["physician_1"], 0, wx.RIGHT, 20
        )
        sizer_physician_checkbox.Add(self.checkbox["physician_2"], 0, 0, 0)
        sizer_physician.Add(sizer_physician_input, 0, 0, 0)
        sizer_physician.Add(sizer_physician_input_and_button, 0, wx.EXPAND, 0)
        sizer_physician.Add(sizer_physician_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_physician, 1, wx.ALL | wx.EXPAND, 5)

        sizer_tx_site.Add(self.label["tx_site"], 0, 0, 0)
        sizer_tx_site.Add(self.input["tx_site"], 0, wx.EXPAND, 0)
        sizer_tx_site_checkbox.Add(self.checkbox["tx_site_1"], 0, wx.RIGHT, 20)
        sizer_tx_site_checkbox.Add(self.checkbox["tx_site_2"], 0, 0, 0)
        sizer_tx_site.Add(sizer_tx_site_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_tx_site, 1, wx.ALL | wx.EXPAND, 5)

        # self.label['fx_grp'] = wx.StaticText(self, wx.ID_ANY, "Fx Group:")
        sizer_rx_input.Add(self.label["rx_dose"], 0, 0, 0)
        sizer_rx_input.Add(self.input["rx_dose"], 0, 0, 0)
        # sizer_fx_grp_input.Add(self.label['fx_grp'], 0, wx.LEFT, 20)
        # sizer_fx_grp_input.Add(self.input['fx_grp'], 0, wx.LEFT, 20)
        sizer_rx_fx_grp_input.Add(sizer_rx_input, 0, 0, 0)
        # sizer_rx_fx_grp_input.Add(sizer_fx_grp_input, 0, 0, 0)
        sizer_rx.Add(sizer_rx_fx_grp_input, 0, 0, 0)
        sizer_checkbox_rx.Add(self.checkbox["rx_dose_1"], 0, wx.RIGHT, 20)
        sizer_checkbox_rx.Add(self.checkbox["rx_dose_2"], 0, 0, 0)
        sizer_rx.Add(sizer_checkbox_rx, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_rx, 1, wx.ALL | wx.EXPAND, 5)
        sizer_plan_data.Add(
            self.button_apply_plan_data, 0, wx.ALL | wx.EXPAND, 5
        )
        sizer_plan_data_wrapper.Add(sizer_plan_data, 1, wx.ALL | wx.EXPAND, 10)
        sizer_main.Add(sizer_plan_data_wrapper, 1, wx.EXPAND, 0)
        sizer_roi_tree.Add(self.tree_ctrl_roi, 1, wx.ALL | wx.EXPAND, 0)
        self.panel_roi_tree.SetSizer(sizer_roi_tree)
        sizer_roi_map.Add(self.panel_roi_tree, 1, wx.EXPAND, 0)
        sizer_roi_map.Add(self.button_roi_manager, 0, wx.EXPAND | wx.ALL, 5)

        sizer_physician_roi_with_add = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi.Add(self.label["physician_roi"], 0, 0, 0)
        sizer_physician_roi.Add(self.input_roi["physician"], 0, wx.EXPAND, 0)
        sizer_physician_roi_with_add.Add(sizer_physician_roi, 1, wx.EXPAND, 0)

        sizer_roi_type_with_add = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_type_store_in_map = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_type.Add(self.label["roi_type"], 0, 0, 0)
        sizer_roi_type.Add(self.input_roi["type"], 0, wx.EXPAND, 0)
        sizer_roi_type_store_in_map.Add((20, 18), 0, 0, 0)
        sizer_roi_type_store_in_map.Add(
            self.button_save_roi_type_in_map,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_roi_type_with_add.Add(sizer_roi_type, 1, wx.EXPAND, 0)
        sizer_roi_type_with_add.Add(
            sizer_roi_type_store_in_map, 0, wx.EXPAND, 0
        )

        sizer_selected_roi.Add(
            sizer_physician_roi_with_add, 1, wx.ALL | wx.EXPAND, 5
        )
        sizer_selected_roi.Add(
            sizer_roi_type_with_add, 1, wx.ALL | wx.EXPAND, 5
        )

        sizer_roi_map.Add(sizer_selected_roi, 0, wx.EXPAND, 0)
        sizer_roi_map_wrapper.Add(sizer_roi_map, 1, wx.ALL | wx.EXPAND, 10)

        sizer_main.Add(sizer_roi_map_wrapper, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        self.label_warning = wx.StaticText(self, wx.ID_ANY, "")
        sizer_warning.Add(self.label_warning, 1, wx.EXPAND, 0)

        sizer_warning_buttons.Add(sizer_warning, 1, wx.ALL | wx.EXPAND, 5)
        # sizer_buttons.Add(self.button_assign_ptv_test, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_preprocess, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_save_roi_map, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_import, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_warning_buttons.Add(
            sizer_buttons, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5
        )
        sizer_wrapper.Add(sizer_warning_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def run(self):
        self.Show()
        if self.inbox is not None and isdir(self.inbox):
            inbox = self.inbox
        elif isdir(self.options.INBOX_DIR):
            inbox = self.options.INBOX_DIR
        else:
            inbox = ""
        self.text_ctrl_directory.SetValue(inbox)

        if self.auto_parse:
            self.dicom_importer = self.get_importer()

    def on_cancel(self, evt):
        self.roi_map.import_from_file()  # reload from file, ignore changes
        # pub.unsubscribe(self.parse_dicom_data, "parse_dicom_data")
        # pub.unsubscribe(self.set_pre_import_parsed_dicom_data, 'set_pre_import_parsed_dicom_data')
        # pub.unsubscribe(self.pre_import_complete, "pre_import_complete")
        pub.sendMessage("import_dicom_cancel")
        self.do_unsubscribe()
        self.Destroy()

    @staticmethod
    def do_unsubscribe():
        pub.unsubAll(topicName="parse_dicom_data")
        pub.unsubAll(topicName="set_pre_import_parsed_dicom_data")
        pub.unsubAll(topicName="pre_import_complete")
        pub.unsubAll(topicName="pre_import_canceled")
        pub.unsubAll(topicName="build_dicom_file_tree")

    def on_save_roi_map(self, evt):
        RemapROIFrame(self.roi_map)

    def on_preprocess(self, evt):
        self.PreprocessDicom = PreprocessDicom(self)

    def on_browse(self, evt):
        """
        Clear data, open a DirDialog, run a DicomTreeBuilder on selected directory
        """
        starting_dir = self.text_ctrl_directory.GetValue()
        if starting_dir == "":
            starting_dir = self.start_path
        if not isdir(starting_dir):
            starting_dir = ""

        dlg = wx.DirDialog(
            self,
            "Select inbox directory",
            starting_dir,
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.build_dicom_file_tree(dlg.GetPath())

    def build_dicom_file_tree(self, directory):
        self.parsed_dicom_data = {}
        for key in list(self.global_plan_over_rides):
            self.global_plan_over_rides[key] = {
                "value": None,
                "only_if_missing": False,
            }
        self.clear_plan_data()
        if self.dicom_importer:
            self.tree_ctrl_roi.DeleteChildren(self.dicom_importer.root_rois)

        self.text_ctrl_directory.SetValue(directory)
        self.dicom_importer = self.get_importer()

        self.PreprocessDicom = None

    def get_importer(self):
        return DicomTreeBuilder(
            self.text_ctrl_directory.GetValue(),
            self.tree_ctrl_import,
            self.tree_ctrl_roi,
            self.tree_ctrl_roi_root,
            self.tree_ctrl_images,
            self.roi_map,
            search_subfolders=self.checkbox_subfolders.GetValue(),
        )

    def on_file_tree_select(self, evt):
        """
        On selection of an item in the file tree, update the plan dependent elements of the Frame
        """
        uid = self.get_file_tree_item_plan_uid(evt.GetItem())
        self.tree_ctrl_roi.SelectItem(self.tree_ctrl_roi_root, True)
        if (
            uid in list(self.parsed_dicom_data)
            and self.parsed_dicom_data[uid].validation["complete_file_set"]
        ):
            if uid != self.selected_uid:
                self.selected_uid = uid
                wx.BeginBusyCursor()
                self.dicom_importer.rebuild_tree_ctrl_rois(uid)
                self.tree_ctrl_roi.ExpandAll()
                data = self.parsed_dicom_data[uid]

                self.input["mrn"].SetValue(data.mrn)
                self.input["study_instance_uid"].SetValue(
                    data.study_instance_uid_to_be_imported
                )
                if data.birth_date is None or data.birth_date == "":
                    self.input["birth_date"].SetValue("")
                else:
                    self.input["birth_date"].SetValue(
                        datetime_to_date_string(data.birth_date)
                    )
                if data.sim_study_date is None or data.sim_study_date == "":
                    self.input["sim_study_date"].SetValue("")
                else:
                    self.input["sim_study_date"].SetValue(
                        datetime_to_date_string(data.sim_study_date)
                    )
                physician = ["DEFAULT", data.physician][
                    data.physician in self.roi_map.get_physicians()
                ]
                self.input["physician"].SetValue(physician)
                self.input["tx_site"].SetValue(data.tx_site)
                self.input["rx_dose"].SetValue(str(data.rx_dose))
                self.dicom_importer.update_mapped_roi_status(data.physician)
                self.update_all_roi_text_with_roi_type()
                wx.EndBusyCursor()
                self.update_physician_roi_choices()
                self.enable_inputs()
        else:
            self.clear_plan_data()
            self.enable_inputs(False)
            self.selected_uid = None
            self.tree_ctrl_roi.DeleteChildren(self.dicom_importer.root_rois)
        self.selected_uid = uid
        self.update_warning_label()

    def on_roi_tree_select(self, evt):
        self.allow_input_roi_apply = False
        self.selected_roi = self.get_roi_tree_item_name(evt.GetItem())
        self.update_roi_inputs()
        self.allow_input_roi_apply = True

    def roi_tree_right_click_action(self, physician, roi_name, dlg, *evt):
        dlg(self, physician, self.roi_map, roi_name)
        self.update_roi_inputs()
        self.dicom_importer.update_mapped_roi_status(physician)

    def on_roi_tree_right_click(self, evt):
        if (
            evt.GetItem().GetParent() is not None
        ):  # ignore right click on tree root node
            roi_name = (
                evt.GetItem().GetText().split(" ----- ")[0]
            )  # remove PTV flags
            physician = self.input["physician"].GetValue()
            is_mapped = not evt.GetItem().GetImage()

            # TODO: This block of code works, but is overly complicated
            msg_prepend = "%s %s as" % (["Add", "Remove"][is_mapped], roi_name)
            labels = [
                "%s %s" % (msg_prepend, roi_type)
                for roi_type in ["Physician ROI", "Variation"]
            ]
            if is_mapped:
                if self.roi_map.is_physician_roi(roi_name, physician):
                    dlg_objects = [DelPhysicianROI]
                    labels = [labels[0]]
                else:
                    dlg_objects = [DelVariation]
                    labels = [labels[1]]
            else:
                dlg_objects = [AddPhysicianROI, AssignVariation]
            pre_func = partial(
                self.roi_tree_right_click_action, physician, roi_name
            )

            popup = PopupMenu(self)
            for i, label in enumerate(labels):
                if self.input["physician"].GetValue() != "DEFAULT":
                    popup.add_menu_item(
                        label, partial(pre_func, dlg_objects[i])
                    )
            # if is_mapped:
            #     popup.add_menu_item("Do Not Import", partial(pre_func, dlg_objects[0]))

            popup.add_menu_item(
                "Edit ROI Name", partial(self.change_plan_roi_name, evt)
            )

            popup.run()

    def change_plan_roi_name(self, evt_tree, *evt):
        ChangePlanROIName(
            self.tree_ctrl_roi,
            evt_tree.GetItem(),
            self.selected_uid,
            self.parsed_dicom_data[self.selected_uid],
            self.dicom_importer,
        )
        self.dicom_importer.update_mapped_roi_status(
            self.input["physician"].GetValue()
        )
        self.update_physician_roi_choices()

    def update_input_roi_physician_enable(self):
        if self.selected_roi:
            if self.input_roi["physician"].GetValue() == "uncategorized":
                self.input_roi["physician"].Enable()
                self.button_save_roi_type_in_map.Disable()
            else:
                self.input_roi["physician"].Disable()
                self.button_save_roi_type_in_map.Enable()

            self.input_roi["type"].Enable()
        else:
            self.input_roi["physician"].Disable()
            self.input_roi["type"].Disable()
            self.button_save_roi_type_in_map.Disable()

    def update_roi_inputs(self):
        self.allow_input_roi_apply = False
        physician = self.input["physician"].GetValue()
        if self.selected_roi and self.roi_map.is_physician(physician):
            physician_roi = self.roi_map.get_physician_roi(
                physician, self.selected_roi
            )
            roi_key = self.dicom_importer.roi_name_map[self.selected_roi][
                "key"
            ]
            uid = self.selected_uid
            roi_type = self.parsed_dicom_data[uid].get_roi_type(roi_key)
            self.input_roi["physician"].SetValue(physician_roi)
            self.update_physician_roi_choices(physician_roi)
            self.input_roi["type"].SetValue(roi_type)

            self.update_roi_text_with_roi_type(self.selected_roi, roi_type)
        else:
            self.input_roi["physician"].SetValue("")
            self.input_roi["type"].SetValue("")
        self.allow_input_roi_apply = True
        self.update_input_roi_physician_enable()

    def update_roi_text_with_roi_type(self, roi, roi_type):
        roi_type_for_tree_text = [None, "PTV"][roi_type == "PTV"]
        self.dicom_importer.update_tree_ctrl_roi_with_roi_type(
            roi, roi_type=roi_type_for_tree_text
        )

    def update_all_roi_text_with_roi_type(self):
        self.parsed_dicom_data[self.selected_uid].autodetect_target_roi_type()
        for roi in list(self.dicom_importer.roi_name_map):
            roi_key = self.dicom_importer.roi_name_map[roi]["key"]
            roi_type = self.parsed_dicom_data[self.selected_uid].get_roi_type(
                roi_key
            )
            self.update_roi_text_with_roi_type(roi, roi_type)

    def clear_plan_data(self):
        for input_obj in self.input.values():
            input_obj.SetValue("")

        self.reset_label_colors()

    def get_file_tree_item_plan_uid(self, item):
        plan_node = None
        node_id, node_type = self.dicom_importer.get_id_of_tree_ctrl_node(item)

        if node_type == "plan":
            plan_node = item

        elif node_type == "study":
            plan_node, valid = self.tree_ctrl_import.GetFirstChild(item)

        elif node_type == "patient":
            study_node, valid = self.tree_ctrl_import.GetFirstChild(item)
            plan_node, valid = self.tree_ctrl_import.GetFirstChild(study_node)

        if plan_node is not None:
            uid, node_type = self.dicom_importer.get_id_of_tree_ctrl_node(
                plan_node
            )
            return uid

    def get_file_tree_item_study_uid(self, item):
        study_node = None
        node_id, node_type = self.dicom_importer.get_id_of_tree_ctrl_node(item)

        if node_type == "study":
            study_node = item

        elif node_type == "plan":
            study_node, valid = self.tree_ctrl_import.GetItemParent(item)

        elif node_type == "patient":
            study_node, valid = self.tree_ctrl_import.GetFirstChild(item)

        if study_node:
            return self.dicom_importer.node_to_study_uid[study_node]

    def get_roi_tree_item_name(self, item):
        for name, node in self.dicom_importer.roi_nodes.items():
            if item == node:
                return name
        return None

    def on_text_change(self, evt):
        for key, input_obj in self.input.items():
            if input_obj.GetId() == evt.GetId():
                self.update_label_text_color(key)
                return

    def on_physician_change(self):
        self.update_physician_roi_choices()
        physician = self.input["physician"].GetValue()
        if physician:
            self.enable_roi_inputs()
        else:
            self.disable_roi_inputs()

        self.update_roi_inputs()
        self.dicom_importer.update_mapped_roi_status(physician)
        self.update_roi_inputs()

    def update_label_text_color(self, key):
        red_value = [255, 0][self.input[key].GetValue() != ""]
        self.label[key].SetForegroundColour(wx.Colour(red_value, 0, 0))

    def reset_label_colors(self):
        for label in self.label.values():
            label.SetForegroundColour(wx.Colour(0, 0, 0))

    def enable_inputs(self, *arg):
        if arg:
            enable = arg[0]
        else:
            enable = True

        for input_obj in self.input.values():
            input_obj.Enable(enable)
        self.button_edit_sim_study_date.Enable(enable)
        self.button_edit_birth_date.Enable(enable)
        self.button_apply_plan_data.Enable(enable)
        self.button_roi_manager.Enable(enable)
        self.button_delete_study.Enable(enable)
        self.button_add_physician.Enable(enable)
        for check_box in self.checkbox.values():
            check_box.Enable(enable)

    def disable_roi_inputs(self):
        for input_obj in self.input_roi.values():
            input_obj.Disable()
        self.button_save_roi_type_in_map.Disable()

    def enable_roi_inputs(self):
        for key, input_obj in self.input_roi.items():
            if key not in {"physician", "type"}:
                input_obj.Enable()

    def update_physician_roi_choices(self, physician_roi=None):
        physician = self.input["physician"].GetValue()
        if self.roi_map.is_physician(physician):
            choices = self.roi_map.get_physician_rois(physician)
        else:
            choices = []
        if choices and physician_roi in {"uncategorized"}:
            choices = list(
                set(choices)
                - set(self.dicom_importer.get_used_physician_rois(physician))
            )
            choices.sort()
            choices.append("uncategorized")
        self.input_roi["physician"].Clear()
        self.input_roi["physician"].Append(choices)
        if physician_roi is not None:
            self.input_roi["physician"].SetValue(physician_roi)

    def on_apply_plan(self, evt):
        wx.BeginBusyCursor()
        current_physician = self.input["physician"].GetValue()
        self.on_physician_change()
        over_rides = self.parsed_dicom_data[self.selected_uid].plan_over_rides
        apply_all_selected = False
        for key in list(over_rides):
            value = self.input[key].GetValue()
            if "date" in key:
                value = self.validate_date(value)
            elif key == "rx_dose":
                value = self.validate_dose(value)
            else:
                if not value:
                    value = None
            over_rides[key] = value

            # Apply all
            if "%s_1" % key in list(self.checkbox):
                apply_all_selected = True
                if self.checkbox["%s_1" % key].IsChecked():
                    self.global_plan_over_rides[key]["value"] = value
                    self.global_plan_over_rides[key][
                        "only_if_missing"
                    ] = self.checkbox["%s_2" % key].IsChecked()

        self.clear_plan_check_boxes()
        if apply_all_selected:
            self.validate()
        else:
            self.validate(uid=self.selected_uid)

        if current_physician != self.input["physician"]:
            self.update_all_roi_text_with_roi_type()

        self.update_warning_label()
        wx.EndBusyCursor()

    def on_apply_roi(self, evt):
        if self.allow_input_roi_apply:
            roi_type_over_ride = self.parsed_dicom_data[
                self.selected_uid
            ].roi_over_ride["type"]
            key = self.dicom_importer.roi_name_map[self.selected_roi]["key"]
            roi_type_over_ride[key] = self.input_roi["type"].GetValue()
            self.validate(uid=self.selected_uid)
            self.update_warning_label()
            self.dicom_importer.update_mapped_roi_status(
                self.input["physician"].GetValue()
            )
            self.update_roi_text_with_roi_type(
                self.selected_roi, roi_type=self.input_roi["type"].GetValue()
            )

    @staticmethod
    def validate_date(date):
        try:
            dt = parse_date(date)
            truncated = datetime_obj(dt.year, dt.month, dt.day)
            return str(truncated).replace("-", "")
        except Exception:
            return None

    @staticmethod
    def validate_dose(dose):
        try:
            return float(dose)
        except ValueError:
            return None

    @staticmethod
    def is_uid_valid(uid):
        with DVH_SQL() as cnx:
            valid_uid = not cnx.is_study_instance_uid_in_table("Plans", uid)

        if valid_uid:
            return True
        return False

    def clear_plan_check_boxes(self):
        for checkbox in self.checkbox.values():
            checkbox.SetValue(False)

    def on_check_apply_all(self, evt):
        for key in [
            "birth_date",
            "sim_study_date",
            "physician",
            "tx_site",
            "rx_dose",
        ]:
            if self.checkbox["%s_1" % key].GetId() == evt.GetId():
                if not self.checkbox["%s_1" % key].IsChecked():
                    self.checkbox["%s_2" % key].SetValue(False)
                return
            if self.checkbox["%s_2" % key].GetId() == evt.GetId():
                if self.checkbox["%s_2" % key].IsChecked():
                    self.checkbox["%s_1" % key].SetValue(True)
                return

    def on_import(self, evt):
        if self.parsed_dicom_data and self.dicom_importer.checked_plans:
            if sql_write_test()["write"]:
                # self.patient_orientation_warning()

                self.roi_map.write_to_file()
                self.options.set_option(
                    "KEEP_IN_INBOX", self.checkbox_keep_in_inbox.GetValue()
                )
                self.options.set_option(
                    "AUTO_SUM_DOSE", self.checkbox_auto_sum_dose.GetValue()
                )
                self.options.set_option(
                    "COPY_MISC_FILES", self.checkbox_copy_misc_files.GetValue()
                )
                self.options.save()
                study_uid_dict = get_study_uid_dict(
                    list(self.dicom_importer.checked_plans),
                    self.parsed_dicom_data,
                    multi_plan_only=True,
                )

                finish_import = True
                if (
                    study_uid_dict
                    and not self.checkbox_auto_sum_dose.GetValue()
                ):
                    dlg = AssignPTV(
                        self, self.parsed_dicom_data, study_uid_dict
                    )
                    dlg.ShowModal()
                    finish_import = dlg.continue_status

                if finish_import:
                    ImportWorker(
                        self.parsed_dicom_data,
                        list(self.dicom_importer.checked_plans),
                        self.checkbox_include_uncategorized.GetValue(),
                        self.dicom_importer.other_dicom_files,
                        self.start_path,
                        self.checkbox_keep_in_inbox.GetValue(),
                        self.roi_map,
                        self.options.USE_DICOM_DVH,
                        self.checkbox_auto_sum_dose.GetValue(),
                        self.checkbox_copy_misc_files.GetValue(),
                    )
                    dlg = ImportStatusDialog()
                    # calling self.Close() below caused issues in Windows if Show() used instead of ShowModal()
                    [dlg.Show, dlg.ShowModal][is_windows()]()
                    self.Close()
                    self.do_unsubscribe()
            else:
                dlg = wx.MessageDialog(
                    self,
                    "Unable to write to SQL DB!",
                    caption="SQL Connection Failure",
                    style=wx.OK
                    | wx.OK_DEFAULT
                    | wx.CENTER
                    | wx.ICON_EXCLAMATION,
                )
                dlg.ShowModal()
                dlg.Destroy()

        else:
            dlg = wx.MessageDialog(
                self,
                "No plans have been selected.",
                caption="Import Failure",
                style=wx.OK | wx.OK_DEFAULT | wx.CENTER | wx.ICON_EXCLAMATION,
            )
            dlg.ShowModal()
            dlg.Destroy()

    def parse_dicom_data(self):
        PreImportFileSetParserWorker(
            self.dicom_importer.dicom_file_paths,
            self.dicom_importer.other_dicom_files,
        )

    def pre_import_complete(self):
        self.label_progress.SetLabelText(
            "Plan count: %s" % len(list(self.dicom_importer.plan_nodes))
        )
        self.is_all_data_parsed = True
        wx.CallAfter(self.validate)

    def pre_import_canceled(self):
        self.label_progress.SetLabelText("")
        self.label_warning.SetLabelText("Parsing Canceled")

    def set_pre_import_parsed_dicom_data(self, msg):
        uid = msg["uid"]
        self.parsed_dicom_data[uid] = PreImportData(**msg["init_params"])
        self.parsed_dicom_data[
            uid
        ].global_plan_over_rides = self.global_plan_over_rides
        if not self.parsed_dicom_data[uid].ptv_exists:
            self.parsed_dicom_data[uid].autodetect_target_roi_type()
            self.validate(uid)
        self.update_warning_label()
        self.update_roi_inputs()

    def validate(self, uid=None):
        red = wx.Colour(255, 0, 0)
        orange = wx.Colour(255, 165, 0)
        yellow = wx.Colour(255, 255, 0)
        if self.is_all_data_parsed:
            if not uid:
                nodes = self.dicom_importer.plan_nodes
            else:
                nodes = {uid: self.dicom_importer.plan_nodes[uid]}
            for node_uid, node in nodes.items():
                if node_uid in list(self.parsed_dicom_data):
                    validation = self.parsed_dicom_data[node_uid].validation
                    failed_keys = {
                        key
                        for key, value in validation.items()
                        if not value["status"]
                    }
                else:
                    failed_keys = {"complete_file_set"}
                if failed_keys:
                    if {
                        "study_instance_uid",
                        "complete_file_set",
                    }.intersection(failed_keys):
                        color = red
                    elif {"physician", "ptv"}.intersection(failed_keys):
                        color = orange
                    else:
                        color = yellow
                elif node_uid in self.dicom_importer.incomplete_plans:
                    color = red
                else:
                    color = None
                self.tree_ctrl_import.SetItemBackgroundColour(node, color)

                if node_uid is not None:
                    self.tree_ctrl_import.CheckItem(node, color != red)

    def update_warning_label(self):
        msg = ""
        if self.selected_uid:
            if self.selected_uid in list(self.parsed_dicom_data):
                warning = self.parsed_dicom_data[self.selected_uid].warning
                msg = warning["label"]
                if (
                    warning["incomplete"]
                    and self.selected_uid not in self.incomplete_studies
                ):
                    self.incomplete_studies.append(self.selected_uid)
            else:
                msg = "ERROR: Incomplete Fileset. RT Plan, Dose, and Structure required."
        self.label_warning.SetLabelText(msg)

    def on_delete_study(self, evt):
        uid = self.input["study_instance_uid"].GetValue()
        with DVH_SQL() as cnx:
            if cnx.is_uid_imported(uid):
                dlg = wx.MessageDialog(
                    self,
                    "Delete all data in database with this UID?",
                    caption="Delete Study",
                    style=wx.YES
                    | wx.NO
                    | wx.NO_DEFAULT
                    | wx.CENTER
                    | wx.ICON_EXCLAMATION,
                )
            else:
                dlg = wx.MessageDialog(
                    self,
                    "Study Instance UID not found in Database",
                    caption="Delete Study",
                    style=wx.OK | wx.CENTER | wx.ICON_EXCLAMATION,
                )

            res = dlg.ShowModal()
            dlg.Center()
            if res == wx.ID_YES:
                # As of DVH v0.7.5, study_instance_uid may end with _N where N is the nth plan of a file set
                cnx.delete_rows("study_instance_uid LIKE '%s%%'" % uid)

        dlg.Destroy()

        self.validate()  # Eclipse plans may have multiple plan UIDs for the same case, re-validate all plans
        self.update_warning_label()

    def on_edit_birth_date(self, evt):
        self.on_edit_date("birth_date")

    def on_edit_sim_study_date(self, evt):
        self.on_edit_date("sim_study_date")

    def on_edit_date(self, key):
        DatePicker(
            initial_date=self.input[key].GetValue(),
            title=key.replace("_", " ").title(),
            action=self.input[key].SetValue,
        )

        self.validate(uid=self.selected_uid)
        self.update_warning_label()

    def on_roi_manager(self, evt):
        RoiManager(
            self,
            self.roi_map,
            self.input["physician"].GetValue(),
            self.input_roi["physician"].GetValue(),
        )
        self.update_physician_choices(keep_old_physician=True)
        self.update_physician_roi_choices()
        self.update_roi_inputs()
        self.dicom_importer.update_mapped_roi_status(
            self.input["physician"].GetValue()
        )
        self.update_input_roi_physician_enable()

    def on_add_physician(self, evt):
        AddPhysician(
            self.roi_map, initial_physician=self.input["physician"].GetValue()
        )
        self.update_physician_choices()

    def on_manage_physician_roi(self, evt):
        physician = self.input["physician"].GetValue()
        unlinked_institutional_rois = (
            self.roi_map.get_unused_institutional_rois(physician)
        )
        AddPhysicianROI(self, physician, unlinked_institutional_rois)

    def on_manage_roi_type(self, evt):
        AddROIType(self)

    def update_physician_choices(self, keep_old_physician=False):
        old_physician = self.input["physician"].GetValue()
        old_physicians = self.input["physician"].Items
        new_physicians = self.roi_map.get_physicians()
        new_physician = [
            p for p in new_physicians if p and p not in old_physicians
        ]
        self.input["physician"].Clear()
        self.input["physician"].Append(new_physicians)
        if not keep_old_physician and new_physician:
            self.input["physician"].SetValue(new_physician[0])
        else:
            self.input["physician"].SetValue(old_physician)

    def on_physician_roi_change(self, evt):
        physician = self.input["physician"].GetValue()
        variation = self.selected_roi
        physician_roi = self.input_roi["physician"].GetValue()

        if physician_roi not in self.roi_map.get_physician_rois(physician):
            self.roi_map.add_physician_roi(physician, physician_roi)
        if variation not in self.roi_map.get_variations(
            physician, physician_roi
        ):
            self.roi_map.add_variations(physician, physician_roi, variation)

        self.dicom_importer.update_mapped_roi_status(physician)
        self.update_input_roi_physician_enable()

    def patient_orientation_warning(self):
        dsets = self.parsed_dicom_data
        non_hfs = {
            ds.mrn: ds.patient_orientation
            for ds in dsets.values()
            if ds.patient_orientation != "HFS"
        }
        if non_hfs:
            caption = "Non-HFS Orientations Detected"
            msg = (
                "WARNGING: Due to a bug in dicompyler-core <=0.5.5, DVHs may be incorrect for non-HFS orientations."
                " Please verify the following patients (MRNs):\n%s"
                % ", ".join(sorted(list(non_hfs)))
            )
            ErrorDialog(self, msg, caption)

    def on_save_roi_type_in_map(self, *evt):
        physician = self.input["physician"].GetValue()
        physician_roi = self.input_roi["physician"].GetValue()
        roi_type = self.input_roi["type"].GetValue()
        self.roi_map.set_roi_type(physician, physician_roi, roi_type)


class ImportStatusDialog(wx.Dialog):
    """
    Dialog with progress information about DICOM import
    """

    def __init__(self):
        wx.Dialog.__init__(self, None)
        self.gauge_study = wx.Gauge(self, wx.ID_ANY, 100)
        self.gauge_calculation = wx.Gauge(self, wx.ID_ANY, 100)
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        # self.error_details_pane = wx.CollapsiblePane(self, label='Details')
        # self.error_details_window = wx.ScrolledWindow(self.error_details_pane.GetPane())
        # self.error_details_text = wx.StaticText(self.error_details_window, wx.ID_ANY,
        #                                         "Error details go here.\n"
        #                                         "Will add things soon.")

        self.__set_properties()
        self.__do_layout()
        self.__do_subscribe()

        self.Bind(
            wx.EVT_BUTTON, self.set_terminate, id=self.button_cancel.GetId()
        )
        self.Bind(wx.EVT_CLOSE, self.set_terminate)

        self.start_time = datetime.now()

    def __do_subscribe(self):
        pub.subscribe(self.update_patient, "update_patient")
        pub.subscribe(self.update_calculation, "update_calculation")
        pub.subscribe(self.update_dvh_progress, "update_dvh_progress")
        pub.subscribe(self.update_elapsed_time, "update_elapsed_time")
        pub.subscribe(self.close, "close")

    @staticmethod
    def do_unsubscribe():
        for topic in [
            "update_patient",
            "update_calculation",
            "update_elapsed_time",
            "close",
        ]:
            pub.unsubAll(topicName=topic)

    def __set_properties(self):
        self.SetTitle("Import Progress")
        self.SetSize((700, 260))

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_progress = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_calculation = wx.BoxSizer(wx.VERTICAL)
        sizer_study = wx.BoxSizer(wx.VERTICAL)
        sizer_time_cancel = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_error_pane = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_error_window = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_error_text = wx.BoxSizer(wx.HORIZONTAL)

        self.label_study_counter = wx.StaticText(
            self, wx.ID_ANY, " " * 12, style=wx.ALIGN_CENTER
        )
        sizer_study.Add(self.label_study_counter, 0, wx.ALIGN_CENTER, 0)
        self.label_patient = wx.StaticText(self, wx.ID_ANY, "Patient:")
        sizer_study.Add(self.label_patient, 0, 0, 0)
        self.label_study = wx.StaticText(
            self, wx.ID_ANY, "Plan SOP Instance UID:"
        )
        sizer_study.Add(self.label_study, 0, 0, 0)
        sizer_study.Add(self.gauge_study, 0, wx.EXPAND, 0)

        sizer_progress.Add(sizer_study, 0, wx.ALL | wx.EXPAND, 5)
        self.label_calculation = wx.StaticText(
            self, wx.ID_ANY, "Calculation: DVH"
        )
        sizer_calculation.Add(self.label_calculation, 0, 0, 0)
        self.label_structure = wx.StaticText(self, wx.ID_ANY, "")
        sizer_calculation.Add(self.label_structure, 0, 0, 0)
        sizer_calculation.Add(self.gauge_calculation, 0, wx.EXPAND, 0)
        sizer_progress.Add(sizer_calculation, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_progress, 0, wx.EXPAND | wx.ALL, 5)

        self.label_elapsed_time = wx.StaticText(
            self, wx.ID_ANY, "Elapsed time:"
        )
        sizer_time_cancel.Add(
            self.label_elapsed_time, 1, wx.EXPAND | wx.ALL, 5
        )
        sizer_time_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_time_cancel, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def close(self):
        self.do_unsubscribe()
        self.Destroy()

    def update_patient(self, msg):
        """
        Update patient/study related information. Linked with pubsub to ImportWorker
        :param msg: study_number, study_total, patient_name, uid, and progress values
        :type msg: dict
        """
        wx.CallAfter(
            self.label_study_counter.SetLabelText,
            "Plan %s of %s" % (msg["study_number"], msg["study_total"]),
        )
        wx.CallAfter(
            self.label_patient.SetLabelText,
            "Patient: %s" % msg["patient_name"],
        )
        wx.CallAfter(
            self.label_study.SetLabelText,
            "Plan SOP Instance UID: %s" % msg["uid"],
        )
        wx.CallAfter(self.gauge_study.SetValue, msg["progress"])
        self.update_elapsed_time()

    def update_calculation(self, msg):
        """
        Update calculation related information. Linked with pubsub to ImportWorker
        :param msg: calculation type, roi_num, roi_total, roi_name, and progress values
        :type msg: dict
        """
        wx.CallAfter(
            self.button_cancel.Enable,
            "Dose Grid Summation" not in msg["calculation"],
        )
        wx.CallAfter(
            self.label_calculation.SetLabelText,
            "Calculation: %s" % msg["calculation"],
        )
        wx.CallAfter(self.gauge_calculation.SetValue, msg["progress"])

        if msg["roi_name"]:
            label_text = "Structure (%s of %s): %s" % (
                msg["roi_num"],
                msg["roi_total"],
                msg["roi_name"],
            )
        else:
            label_text = ""
        wx.CallAfter(self.label_structure.SetLabelText, label_text)
        self.update_elapsed_time()

    def update_dvh_progress(self, msg):
        label = self.label_structure.GetLabelText()
        if "[" in label and label.endswith("%]"):
            label = label[: label.rfind("[")].strip()
        label = "%s [%0.0f%%]" % (label, msg * 100)
        wx.CallAfter(self.label_structure.SetLabelText, label)
        self.update_elapsed_time()

    def update_elapsed_time(self):
        """
        Update the elapsed time. Linked with pubsub to ImportWorker
        """
        elapsed_time = get_elapsed_time(self.start_time, datetime.now())
        wx.CallAfter(
            self.label_elapsed_time.SetLabelText,
            "Elapsed Time: %s" % elapsed_time,
        )

    def set_terminate(self, *evt):
        caption = "Terminate import?"
        MessageDialog(self, caption, action_yes_func=self.send_terminate)

    def send_terminate(self):
        pub.sendMessage("terminate_import")
        self.close()


class StudyImporter:
    def __init__(
        self, init_params, msg, import_uncategorized, final_plan_in_study
    ):
        """
        Intended to import a study on init, no use afterwards as no properties available
        :param init_params: initial parameters to create DICOM_Parser object
        :type init_params: dict
        :param msg: initial pub message for update patient, includes plan counting and progress
        :type msg: dict
        :param import_uncategorized: import ROIs even if not in ROI map, if set to True
        :type import_uncategorized: bool
        :param final_plan_in_study: prompts composite PTV calculations if True
        :type final_plan_in_study: bool
        """

        # Store SQL time for deleting a partially imported plan
        with DVH_SQL() as cnx:
            self.last_import_time = cnx.now

        self.init_params = init_params
        self.msg = msg
        self.import_uncategorized = import_uncategorized
        self.final_plan_in_study = final_plan_in_study

        self.terminate = False
        pub.subscribe(self.set_terminate, "terminate_import")

        self.run()

    def run(self):

        wx.CallAfter(pub.sendMessage, "update_patient", msg=self.msg)
        wx.CallAfter(pub.sendMessage, "update_elapsed_time")
        msg = {
            "calculation": "DICOM Parsing",
            "roi_num": 1,
            "roi_total": 1,
            "roi_name": "",
            "progress": 0,
        }
        wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)

        parsed_data = DICOM_Parser(**self.init_params)

        wx.CallAfter(pub.sendMessage, "update_elapsed_time")

        # Storing this now, parsed_data sometimes gets cleared prior storing actual values in this message when
        # generating this immediately before pub.sendMessage
        move_msg = {
            "files": [
                parsed_data.plan_file,
                parsed_data.structure_file,
                parsed_data.dose_file,
            ],
            "mrn": parsed_data.mrn,
            "uid": parsed_data.study_instance_uid_to_be_imported,
            "import_path": parsed_data.import_path,
        }

        mrn = parsed_data.mrn
        study_uid = parsed_data.study_instance_uid_to_be_imported
        structures = parsed_data.structure_name_and_type
        roi_name_map = {
            key: structures[key]["name"]
            for key in list(structures)
            if structures[key]["type"] != "MARKER"
        }
        data_to_import = {
            "Plans": [parsed_data.get_plan_row()],
            "Rxs": parsed_data.get_rx_rows(),
            "Beams": parsed_data.get_beam_rows(),
            "DICOM_Files": [parsed_data.get_dicom_file_row()],
            "DVHs": [],
        }  # DVHs will only include PTVs, others pushed en route

        if (
            not self.import_uncategorized
        ):  # remove uncategorized ROIs unless this is checked
            for roi_key in list(roi_name_map):
                if parsed_data.get_physician_roi(roi_key) == "uncategorized":
                    roi_name_map.pop(roi_key)

        # Remove previously imported roi's (e.g., when dose summations occur)
        with DVH_SQL() as cnx:
            for roi_key in list(roi_name_map):
                if cnx.is_roi_imported(
                    clean_name(roi_name_map[roi_key]), study_uid
                ):
                    roi_name_map.pop(roi_key)

        roi_total = len(roi_name_map)
        ptvs = {key: [] for key in ["dvh", "volume", "index"]}

        for roi_counter, roi_key in enumerate(list(roi_name_map)):
            if self.terminate:
                continue
            else:
                # Send messages to status dialog about progress
                msg = {
                    "calculation": "DVH",
                    "roi_num": roi_counter + 1,
                    "roi_total": roi_total,
                    "roi_name": roi_name_map[roi_key],
                    "progress": int(100 * (roi_counter + 1) / roi_total),
                }
                wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
                wx.CallAfter(pub.sendMessage, "update_elapsed_time")

                try:
                    dvh_row = parsed_data.get_dvh_row(roi_key)
                except MemoryError as e:
                    msg = (
                        "StudyImporter.run: Memory Error - "
                        "Skipping roi: %s, for mrn: %s"
                        % (roi_name_map[roi_key], mrn)
                    )
                    push_to_log(e, msg=msg)
                    dvh_row = None

                if dvh_row:
                    roi_type = dvh_row["roi_type"][0]

                    # Collect dvh, volume, and index of ptvs to be used for post-import calculations
                    if roi_type.startswith("PTV"):
                        ptvs["dvh"].append(dvh_row["dvh_string"][0])
                        ptvs["volume"].append(dvh_row["volume"][0])
                        ptvs["index"].append(len(data_to_import["DVHs"]))
                        data_to_import["DVHs"].append(dvh_row)
                    else:
                        self.push({"DVHs": [dvh_row]})

        # Sort PTVs by their D_95% (applicable to SIBs)
        if ptvs["dvh"] and not self.terminate:
            ptv_order = rank_ptvs_by_D95(ptvs)
            for ptv_row, dvh_row_index in enumerate(ptvs["index"]):
                data_to_import["DVHs"][dvh_row_index]["roi_type"][
                    0
                ] = "PTV%s" % (ptv_order[ptv_row] + 1)

        # Must push data to SQL before processing post import calculations since they rely on SQL
        if not self.terminate:
            self.push(data_to_import)

        # Wait until entire study has been pushed since these values are based on entire PTV volume,
        # unless plan_ptvs are assigned
        if (
            self.final_plan_in_study or parsed_data.plan_ptvs
        ) and not self.terminate:
            if db_update.uid_has_ptvs(study_uid):

                # collect roi names for post-import calculations
                # This block moved here since patient's with multiple plans use multiple threads, calculate this
                # on import of final plan import
                post_import_rois = []
                roi_name_map = {
                    key: structures[key]["name"]
                    for key in list(structures)
                    if structures[key]["type"] != "MARKER"
                }
                for roi_counter, roi_key in enumerate(list(roi_name_map)):
                    roi_name = clean_name(roi_name_map[roi_key])
                    with DVH_SQL() as cnx:
                        condition = (
                            "roi_name = '%s' and study_instance_uid = '%s'"
                            % (roi_name, study_uid)
                        )
                        query_return = cnx.query(
                            "DVHs", "roi_type, physician_roi", condition
                        )
                    if query_return:
                        roi_type, physician_roi = tuple(query_return[0])
                        if str(roi_type).lower() in ["organ", "ctv", "gtv"]:
                            if not (
                                str(physician_roi).lower()
                                in [
                                    "uncategorized",
                                    "ignored",
                                    "external",
                                    "skin",
                                    "body",
                                ]
                                or roi_name.lower()
                                in ["external", "skin", "body"]
                            ):
                                post_import_rois.append(
                                    clean_name(roi_name_map[roi_key])
                                )

                # Calculate the PTV overlap for each roi
                tv = db_update.get_total_treatment_volume_of_study(
                    study_uid, ptvs=parsed_data.plan_ptvs
                )
                self.post_import_calc(
                    "PTV Overlap Volume",
                    study_uid,
                    post_import_rois,
                    db_update.treatment_volume_overlap,
                    tv,
                )

                # Calculate the centroid distances of roi-to-PTV for each roi
                tv_centroid = db_update.get_treatment_volume_centroid(tv)
                self.post_import_calc(
                    "Centroid Distance to PTV",
                    study_uid,
                    post_import_rois,
                    db_update.dist_to_ptv_centroids,
                    tv_centroid,
                )

                # Calculate minimum, mean, median, and max distances and DTH
                # tv_coord = db_update.get_treatment_volume_coord(tv)
                # tv_coord = sample_roi(tv_coord)
                self.post_import_calc(
                    "Distances to PTV",
                    study_uid,
                    post_import_rois,
                    db_update.min_distances,
                    tv,
                )

                self.update_ptv_data_in_db(tv, study_uid)

            else:
                msg = (
                    "StudyImporter.run: Skipping PTV related calculations. No PTV found for mrn: %s"
                    % mrn
                )
                push_to_log(msg=msg)

        if self.terminate:
            self.delete_partially_updated_plan()
        else:
            pub.sendMessage("dicom_import_move_files_queue", msg=move_msg)

        if self.final_plan_in_study:
            pub.sendMessage("dicom_import_move_files")

    @staticmethod
    def push(data_to_import):
        """
        Push data to the SQL database
        :param data_to_import: data to import, should be formatted as indicated in db.sql_connector.DVH_SQL.insert_row
        :type data_to_import: dict
        """
        with DVH_SQL() as cnx:
            cnx.insert_data_set(data_to_import)

    def post_import_calc(self, title, uid, rois, func, pre_calc):
        """
        Generic function to perform a post-import calculation
        :param title: title to be displayed in progress dialog
        :type title: str
        :param uid: the plan uid to be displayed in the progress dialog
        :type uid: str
        :param rois: the roi_names to be processed
        :type rois: list
        :param func: the function from db.update called to process the data
        :param pre_calc: data related to total treatment volume for the specific func passed
        """

        if not self.terminate:
            roi_total = len(rois)
            for roi_counter, roi_name in enumerate(rois):
                msg = {
                    "calculation": title,
                    "roi_num": roi_counter + 1,
                    "roi_total": roi_total,
                    "roi_name": roi_name,
                    "progress": int(100 * roi_counter / roi_total),
                }
                wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
                func(uid, roi_name, pre_calc=pre_calc)

    def update_ptv_data_in_db(self, tv, study_uid):
        if not self.terminate:
            # Update progress dialog
            msg = {
                "calculation": "Total Treatment Volume Statistics",
                "roi_num": 0,
                "roi_total": 1,
                "roi_name": "PTV",
                "progress": 0,
            }
            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)

            # Update PTV geometric data
            db_update.update_ptv_data(tv, study_uid)

            # Update progress dialog
            msg["roi_num"], msg["progress"] = 1, 100
            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)

    def delete_partially_updated_plan(self):
        """
        If import process fails, call this function to remove the partially imported data into SQL
        """
        with DVH_SQL() as cnx:
            if cnx.db_type == "sqlite":
                cnx.delete_rows(
                    "DATETIME(import_time_stamp) > DATETIME('%s')"
                    % self.last_import_time
                )
            else:
                cnx.delete_rows(
                    "import_time_stamp > '%s'::date" % self.last_import_time
                )

    def set_terminate(self):
        self.terminate = True


class ImportWorker(Thread):
    """
    Create a thread separate from the GUI to perform the import calculations
    """

    def __init__(
        self,
        data,
        checked_uids,
        import_uncategorized,
        other_dicom_files,
        start_path,
        keep_in_inbox,
        roi_map,
        use_dicom_dvh,
        auto_sum_dose,
        copy_misc_files,
    ):
        """
        :param data: parsed dicom data
        :type data: dict
        :param checked_uids: uids that were selected in the GUI for import
        :type checked_uids: list
        :param import_uncategorized: if True, import rois with names that that are not mapped
        :type import_uncategorized: bool
        :param other_dicom_files: other dicom files found in the import directory
        :type other_dicom_files: dict
        :param keep_in_inbox: Set to False to move files, True to copy files to imported
        :type keep_in_inbox: bool
        :param roi_map: pass the latest roi_map
        :param use_dicom_dvh: if DVH exists in DICOM RT-Dose, import it instead of calculating
        :type use_dicom_dvh: bool
        :param auto_sum_dose:
        :type auto_sum_dose: bool
        :param copy_misc_files:
        :type copy_misc_files: bool
        """
        Thread.__init__(self)

        self.delete_dose_sum_files()  # do this before starting the thread to avoid crash

        self.data = data
        self.checked_uids = checked_uids
        self.import_uncategorized = import_uncategorized
        self.other_dicom_files = other_dicom_files
        self.start_path = start_path
        self.keep_in_inbox = keep_in_inbox
        self.roi_map = roi_map
        self.use_dicom_dvh = use_dicom_dvh
        self.auto_sum_dose = auto_sum_dose
        self.copy_misc_files = copy_misc_files

        self.dose_sum_save_file_names = self.get_dose_sum_save_file_names()
        self.move_msg_queue = []
        self.terminate = False

        self.__do_subscribe()

        self.start()  # start the thread

    def __do_subscribe(self):
        pub.subscribe(self.move_files, "dicom_import_move_files")
        pub.subscribe(
            self.track_move_files_msg, "dicom_import_move_files_queue"
        )
        pub.subscribe(self.set_terminate, "terminate_import")

    def run(self):
        if self.auto_sum_dose:
            msg = {
                "calculation": "Dose Grid Summation(s)... please wait",
                "roi_num": 0,
                "roi_total": 1,
                "roi_name": "",
                "progress": 0,
            }
            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
            self.run_dose_sum()

        self.run_import()
        if not self.terminate:
            wx.CallAfter(pub.sendMessage, "backup_sqlite_db")
        self.close()

    def close(self):
        self.delete_dose_sum_files()
        remove_empty_sub_folders(self.start_path)
        pub.sendMessage("close")

    def run_dose_sum(self):
        """Could not implement with threading due to memory allocation issues"""
        pool = Pool(processes=1)
        pool.starmap(self.sum_two_doses, self.dose_sum_args)
        pool.close()

    def run_import(self):
        queue = self.import_queue
        worker = Thread(target=self.import_target, args=[queue])
        worker.setDaemon(True)
        worker.start()
        queue.join()

    def import_target(self, queue):
        while queue.qsize():
            parameters = queue.get()
            if not self.terminate:
                StudyImporter(*parameters)
            queue.task_done()

    def get_dose_file_sets(self):
        study_uids = get_study_uid_dict(self.checked_uids, self.data)
        dose_file_sets = {}
        for study_uid, plan_uid_set in study_uids.items():
            if len(plan_uid_set) > 1:
                dose_file_sets[study_uid] = [
                    self.data[plan_uid].dose_file for plan_uid in plan_uid_set
                ]
        return dose_file_sets

    @property
    def import_queue(self):
        study_uids = get_study_uid_dict(self.checked_uids, self.data)
        plan_total = len(self.checked_uids)
        plan_counter = 0
        queue = Queue()
        for study_uid, plan_uid_set in study_uids.items():
            plan_count = len(plan_uid_set)
            for i, plan_uid in enumerate(plan_uid_set):
                if plan_uid in list(self.data):

                    msg = {
                        "patient_name": self.data[plan_uid].patient_name,
                        "uid": self.data[
                            plan_uid
                        ].study_instance_uid_to_be_imported,
                        "progress": int(100 * plan_counter / plan_total),
                        "study_number": plan_counter + 1,
                        "study_total": plan_total,
                    }
                    init_param = self.data[plan_uid].init_param
                    init_param["roi_map"] = self.roi_map
                    init_param["use_dicom_dvh"] = self.use_dicom_dvh
                    if self.auto_sum_dose:
                        if study_uid in self.dose_sum_save_file_names.keys():
                            init_param[
                                "dose_sum_file"
                            ] = self.dose_sum_save_file_names[study_uid]
                    elif plan_count > 1:
                        init_param["plan_over_rides"][
                            "study_instance_uid"
                        ] = "%s_%s" % (study_uid, i + 1)
                    final_plan = (
                        True
                        if not self.auto_sum_dose
                        else plan_uid == plan_uid_set[-1]
                    )
                    args = (
                        init_param,
                        msg,
                        self.import_uncategorized,
                        final_plan,
                    )
                    queue.put(args)
                else:
                    msg = (
                        "ImportWorker.import_queue: This plan could not be parsed. Skipping import. "
                        "Did you supply RT Structure, Dose, and Plan?\n\tPlan UID: %s\n\tMRN: %s"
                        % (plan_uid, self.data[plan_uid].mrn)
                    )
                    push_to_log(msg=msg)

                plan_counter += 1
        return queue

    def move_files(self):
        for msg in self.move_msg_queue:
            files = msg["files"]
            if (
                self.copy_misc_files
                and msg["uid"] in self.other_dicom_files.keys()
            ):
                files.extend(self.other_dicom_files[msg["uid"]])

            new_dir = join(msg["import_path"], msg["mrn"])
            move_files_to_new_path(
                files,
                new_dir,
                copy_files=self.keep_in_inbox,
                callback=self.update_copy_status,
            )
        self.move_msg_queue = []  # clear queue

    @staticmethod
    def update_copy_status(i, file_count):
        status = "Copying file %s of %s" % (i + 1, file_count)
        progress = (float(i) / file_count) * 100
        msg = {
            "calculation": status,
            "roi_num": i,
            "roi_total": file_count,
            "roi_name": "",
            "progress": progress,
        }
        wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)

    def track_move_files_msg(self, msg):
        self.move_msg_queue.append(msg)

    def set_terminate(self):
        self.terminate = True

    @property
    def dose_sum_args(self):
        pool_args = []
        file_names = self.dose_sum_save_file_names
        for uid, dose_file_set in self.get_dose_file_sets().items():
            if len(dose_file_set) > 1:
                args = (dose_file_set[0], dose_file_set[1], file_names[uid])
                pool_args.append(args)
            if len(dose_file_set) > 2:
                for dose_file in dose_file_set[2:]:
                    args = (file_names[uid], dose_file, file_names[uid])
                    pool_args.append(args)
        return pool_args

    def get_dose_sum_save_file_names(self):
        dose_file_sets = self.get_dose_file_sets()
        current_temp_files = [
            f for f in listdir(TEMP_DIR) if "temp_dose_sum" in f
        ]
        file_save_names = []
        counter = 1
        while len(file_save_names) < len(list(dose_file_sets)):
            file_save_name = "temp_dose_sum_%s" % counter
            counter += 1
            if file_save_name not in current_temp_files:
                file_save_names.append(file_save_name)

        file_save_names_dict = {
            uid: join(TEMP_DIR, file_save_names[i])
            for i, uid in enumerate(list(dose_file_sets))
        }

        return file_save_names_dict

    @staticmethod
    def sum_two_doses(dose_file_1, dose_file_2, save_to):
        grid_1 = DoseGrid(dose_file_1)
        grid_2 = DoseGrid(dose_file_2)
        grid_1.add(grid_2)
        grid_1.save_dcm(join(TEMP_DIR, save_to))

    @staticmethod
    def delete_dose_sum_files():
        for f in listdir(TEMP_DIR):
            if "temp_dose_sum" in f:
                remove(join(TEMP_DIR, f))


def get_study_uid_dict(checked_uids, parsed_dicom_data, multi_plan_only=False):
    """
    This thread iterates through self.checked_uids which contains plan uids, but we need to iterate through
    study instance uids so that plans on the same study are imported adjacently.
    :return: a dictionary with study uids for the keys and a list of associated plan uids for values
    :rtype: dict
    """
    study_uids = {}
    for plan_uid in checked_uids:
        study_uid = parsed_dicom_data[
            plan_uid
        ].study_instance_uid_to_be_imported
        if study_uid not in list(study_uids):
            study_uids[study_uid] = []
        study_uids[study_uid].append(plan_uid)

    if multi_plan_only:
        for study_uid in list(study_uids):
            if len(study_uids[study_uid]) < 2:
                study_uids.pop(study_uid)

    return study_uids


class AssignPTV(wx.Dialog):
    def __init__(self, parent, parsed_dicom_data, study_uid_dict):
        wx.Dialog.__init__(self, parent)

        self.continue_status = False

        self.parsed_dicom_data = parsed_dicom_data
        self.study_uid_dict = study_uid_dict

        self.__initialize_uid_dict()
        self.__initialize_ptv_dict()
        self.__initialize_patient_name_list()
        self.current_index = 0

        self.plan_uid, self.study_uid = self.uids[self.current_index]

        self.input_keys = [
            "patient_name",
            "study_instance_uid",
            "plan_uid",
            "sim_study_date",
            "tx_site",
        ]
        self.text_ctrl = {
            key: wx.TextCtrl(self, wx.ID_ANY, "") for key in self.input_keys
        }
        self.label = {
            key: wx.StaticText(
                self,
                wx.ID_ANY,
                key.replace("_", " ").title().replace("Uid", "UID") + ":",
            )
            for key in self.input_keys
        }

        self.button_add = wx.Button(self, wx.ID_ANY, ">")
        self.button_remove = wx.Button(self, wx.ID_ANY, "<")

        keys = ["ignored", "included"]
        self.list_ctrl = {
            key: wx.ListCtrl(
                self,
                wx.ID_ANY,
                style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES,
            )
            for key in keys
        }
        self.data_table = {
            key: DataTable(
                self.list_ctrl[key], columns=[key.capitalize()], widths=[-2]
            )
            for key in keys
        }

        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_back = wx.Button(self, wx.ID_ANY, "Back")
        self.button_next = wx.Button(self, wx.ID_ANY, "Next")

        self.gauge = wx.Gauge(self, wx.ID_ANY, 100)

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.update_data()

    def __set_properties(self):
        self.SetTitle("PTV Assignment for Overlap and Distance Calculations")

        for text_ctrl in self.text_ctrl.values():
            text_ctrl.Disable()

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_next, id=self.button_next.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_back, id=self.button_back.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_include, id=self.button_add.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_ignore, id=self.button_remove.GetId())

    def __do_layout(self):
        # Sizers
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_input = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_text_ctrl = {
            key: wx.BoxSizer(wx.VERTICAL) for key in self.input_keys
        }
        sizer_add_remove = wx.BoxSizer(wx.VERTICAL)
        sizer_list_ctrl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_back_next = wx.BoxSizer(wx.HORIZONTAL)
        sizer_gauge = wx.BoxSizer(wx.HORIZONTAL)

        # Add text_ctrl and label objects
        for key in self.input_keys:
            sizer_text_ctrl[key].Add(self.label[key], 0, 0, 0)
            sizer_text_ctrl[key].Add(self.text_ctrl[key], 0, wx.EXPAND, 0)
            sizer_input.Add(sizer_text_ctrl[key], 0, wx.ALL | wx.EXPAND, 5)

        # PTV assignment objections
        sizer_list_ctrl.Add(self.list_ctrl["ignored"], 0, wx.EXPAND, 0)
        sizer_add_remove.Add((20, 20), 0, 0, 0)  # Top Spacer
        sizer_add_remove.Add(self.button_add, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer_add_remove.Add(
            self.button_remove, 0, wx.ALIGN_CENTER | wx.ALL, 5
        )
        sizer_add_remove.Add((20, 20), 0, 0, 0)  # Bottom Spacer
        sizer_list_ctrl.Add(sizer_add_remove, 0, wx.ALL | wx.EXPAND, 10)
        sizer_list_ctrl.Add(self.list_ctrl["included"], 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_list_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        # Cancel, Back, and Next buttons
        sizer_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_buttons.Add(sizer_cancel, 0, wx.EXPAND, 0)
        sizer_gauge.Add(self.gauge, 1, wx.EXPAND | wx.ALL, 5)
        sizer_buttons.Add(self.gauge, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 50)
        sizer_back_next.Add(self.button_back, 0, wx.ALL, 5)
        sizer_back_next.Add(self.button_next, 0, wx.ALL, 5)
        sizer_buttons.Add(sizer_back_next, 0, wx.EXPAND, 0)

        sizer_main.Add(sizer_input, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(
            sizer_buttons, 0, wx.ALIGN_RIGHT | wx.ALL | wx.EXPAND, 5
        )

        note = wx.StaticText(
            self,
            wx.ID_ANY,
            "NOTE: Only StudyInstanceUIDs associated with multiple dose files "
            "are included/needed in this PTV Assignment window.",
        )
        note.SetFont(
            wx.Font(
                11,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "",
            )
        )
        sizer_main.Add(note, 0, wx.ALL, 10)

        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Layout()
        self.Center()

    def __initialize_uid_dict(self):
        """Create a list of tuples (plan_uid, study_uid) for multi-plan studies"""
        self.uids = []
        self.study_uid_list = []
        self.plan_uid_lists = {}
        for study_uid, plan_uid_set in self.study_uid_dict.items():
            if len(plan_uid_set) > 1:
                if study_uid not in self.study_uid_list:
                    self.study_uid_list.append(study_uid)
                    self.plan_uid_lists[study_uid] = []
                for plan_uid in plan_uid_set:
                    self.plan_uid_lists[study_uid].append(plan_uid)
                    self.uids.append((plan_uid, study_uid))

    def __initialize_ptv_dict(self):
        """Create dict to track all PTVs in a study, and to which plans they are assigned"""
        self.ptvs = {}
        for plan_uid, study_uid in self.uids:
            if study_uid not in list(self.ptvs):
                self.ptvs[study_uid] = set()
            if plan_uid not in list(self.ptvs):
                self.ptvs[plan_uid] = set(
                    self.parsed_dicom_data[plan_uid].plan_ptvs
                )
            ptvs = set(
                self.parsed_dicom_data[plan_uid].stored_values["ptv_names"]
            )
            self.ptvs[study_uid] = self.ptvs[study_uid].union(ptvs)

    def __initialize_patient_name_list(self):
        self.patient_name_list = []
        for study_uid in self.study_uid_list:
            for plan_uid in self.plan_uid_lists[study_uid]:
                patient_name = self.parsed_dicom_data[plan_uid].patient_name
                if patient_name not in self.patient_name_list:
                    self.patient_name_list.append(patient_name)

    def update_labels(self):
        study_index = self.study_uid_list.index(self.study_uid)
        study_length = len(self.study_uid_list)
        plan_uid_index = self.plan_uid_lists[self.study_uid].index(
            self.plan_uid
        )
        plan_length = len(self.plan_uid_lists[self.study_uid])
        pat_index = self.patient_name_list.index(
            self.text_ctrl["patient_name"].GetValue()
        )
        pat_length = len(self.patient_name_list)

        study_label_end = ": (%s/%s)" % (study_index + 1, study_length)
        new_study_label = (
            self.label["study_instance_uid"].GetLabel().split(":")[0]
            + study_label_end
        )
        self.label["study_instance_uid"].SetLabel(new_study_label)

        plan_label_end = ": (%s/%s)" % (plan_uid_index + 1, plan_length)
        new_plan_label = (
            self.label["plan_uid"].GetLabel().split(":")[0] + plan_label_end
        )
        self.label["plan_uid"].SetLabel(new_plan_label)

        pat_label_end = ": (%s/%s)" % (pat_index + 1, pat_length)
        right_colon_index = self.label["patient_name"].GetLabel().rfind(":")
        new_pat_label = (
            self.label["patient_name"].GetLabel()[:right_colon_index]
            + pat_label_end
        )
        self.label["patient_name"].SetLabel(new_pat_label)

    def update_data(self, increment=0):
        self.current_index += increment
        progress = 100 * float(self.current_index) / (len(self.uids) - 1)
        self.gauge.SetValue(progress)
        self.update_back_next_buttons()
        if self.current_index < len(self.uids):
            self.plan_uid, self.study_uid = self.uids[self.current_index]
            data = self.parsed_dicom_data[self.plan_uid]
            for key, text_ctrl in self.text_ctrl.items():
                value = (
                    getattr(data, key) if key != "plan_uid" else self.plan_uid
                )
                if key == "sim_study_date":
                    try:
                        date = parse_date(value)
                        value = "%s-%s-%s" % (date.year, date.month, date.day)
                    except Exception:
                        pass
                text_ctrl.SetValue(value)
            self.update_ptv_data_tables()
            self.update_labels()
        else:
            self.close()

    def update_ptv_data_tables(self):
        ptvs = self.get_current_ptv_assignments()
        for key in ["ignored", "included"]:
            column = key.capitalize()
            self.data_table[key].set_data({column: ptvs[key]}, [column])

    def get_current_ptv_assignments(self):
        included, ignored = [], []
        for ptv in self.ptvs[self.study_uid]:
            if ptv in self.ptvs[self.plan_uid]:
                included.append(ptv)
            else:
                ignored.append(ptv)
        included.sort()
        ignored.sort()
        return {"included": included, "ignored": ignored}

    def on_next(self, *evt):
        self.update_data(1)

    def on_back(self, *evt):
        self.update_data(-1)

    def on_include(self, *evt):
        selected_ptvs = set(
            [row[0] for row in self.data_table["ignored"].selected_row_data]
        )
        self.ptvs[self.plan_uid] = self.ptvs[self.plan_uid].union(
            selected_ptvs
        )
        self.update_data()

    def on_ignore(self, *evt):
        selected_ptvs = set(
            [row[0] for row in self.data_table["included"].selected_row_data]
        )
        self.ptvs[self.plan_uid] = self.ptvs[self.plan_uid].difference(
            selected_ptvs
        )
        self.update_data()

    def close(self):
        for plan_uid, parsed_dicom_data in self.parsed_dicom_data.items():
            if plan_uid in self.ptvs.values():
                parsed_dicom_data.plan_ptvs = list(self.ptvs[plan_uid])
        self.continue_status = True
        self.Close()

    def update_back_next_buttons(self):
        self.button_back.Enable(self.current_index > 0)
        label = "Next" if self.current_index < len(self.uids) - 1 else "Finish"
        self.button_next.SetLabel(label)


class PreprocessDicom:
    def __init__(self, parent):
        self.parent = parent
        self.directory = None

        self.__do_subscribe()

        self.run_warning()  # will call self.run()

    def __do_subscribe(self):
        pub.subscribe(
            self.build_dicom_file_tree_prompt, "build_dicom_file_tree_prompt"
        )

    def __do_unsubscribe(self):
        pub.unsubAll(topicName="build_dicom_file_tree_prompt")

    def run_warning(self):
        caption = "WARNING\nThis will edit the StudyInstanceUID of DICOM files selected in the next window!"
        message = "This shouldn't be needed for DICOM compliant files, use with caution.\n\nAre you sure?"
        MessageDialog(self.parent, caption, message, action_yes_func=self.run)

    def run(self):
        dlg = wx.DirDialog(
            self.parent,
            "Select a directory",
            "",
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.directory = dlg.GetPath()
            _, obj_list = get_new_uids_by_directory(self.directory)
            ProgressFrame(
                obj_list,
                edit_study_uid,
                title="Writing New StudyInstanceUIDs",
                action_msg="Processing File",
                close_msg="build_dicom_file_tree_prompt",
                kwargs=True,
            )
        dlg.Destroy()

    def build_dicom_file_tree(self):
        if self.directory is not None:
            pub.sendMessage("build_dicom_file_tree", directory=self.directory)

    def build_dicom_file_tree_prompt(self):
        caption = "Parse this directory for import?"
        MessageDialog(
            self.parent, caption, action_yes_func=self.build_dicom_file_tree
        )
        self.__do_unsubscribe()
