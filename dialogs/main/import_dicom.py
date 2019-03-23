import wx
from db.dicom_importer import DICOM_Directory
from os.path import isdir
from options import get_settings, parse_settings_file
from wx.lib.agw.customtreectrl import CustomTreeCtrl
from wx.lib.agw.customtreectrl import TR_AUTO_CHECK_CHILD, TR_AUTO_CHECK_PARENT, TR_DEFAULT_STYLE


class ImportDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        wx.Dialog.__init__(self, None, title='Import DICOM')

        abs_file_path = get_settings('import')
        start_path = parse_settings_file(abs_file_path)['inbox']

        self.SetSize((650, 600))
        self.text_ctrl_directory = wx.TextCtrl(self, wx.ID_ANY, start_path, style=wx.TE_READONLY)
        self.button_browse = wx.Button(self, wx.ID_ANY, u"Browse…")
        self.checkbox_subfolders = wx.CheckBox(self, wx.ID_ANY, "Search within subfolders")
        self.panel_study_tree = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.gauge = wx.Gauge(self, -1, 100)
        self.button_import_all = wx.Button(self, wx.ID_ANY, "Import")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.tree_ctrl_import = CustomTreeCtrl(self.panel_study_tree, wx.ID_ANY, agwStyle=TR_AUTO_CHECK_CHILD | TR_AUTO_CHECK_PARENT | TR_DEFAULT_STYLE)
        self.tree_ctrl_import.SetBackgroundColour(wx.WHITE)

        self.Bind(wx.EVT_BUTTON, self.on_browse, id=self.button_browse.GetId())
        # self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_select, id=self.tree_ctrl_import.GetId())

        self.__set_properties()
        self.__do_layout()

        self.dicom_dir = DICOM_Directory(start_path, self.tree_ctrl_import)
        self.parse_directory()

    def __set_properties(self):
        self.checkbox_subfolders.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                                 wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.checkbox_subfolders.SetValue(1)

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_db_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_studies = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Studies"), wx.VERTICAL)
        sizer_progress = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dicom_import_directory = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY,
                                                                      "DICOM Import Directory"), wx.VERTICAL)
        sizer_directory = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6.Add(self.text_ctrl_directory, 1, wx.ALL | wx.EXPAND, 5)
        sizer_6.Add(self.button_browse, 0, wx.ALL, 5)
        sizer_directory.Add(sizer_6, 1, wx.EXPAND, 0)
        sizer_directory.Add(self.checkbox_subfolders, 0, wx.LEFT, 10)
        sizer_dicom_import_directory.Add(sizer_directory, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_dicom_import_directory, 0, wx.ALL | wx.EXPAND, 10)
        label_note = wx.StaticText(self, wx.ID_ANY, "NOTE: Only the latest files will be used for a "
                                                    "given study instance UID, all others ignored.")
        label_note.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        sizer_studies.Add(label_note, 0, wx.ALL, 5)
        sizer_studies.Add(self.panel_study_tree, 1, wx.ALL | wx.EXPAND, 5)
        sizer_db_tree.Add(self.tree_ctrl_import, 1, wx.EXPAND, 0)
        self.panel_study_tree.SetSizer(sizer_db_tree)
        self.label_progress = wx.StaticText(self, wx.ID_ANY, "Progress: Status message")
        self.label_progress.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        sizer_progress.Add(self.label_progress, 1, 0, 0)
        sizer_progress.Add(self.gauge, 1, wx.ALL, 5)
        sizer_studies.Add(sizer_progress, 0, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_studies, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sizer_buttons.Add(self.button_import_all, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def parse_directory(self):
        self.gauge.Show()
        file_count = self.dicom_dir.file_count
        self.dicom_dir.initialize_root()
        self.tree_ctrl_import.Expand(self.dicom_dir.root)
        while self.dicom_dir.current_index < file_count:
            self.dicom_dir.append_next_file_to_tree()
            self.gauge.SetValue(int(100 * self.dicom_dir.current_index / file_count))
            self.update_progress_message()
            self.tree_ctrl_import.ExpandAll()
            wx.Yield()
        self.gauge.Hide()
        # self.dicom_dir.build_wx_tree_ctrl(self.tree_ctrl_db)

    def on_browse(self, evt):
        starting_dir = self.text_ctrl_directory.GetValue()
        if not isdir(starting_dir):
            starting_dir = ""
        dlg = wx.DirDialog(self, "Select inbox directory", starting_dir, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.text_ctrl_directory.SetValue(dlg.GetPath())
            self.dicom_dir = DICOM_Directory(self.text_ctrl_directory.GetValue(), self.tree_ctrl_import,
                                             self.checkbox_subfolders.GetValue())
            self.parse_directory()
        dlg.Destroy()

    def update_progress_message(self):
        self.label_progress.SetLabelText("Progress: %s Patients - %s Studies - %s Files" %
                                         (self.dicom_dir.count['patient'],
                                          self.dicom_dir.count['study'],
                                          self.dicom_dir.count['file']))

    # def on_tree_select(self, evt):
    #     print(self.tree_ctrl_import.IsItemChecked(evt.GetItem()))
    #     self.tree_ctrl_import.AutoCheckChild(evt.GetItem(), 1)
    #     self.tree_ctrl_import.AutoCheckParent(evt.GetItem(), 1)
