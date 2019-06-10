import wx
import wx.adv
from wx.lib.agw.customtreectrl import CustomTreeCtrl, TR_AUTO_CHECK_CHILD, TR_AUTO_CHECK_PARENT, TR_DEFAULT_STYLE
from datetime import date as datetime_obj, datetime
from dateutil.parser import parse as parse_date
from db import update as db_update
from db.sql_connector import DVH_SQL
from db.dicom_importer import DICOM_Importer
from db.dicom_parser import DICOM_Parser
from dialogs.main import DatePicker
from dialogs.roi_map import AddPhysician, AddPhysicianROI, AddROIType, RoiManager, ChangePlanROIName
from dicompylercore import dicomparser
from os.path import isdir, join, dirname
from os import listdir, rmdir
from paths import IMPORT_SETTINGS_PATH, parse_settings_file
from pubsub import pub
from tools.utilities import datetime_to_date_string, get_elapsed_time, move_files_to_new_path, rank_ptvs_by_D95,\
    set_msw_background_color
from tools.roi_name_manager import clean_name
from threading import Thread


# TODO: Provide methods to write over-rides to DICOM file
class ImportDICOM_Dialog(wx.Frame):
    def __init__(self, roi_map, options, inbox=None):
        wx.Frame.__init__(self, None, title='Import DICOM')

        set_msw_background_color(self)  # If windows, change the background color

        self.initial_inbox = inbox
        self.options = options

        with DVH_SQL() as cnx:
            cnx.initialize_database()

        self.SetSize((1350, 800))

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
        self.button_edit_sim_study_date = wx.Button(self, wx.ID_ANY, "Edit")
        self.button_edit_birth_date = wx.Button(self, wx.ID_ANY, "Edit")
        self.input['physician'].SetValue('')
        self.input['tx_site'].SetValue('')
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

        self.panel_roi_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.input_roi = {'physician': wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY),
                          'type': wx.ComboBox(self, wx.ID_ANY, choices=self.options.ROI_TYPES, style=wx.CB_DROPDOWN)}
        self.input_roi['type'].SetValue('')
        self.button_autodetect_targets = wx.Button(self, wx.ID_ANY, "Autodetect Target/Tumor ROIs")
        self.button_variation_manager = wx.Button(self, wx.ID_ANY, "ROI Manager")
        # TODO: Allow user to edit or delete DICOM ROI name/structure
        # self.button_manage_physician_roi = wx.Button(self, wx.ID_ANY, "Physician ROI Manager")
        # self.button_manage_roi_type = wx.Button(self, wx.ID_ANY, "Manage")

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

        self.is_all_data_parsed = False
        self.dicom_dir = None

        self.incomplete_studies = []

        self.terminate = {'status': False}  # used to terminate thread on cancel in Import Dialog

        self.run()

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
        # self.Bind(wx.EVT_TEXT, self.on_apply_roi, id=self.input_roi['type'].GetId())
        # self.Bind(wx.EVT_TEXT, self.on_apply_roi, id=self.input_roi['physician'].GetId())

        for key in ['birth_date', 'sim_study_date', 'physician', 'tx_site', 'rx_dose']:
            self.Bind(wx.EVT_CHECKBOX, self.on_check_apply_all, id=self.checkbox['%s_1' % key].GetId())
            self.Bind(wx.EVT_CHECKBOX, self.on_check_apply_all, id=self.checkbox['%s_2' % key].GetId())

        self.Bind(wx.EVT_BUTTON, self.on_edit_birth_date, id=self.button_edit_birth_date.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_edit_sim_study_date, id=self.button_edit_sim_study_date.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_add_physician, id=self.button_add_physician.GetId())

        self.Bind(wx.EVT_BUTTON, self.on_import, id=self.button_import.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=self.button_cancel.GetId())

        self.Bind(wx.EVT_BUTTON, self.on_autodetect_target, id=self.button_autodetect_targets.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_variation_manager, id=self.button_variation_manager.GetId())
        # self.Bind(wx.EVT_BUTTON, self.on_manage_physician_roi, id=self.button_manage_physician_roi.GetId())
        # self.Bind(wx.EVT_BUTTON, self.on_manage_roi_type, id=self.button_manage_roi_type.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.on_physician_roi_change, id=self.input_roi['physician'].GetId())
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_physician_roi_change, id=self.input_roi['physician'].GetId())

        # self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_roi_tree_double_click, id=self.tree_ctrl_roi.GetId())

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
        self.tree_ctrl_images = {'yes': self.image_list.Add(wx.Image("icons/iconfinder_ok-green_53916.png",
                                                                     wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                                 'no': self.image_list.Add(wx.Image("icons/iconfinder_ko-red_53948.png",
                                                                    wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())}
        self.tree_ctrl_roi.AssignImageList(self.image_list)

        self.button_cancel.SetToolTip("Changes to ROI Map will be disregarded.")
        self.button_import.SetToolTip("Save ROI Map changes and import checked studies.")

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
        sizer_rx.Add(self.label['rx_dose'], 0, 0, 0)
        sizer_rx.Add(self.input['rx_dose'], 0, 0, 0)
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
        sizer_roi_map.Add(self.button_autodetect_targets, 0, wx.EXPAND | wx.ALL, 5)
        sizer_roi_map.Add(self.button_variation_manager, 0, wx.EXPAND | wx.ALL, 5)
        # sizer_roi_map.Add(self.button_manage_physician_roi, 0, wx.EXPAND | wx.ALL, 5)

        self.label['physician_roi'] = wx.StaticText(self, wx.ID_ANY, "Physician's ROI Label:")
        sizer_physician_roi_with_add = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi.Add(self.label['physician_roi'], 0, 0, 0)
        sizer_physician_roi.Add(self.input_roi['physician'], 0, wx.EXPAND, 0)
        sizer_physician_roi_with_add.Add(sizer_physician_roi, 1, wx.EXPAND, 0)
        # sizer_physician_roi_with_add.Add(self.button_manage_physician_roi, 0, wx.TOP, 15)

        self.label['roi_type'] = wx.StaticText(self, wx.ID_ANY, "ROI Type:")
        sizer_roi_type_with_add = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_type.Add(self.label['roi_type'], 0, 0, 0)
        sizer_roi_type.Add(self.input_roi['type'], 0, wx.EXPAND, 0)
        sizer_roi_type_with_add.Add(sizer_roi_type, 1, wx.EXPAND, 0)
        # sizer_roi_type_with_add.Add(self.button_manage_roi_type, 0, wx.TOP, 15)

        sizer_selected_roi.Add(sizer_physician_roi_with_add, 1, wx.ALL | wx.EXPAND, 5)
        sizer_selected_roi.Add(sizer_roi_type_with_add, 1, wx.ALL | wx.EXPAND, 5)

        sizer_roi_map.Add(sizer_selected_roi, 0, wx.EXPAND, 0)
        sizer_roi_map_wrapper.Add(sizer_roi_map, 1, wx.ALL | wx.EXPAND, 10)

        sizer_main.Add(sizer_roi_map_wrapper, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        self.label_warning = wx.StaticText(self, wx.ID_ANY, '')
        sizer_warning.Add(self.label_warning, 1, wx.EXPAND, 0)

        sizer_warning_buttons.Add(sizer_warning, 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_import, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_warning_buttons.Add(sizer_buttons, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_warning_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def run(self):
        self.Show()
        if self.initial_inbox is None or not isdir(self.initial_inbox):
            self.initial_inbox = ''
        self.text_ctrl_directory.SetValue(self.initial_inbox)
        self.dicom_dir = DICOM_Importer(self.initial_inbox, self.tree_ctrl_import, self.tree_ctrl_roi,
                                        self.tree_ctrl_roi_root, self.tree_ctrl_images, self.roi_map)
        self.parse_directory()

    def on_cancel(self, evt):
        self.roi_map.import_from_file()  # reload from file, ignore changes
        self.Destroy()

    def parse_directory(self):
        # TODO: Thread this function (parse_directory)
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
        self.tree_ctrl_import.CheckItem(self.dicom_dir.root_files, True)
        # self.text_ctrl_directory

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
                                            self.tree_ctrl_roi, self.tree_ctrl_roi_root, self.tree_ctrl_images,
                                            self.roi_map, search_subfolders=self.checkbox_subfolders.GetValue())
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
        self.tree_ctrl_roi.SelectItem(self.tree_ctrl_roi_root, True)
        if uid in list(self.parsed_dicom_data) and self.parsed_dicom_data[uid].validation['complete_file_set']:
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
                self.input['physician'].SetValue(data.physician)
                self.input['tx_site'].SetValue(data.tx_site)
                self.input['rx_dose'].SetValue(str(data.rx_dose))
                self.dicom_dir.check_mapped_rois(data.physician)
                del wait
                self.update_physician_roi_choices()
                self.enable_inputs()
        else:
            self.clear_plan_data()
            self.disable_inputs()
            self.selected_uid = None
            self.tree_ctrl_roi.DeleteChildren(self.dicom_dir.root_rois)
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
            roi_key = self.dicom_dir.roi_name_map[self.selected_roi]['key']
            uid = self.selected_uid
            roi_type = self.parsed_dicom_data[uid].get_roi_type(roi_key)
            self.input_roi['physician'].SetValue(physician_roi)
            self.update_physician_roi_choices(physician_roi)
            self.input_roi['type'].SetValue(roi_type)
        else:
            self.input_roi['physician'].SetValue('')
            self.input_roi['type'].SetValue('')
        self.allow_input_roi_apply = True
        self.update_input_roi_physician_enable()

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
        self.button_autodetect_targets.Disable()
        self.button_variation_manager.Disable()
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
        self.button_autodetect_targets.Enable()
        self.button_variation_manager.Enable()
        self.button_delete_study.Enable()
        self.button_add_physician.Enable()
        for check_box in self.checkbox.values():
            check_box.Enable()

    def disable_roi_inputs(self):
        # self.button_autodetect_targets.Disable()
        # self.button_variation_manager.Disable()
        # self.button_manage_physician_roi.Disable()
        # self.button_manage_roi_type.Disable()
        for input_obj in self.input_roi.values():
            input_obj.Disable()

    def enable_roi_inputs(self):
        # self.button_autodetect_targets.Enable()
        # self.button_variation_manager.Enable()
        # self.button_manage_physician_roi.Enable()
        # self.button_manage_roi_type.Enable()
        for input_obj in self.input_roi.values():
            if input_obj not in {self.input_roi['physician'], self.input_roi['type']}:
                input_obj.Enable()

    def update_physician_roi_choices(self, physician_roi=None):
        physician = self.input['physician'].GetValue()
        if self.roi_map.is_physician(physician):
            choices = self.roi_map.get_physician_rois(physician)
        else:
            choices = []
        if choices and physician_roi in {'uncategorized'}:
            choices = list(set(choices) - set(self.dicom_dir.get_used_physician_rois(physician)))
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
            key = self.dicom_dir.roi_name_map[self.selected_roi]['key']
            roi_type_over_ride[key] = self.input_roi['type'].GetValue()
            self.validate(uid=self.selected_uid)
            self.update_warning_label()
            self.dicom_dir.check_mapped_rois()

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
        ImportWorker(self.parsed_dicom_data, list(self.dicom_dir.checked_studies),
                     self.checkbox_include_uncategorized.GetValue(), self.terminate)
        dlg = ImportStatusDialog(self.terminate)
        dlg.Show()
        self.Close()

    def parse_dicom_data(self):
        # TODO: Thread this function (parse_dicom_data)
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
                if file_paths['rtplan']['file_path'] and file_paths['rtstruct']['file_path'] and \
                        file_paths['rtdose']['file_path']:
                    self.parsed_dicom_data[uid] = DICOM_Parser(plan=file_paths['rtplan']['file_path'],
                                                               structure=file_paths['rtstruct']['file_path'],
                                                               dose=file_paths['rtdose']['file_path'],
                                                               global_plan_over_rides=self.global_plan_over_rides,
                                                               roi_map=self.roi_map)

            self.gauge.SetValue(int(100 * (study_counter+1) / study_total))
            wx.Yield()

        self.gauge.Hide()
        self.label_progress.SetLabelText("All %s studies parsed" % study_total)

        del wait

        self.is_all_data_parsed = True

    def validate(self, uid=None):
        if self.is_all_data_parsed:
            wait = wx.BusyCursor()
            if not uid:
                nodes = self.dicom_dir.study_nodes
            else:
                nodes = {uid: self.dicom_dir.study_nodes[uid]}
            for uid, node in nodes.items():
                if uid in list(self.parsed_dicom_data):
                    validation = self.parsed_dicom_data[uid].validation
                    failed_keys = {key for key, value in validation.items() if not value['status']}
                else:
                    failed_keys = {'complete_file_set'}
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
            del wait

    def update_warning_label(self):
        msg = ''
        if self.selected_uid:
            if self.selected_uid in list(self.parsed_dicom_data):
                validation = self.parsed_dicom_data[self.selected_uid].validation
                failed_keys = {key for key, value in validation.items() if not value['status']}
                if failed_keys:
                    if 'complete_file_set' in failed_keys:
                        msg = "WARNING: %s" % validation['complete_file_set']['message']
                        if self.selected_uid not in self.incomplete_studies:
                            self.incomplete_studies.append(self.selected_uid)
                    else:
                        msg = "WARNING: %s" % ' '.join([validation[key]['message'] for key in failed_keys])
            else:
                msg = "WARNING: Incomplete Fileset. RT Plan, Dose, and Structure required."
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
        dlg = DatePicker(initial_date=self.input[key].GetValue(),
                         title=key.replace('_', ' ').title())
        res = dlg.ShowModal()
        if res == wx.ID_OK or (res == wx.ID_CANCEL and dlg.none):
            self.input[key].SetValue(dlg.date)
        dlg.Destroy()

        self.validate(self.selected_uid)
        self.update_warning_label()

    def on_autodetect_target(self, evt):
        for roi in self.dicom_dir.roi_name_map.values():
            self.parsed_dicom_data[self.selected_uid].autodetect_target_roi_type(roi['key'])
        self.update_roi_inputs()
        self.validate(self.selected_uid)
        self.update_warning_label()

    def on_variation_manager(self, evt):
        RoiManager(self, self.roi_map, self.input['physician'].GetValue(), self.input_roi['physician'].GetValue())
        self.update_physician_choices(keep_old_physician=True)
        self.update_physician_roi_choices()
        self.update_roi_inputs()
        self.dicom_dir.check_mapped_rois(self.input['physician'].GetValue())
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

        self.dicom_dir.check_mapped_rois(physician)
        self.update_input_roi_physician_enable()

    def on_roi_tree_double_click(self, evt):
        ChangePlanROIName(self.tree_ctrl_roi,
                          evt.GetItem(),
                          self.input['mrn'].GetValue(),
                          self.input['study_instance_uid'].GetValue(),
                          self.parsed_dicom_data[self.input['study_instance_uid'].GetValue()])
        # self.dicom_dir = self.parsed_dicom_data[self.input['study_instance_uid'].GetValue()]
        # self.dicom_dir.check_mapped_rois(self.input['physician'].GetValue())


class ImportStatusDialog(wx.Dialog):
    def __init__(self, terminate):
        wx.Dialog.__init__(self, None)
        self.gauge_study = wx.Gauge(self, wx.ID_ANY, 100)
        self.gauge_calculation = wx.Gauge(self, wx.ID_ANY, 100)
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

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
        sizer_progress.Add(sizer_calculation, 0, wx.ALL | wx.EXPAND, 5)
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

    def set_terminate(self, evt):
        self.terminate['status'] = True
        self.close()


class ImportWorker(Thread):
    def __init__(self, data, checked_uids, import_uncategorized, terminate):
        """
        :param data: parased dicom data
        :type data: dict of DICOM_Parser
        """
        Thread.__init__(self)

        self.data = data
        self.checked_uids = checked_uids
        self.import_uncategorized = import_uncategorized
        self.terminate = terminate

        with DVH_SQL() as cnx:
            self.last_import_time = cnx.now  # use psql time rather than CPU since time stamps in DB are based on psql

        self.start()  # start the thread

    def run(self):
        with DVH_SQL() as cnx:
            study_total = len(self.checked_uids)
            for study_counter, uid in enumerate(self.checked_uids):
                if uid in list(self.data):
                    if cnx.is_uid_imported(self.data[uid].study_instance_uid_to_be_imported):
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
                        if self.terminate['status']:
                            self.delete_partially_updated_study()
                            return
                else:
                    print('WARNING: This study could not be parsed. Skipping import. '
                          'Did you supply RT Structure, Dose, and Plan?')
                    print('\tStudy Instance UID: %s' % uid)

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

        if not self.import_uncategorized:  # remove uncategorized ROIs unless this is checked
            ignore_me = []
            for roi_key in list(roi_name_map):
                if self.data[uid].get_physician_roi(roi_key) == 'uncategorized' and \
                        self.data[uid].get_roi_type(roi_key) not in {'GTV', 'CTV', 'ITV', 'PTV'}:
                    ignore_me.append(roi_key)
            for roi_key in ignore_me:
                roi_name_map.pop(roi_key)

        post_import_rois = []
        roi_total = len(roi_name_map)
        ptvs = {key: [] for key in ['dvh', 'volume', 'index']}
        for roi_counter, roi_key in enumerate(list(roi_name_map)):
            if self.terminate['status']:
                return
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
                        if not (physician_roi.lower() in ['uncategorized', 'ignored', 'external', 'skin', 'body'] or
                                roi_name.lower() in ['external', 'skin', 'body']):
                            post_import_rois.append(clean_name(roi_name_map[roi_key]))

        if ptvs['dvh']:
            ptv_order = rank_ptvs_by_D95(ptvs)
            for ptv_row, dvh_row_index in enumerate(ptvs['index']):
                data_to_import['DVHs'][dvh_row_index]['roi_type'][0] = "PTV%s" % (ptv_order[ptv_row]+1)

        self.push(data_to_import)  # Must push data before processing post import calculations

        if ptvs['dvh']:
            tv = db_update.get_treatment_volume(uid)
            self.post_import_calc('PTV Overlap Volume', uid, post_import_rois,
                                  db_update.treatment_volume_overlap, tv)
            if self.terminate['status']:
                return

            tv_centroid = db_update.get_treatment_volume_centroid(tv)
            self.post_import_calc('Centroid Distance to PTV', uid, post_import_rois,
                                  db_update.dist_to_ptv_centroids, tv_centroid)
            if self.terminate['status']:
                return

            tv_coord = db_update.get_treatment_volume_coord(tv)
            self.post_import_calc('Distances to PTV', uid, post_import_rois,
                                  db_update.min_distances, tv_coord)
            if self.terminate['status']:
                return

            msg = {'calculation': 'Total Treatment Volume Statistics',
                   'roi_num': 0,
                   'roi_total': 1,
                   'roi_name': 'PTV',
                   'progress': 0}
            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)
            db_update.update_ptv_data(tv, uid)
            msg['roi_num'], msg['progress'] = 1, 100
            wx.CallAfter(pub.sendMessage, "update_calculation", msg=msg)

        else:
            print("WARNING: No PTV found for %s" % uid)
            print("\tSkipping PTV related calculations.")

        self.move_files(uid)

        with DVH_SQL() as cnx:
            self.last_import_time = cnx.now

    @staticmethod
    def push(data_to_import):
        with DVH_SQL() as cnx:
            for key in list(data_to_import):
                for row in data_to_import[key]:
                    cnx.insert_row(key, row)

    def post_import_calc(self, title, uid, rois, func, pre_calc):
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

    def move_files(self, uid):
        print('moving files for %s' % uid)
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

    def delete_partially_updated_study(self):
        with DVH_SQL() as cnx:
            cnx.delete_rows("import_time_stamp > '%s'::date" % self.last_import_time)
