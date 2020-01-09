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
from wx.lib.agw.customtreectrl import CustomTreeCtrl, TR_AUTO_CHECK_CHILD, TR_AUTO_CHECK_PARENT, TR_DEFAULT_STYLE
from datetime import date as datetime_obj, datetime
from dateutil.parser import parse as parse_date
from dicompylercore import dicomparser
from os.path import isdir, join, dirname
from os import listdir, rmdir
from pubsub import pub
from threading import Thread
from dvha.db import update as db_update
from dvha.db.sql_connector import DVH_SQL
from dvha.db.dicom_importer import DicomImporter
from dvha.db.dicom_parser import DICOM_Parser
from dvha.dialogs.main import DatePicker
from dvha.dialogs.roi_map import AddPhysician, AddPhysicianROI, AddROIType, RoiManager, ChangePlanROIName
from dvha.paths import IMPORT_SETTINGS_PATH, parse_settings_file, IMPORTED_DIR, ICONS
from dvha.tools.dicom_dose_sum import sum_dose_grids
from dvha.tools.roi_name_manager import clean_name
from dvha.tools.utilities import datetime_to_date_string, get_elapsed_time, move_files_to_new_path, rank_ptvs_by_D95,\
    set_msw_background_color, is_windows, get_tree_ctrl_image, sample_roi, remove_empty_folders, get_window_size


# TODO: Provide methods to write over-rides to DICOM file
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
        :param inbox: optional initial directory
        :type inbox: str
        """
        wx.Frame.__init__(self, None, title='Import DICOM')

        set_msw_background_color(self)  # If windows, change the background color

        self.initial_inbox = inbox
        self.options = options
        self.auto_parse = auto_parse

        with DVH_SQL() as cnx:
            cnx.initialize_database()

        self.SetSize(get_window_size(0.804, 0.762))

        self.parsed_dicom_data = {}
        self.selected_uid = None

        self.roi_map = roi_map
        self.selected_roi = None

        self.start_path = parse_settings_file(IMPORT_SETTINGS_PATH)['inbox']

        self.checkbox = {}
        keys = ['birth_date', 'sim_study_date', 'physician', 'tx_site', 'rx_dose']
        for key in keys:
            self.checkbox['%s_1' % key] = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
            self.checkbox['%s_2' % key] = wx.CheckBox(self, wx.ID_ANY, "Only if missing")
        self.global_plan_over_rides = {key: {'value': None, 'only_if_missing': False} for key in keys}

        self.text_ctrl_directory = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_READONLY)

        with DVH_SQL() as cnx:
            tx_sites = cnx.get_unique_values('Plans', 'tx_site')

        self.input = {'mrn': wx.TextCtrl(self, wx.ID_ANY, ""),
                      'study_instance_uid': wx.TextCtrl(self, wx.ID_ANY, ""),
                      'birth_date': wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY),
                      'sim_study_date': wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY),
                      'physician': wx.ComboBox(self, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY),
                      'tx_site': wx.ComboBox(self, wx.ID_ANY, choices=tx_sites, style=wx.CB_DROPDOWN),
                      'rx_dose': wx.TextCtrl(self, wx.ID_ANY, "")}
        # 'fx_grp': wx.ComboBox(self, wx.ID_ANY, choices=['1'], style=wx.CB_DROPDOWN | wx.CB_READONLY)}

        self.input['physician'].SetValue('')
        self.input['tx_site'].SetValue('')
        # self.input['fx_grp'].SetValue('1')
        self.button_edit_sim_study_date = wx.Button(self, wx.ID_ANY, "Edit")
        self.button_edit_birth_date = wx.Button(self, wx.ID_ANY, "Edit")

        self.button_apply_plan_data = wx.Button(self, wx.ID_ANY, "Apply")
        self.button_delete_study = wx.Button(self, wx.ID_ANY, "Delete Study in Database with this UID")
        self.button_delete_study.Disable()
        self.button_add_physician = wx.Button(self, wx.ID_ANY, "Add")

        self.button_browse = wx.Button(self, wx.ID_ANY, u"Browse…")
        self.checkbox_subfolders = wx.CheckBox(self, wx.ID_ANY, "Search within sub-folders")
        self.panel_study_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.gauge = wx.Gauge(self, -1, 100)
        self.button_import = wx.Button(self, wx.ID_ANY, "Import")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_save_roi_map = wx.Button(self, wx.ID_ANY, "Save ROI Map")

        self.panel_roi_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.input_roi = {'physician': wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY),
                          'type': wx.ComboBox(self, wx.ID_ANY, choices=self.options.ROI_TYPES, style=wx.CB_DROPDOWN)}
        self.input_roi['type'].SetValue('')
        self.button_roi_manager = wx.Button(self, wx.ID_ANY, "ROI Manager")

        self.disable_inputs()
        self.disable_roi_inputs()

        styles = TR_AUTO_CHECK_CHILD | TR_AUTO_CHECK_PARENT | TR_DEFAULT_STYLE
        self.tree_ctrl_import = CustomTreeCtrl(self.panel_study_tree, wx.ID_ANY, agwStyle=styles)
        self.tree_ctrl_import.SetBackgroundColour(wx.WHITE)

        self.tree_ctrl_roi = CustomTreeCtrl(self.panel_roi_tree, wx.ID_ANY, agwStyle=TR_DEFAULT_STYLE)
        self.tree_ctrl_roi.SetBackgroundColour(wx.WHITE)
        self.tree_ctrl_roi_root = self.tree_ctrl_roi.AddRoot('RT Structures', ct_type=0)

        self.checkbox_include_uncategorized = wx.CheckBox(self, wx.ID_ANY, "Import uncategorized ROIs")

        self.allow_input_roi_apply = False

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()
        self.__do_subscribe()

        self.is_all_data_parsed = False
        self.dicom_importer = None

        self.incomplete_studies = []

        self.terminate = {'status': False}  # used to terminate thread on cancel in Import Dialog

        self.run()

    def __do_subscribe(self):
        """
        After DICOM directory is scanned and sorted, parse_dicom_data will be called
        """
        pub.subscribe(self.parse_dicom_data, "parse_dicom_data")
        pub.subscribe(self.remove_empty_folders, "remove_empty_folders")

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_browse, id=self.button_browse.GetId())

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_file_tree_select, id=self.tree_ctrl_import.GetId())
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_roi_tree_select, id=self.tree_ctrl_roi.GetId())

        for input_obj in self.input.values():
            self.Bind(wx.EVT_TEXT, self.on_text_change, id=input_obj.GetId())

        self.Bind(wx.EVT_BUTTON, self.on_delete_study, id=self.button_delete_study.GetId())

        self.Bind(wx.EVT_COMBOBOX, self.on_text_change, id=self.input['physician'].GetId())
        self.Bind(wx.EVT_COMBOBOX, self.on_text_change, id=self.input['tx_site'].GetId())

        self.Bind(wx.EVT_BUTTON, self.on_apply_plan, id=self.button_apply_plan_data.GetId())

        self.Bind(wx.EVT_COMBOBOX, self.on_apply_roi, id=self.input_roi['type'].GetId())
        self.Bind(wx.EVT_COMBOBOX, self.on_apply_roi, id=self.input_roi['physician'].GetId())

        for key in ['birth_date', 'sim_study_date', 'physician', 'tx_site', 'rx_dose']:
            self.Bind(wx.EVT_CHECKBOX, self.on_check_apply_all, id=self.checkbox['%s_1' % key].GetId())
            self.Bind(wx.EVT_CHECKBOX, self.on_check_apply_all, id=self.checkbox['%s_2' % key].GetId())

        self.Bind(wx.EVT_BUTTON, self.on_edit_birth_date, id=self.button_edit_birth_date.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_edit_sim_study_date, id=self.button_edit_sim_study_date.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_add_physician, id=self.button_add_physician.GetId())

        self.Bind(wx.EVT_BUTTON, self.on_import, id=self.button_import.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=self.button_cancel.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_save_roi_map, id=self.button_save_roi_map.GetId())

        self.Bind(wx.EVT_BUTTON, self.on_roi_manager, id=self.button_roi_manager.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.on_physician_roi_change, id=self.input_roi['physician'].GetId())

    def __set_properties(self):

        self.checkbox_subfolders.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                                 wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_subfolders.SetValue(1)
        self.checkbox_include_uncategorized.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_include_uncategorized.SetValue(0)

        for checkbox in self.checkbox.values():
            checkbox.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))

        self.image_list = wx.ImageList(16, 16)
        self.tree_ctrl_images = {'yes': self.image_list.Add(get_tree_ctrl_image(ICONS['ok-green'])),
                                 'no': self.image_list.Add(get_tree_ctrl_image(ICONS['ko-red']))}
        self.tree_ctrl_roi.AssignImageList(self.image_list)

        self.button_cancel.SetToolTip("Cancel and do not save ROI Map changes since last save.")
        self.button_import.SetToolTip("Save ROI Map changes and import checked studies.")
        self.button_save_roi_map.SetToolTip("Save ROI Map changes.")

    def __do_layout(self):
        self.label = {}
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_warning = wx.BoxSizer(wx.HORIZONTAL)
        sizer_warning_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_map_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_map = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "ROI Mapping for Selected Study"), wx.VERTICAL)
        sizer_selected_roi = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Map for Selected ROI"), wx.VERTICAL)
        sizer_roi_type = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plan_data_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plan_data = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Plan Data for Selected Study"), wx.VERTICAL)
        sizer_rx = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_rx_fx_grp_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_rx_input = wx.BoxSizer(wx.VERTICAL)
        # sizer_fx_grp_input = wx.BoxSizer(wx.VERTICAL)
        sizer_checkbox_rx = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tx_site = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_tx_site_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_physician_input = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_input_and_button = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sim_study_date = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_sim_study_date_text_button = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sim_study_date_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_birth_date = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_birth_date_text_button = wx.BoxSizer(wx.HORIZONTAL)
        sizer_birth_date_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_uid = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_mrn = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_browse_and_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_studies = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Studies"), wx.VERTICAL)
        sizer_progress = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dicom_import_directory = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "DICOM Import Directory"),
                                                         wx.VERTICAL)
        sizer_directory = wx.BoxSizer(wx.VERTICAL)
        sizer_browse = wx.BoxSizer(wx.HORIZONTAL)
        sizer_browse.Add(self.text_ctrl_directory, 1, wx.ALL | wx.EXPAND, 5)
        sizer_browse.Add(self.button_browse, 0, wx.ALL, 5)
        sizer_directory.Add(sizer_browse, 1, wx.EXPAND, 0)
        sizer_directory.Add(self.checkbox_subfolders, 0, wx.LEFT, 10)
        sizer_dicom_import_directory.Add(sizer_directory, 1, wx.EXPAND, 0)
        sizer_browse_and_tree.Add(sizer_dicom_import_directory, 0, wx.ALL | wx.EXPAND, 10)
        label_note = wx.StaticText(self, wx.ID_ANY,
                                   "NOTE: Only the latest files will be used for a given study instance UID, "
                                   "all others ignored.")
        label_note.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        sizer_studies.Add(label_note, 0, wx.ALL, 5)
        sizer_tree.Add(self.tree_ctrl_import, 1, wx.EXPAND, 0)
        self.panel_study_tree.SetSizer(sizer_tree)
        sizer_studies.Add(self.panel_study_tree, 1, wx.ALL | wx.EXPAND, 5)
        sizer_studies.Add(self.checkbox_include_uncategorized, 0, wx.LEFT | wx.BOTTOM | wx.EXPAND, 10)
        self.label_progress = wx.StaticText(self, wx.ID_ANY, "")
        self.label_progress.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        sizer_progress.Add(self.label_progress, 1, 0, 0)
        sizer_progress.Add(self.gauge, 1, wx.LEFT | wx.EXPAND, 40)
        sizer_studies.Add(sizer_progress, 0, wx.EXPAND | wx.RIGHT, 5)
        sizer_browse_and_tree.Add(sizer_studies, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer_main.Add(sizer_browse_and_tree, 1, wx.EXPAND, 0)

        self.label['mrn'] = wx.StaticText(self, wx.ID_ANY, "MRN:")
        sizer_mrn.Add(self.label['mrn'], 0, 0, 0)
        sizer_mrn.Add(self.input['mrn'], 0, wx.EXPAND, 0)

        sizer_plan_data.Add(sizer_mrn, 1, wx.ALL | wx.EXPAND, 5)
        self.label['study_instance_uid'] = wx.StaticText(self, wx.ID_ANY, "Study Instance UID:")
        sizer_uid.Add(self.label['study_instance_uid'], 0, 0, 0)
        sizer_uid.Add(self.input['study_instance_uid'], 0, wx.EXPAND, 0)
        sizer_uid.Add(self.button_delete_study, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        sizer_plan_data.Add(sizer_uid, 1, wx.ALL | wx.EXPAND, 5)
        self.label['birth_date'] = wx.StaticText(self, wx.ID_ANY, "Birthdate:")
        sizer_birth_date.Add(self.label['birth_date'], 0, 0, 0)
        sizer_birth_date_text_button.Add(self.input['birth_date'], 0, 0, 0)
        sizer_birth_date_text_button.Add(self.button_edit_birth_date, 0, wx.LEFT, 10)
        sizer_birth_date_checkbox.Add(self.checkbox['birth_date_1'], 0, wx.RIGHT, 20)
        sizer_birth_date_checkbox.Add(self.checkbox['birth_date_2'], 0, 0, 0)
        sizer_birth_date.Add(sizer_birth_date_text_button, 0, 0, 0)
        sizer_birth_date.Add(sizer_birth_date_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_birth_date, 1, wx.ALL | wx.EXPAND, 5)

        self.label['sim_study_date'] = wx.StaticText(self, wx.ID_ANY, "Sim Study Date:")
        sizer_sim_study_date.Add(self.label['sim_study_date'], 0, 0, 0)
        sizer_sim_study_date_text_button.Add(self.input['sim_study_date'], 0, 0, 0)
        sizer_sim_study_date_text_button.Add(self.button_edit_sim_study_date, 0, wx.LEFT, 10)
        sizer_sim_study_date_checkbox.Add(self.checkbox['sim_study_date_1'], 0, wx.RIGHT, 20)
        sizer_sim_study_date_checkbox.Add(self.checkbox['sim_study_date_2'], 0, 0, 0)
        sizer_sim_study_date.Add(sizer_sim_study_date_text_button, 0, 0, 0)
        sizer_sim_study_date.Add(sizer_sim_study_date_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_sim_study_date, 1, wx.ALL | wx.EXPAND, 5)

        self.label['physician'] = wx.StaticText(self, wx.ID_ANY, "Physician:")
        sizer_physician_input.Add(self.label['physician'], 0, 0, 0)
        sizer_physician_input_and_button.Add(self.input['physician'], 0, 0, 0)
        sizer_physician_input_and_button.Add(self.button_add_physician, 0, wx.LEFT, 5)
        sizer_physician_checkbox.Add(self.checkbox['physician_1'], 0, wx.RIGHT, 20)
        sizer_physician_checkbox.Add(self.checkbox['physician_2'], 0, 0, 0)
        sizer_physician.Add(sizer_physician_input, 0, 0, 0)
        sizer_physician.Add(sizer_physician_input_and_button, 0, wx.EXPAND, 0)
        sizer_physician.Add(sizer_physician_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_physician, 1, wx.ALL | wx.EXPAND, 5)

        self.label['tx_site'] = wx.StaticText(self, wx.ID_ANY, "Tx Site:")
        sizer_tx_site.Add(self.label['tx_site'], 0, 0, 0)
        sizer_tx_site.Add(self.input['tx_site'], 0, wx.EXPAND, 0)
        sizer_tx_site_checkbox.Add(self.checkbox['tx_site_1'], 0, wx.RIGHT, 20)
        sizer_tx_site_checkbox.Add(self.checkbox['tx_site_2'], 0, 0, 0)
        sizer_tx_site.Add(sizer_tx_site_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_tx_site, 1, wx.ALL | wx.EXPAND, 5)

        self.label['rx_dose'] = wx.StaticText(self, wx.ID_ANY, "Rx Dose (Gy):")
        # self.label['fx_grp'] = wx.StaticText(self, wx.ID_ANY, "Fx Group:")
        sizer_rx_input.Add(self.label['rx_dose'], 0, 0, 0)
        sizer_rx_input.Add(self.input['rx_dose'], 0, 0, 0)
        # sizer_fx_grp_input.Add(self.label['fx_grp'], 0, wx.LEFT, 20)
        # sizer_fx_grp_input.Add(self.input['fx_grp'], 0, wx.LEFT, 20)
        sizer_rx_fx_grp_input.Add(sizer_rx_input, 0, 0, 0)
        # sizer_rx_fx_grp_input.Add(sizer_fx_grp_input, 0, 0, 0)
        sizer_rx.Add(sizer_rx_fx_grp_input, 0, 0, 0)
        sizer_checkbox_rx.Add(self.checkbox['rx_dose_1'], 0, wx.RIGHT, 20)
        sizer_checkbox_rx.Add(self.checkbox['rx_dose_2'], 0, 0, 0)
        sizer_rx.Add(sizer_checkbox_rx, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_rx, 1, wx.ALL | wx.EXPAND, 5)
        sizer_plan_data.Add(self.button_apply_plan_data, 0, wx.ALL | wx.EXPAND, 5)
        sizer_plan_data_wrapper.Add(sizer_plan_data, 1, wx.ALL | wx.EXPAND, 10)
        sizer_main.Add(sizer_plan_data_wrapper, 1, wx.EXPAND, 0)
        sizer_roi_tree.Add(self.tree_ctrl_roi, 1, wx.ALL | wx.EXPAND, 0)
        self.panel_roi_tree.SetSizer(sizer_roi_tree)
        sizer_roi_map.Add(self.panel_roi_tree, 1, wx.EXPAND, 0)
        sizer_roi_map.Add(self.button_roi_manager, 0, wx.EXPAND | wx.ALL, 5)

        self.label['physician_roi'] = wx.StaticText(self, wx.ID_ANY, "Physician's ROI Label:")
        sizer_physician_roi_with_add = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi.Add(self.label['physician_roi'], 0, 0, 0)
        sizer_physician_roi.Add(self.input_roi['physician'], 0, wx.EXPAND, 0)
        sizer_physician_roi_with_add.Add(sizer_physician_roi, 1, wx.EXPAND, 0)

        self.label['roi_type'] = wx.StaticText(self, wx.ID_ANY, "ROI Type:")
        sizer_roi_type_with_add = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_type.Add(self.label['roi_type'], 0, 0, 0)
        sizer_roi_type.Add(self.input_roi['type'], 0, wx.EXPAND, 0)
        sizer_roi_type_with_add.Add(sizer_roi_type, 1, wx.EXPAND, 0)

        sizer_selected_roi.Add(sizer_physician_roi_with_add, 1, wx.ALL | wx.EXPAND, 5)
        sizer_selected_roi.Add(sizer_roi_type_with_add, 1, wx.ALL | wx.EXPAND, 5)

        sizer_roi_map.Add(sizer_selected_roi, 0, wx.EXPAND, 0)
        sizer_roi_map_wrapper.Add(sizer_roi_map, 1, wx.ALL | wx.EXPAND, 10)

        sizer_main.Add(sizer_roi_map_wrapper, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        self.label_warning = wx.StaticText(self, wx.ID_ANY, '')
        sizer_warning.Add(self.label_warning, 1, wx.EXPAND, 0)

        sizer_warning_buttons.Add(sizer_warning, 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_save_roi_map, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_import, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_warning_buttons.Add(sizer_buttons, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_warning_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

        self.gauge.Hide()

    def run(self):
        self.Show()
        if self.initial_inbox is None or not isdir(self.initial_inbox):
            self.initial_inbox = ''
        self.text_ctrl_directory.SetValue(self.initial_inbox)

        if self.auto_parse:
            self.dicom_importer = self.get_importer()

    def on_cancel(self, evt):
        self.roi_map.import_from_file()  # reload from file, ignore changes
        self.Destroy()

    def on_save_roi_map(self, evt):
        self.roi_map.write_to_file()

    def on_browse(self, evt):
        """
        Clear data, open a DirDialog, run a DicomImporter on selected directory
        """
        self.parsed_dicom_data = {}
        for key in list(self.global_plan_over_rides):
            self.global_plan_over_rides[key] = {'value': None, 'only_if_missing': False}
        self.clear_plan_data()
        if self.dicom_importer:
            self.tree_ctrl_roi.DeleteChildren(self.dicom_importer.root_rois)
        starting_dir = self.text_ctrl_directory.GetValue()
        if starting_dir == '':
            starting_dir = self.start_path
        if not isdir(starting_dir):
            starting_dir = ""

        dlg = wx.DirDialog(self, "Select inbox directory", starting_dir, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.text_ctrl_directory.SetValue(dlg.GetPath())
            self.dicom_importer = self.get_importer()

    def get_importer(self):
        return DicomImporter(self.text_ctrl_directory.GetValue(), self.tree_ctrl_import,
                             self.tree_ctrl_roi, self.tree_ctrl_roi_root, self.tree_ctrl_images,
                             self.roi_map, search_subfolders=self.checkbox_subfolders.GetValue())

    def on_file_tree_select(self, evt):
        """
        On selection of an item in the file tree, update the plan dependent elements of the Frame
        """
        uid = self.get_file_tree_item_plan_uid(evt.GetItem())
        self.tree_ctrl_roi.SelectItem(self.tree_ctrl_roi_root, True)
        if uid in list(self.parsed_dicom_data) and self.parsed_dicom_data[uid].validation['complete_file_set']:
            if uid != self.selected_uid:
                self.selected_uid = uid
                wait = wx.BusyCursor()
                self.dicom_importer.rebuild_tree_ctrl_rois(uid)
                self.tree_ctrl_roi.ExpandAll()
                if uid not in list(self.parsed_dicom_data):
                    file_paths = self.dicom_importer.dicom_file_paths[uid]
                    self.parsed_dicom_data[uid] = DICOM_Parser(plan=file_paths['rtplan']['file_path'],
                                                               structure=file_paths['rtstruct']['file_path'],
                                                               dose=file_paths['rtdose']['file_path'],
                                                               global_plan_over_rides=self.global_plan_over_rides,
                                                               roi_map=self.roi_map)
                data = self.parsed_dicom_data[uid]

                self.input['mrn'].SetValue(data.mrn)
                self.input['study_instance_uid'].SetValue(data.study_instance_uid_to_be_imported)
                if data.birth_date is None or data.birth_date == '':
                    self.input['birth_date'].SetValue('')
                else:
                    self.input['birth_date'].SetValue(datetime_to_date_string(data.birth_date))
                if data.sim_study_date is None or data.sim_study_date == '':
                    self.input['sim_study_date'].SetValue('')
                else:
                    self.input['sim_study_date'].SetValue(datetime_to_date_string(data.sim_study_date))
                physician = ['DEFAULT', data.physician][data.physician in self.roi_map.get_physicians()]
                self.input['physician'].SetValue(physician)
                self.input['tx_site'].SetValue(data.tx_site)
                self.input['rx_dose'].SetValue(str(data.rx_dose))
                self.dicom_importer.update_mapped_roi_status(data.physician)
                del wait
                self.update_physician_roi_choices()
                self.enable_inputs()
        else:
            self.clear_plan_data()
            self.disable_inputs()
            self.selected_uid = None
            self.tree_ctrl_roi.DeleteChildren(self.dicom_importer.root_rois)
        self.selected_uid = uid
        self.update_warning_label()

    def on_roi_tree_select(self, evt):
        self.allow_input_roi_apply = False
        self.selected_roi = self.get_roi_tree_item_name(evt.GetItem())
        self.update_roi_inputs()
        self.allow_input_roi_apply = True

    def update_input_roi_physician_enable(self):
        if self.selected_roi:
            if self.input_roi['physician'].GetValue() == 'uncategorized':
                self.input_roi['physician'].Enable()
            else:
                self.input_roi['physician'].Disable()

            self.input_roi['type'].Enable()
        else:
            self.input_roi['physician'].Disable()
            self.input_roi['type'].Disable()

    def update_roi_inputs(self):
        self.allow_input_roi_apply = False
        physician = self.input['physician'].GetValue()
        if self.selected_roi and self.roi_map.is_physician(physician):
            physician_roi = self.roi_map.get_physician_roi(physician, self.selected_roi)
            roi_key = self.dicom_importer.roi_name_map[self.selected_roi]['key']
            uid = self.selected_uid
            roi_type = self.parsed_dicom_data[uid].get_roi_type(roi_key)
            self.input_roi['physician'].SetValue(physician_roi)
            self.update_physician_roi_choices(physician_roi)
            self.input_roi['type'].SetValue(roi_type)

            self.update_roi_text_with_roi_type(self.selected_roi, roi_type)
        else:
            self.input_roi['physician'].SetValue('')
            self.input_roi['type'].SetValue('')
        self.allow_input_roi_apply = True
        self.update_input_roi_physician_enable()

    def update_roi_text_with_roi_type(self, roi, roi_type):
        roi_type_for_tree_text = [None, 'PTV'][roi_type == 'PTV']
        self.dicom_importer.update_tree_ctrl_roi_with_roi_type(roi, roi_type=roi_type_for_tree_text)

    def clear_plan_data(self):
        for input_obj in self.input.values():
            input_obj.SetValue('')

        self.reset_label_colors()

    def get_file_tree_item_plan_uid(self, item):
        plan_node = None
        node_id, node_type = self.dicom_importer.get_id_of_tree_ctrl_node(item)

        # if item is a plan node
        if node_type == 'plan':
            plan_node = item

        # if item is a study node
        elif node_type == 'study':
            plan_node, valid = self.tree_ctrl_import.GetFirstChild(item)

        # if item is a patient node
        elif node_type == 'patient':
            study_node, valid = self.tree_ctrl_import.GetFirstChild(item)
            plan_node, valid = self.tree_ctrl_import.GetFirstChild(study_node)

        if plan_node is not None:
            uid, node_type = self.dicom_importer.get_id_of_tree_ctrl_node(plan_node)
            return uid

    def get_file_tree_item_study_uid(self, item):
        study_node = None
        node_id, node_type = self.dicom_importer.get_id_of_tree_ctrl_node(item)

        # if selected item is a study node
        if node_type == 'study':
            study_node = item

        # if selected item is plan node
        elif node_type == 'plan':
            study_node, valid = self.tree_ctrl_import.GetItemParent(item)

        # if selected item is a patient node
        elif node_type == 'patient':
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
        physician = self.input['physician'].GetValue()
        if physician:
            self.enable_roi_inputs()
        else:
            self.disable_roi_inputs()

        self.update_roi_inputs()
        self.dicom_importer.update_mapped_roi_status(physician)
        self.update_roi_inputs()

    def update_label_text_color(self, key):
        red_value = [255, 0][self.input[key].GetValue() != '']
        self.label[key].SetForegroundColour(wx.Colour(red_value, 0, 0))

    def reset_label_colors(self):
        for label in self.label.values():
            label.SetForegroundColour(wx.Colour(0, 0, 0))

    def disable_inputs(self):
        for input_obj in self.input.values():
            input_obj.Disable()
        self.button_edit_sim_study_date.Disable()
        self.button_edit_birth_date.Disable()
        self.button_apply_plan_data.Disable()
        self.button_roi_manager.Disable()
        self.button_delete_study.Disable()
        self.button_add_physician.Disable()
        for check_box in self.checkbox.values():
            check_box.Disable()

    def enable_inputs(self):
        for input_obj in self.input.values():
            input_obj.Enable()
        self.button_edit_sim_study_date.Enable()
        self.button_edit_birth_date.Enable()
        self.button_apply_plan_data.Enable()
        self.button_roi_manager.Enable()
        self.button_delete_study.Enable()
        self.button_add_physician.Enable()
        for check_box in self.checkbox.values():
            check_box.Enable()

    def disable_roi_inputs(self):
        for input_obj in self.input_roi.values():
            input_obj.Disable()

    def enable_roi_inputs(self):
        for key, input_obj in self.input_roi.items():
            if key not in {'physician', 'type'}:
                input_obj.Enable()

    def update_physician_roi_choices(self, physician_roi=None):
        physician = self.input['physician'].GetValue()
        if self.roi_map.is_physician(physician):
            choices = self.roi_map.get_physician_rois(physician)
        else:
            choices = []
        if choices and physician_roi in {'uncategorized'}:
            choices = list(set(choices) - set(self.dicom_importer.get_used_physician_rois(physician)))
            choices.sort()
            choices.append('uncategorized')
        self.input_roi['physician'].Clear()
        self.input_roi['physician'].Append(choices)
        if physician_roi is not None:
            self.input_roi['physician'].SetValue(physician_roi)

    def on_apply_plan(self, evt):
        wait = wx.BusyCursor()
        self.on_physician_change()
        over_rides = self.parsed_dicom_data[self.selected_uid].plan_over_rides
        apply_all_selected = False
        for key in list(over_rides):
            value = self.input[key].GetValue()
            if 'date' in key:
                over_rides[key] = self.validate_date(value)
            elif key == 'rx_dose':
                over_rides[key] = self.validate_dose(value)
            else:
                if not value:
                    value = None
                over_rides[key] = value

            # Apply all
            if "%s_1" % key in list(self.checkbox):
                apply_all_selected = True
                if self.checkbox["%s_1" % key].IsChecked():
                    self.global_plan_over_rides[key]['value'] = value
                    self.global_plan_over_rides[key]['only_if_missing'] = self.checkbox["%s_2" % key].IsChecked()

        self.clear_plan_check_boxes()
        if apply_all_selected:
            self.validate()
        else:
            self.validate(uid=self.selected_uid)
        self.update_warning_label()
        del wait

    def on_apply_roi(self, evt):
        if self.allow_input_roi_apply:
            roi_type_over_ride = self.parsed_dicom_data[self.selected_uid].roi_type_over_ride
            key = self.dicom_importer.roi_name_map[self.selected_roi]['key']
            roi_type_over_ride[key] = self.input_roi['type'].GetValue()
            self.validate(uid=self.selected_uid)
            self.update_warning_label()
            self.dicom_importer.update_mapped_roi_status(self.input['physician'].GetValue())
            self.update_roi_text_with_roi_type(self.selected_roi, roi_type=self.input_roi['type'].GetValue())

    @staticmethod
    def validate_date(date):
        try:
            dt = parse_date(date)
            truncated = datetime_obj(dt.year, dt.month, dt.day)
            return str(truncated).replace('-', '')
        except:
            return None

    @staticmethod
    def validate_dose(dose):
        try:
            return float(dose)
        except:
            return None

    @staticmethod
    def is_uid_valid(uid):
        with DVH_SQL() as cnx:
            valid_uid = not cnx.is_study_instance_uid_in_table('Plans', uid)

        if valid_uid:
            return True
        return False

    def clear_plan_check_boxes(self):
        for checkbox in self.checkbox.values():
            checkbox.SetValue(False)

    def on_check_apply_all(self, evt):
        for key in ['birth_date', 'sim_study_date', 'physician', 'tx_site', 'rx_dose']:
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
            self.roi_map.write_to_file()
            ImportWorker(self.parsed_dicom_data, list(self.dicom_importer.checked_plans),
                         self.checkbox_include_uncategorized.GetValue(), self.terminate,
                         self.dicom_importer.other_dicom_files)
            dlg = ImportStatusDialog(self.terminate)
            # calling self.Close() below caused issues in Windows if Show() used instead of ShowModal()
            [dlg.Show, dlg.ShowModal][is_windows()]()
            self.Close()
        else:
            dlg = wx.MessageDialog(self, "No plans have been selected.", caption='Import Failure',
                                   style=wx.OK | wx.OK_DEFAULT | wx.CENTER | wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()

    def remove_empty_folders(self):
        remove_empty_folders(self.start_path)

    def parse_dicom_data(self):
        self.button_cancel.Disable()
        self.button_save_roi_map.Disable()
        self.button_import.Disable()
        wait = wx.BusyInfo("Parsing DICOM data\nPlease wait...")
        parsed_uids = list(self.parsed_dicom_data)
        plan_total = len(list(self.dicom_importer.plan_nodes))
        self.gauge.SetValue(0)
        self.gauge.Show()
        for plan_counter, uid in enumerate(list(self.dicom_importer.plan_nodes)):
            self.label_progress.SetLabelText("Parsing %s of %s studies" % (plan_counter+1, plan_total))
            if uid not in parsed_uids:
                file_paths = self.dicom_importer.dicom_file_paths[uid]
                wx.Yield()
                if file_paths['rtplan'] and file_paths['rtstruct'] and file_paths['rtdose']:
                    self.parsed_dicom_data[uid] = DICOM_Parser(plan=file_paths['rtplan'][0],
                                                               structure=file_paths['rtstruct'][0],
                                                               dose=file_paths['rtdose'][0],
                                                               global_plan_over_rides=self.global_plan_over_rides,
                                                               roi_map=self.roi_map)

            wx.CallAfter(self.gauge.SetValue, int(100 * (plan_counter+1) / plan_total))
        self.label_progress.SetLabelText("Auto-detecting plans missing PTV labels")
        self.autodetect_target_for_plans_missing_targets()
        self.gauge.Hide()
        self.label_progress.SetLabelText("All %s plans parsed" % plan_total)

        del wait

        self.button_cancel.Enable()
        self.button_save_roi_map.Enable()
        self.button_import.Enable()

        self.is_all_data_parsed = True
        self.validate()

    def validate(self, uid=None):
        red = wx.Colour(255, 0, 0)
        orange = wx.Colour(255, 165, 0)
        yellow = wx.Colour(255, 255, 0)
        if self.is_all_data_parsed:
            wait = wx.BusyCursor()
            if not uid:
                nodes = self.dicom_importer.plan_nodes
            else:
                nodes = {uid: self.dicom_importer.plan_nodes[uid]}
            for uid, node in nodes.items():
                if uid in list(self.parsed_dicom_data):
                    validation = self.parsed_dicom_data[uid].validation
                    failed_keys = {key for key, value in validation.items() if not value['status']}
                else:
                    failed_keys = {'complete_file_set'}
                if failed_keys:
                    if {'study_instance_uid', 'complete_file_set'}.intersection(failed_keys):
                        color = red
                    elif {'physician', 'ptv'}.intersection(failed_keys):
                        color = orange
                    else:
                        color = yellow
                elif uid in self.dicom_importer.incomplete_plans:
                    color = red
                else:
                    color = None
                self.tree_ctrl_import.SetItemBackgroundColour(node, color)

                if uid is not None:
                    self.tree_ctrl_import.CheckItem(node, color != red)

            del wait

    def update_warning_label(self):
        msg = ''
        if self.selected_uid:
            if self.selected_uid in list(self.parsed_dicom_data):
                validation = self.parsed_dicom_data[self.selected_uid].validation
                failed_keys = {key for key, value in validation.items() if not value['status']}
                if failed_keys:
                    if 'complete_file_set' in failed_keys:
                        msg = "ERROR: %s" % validation['complete_file_set']['message']
                        if self.selected_uid not in self.incomplete_studies:
                            self.incomplete_studies.append(self.selected_uid)
                    else:
                        msg = "WARNING: %s" % ' '.join([validation[key]['message'] for key in failed_keys])
            else:
                msg = "ERROR: Incomplete Fileset. RT Plan, Dose, and Structure required."
        self.label_warning.SetLabelText(msg)

    def on_delete_study(self, evt):
        uid = self.input['study_instance_uid'].GetValue()
        with DVH_SQL() as cnx:
            if cnx.is_uid_imported(uid):
                dlg = wx.MessageDialog(self, "Delete all data in database with this UID?", caption='Delete Study',
                                       style=wx.YES | wx.NO | wx.NO_DEFAULT | wx.CENTER | wx.ICON_EXCLAMATION)
            else:
                dlg = wx.MessageDialog(self, "Study Instance UID not found in Database", caption='Delete Study',
                                       style=wx.OK | wx.CENTER | wx.ICON_EXCLAMATION)

            res = dlg.ShowModal()
            dlg.Center()
            if res == wx.ID_YES:
                cnx.delete_rows("study_instance_uid = '%s'" % uid)

        dlg.Destroy()

        self.validate(uid=self.selected_uid)
        self.update_warning_label()

    def on_edit_birth_date(self, evt):
        self.on_edit_date('birth_date')

    def on_edit_sim_study_date(self, evt):
        self.on_edit_date('sim_study_date')

    def on_edit_date(self, key):
        DatePicker(initial_date=self.input[key].GetValue(),
                   title=key.replace('_', ' ').title(),
                   action=self.input[key].SetValue)

        self.validate(self.selected_uid)
        self.update_warning_label()

    def autodetect_target_for_plans_missing_targets(self):
        for uid, parsed_dicom_data in self.parsed_dicom_data.items():
            if not parsed_dicom_data.ptv_exists:
                parsed_dicom_data.autodetect_target_roi_type()
                self.validate(uid)
        self.update_warning_label()
        self.update_roi_inputs()

    def on_roi_manager(self, evt):
        RoiManager(self, self.roi_map, self.input['physician'].GetValue(), self.input_roi['physician'].GetValue())
        self.update_physician_choices(keep_old_physician=True)
        self.update_physician_roi_choices()
        self.update_roi_inputs()
        self.dicom_importer.update_mapped_roi_status(self.input['physician'].GetValue())
        self.update_input_roi_physician_enable()

    def on_add_physician(self, evt):
        AddPhysician(self.roi_map, initial_physician=self.input['physician'].GetValue())
        self.update_physician_choices()

    def on_manage_physician_roi(self, evt):
        physician = self.input['physician'].GetValue()
        unlinked_institutional_rois = self.roi_map.get_unused_institutional_rois(physician)
        AddPhysicianROI(self, physician, unlinked_institutional_rois)

    def on_manage_roi_type(self, evt):
        AddROIType(self)

    def update_physician_choices(self, keep_old_physician=False):
        old_physician = self.input['physician'].GetValue()
        old_physicians = self.input['physician'].Items
        new_physicians = self.roi_map.get_physicians()
        new_physician = [p for p in new_physicians if p and p not in old_physicians]
        self.input['physician'].Clear()
        self.input['physician'].Append(new_physicians)
        if not keep_old_physician and new_physician:
            self.input['physician'].SetValue(new_physician[0])
        else:
            self.input['physician'].SetValue(old_physician)

    def on_physician_roi_change(self, evt):
        physician = self.input['physician'].GetValue()
        variation = self.selected_roi
        physician_roi = self.input_roi['physician'].GetValue()

        if physician_roi not in self.roi_map.get_physician_rois(physician):
            self.roi_map.add_physician_roi(physician, physician_roi)
        if variation not in self.roi_map.get_variations(physician, physician_roi):
            self.roi_map.add_variation(physician, physician_roi, variation)

        self.dicom_importer.update_mapped_roi_status(physician)
        self.update_input_roi_physician_enable()

    def on_roi_tree_double_click(self, evt):
        ChangePlanROIName(self.tree_ctrl_roi,
                          evt.GetItem(),
                          self.input['mrn'].GetValue(),
                          self.input['study_instance_uid'].GetValue(),
                          self.parsed_dicom_data[self.input['study_instance_uid'].GetValue()])
        # self.dicom_dir = self.parsed_dicom_data[self.input['study_instance_uid'].GetValue()]
        # self.dicom_dir.update_mapped_roi_status(self.input['physician'].GetValue())


class ImportStatusDialog(wx.Dialog):
    """
    Dialog with progress information about DICOM import
    """
    def __init__(self, terminate):
        """
        Terminate will be linked to ImportWorker, which will periodically check it's value, if true
        the thread will gracefully terminate. This class can set terminate to true with the cancel button.
        :param terminate: will cancel ImportWorker thread if set to True
        :type terminate: dict
        """
        wx.Dialog.__init__(self, None)
        self.gauge_study = wx.Gauge(self, wx.ID_ANY, 100)
        self.gauge_calculation = wx.Gauge(self, wx.ID_ANY, 100)
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        # self.error_details_pane = wx.CollapsiblePane(self, label='Details')
        # self.error_details_window = wx.ScrolledWindow(self.error_details_pane.GetPane())
        # self.error_details_text = wx.StaticText(self.error_details_window, wx.ID_ANY,
        #                                         "Error details go here.\n"
        #                                         "Will add things soon.")

        self.terminate = terminate

        self.__set_properties()
        self.__do_layout()
        self.__do_subscribe()

        self.Bind(wx.EVT_BUTTON, self.set_terminate, id=self.button_cancel.GetId())

        self.start_time = datetime.now()

    def __do_subscribe(self):
        pub.subscribe(self.update_patient, "update_patient")
        pub.subscribe(self.update_calculation, "update_calculation")
        pub.subscribe(self.update_elapsed_time, "update_elapsed_time")
        pub.subscribe(self.close, "close")

    def __set_properties(self):
        self.SetTitle("Import Progress")
        self.SetSize((700, 260))

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_progress = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_calculation = wx.BoxSizer(wx.VERTICAL)
        sizer_study = wx.BoxSizer(wx.VERTICAL)
        sizer_time_cancel = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_error_pane = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_error_window = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_error_text = wx.BoxSizer(wx.HORIZONTAL)

        self.label_study_counter = wx.StaticText(self, wx.ID_ANY, "Plan 1 of 1")
        sizer_study.Add(self.label_study_counter, 0, wx.ALIGN_CENTER, 0)
        self.label_patient = wx.StaticText(self, wx.ID_ANY, "Patient:")
        sizer_study.Add(self.label_patient, 0, 0, 0)
        self.label_study = wx.StaticText(self, wx.ID_ANY, "Plan SOP Instance UID:")
        sizer_study.Add(self.label_study, 0, 0, 0)
        sizer_study.Add(self.gauge_study, 0, wx.EXPAND, 0)

        sizer_progress.Add(sizer_study, 0, wx.ALL | wx.EXPAND, 5)
        self.label_calculation = wx.StaticText(self, wx.ID_ANY, "Calculation: DVH")
        sizer_calculation.Add(self.label_calculation, 0, 0, 0)
        self.label_structure = wx.StaticText(self, wx.ID_ANY, "")
        sizer_calculation.Add(self.label_structure, 0, 0, 0)
        sizer_calculation.Add(self.gauge_calculation, 0, wx.EXPAND, 0)
        sizer_progress.Add(sizer_calculation, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_progress, 0, wx.EXPAND | wx.ALL, 5)

        self.label_elapsed_time = wx.StaticText(self, wx.ID_ANY, "Elapsed time:")
        sizer_time_cancel.Add(self.label_elapsed_time, 1, wx.EXPAND | wx.ALL, 5)
        sizer_time_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_time_cancel, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def close(self):
        self.Destroy()

    def update_patient(self, msg):
        """
        Update patient/study related information. Linked with pubsub to ImportWorker
        :param msg: study_number, study_total, patient_name, uid, and progress values
        :type msg: dict
        """
        wx.CallAfter(self.label_study_counter.SetLabelText, "Plan %s of %s" %
                     (msg['study_number'], msg['study_total']))
        wx.CallAfter(self.label_patient.SetLabelText, "Patient: %s" % msg['patient_name'])
        wx.CallAfter(self.label_study.SetLabelText, "Plan SOP Instance UID: %s" % msg['uid'])
        wx.CallAfter(self.gauge_study.SetValue, msg['progress'])

    def update_calculation(self, msg):
        """
        Update calculation related information. Linked with pubsub to ImportWorker
        :param msg: calculation type, roi_num, roi_total, roi_name, and progress values
        :type msg: dict
        """
        wx.CallAfter(self.label_calculation.SetLabelText, "Calculation: %s" % msg['calculation'])
        wx.CallAfter(self.label_structure.SetLabelText, "Structure (%s of %s): %s" %
                     (msg['roi_num'], msg['roi_total'], msg['roi_name']))
        wx.CallAfter(self.gauge_calculation.SetValue, msg['progress'])

    def update_elapsed_time(self):
        """
        Update the elapsed time. Linked with pubsub to ImportWorker
        """
        elapsed_time = get_elapsed_time(self.start_time, datetime.now())
        wx.CallAfter(self.label_elapsed_time.SetLabelText, "Elapsed Time: %s" % elapsed_time)

    def set_terminate(self, evt):
        self.terminate['status'] = True  # Linked to ImportWorker
        self.close()


class ImportWorker(Thread):
    """
    Create a thread separate from the GUI to perform the import calculations
    """
    def __init__(self, data, checked_uids, import_uncategorized, terminate, other_dicom_files):
        """
        :param data: parsed dicom data
        :type data: dict
        :param checked_uids: uids that were selected in the GUI for import
        :type checked_uids: list
        :param import_uncategorized: if True, import rois with names that that are not mapped
        :type import_uncategorized: bool
        :param terminate: thread will periodically check this value, if true, gracefully terminate
        :type terminate: dict
        :param other_dicom_files: other dicom files found in the import directory
        :type other_dicom_files: dict
        """
        Thread.__init__(self)

        self.data = data
        self.checked_uids = checked_uids
        self.import_uncategorized = import_uncategorized
        self.terminate = terminate
        self.other_dicom_files = other_dicom_files

        with DVH_SQL() as cnx:
            self.last_import_time = cnx.now  # use pgsql time rather than CPU since time stamps in DB are based on psql

        self.start()  # start the thread

    def run(self):
        try:
            self.import_studies()

        except MemoryError as mem_err:
            # This usually occurs for DVHs of large ROIs or minimum distance calculations
            print(mem_err)

        except Exception as e:
            print('Error: ', e)
            print('Import incomplete. Any studies successfully imported were transferred to your imported folder:')
            print('\t%s' % IMPORTED_DIR)
            print('\tIf a study was partially imported, all data has been removed from the database '
                  'and its DICOM files remain in your inbox.')
            self.delete_partially_updated_plan()

        wx.CallAfter(pub.sendMessage, "close")

    def get_study_uids(self):
        """
        This thread iterates through self.checked_uids which contains plan uids, but we need to iterate through
        study instance uids so that plans on the same study are imported adjacently.
        :return: a dictionary with study uids for the keys and a list of associated plan uids for values
        :rtype: dict
        """
        study_uids = {}
        for plan_uid in self.checked_uids:
            study_uid = self.data[plan_uid].study_instance_uid_to_be_imported
            if study_uid not in list(study_uids):
                study_uids[study_uid] = []
            study_uids[study_uid].append(plan_uid)
        return study_uids

    def import_studies(self):
        """
        Iterate through StudyInstanceUIDs that match plan SOPInstanceUIDs in self.checked_uids
        Update dialog with status information
        If there are multiple plans for a study uid, sum the dose grids
        Import the study
        """

        study_uids = self.get_study_uids()
        plan_total = len(self.checked_uids)
        plan_counter = 0
        for study_uid, plan_uid_set in study_uids.items():
            if len(plan_uid_set) > 1:
                dose_files = [self.data[plan_uid].dicompyler_data['dose'] for plan_uid in plan_uid_set]

                wait = wx.BusyInfo('Summing grids for\n%s' % study_uid)
                dose_sum = sum_dose_grids(dose_files)
                del wait
                for plan_uid in plan_uid_set:
                    self.data[plan_uid].import_dose_sum(dose_sum)

            for i, plan_uid in enumerate(plan_uid_set):
                if plan_uid in list(self.data):

                    msg = {'patient_name': self.data[plan_uid].patient_name,
                           'uid': self.data[plan_uid].study_instance_uid_to_be_imported,
                           'progress': int(100 * plan_counter / plan_total),
                           'study_number': plan_counter + 1,
                           'study_total': plan_total}
                    wx.CallAfter(pub.sendMessage, "update_patient", msg=msg)
                    wx.CallAfter(pub.sendMessage, "update_elapsed_time")

                    self.import_study(plan_uid, final_plan_in_study=plan_uid == plan_uid_set[-1])
                    if self.terminate['status']:
                        self.delete_partially_updated_plan()
                        return
                else:
                    print('WARNING: This plan could not be parsed. Skipping import. '
                          'Did you supply RT Structure, Dose, and Plan?')
                    print('\tPlan UID: %s' % plan_uid)
                    print('\tMRN: %s' % self.data[plan_uid].mrn)

                plan_counter += 1

        pub.sendMessage("remove_empty_folders")

    def import_study(self, plan_uid, final_plan_in_study=True):
        """
        Import DVHs and perform post-import calculations for a given plan uid (SOPInstanceUID from RTPlan)
        :param plan_uid: the SOPInstanceUID from the DICOM RT Plan file
        :type plan_uid: str
        :param final_plan_in_study: indicates if post-import calculations should be performed and files moved
        :type final_plan_in_study: bool
        """
        dicom_rt_struct = dicomparser.DicomParser(self.data[plan_uid].structure_file)
        study_uid = self.data[plan_uid].study_instance_uid_to_be_imported
        structures = dicom_rt_struct.GetStructures()
        roi_name_map = {key: structures[key]['name'] for key in list(structures) if structures[key]['type'] != 'MARKER'}
        data_to_import = {'Plans': [self.data[plan_uid].get_plan_row()],
                          'Rxs': self.data[plan_uid].get_rx_rows(),
                          'Beams': self.data[plan_uid].get_beam_rows(),
                          'DICOM_Files': [self.data[plan_uid].get_dicom_file_row()],
                          'DVHs': []}

        if not self.import_uncategorized:  # remove uncategorized ROIs unless this is checked
            for roi_key in list(roi_name_map):
                if self.data[plan_uid].get_physician_roi(roi_key) == 'uncategorized':
                    roi_name_map.pop(roi_key)

        post_import_rois = []
        roi_total = len(roi_name_map)
        ptvs = {key: [] for key in ['dvh', 'volume', 'index']}
        with DVH_SQL() as cnx:
            for roi_counter, roi_key in enumerate(list(roi_name_map)):
                if self.terminate['status']:
                    return

                # Skip dvh calculation if roi was already imported (e.g, from previous plan in this study)
                if not cnx.is_roi_imported(roi_name_map[roi_key], study_uid):

                    # Send messages to status dialog about progress
                    msg = {'calculation': 'DVH',
                           'roi_num': roi_counter+1,
                           'roi_total': roi_total,
                           'roi_name': roi_name_map[roi_key],
                           'progress': int(100 * (roi_counter+1) / roi_total)}
                    wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
                    wx.CallAfter(pub.sendMessage, "update_elapsed_time")

                    dvh_row = self.data[plan_uid].get_dvh_row(roi_key)
                    if dvh_row:
                        roi_type = dvh_row['roi_type'][0]
                        roi_name = dvh_row['roi_name'][0]
                        physician_roi = dvh_row['physician_roi'][0]

                        # Collect dvh, volume, and index of ptvs to be used for post-import calculations
                        if roi_type.startswith('PTV'):
                            ptvs['dvh'].append(dvh_row['dvh_string'][0])
                            ptvs['volume'].append(dvh_row['volume'][0])
                            ptvs['index'].append(len(data_to_import['DVHs']))

                        data_to_import['DVHs'].append(dvh_row)

                        # collect roi names for post-import calculations
                        if roi_type and roi_name and physician_roi:
                            if roi_type.lower() in ['organ', 'ctv', 'gtv']:
                                if not (physician_roi.lower() in
                                        ['uncategorized', 'ignored', 'external', 'skin', 'body']
                                        or roi_name.lower() in ['external', 'skin', 'body']):
                                    post_import_rois.append(clean_name(roi_name_map[roi_key]))

        # Sort PTVs by their D_95% (applicable to SIBs)
        if ptvs['dvh']:
            ptv_order = rank_ptvs_by_D95(ptvs)
            for ptv_row, dvh_row_index in enumerate(ptvs['index']):
                data_to_import['DVHs'][dvh_row_index]['roi_type'][0] = "PTV%s" % (ptv_order[ptv_row]+1)

        # Must push data to SQL before processing post import calculations since they rely on SQL
        self.push(data_to_import)

        # Wait until entire study has been pushed since these values are based on entire PTV volume
        if final_plan_in_study:
            if ptvs['dvh']:

                # Calculate the PTV overlap for each roi
                tv = db_update.get_total_treatment_volume_of_study(study_uid)
                self.post_import_calc('PTV Overlap Volume', study_uid, post_import_rois,
                                      db_update.treatment_volume_overlap, tv)
                if self.terminate['status']:
                    return

                # Calculate the centroid distances of roi-to-PTV for each roi
                tv_centroid = db_update.get_treatment_volume_centroid(tv)
                self.post_import_calc('Centroid Distance to PTV', study_uid, post_import_rois,
                                      db_update.dist_to_ptv_centroids, tv_centroid)
                if self.terminate['status']:
                    return

                # Calculate minimum, mean, median, and max distances and DTH
                tv_coord = db_update.get_treatment_volume_coord(tv)
                tv_coord = sample_roi(tv_coord)
                self.post_import_calc('Distances to PTV', study_uid, post_import_rois,
                                      db_update.min_distances, tv_coord)
                if self.terminate['status']:
                    return

                # Update progress dialog
                msg = {'calculation': 'Total Treatment Volume Statistics',
                       'roi_num': 0,
                       'roi_total': 1,
                       'roi_name': 'PTV',
                       'progress': 0}
                wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)

                # Update PTV geometric data
                db_update.update_ptv_data(tv, study_uid)

                # Update progress dialog
                msg['roi_num'], msg['progress'] = 1, 100
                wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)

            else:
                print("WARNING: No PTV found for %s" % plan_uid)
                print("\tMRN: %s" % self.data[plan_uid].mrn)
                print("\tSkipping PTV related calculations.")

        # Move files to imported directory
        if final_plan_in_study:
            self.move_files(plan_uid, study_uid)

            # Record the time per SQL of last complete import for a study
            with DVH_SQL() as cnx:
                self.last_import_time = cnx.now

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
        roi_total = len(rois)
        for roi_counter, roi_name in enumerate(rois):
            if self.terminate['status']:
                return
            msg = {'calculation': title,
                   'roi_num': roi_counter + 1,
                   'roi_total': roi_total,
                   'roi_name': roi_name,
                   'progress': int(100 * roi_counter / roi_total)}
            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
            func(uid, roi_name, pre_calc=pre_calc)

    def move_files(self, uid, study_uid):
        files = [self.data[uid].plan_file,
                 self.data[uid].structure_file,
                 self.data[uid].dose_file]
        if study_uid in self.other_dicom_files.keys():
            files.extend(self.other_dicom_files[study_uid])

        new_dir = join(self.data[uid].import_path, self.data[uid].mrn)
        move_files_to_new_path(files, new_dir)

        # remove old directory if empty
        for file in files:
            old_dir = dirname(file)
            if isdir(old_dir) and not listdir(old_dir):
                rmdir(old_dir)

    def delete_partially_updated_plan(self):
        """
        If import process fails, call this function to remove the partially imported data into SQL
        """
        with DVH_SQL() as cnx:
            if cnx.db_type == 'sqlite':
                cnx.delete_rows("import_time_stamp > date(%s)" % self.last_import_time)
            else:
                cnx.delete_rows("import_time_stamp > '%s'::date" % self.last_import_time)
