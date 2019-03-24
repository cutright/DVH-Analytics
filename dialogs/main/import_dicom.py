import wx
import wx.adv
from db.dicom_importer import DICOM_Importer
from db.dicom_parser import DICOM_Parser
from os.path import isdir
from options import get_settings, parse_settings_file
from wx.lib.agw.customtreectrl import CustomTreeCtrl
from wx.lib.agw.customtreectrl import TR_AUTO_CHECK_CHILD, TR_AUTO_CHECK_PARENT, TR_DEFAULT_STYLE
from tools.utilities import datetime_to_date_string
from db.sql_connector import DVH_SQL


class ImportDICOM_Dialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        wx.Dialog.__init__(self, None, title='Import DICOM')

        abs_file_path = get_settings('import')
        start_path = parse_settings_file(abs_file_path)['inbox']

        self.SetSize((1250, 829))
        self.text_ctrl_directory = wx.TextCtrl(self, wx.ID_ANY, start_path, style=wx.TE_READONLY)
        self.button_browse = wx.Button(self, wx.ID_ANY, u"Browse…")
        self.checkbox_subfolders = wx.CheckBox(self, wx.ID_ANY, "Search within subfolders")
        self.panel_study_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.gauge = wx.Gauge(self, -1, 100)
        self.button_import = wx.Button(self, wx.ID_ANY, "Import")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.text_ctrl_mrn = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_mrn_1 = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
        self.checkbox_mrn_2 = wx.CheckBox(self, wx.ID_ANY, "If missing")
        self.text_ctrl_uid = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_uid_1 = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
        self.checkbox_uid_2 = wx.CheckBox(self, wx.ID_ANY, "If missing")
        self.datepicker_birthdate = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_birthdate_1 = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
        self.checkbox_birthdate_2 = wx.CheckBox(self, wx.ID_ANY, "If missing")
        self.datepicker_sim_study_date = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_sim_study_date_1 = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
        self.checkbox_sim_study_date_2 = wx.CheckBox(self, wx.ID_ANY, "If missing")
        cnx = DVH_SQL()
        choices = cnx.get_unique_values('Plans', 'physician')
        self.combo_box_physician = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN)
        self.checkbox_physician_1 = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
        self.checkbox_physician_2 = wx.CheckBox(self, wx.ID_ANY, "If missing")
        choices = cnx.get_unique_values('Plans', 'tx_site')
        cnx.close()
        self.combo_box_tx_site = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN)
        self.checkbox_tx_site_1 = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
        self.checkbox_tx_site_2 = wx.CheckBox(self, wx.ID_ANY, "If missing")
        self.text_ctrl_rx = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_rx_1 = wx.CheckBox(self, wx.ID_ANY, "Apply to all studies")
        self.checkbox_rx_2 = wx.CheckBox(self, wx.ID_ANY, "If missing")
        self.button_apply_plan_data = wx.Button(self, wx.ID_ANY, "Apply")
        self.panel_roi_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.combo_box_institutional_roi = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.combo_box_physician_roi = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.combo_box_roi_type = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.button_apply_roi = wx.Button(self, wx.ID_ANY, "Apply")

        styles = TR_AUTO_CHECK_CHILD | TR_AUTO_CHECK_PARENT | TR_DEFAULT_STYLE
        self.tree_ctrl_import = CustomTreeCtrl(self.panel_study_tree, wx.ID_ANY, agwStyle=styles)
        self.tree_ctrl_import.SetBackgroundColour(wx.WHITE)

        self.tree_ctrl_roi = CustomTreeCtrl(self.panel_roi_tree, wx.ID_ANY, agwStyle=styles)
        self.tree_ctrl_roi.SetBackgroundColour(wx.WHITE)
        self.tree_ctrl_roi_root = self.tree_ctrl_roi.AddRoot('RT Structures', ct_type=1)

        self.Bind(wx.EVT_BUTTON, self.on_browse, id=self.button_browse.GetId())
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_file_tree_select, id=self.tree_ctrl_import.GetId())

        self.__set_properties()
        self.__do_layout()

        self.dicom_dir = DICOM_Importer(start_path, self.tree_ctrl_import, self.tree_ctrl_roi, self.tree_ctrl_roi_root)
        self.parse_directory()

    def __set_properties(self):
        self.checkbox_subfolders.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                                 wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_subfolders.SetValue(1)

        self.checkbox_mrn_1.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_mrn_2.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_uid_1.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_uid_2.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_birthdate_1.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_birthdate_2.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_sim_study_date_1.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_sim_study_date_2.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_physician_1.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_physician_2.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_tx_site_1.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_tx_site_2.SetFont(
            wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_rx_1.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_rx_2.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_map_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_roi_map = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "ROI Mapping for Selected Study"), wx.VERTICAL)
        sizer_selected_roi = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Map for Selected ROI"), wx.VERTICAL)
        sizer_roi_type = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_institutional_roi = wx.BoxSizer(wx.VERTICAL)
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
        sizer_sim_study_date_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_birthdate = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_birthdate_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_uid = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_uid_checkbox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_mrn = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_mrn_checkbox = wx.BoxSizer(wx.HORIZONTAL)
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
        self.label_progress = wx.StaticText(self, wx.ID_ANY, "Progress: Status message")
        self.label_progress.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        sizer_progress.Add(self.label_progress, 1, 0, 0)
        sizer_progress.Add(self.gauge, 1, wx.LEFT | wx.EXPAND, 40)
        sizer_studies.Add(sizer_progress, 0, wx.EXPAND, 0)
        sizer_browse_and_tree.Add(sizer_studies, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer_main.Add(sizer_browse_and_tree, 1, wx.EXPAND, 0)

        label_mrn = wx.StaticText(self, wx.ID_ANY, "MRN:")
        sizer_mrn.Add(label_mrn, 0, 0, 0)
        sizer_mrn.Add(self.text_ctrl_mrn, 0, wx.EXPAND, 0)
        sizer_mrn_checkbox.Add(self.checkbox_mrn_1, 0, wx.RIGHT, 20)
        sizer_mrn_checkbox.Add(self.checkbox_mrn_2, 0, 0, 0)
        sizer_mrn.Add(sizer_mrn_checkbox, 1, wx.EXPAND, 0)

        sizer_plan_data.Add(sizer_mrn, 1, wx.ALL | wx.EXPAND, 5)
        label_uid = wx.StaticText(self, wx.ID_ANY, "Study Instance UID:")
        sizer_uid.Add(label_uid, 0, 0, 0)
        sizer_uid.Add(self.text_ctrl_uid, 0, wx.EXPAND, 0)
        sizer_uid_checkbox.Add(self.checkbox_uid_1, 0, wx.RIGHT, 20)
        sizer_uid_checkbox.Add(self.checkbox_uid_2, 0, 0, 0)
        sizer_uid.Add(sizer_uid_checkbox, 1, wx.EXPAND, 0)

        sizer_plan_data.Add(sizer_uid, 1, wx.ALL | wx.EXPAND, 5)
        label_birthdate = wx.StaticText(self, wx.ID_ANY, "Birthdate:")
        sizer_birthdate.Add(label_birthdate, 0, 0, 0)
        sizer_birthdate.Add(self.datepicker_birthdate, 0, 0, 0)
        sizer_birthdate_checkbox.Add(self.checkbox_birthdate_1, 0, wx.RIGHT, 20)
        sizer_birthdate_checkbox.Add(self.checkbox_birthdate_2, 0, 0, 0)
        sizer_birthdate.Add(sizer_birthdate_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_birthdate, 1, wx.ALL | wx.EXPAND, 5)

        label_sim_study_date = wx.StaticText(self, wx.ID_ANY, "Sim Study Date:")
        sizer_sim_study_date.Add(label_sim_study_date, 0, 0, 0)
        sizer_sim_study_date.Add(self.datepicker_sim_study_date, 0, 0, 0)
        sizer_sim_study_date_checkbox.Add(self.checkbox_sim_study_date_1, 0, wx.RIGHT, 20)
        sizer_sim_study_date_checkbox.Add(self.checkbox_sim_study_date_2, 0, 0, 0)
        sizer_sim_study_date.Add(sizer_sim_study_date_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_sim_study_date, 1, wx.ALL | wx.EXPAND, 5)

        label_physician = wx.StaticText(self, wx.ID_ANY, "Physician:")
        sizer_physician.Add(label_physician, 0, 0, 0)
        sizer_physician.Add(self.combo_box_physician, 0, 0, 0)
        sizer_physician_checkbox.Add(self.checkbox_physician_1, 0, wx.RIGHT, 20)
        sizer_physician_checkbox.Add(self.checkbox_physician_2, 0, 0, 0)
        sizer_physician.Add(sizer_physician_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_physician, 1, wx.ALL | wx.EXPAND, 5)

        label_tx_site = wx.StaticText(self, wx.ID_ANY, "Tx Site:")
        sizer_tx_site.Add(label_tx_site, 0, 0, 0)
        sizer_tx_site.Add(self.combo_box_tx_site, 0, wx.EXPAND, 0)
        sizer_tx_site_checkbox.Add(self.checkbox_tx_site_1, 0, wx.RIGHT, 20)
        sizer_tx_site_checkbox.Add(self.checkbox_tx_site_2, 0, 0, 0)
        sizer_tx_site.Add(sizer_tx_site_checkbox, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_tx_site, 1, wx.ALL | wx.EXPAND, 5)

        label_rx = wx.StaticText(self, wx.ID_ANY, "Rx Dose (Gy):")
        sizer_rx.Add(label_rx, 0, 0, 0)
        sizer_rx.Add(self.text_ctrl_rx, 0, 0, 0)
        sizer_checkbox_rx.Add(self.checkbox_rx_1, 0, wx.RIGHT, 20)
        sizer_checkbox_rx.Add(self.checkbox_rx_2, 0, 0, 0)
        sizer_rx.Add(sizer_checkbox_rx, 1, wx.EXPAND, 0)
        sizer_plan_data.Add(sizer_rx, 1, wx.ALL | wx.EXPAND, 5)
        sizer_plan_data.Add(self.button_apply_plan_data, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        sizer_plan_data_wrapper.Add(sizer_plan_data, 1, wx.ALL | wx.EXPAND, 10)
        sizer_main.Add(sizer_plan_data_wrapper, 1, wx.EXPAND, 0)
        sizer_roi_tree.Add(self.tree_ctrl_roi, 1, wx.ALL | wx.EXPAND, 0)
        self.panel_roi_tree.SetSizer(sizer_roi_tree)
        sizer_roi_map.Add(self.panel_roi_tree, 1, wx.EXPAND, 0)

        label_institutional_roi = wx.StaticText(self, wx.ID_ANY, "Institutional ROI:")
        sizer_institutional_roi.Add(label_institutional_roi, 0, 0, 0)
        sizer_institutional_roi.Add(self.combo_box_institutional_roi, 0, wx.EXPAND, 0)

        label_physician_roi = wx.StaticText(self, wx.ID_ANY, "Physician ROI:")
        sizer_physician_roi.Add(label_physician_roi, 0, 0, 0)
        sizer_physician_roi.Add(self.combo_box_physician_roi, 0, wx.EXPAND, 0)

        label_roi_type = wx.StaticText(self, wx.ID_ANY, "ROI Type:")
        sizer_roi_type.Add(label_roi_type, 0, 0, 0)
        sizer_roi_type.Add(self.combo_box_roi_type, 0, wx.EXPAND, 0)

        sizer_selected_roi.Add(sizer_institutional_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_selected_roi.Add(sizer_physician_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_selected_roi.Add(sizer_roi_type, 1, wx.ALL | wx.EXPAND, 5)
        sizer_selected_roi.Add(self.button_apply_roi, 0, wx.ALL | wx.EXPAND, 5)

        sizer_roi_map.Add(sizer_selected_roi, 0, wx.EXPAND, 0)
        sizer_roi_map_wrapper.Add(sizer_roi_map, 1, wx.ALL | wx.EXPAND, 10)

        sizer_main.Add(sizer_roi_map_wrapper, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        sizer_buttons.Add(self.button_import, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def parse_directory(self):
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
        self.gauge.Hide()

    def on_browse(self, evt):
        starting_dir = self.text_ctrl_directory.GetValue()
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

    def update_progress_message(self):
        self.label_progress.SetLabelText("Progress: %s Patients - %s Studies - %s Files" %
                                         (self.dicom_dir.count['patient'],
                                          self.dicom_dir.count['study'],
                                          self.dicom_dir.count['file']))

    def on_file_tree_select(self, evt):
        uid = self.get_file_tree_item_uid(evt.GetItem())
        if uid is not None:
            wait = wx.BusyCursor()
            self.dicom_dir.rebuild_tree_ctrl_rois(uid)
            self.tree_ctrl_roi.ExpandAll()
            data = DICOM_Parser(plan=self.dicom_dir.dicom_file_paths[uid]['rtplan']['file_path'],
                                structure=self.dicom_dir.dicom_file_paths[uid]['rtstruct']['file_path'],
                                dose=self.dicom_dir.dicom_file_paths[uid]['rtdose']['file_path'])

            self.text_ctrl_mrn.SetValue(data.mrn)
            self.text_ctrl_uid.SetValue(data.study_instance_uid)
            if data.birth_date is None or data.birth_date == '':
                self.datepicker_birthdate.SetValue('')
            else:
                self.datepicker_birthdate.SetValue(datetime_to_date_string(data.birth_date))
            if data.sim_study_date is None or data.sim_study_date == '':
                self.datepicker_sim_study_date.SetValue('')
            else:
                self.datepicker_sim_study_date.SetValue(datetime_to_date_string(data.sim_study_date))
            self.combo_box_physician.SetValue(data.physician)
            self.combo_box_tx_site.SetValue(data.tx_site)
            self.text_ctrl_rx.SetValue(str(data.rx_dose))
            del wait

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
