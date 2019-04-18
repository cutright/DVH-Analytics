import wx
import wx.adv
from db.dicom_importer import DICOM_Importer
from db.dicom_parser import DICOM_Parser
from dicompylercore import dicomparser
from os.path import isdir, join, dirname
from os import listdir, rmdir
from wx.lib.agw.customtreectrl import CustomTreeCtrl, TR_AUTO_CHECK_CHILD, TR_AUTO_CHECK_PARENT, TR_DEFAULT_STYLE
from tools.utilities import datetime_to_date_string, get_elapsed_time, move_files_to_new_path, rank_ptvs_by_D95
from db.sql_connector import DVH_SQL
from tools.roi_name_manager import DatabaseROIs, clean_name
from dateutil.parser import parse as parse_date
from datetime import date as datetime_obj, datetime
from threading import Thread
from pubsub import pub
from db import update as db_update
from default_options import ROI_TYPES
from dialogs.main.date_picker import DatePicker
from paths import IMPORT_SETTINGS_PATH, parse_settings_file


class ImportDICOM_Dialog(wx.Dialog):
    def __init__(self, inbox=None, *args, **kwds):
        wx.Dialog.__init__(self, None, title='Import DICOM')

        self.SetSize((1350, 800))

        self.parsed_dicom_data = {}
        self.selected_uid = None

        self.roi_map = DatabaseROIs()
        self.selected_roi = None

        self.start_path = parse_settings_file(IMPORT_SETTINGS_PATH)['inbox']

        self.checkbox = {}
        keys = ['birth_date', 'sim_study_date', 'physician', 'tx_site', 'rx_dose']
        for key in keys:
            self.checkbox['%s_1' % key] = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
            self.checkbox['%s_2' % key] = wx.CheckBox(self, wx.ID_ANY, "Only if missing")
        self.global_plan_over_rides = {key: {'value': None, 'only_if_missing': False} for key in keys}

        self.text_ctrl_directory = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_READONLY)

        cnx = DVH_SQL()
        self.input = {'mrn': wx.TextCtrl(self, wx.ID_ANY, ""),
                      'study_instance_uid': wx.TextCtrl(self, wx.ID_ANY, ""),
                      'birth_date': wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY),
                      'sim_study_date': wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY),
                      'physician': wx.ComboBox(self, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN),
                      'tx_site': wx.ComboBox(self, wx.ID_ANY, choices=cnx.get_unique_values('Plans', 'tx_site'),
                                             style=wx.CB_DROPDOWN),
                      'rx_dose': wx.TextCtrl(self, wx.ID_ANY, "")}
        self.button_edit_sim_study_date = wx.Button(self, wx.ID_ANY, "Edit")
        self.button_edit_birth_date = wx.Button(self, wx.ID_ANY, "Edit")
        self.input['physician'].SetValue('')
        self.input['tx_site'].SetValue('')
        self.button_apply_plan_data = wx.Button(self, wx.ID_ANY, "Apply")
        self.button_delete_study = wx.Button(self, wx.ID_ANY, "Delete Study in Database with this UID")
        self.button_delete_study.Disable()
        self.disable_inputs()

        self.button_browse = wx.Button(self, wx.ID_ANY, u"Browse…")
        self.checkbox_subfolders = wx.CheckBox(self, wx.ID_ANY, "Search within subfolders")
        self.panel_study_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.gauge = wx.Gauge(self, -1, 100)
        self.button_import = wx.Button(self, wx.ID_ANY, "Import")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.panel_roi_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.input_roi = {'physician': wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN),
                          'type': wx.ComboBox(self, wx.ID_ANY, choices=ROI_TYPES, style=wx.CB_DROPDOWN)}
        self.input_roi['type'].SetValue('')
        self.button_auto_detect_targets = wx.Button(self, wx.ID_ANY, "Autodetect Targets")
        self.disable_roi_inputs()

        cnx.close()

        styles = TR_AUTO_CHECK_CHILD | TR_AUTO_CHECK_PARENT | TR_DEFAULT_STYLE
        self.tree_ctrl_import = CustomTreeCtrl(self.panel_study_tree, wx.ID_ANY, agwStyle=styles)
        self.tree_ctrl_import.SetBackgroundColour(wx.WHITE)

        self.tree_ctrl_roi = CustomTreeCtrl(self.panel_roi_tree, wx.ID_ANY, agwStyle=styles)
        self.tree_ctrl_roi.SetBackgroundColour(wx.WHITE)
        self.tree_ctrl_roi_root = self.tree_ctrl_roi.AddRoot('RT Structures', ct_type=1)

        self.checkbox_include_uncategorized = wx.CheckBox(self, wx.ID_ANY, "Import uncategorized ROIs")

        self.allow_input_roi_apply = False

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()

        self.is_all_data_parsed = False
        if inbox is None or not isdir(inbox):
            inbox = ''
        self.dicom_dir = DICOM_Importer(inbox, self.tree_ctrl_import, self.tree_ctrl_roi, self.tree_ctrl_roi_root)
        self.parse_directory()

        self.incomplete_studies = []

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
        self.Bind(wx.EVT_TEXT, self.on_apply_roi, id=self.input_roi['type'].GetId())
        self.Bind(wx.EVT_TEXT, self.on_apply_roi, id=self.input_roi['physician'].GetId())

        for key in ['birth_date', 'sim_study_date', 'physician', 'tx_site', 'rx_dose']:
            self.Bind(wx.EVT_CHECKBOX, self.on_check_apply_all, id=self.checkbox['%s_1' % key].GetId())
            self.Bind(wx.EVT_CHECKBOX, self.on_check_apply_all, id=self.checkbox['%s_2' % key].GetId())

        self.Bind(wx.EVT_BUTTON, self.on_edit_birth_date, id=self.button_edit_birth_date.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_edit_sim_study_date, id=self.button_edit_sim_study_date.GetId())

        self.Bind(wx.EVT_BUTTON, self.on_import, id=self.button_import.GetId())

    def __set_properties(self):
        self.checkbox_subfolders.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                                 wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_subfolders.SetValue(1)
        self.checkbox_include_uncategorized.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_include_uncategorized.SetValue(0)

        for checkbox in self.checkbox.values():
            checkbox.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))

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
        sizer_checkbox_rx = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tx_site = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_tx_site_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
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
        self.label_progress = wx.StaticText(self, wx.ID_ANY, "Progress: Status message")
        self.label_progress.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        sizer_progress.Add(self.label_progress, 1, 0, 0)
        sizer_progress.Add(self.gauge, 1, wx.LEFT | wx.EXPAND, 40)
        sizer_studies.Add(sizer_progress, 0, wx.EXPAND, 0)
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
        sizer_physician.Add(self.label['physician'], 0, 0, 0)
        sizer_physician.Add(self.input['physician'], 0, 0, 0)
        sizer_physician_checkbox.Add(self.checkbox['physician_1'], 0, wx.RIGHT, 20)
        sizer_physician_checkbox.Add(self.checkbox['physician_2'], 0, 0, 0)
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
        sizer_rx.Add(self.label['rx_dose'], 0, 0, 0)
        sizer_rx.Add(self.input['rx_dose'], 0, 0, 0)
        sizer_checkbox_rx.Add(self.checkbox['rx_dose_1'], 0, wx.RIGHT, 20)
        sizer_checkbox_rx.Add(self.checkbox['rx_dose_2'], 0, 0, 0)
        sizer_rx.Add(sizer_checkbox_rx, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_rx, 1, wx.ALL | wx.EXPAND, 5)
        sizer_plan_data.Add(self.button_apply_plan_data, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        sizer_plan_data_wrapper.Add(sizer_plan_data, 1, wx.ALL | wx.EXPAND, 10)
        sizer_main.Add(sizer_plan_data_wrapper, 1, wx.EXPAND, 0)
        sizer_roi_tree.Add(self.tree_ctrl_roi, 1, wx.ALL | wx.EXPAND, 0)
        self.panel_roi_tree.SetSizer(sizer_roi_tree)
        sizer_roi_map.Add(self.panel_roi_tree, 1, wx.EXPAND, 0)
        sizer_roi_map.Add(self.button_auto_detect_targets, 0, wx.EXPAND | wx.ALL, 15)

        self.label['physician_roi'] = wx.StaticText(self, wx.ID_ANY, "Physician's ROI Label:")
        sizer_physician_roi.Add(self.label['physician_roi'], 0, 0, 0)
        sizer_physician_roi.Add(self.input_roi['physician'], 0, wx.EXPAND, 0)

        self.label['roi_type'] = wx.StaticText(self, wx.ID_ANY, "ROI Type:")
        sizer_roi_type.Add(self.label['roi_type'], 0, 0, 0)
        sizer_roi_type.Add(self.input_roi['type'], 0, wx.EXPAND, 0)

        sizer_selected_roi.Add(sizer_physician_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_selected_roi.Add(sizer_roi_type, 1, wx.ALL | wx.EXPAND, 5)

        sizer_roi_map.Add(sizer_selected_roi, 0, wx.EXPAND, 0)
        sizer_roi_map_wrapper.Add(sizer_roi_map, 1, wx.ALL | wx.EXPAND, 10)

        sizer_main.Add(sizer_roi_map_wrapper, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        self.label_warning = wx.StaticText(self, wx.ID_ANY, '')
        sizer_warning.Add(self.label_warning, 1, wx.EXPAND, 0)

        sizer_warning_buttons.Add(sizer_warning, 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_import, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_warning_buttons.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_warning_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def parse_directory(self):
        wait = wx.BusyCursor()
        self.gauge.Show()
        file_count = self.dicom_dir.file_count
        self.dicom_dir.initialize_file_tree_root()
        self.tree_ctrl_import.Expand(self.dicom_dir.root_files)
        while self.dicom_dir.current_index < file_count:
            self.dicom_dir.append_next_file_to_tree()
            self.gauge.SetValue(int(100 * self.dicom_dir.current_index / file_count))
            self.update_progress_message()
            self.tree_ctrl_import.ExpandAll()
            wx.Yield()
        self.update_progress_message(complete=True)
        self.gauge.Hide()
        del wait

        self.parse_dicom_data()
        self.validate()

    def on_browse(self, evt):
        self.parsed_dicom_data = {}
        for key in list(self.global_plan_over_rides):
            self.global_plan_over_rides[key] = {'value': None, 'only_if_missing': False}
        self.clear_plan_data()
        self.tree_ctrl_roi.DeleteChildren(self.dicom_dir.root_rois)
        starting_dir = self.text_ctrl_directory.GetValue()
        if starting_dir == '':
            starting_dir = self.start_path
        if not isdir(starting_dir):
            starting_dir = ""
        dlg = wx.DirDialog(self, "Select inbox directory", starting_dir, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.text_ctrl_directory.SetValue(dlg.GetPath())
            self.dicom_dir = DICOM_Importer(self.text_ctrl_directory.GetValue(), self.tree_ctrl_import,
                                            self.tree_ctrl_roi, self.tree_ctrl_roi_root,
                                            search_subfolders=self.checkbox_subfolders.GetValue())
            self.parse_directory()
        dlg.Destroy()

    def update_progress_message(self, complete=False):
        self.label_progress.SetLabelText("%s%s Patients - %s Studies - %s Files" %
                                         (["Progress: ", "Found: "][complete],
                                          self.dicom_dir.count['patient'],
                                          self.dicom_dir.count['study'],
                                          self.dicom_dir.count['file']))

    def on_file_tree_select(self, evt):
        uid = self.get_file_tree_item_uid(evt.GetItem())
        if uid is not None:
            if uid != self.selected_uid:
                self.selected_uid = uid
                wait = wx.BusyCursor()
                self.dicom_dir.rebuild_tree_ctrl_rois(uid)
                self.tree_ctrl_roi.ExpandAll()
                if uid not in list(self.parsed_dicom_data):
                    file_paths = self.dicom_dir.dicom_file_paths[uid]
                    self.parsed_dicom_data[uid] = DICOM_Parser(plan=file_paths['rtplan']['file_path'],
                                                               structure=file_paths['rtstruct']['file_path'],
                                                               dose=file_paths['rtdose']['file_path'],
                                                               global_plan_over_rides=self.global_plan_over_rides)
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
                self.input['physician'].SetValue(data.physician)
                self.input['tx_site'].SetValue(data.tx_site)
                self.input['rx_dose'].SetValue(str(data.rx_dose))
                self.dicom_dir.check_mapped_rois(data.physician)
                del wait
                self.enable_inputs()
            self.update_warning_label()
        else:
            self.clear_plan_data()
            self.disable_inputs()
            self.selected_uid = None
            self.tree_ctrl_roi.DeleteChildren(self.dicom_dir.root_rois)

    def on_roi_tree_select(self, evt):
        self.allow_input_roi_apply = False
        self.selected_roi = self.get_roi_tree_item_name(evt.GetItem())
        self.update_roi_inputs()
        self.allow_input_roi_apply = True

    def update_roi_inputs(self):
        self.allow_input_roi_apply = False
        physician = self.input['physician'].GetValue()
        if self.selected_roi and self.roi_map.is_physician(physician):
            physician_roi = self.roi_map.get_physician_roi(physician, self.selected_roi)
            roi_key = self.dicom_dir.roi_name_map[self.selected_roi]['key']
            uid = self.selected_uid
            roi_type = self.parsed_dicom_data[uid].get_roi_type(roi_key)
            self.input_roi['physician'].SetValue(physician_roi)
            self.input_roi['type'].SetValue(roi_type)
        else:
            self.input_roi['physician'].SetValue('')
            self.input_roi['type'].SetValue('')
        self.allow_input_roi_apply = True

    def clear_plan_data(self):
        for input_obj in self.input.values():
            input_obj.SetValue('')

        self.reset_label_colors()

    def get_file_tree_item_uid(self, item):

        selected_mrn, selected_uid = None, None
        for mrn, node in self.dicom_dir.patient_nodes.items():
            if item == node:
                selected_uid = list(self.dicom_dir.file_tree[mrn])[0]
                break

        if selected_uid is None:
            for uid, node in self.dicom_dir.study_nodes.items():
                if item == node:
                    selected_uid = uid
                    break

        return selected_uid

    def get_roi_tree_item_name(self, item):
        for name, node in self.dicom_dir.roi_nodes.items():
            if item == node:
                return name
        return None

    def on_text_change(self, evt):
        for key, input_obj in self.input.items():
            if input_obj.GetId() == evt.GetId():
                self.update_label_text_color(key)
                if key == 'physician':
                    self.on_physician_change()
                return

    def on_physician_change(self):
        self.update_physician_roi_choices()
        physician = self.input['physician'].GetValue()
        if physician:
            self.enable_roi_inputs()
        else:
            self.disable_roi_inputs()

        self.update_roi_inputs()
        self.dicom_dir.check_mapped_rois(physician)

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
        self.button_delete_study.Disable()
        for check_box in self.checkbox.values():
            check_box.Disable()

    def enable_inputs(self):
        for input_obj in self.input.values():
            input_obj.Enable()
        self.button_edit_sim_study_date.Enable()
        self.button_edit_birth_date.Enable()
        self.button_apply_plan_data.Enable()
        self.button_delete_study.Enable()
        for check_box in self.checkbox.values():
            check_box.Enable()

    def disable_roi_inputs(self):
        self.button_auto_detect_targets.Disable()
        for input_obj in self.input_roi.values():
            input_obj.Disable()

    def enable_roi_inputs(self):
        self.button_auto_detect_targets.Enable()
        for input_obj in self.input_roi.values():
            input_obj.Enable()

    def update_physician_roi_choices(self):
        physician = self.input['physician'].GetValue()
        if self.roi_map.is_physician(physician):
            choices = self.roi_map.get_physician_rois(physician)
        else:
            choices = []
        self.input_roi['physician'].Clear()
        self.input_roi['physician'].Append(choices)

    def on_apply_plan(self, evt):
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

    def on_apply_roi(self, evt):
        if self.allow_input_roi_apply:
            roi_type_over_ride = self.parsed_dicom_data[self.selected_uid].roi_type_over_ride
            key = self.dicom_dir.roi_name_map[self.selected_roi]['key']
            roi_type_over_ride[key] = self.input_roi['type'].GetValue()
            self.validate(uid=self.selected_uid)
            self.update_warning_label()

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
        cnx = DVH_SQL()
        valid_uid = not cnx.is_study_instance_uid_in_table('Plans', uid)
        cnx.close()
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
        ImportWorker(self.parsed_dicom_data, list(self.dicom_dir.checked_studies))
        dlg = ImportStatusDialog()
        dlg.Show()
        self.Close()

    def parse_dicom_data(self):
        wait = wx.BusyCursor()
        parsed_uids = list(self.parsed_dicom_data)
        study_total = len(list(self.dicom_dir.study_nodes))
        self.gauge.SetValue(0)
        self.gauge.Show()
        for study_counter, uid in enumerate(list(self.dicom_dir.study_nodes)):
            self.label_progress.SetLabelText("Parsing %s of %s studies" % (study_counter+1, study_total))
            if uid not in parsed_uids:
                file_paths = self.dicom_dir.dicom_file_paths[uid]
                wx.Yield()
                self.parsed_dicom_data[uid] = DICOM_Parser(plan=file_paths['rtplan']['file_path'],
                                                           structure=file_paths['rtstruct']['file_path'],
                                                           dose=file_paths['rtdose']['file_path'],
                                                           global_plan_over_rides=self.global_plan_over_rides)

            self.gauge.SetValue(int(100 * (study_counter+1) / study_total))
            wx.Yield()

        self.gauge.Hide()
        self.label_progress.SetLabelText("All %s studies parsed" % study_total)

        del wait

        self.is_all_data_parsed = True

    def validate(self, uid=None):
        if self.is_all_data_parsed:
            if not uid:
                nodes = self.dicom_dir.study_nodes
            else:
                nodes = {uid: self.dicom_dir.study_nodes[uid]}
            for uid, node in nodes.items():
                validation = self.parsed_dicom_data[uid].validation
                failed_keys = {key for key, value in validation.items() if not value['status']}
                if failed_keys:
                    if {'study_instance_uid', 'complete_file_set'}.intersection(failed_keys):
                        color = wx.Colour(255, 0, 0)  # red
                    elif {'physician', 'ptv'}.intersection(failed_keys):
                        color = wx.Colour(255, 165, 0)  # orange
                    else:
                        color = wx.Colour(255, 255, 0)  # yellow
                elif uid in self.dicom_dir.incomplete_studies:
                    color = wx.Colour(255, 0, 0)  # red
                else:
                    color = None
                self.tree_ctrl_import.SetItemBackgroundColour(node, color)

    def update_warning_label(self):
        msg = ''
        if self.selected_uid:
            validation = self.parsed_dicom_data[self.selected_uid].validation
            failed_keys = {key for key, value in validation.items() if not value['status']}
            if failed_keys:
                if 'complete_file_set' in failed_keys:
                    msg = "WARNING: %s" % validation['complete_file_set']['message']
                    if self.selected_uid not in self.incomplete_studies:
                        self.incomplete_studies.append(self.selected_uid)
                else:
                    msg = "WARNING: %s" % ' '.join([validation[key]['message'] for key in failed_keys])

        self.label_warning.SetLabelText(msg)

    def on_delete_study(self, evt):
        uid = self.input['study_instance_uid'].GetValue()
        cnx = DVH_SQL()
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
        cnx.close()
        dlg.Destroy()

        self.validate(uid=self.selected_uid)
        self.update_warning_label()

    def on_edit_birth_date(self, evt):
        self.on_edit_date('birth_date')

    def on_edit_sim_study_date(self, evt):
        self.on_edit_date('sim_study_date')

    def on_edit_date(self, key):
        dlg = DatePicker(initial_date=self.input[key].GetValue(),
                         title=key.replace('_', ' ').title())
        res = dlg.ShowModal()
        if res == wx.ID_OK or (res == wx.ID_CANCEL and dlg.none):
            self.input[key].SetValue(dlg.date)
        dlg.Destroy()

        self.validate(self.selected_uid)
        self.update_warning_label()


class ImportStatusDialog(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None)
        self.gauge_study = wx.Gauge(self, wx.ID_ANY, 100)
        self.gauge_calculation = wx.Gauge(self, wx.ID_ANY, 100)
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        self.__do_subscribe()

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
        self.label_study_counter = wx.StaticText(self, wx.ID_ANY, "Study 1 of 1")
        sizer_study.Add(self.label_study_counter, 0, wx.ALIGN_CENTER, 0)
        self.label_patient = wx.StaticText(self, wx.ID_ANY, "Patient:")
        sizer_study.Add(self.label_patient, 0, 0, 0)
        self.label_study = wx.StaticText(self, wx.ID_ANY, "Study Instance UID:")
        sizer_study.Add(self.label_study, 0, 0, 0)
        sizer_study.Add(self.gauge_study, 0, wx.EXPAND, 0)
        sizer_progress.Add(sizer_study, 0, wx.ALL | wx.EXPAND, 5)
        self.label_calculation = wx.StaticText(self, wx.ID_ANY, "Calculation: DVH")
        sizer_calculation.Add(self.label_calculation, 0, 0, 0)
        self.label_structure = wx.StaticText(self, wx.ID_ANY, "Structure: Name (1 of 50)")
        sizer_calculation.Add(self.label_structure, 0, 0, 0)
        sizer_calculation.Add(self.gauge_calculation, 0, wx.EXPAND, 0)
        sizer_progress.Add(sizer_calculation, 0, wx.ALL | wx.EXPAND, 10)
        sizer_wrapper.Add(sizer_progress, 0, wx.EXPAND | wx.ALL, 5)
        self.label_elapsed_time = wx.StaticText(self, wx.ID_ANY, "Elapsed time:")
        sizer_time_cancel.Add(self.label_elapsed_time, 1, wx.EXPAND | wx.ALL, 5)
        sizer_time_cancel.Add(self.button_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_time_cancel, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def close(self):
        self.Destroy()

    def update_patient(self, msg):
        self.label_study_counter.SetLabelText("Study %s of %s" % (msg['study_number'], msg['study_total']))
        self.label_patient.SetLabelText("Patient: %s" % msg['patient_name'])
        self.label_study.SetLabelText("Study Instance UID: %s" % msg['uid'])
        self.gauge_study.SetValue(msg['progress'])

    def update_calculation(self, msg):
        self.label_calculation.SetLabelText("Calculation: %s" % msg['calculation'])
        self.label_structure.SetLabelText("Structure (%s of %s): %s" %
                                          (msg['roi_num'], msg['roi_total'], msg['roi_name']))
        self.gauge_calculation.SetValue(msg['progress'])

    def update_elapsed_time(self):
        elapsed_time = get_elapsed_time(self.start_time, datetime.now())
        self.label_elapsed_time.SetLabelText("Elapsed Time: %s" % elapsed_time)


class ImportWorker(Thread):
    def __init__(self, data, checked_uids):
        """
        :param data: parased dicom data
        :type data: dict of DICOM_Parser
        """
        Thread.__init__(self)
        self.data = data
        self.checked_uids = checked_uids
        # self.calculations = {"PTV Distances",
        #                      "PTV Overlap",
        #                      "ROI Centroid",
        #                      "ROI Spread",
        #                      "ROI Cross-Section",
        #                      "OAR-PTV Centroid Distance",
        #                      "Beam Complexities",
        #                      "Plan Complexities"}
        self.start()  # start the thread

    def run(self):

        study_total = len(self.checked_uids)
        for study_counter, uid in enumerate(self.checked_uids):
            if DVH_SQL().is_uid_imported(self.data[uid].study_instance_uid_to_be_imported):
                print("WARNING: This Study Instance UID is already imported in Database. Skipping Import.")
                print("\t%s" % self.data[uid].study_instance_uid_to_be_imported)
            else:
                msg = {'patient_name': self.data[uid].patient_name,
                       'uid': self.data[uid].study_instance_uid_to_be_imported,
                       'progress': int(100 * study_counter / study_total),
                       'study_number': study_counter+1,
                       'study_total': study_total}
                wx.CallAfter(pub.sendMessage, "update_patient", msg=msg)
                wx.CallAfter(pub.sendMessage, "update_elapsed_time")
                self.import_study(uid)
        wx.CallAfter(pub.sendMessage, "close")

    def import_study(self, uid):
        dicom_rt_struct = dicomparser.DicomParser(self.data[uid].structure_file)
        structures = dicom_rt_struct.GetStructures()
        roi_name_map = {key: structures[key]['name'] for key in list(structures) if structures[key]['type'] != 'MARKER'}
        data_to_import = {'Plans': [self.data[uid].get_plan_row()],
                          'Rxs': self.data[uid].get_rx_rows(),
                          'Beams': self.data[uid].get_beam_rows(),
                          'DICOM_Files': [self.data[uid].get_dicom_file_row()],
                          'DVHs': []}

        post_import_rois = []
        roi_total = len(roi_name_map)
        ptvs = {key: [] for key in ['dvh', 'volume', 'index']}
        for roi_counter, roi_key in enumerate(list(roi_name_map)):
            msg = {'calculation': 'DVH',
                   'roi_num': roi_counter+1,
                   'roi_total': roi_total,
                   'roi_name': roi_name_map[roi_key],
                   'progress': int(100 * (roi_counter+1) / roi_total)}

            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
            wx.CallAfter(pub.sendMessage, "update_elapsed_time")
            dvh_row = self.data[uid].get_dvh_row(roi_key)
            if dvh_row:
                roi_type = dvh_row['roi_type'][0]
                roi_name = dvh_row['roi_name'][0]
                physician_roi = dvh_row['physician_roi'][0]

                if roi_type.startswith('PTV'):
                    ptvs['dvh'].append(dvh_row['dvh_string'][0])
                    ptvs['volume'].append(dvh_row['volume'][0])
                    ptvs['index'].append(len(data_to_import['DVHs']))

                data_to_import['DVHs'].append(dvh_row)

                if roi_type and roi_name and physician_roi:
                    if roi_type.lower() in ['organ', 'ctv', 'gtv']:
                        if not (physician_roi.lower() in ['uncategorized', 'ignored', 'external', 'skin'] or
                                roi_name.lower() in ['external', 'skin']):
                            post_import_rois.append(clean_name(roi_name_map[roi_key]))

        if ptvs['dvh']:
            ptv_order = rank_ptvs_by_D95(ptvs)
            for ptv_row, dvh_row_index in enumerate(ptvs['index']):
                data_to_import['DVHs'][dvh_row_index]['roi_type'][0] = "PTV%s" % (ptv_order[ptv_row]+1)

        self.push(data_to_import)

        self.move_files(uid)

        if ptvs['dvh']:
            self.post_import_calc('Centroid Distance to PTV', uid, post_import_rois,
                                  db_update.dist_to_ptv_centroids, db_update.get_treatment_volume_centroid(uid))

            self.post_import_calc('PTV Overlap Volume', uid, post_import_rois,
                                  db_update.treatment_volume_overlap, db_update.get_treatment_volume(uid))

            self.post_import_calc('Distances to PTV', uid, post_import_rois,
                                  db_update.min_distances, db_update.get_treatment_volume_coord(uid))
        else:
            print("WARNING: No PTV found for %s" % uid)
            print("\tSkipping PTV related calculations.")

    @staticmethod
    def push(data_to_import):
        cnx = DVH_SQL()
        for key in list(data_to_import):
            for row in data_to_import[key]:
                cnx.insert_row(key, row)
        cnx.close()

    @staticmethod
    def post_import_calc(title, uid, rois, func, pre_calc):
        roi_total = len(rois)
        for roi_counter, roi_name in enumerate(rois):
            msg = {'calculation': title,
                   'roi_num': roi_counter + 1,
                   'roi_total': roi_total,
                   'roi_name': roi_name,
                   'progress': int(100 * roi_counter / roi_total)}
            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
            func(uid, roi_name, pre_calc=pre_calc)

    def move_files(self, uid):
        files = [self.data[uid].plan_file,
                 self.data[uid].structure_file,
                 self.data[uid].dose_file]

        new_dir = join(self.data[uid].import_path, self.data[uid].mrn)
        move_files_to_new_path(files, new_dir)

        # remove old directory if empty
        for file in files:
            old_dir = dirname(file)
            if isdir(old_dir) and not listdir(old_dir):
                rmdir(old_dir)
