import wx


class ReimportDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="Reimport from DICOM")

        self.text_ctrl_mrn = wx.TextCtrl(self, wx.ID_ANY, "")
        self.radio_box_delete_from_db = wx.RadioBox(self, wx.ID_ANY, "Current Data", choices=["Delete from DB", "Keep in DB"],
                                                    majorDimension=2, style=wx.RA_SPECIFY_ROWS)
        self.combo_box_study_date = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_uid = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_reimport = wx.Button(self, wx.ID_OK, "Reimport")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.radio_box_delete_from_db.SetSelection(0)
        self.combo_box_study_date.SetMinSize((200, 25))

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_input_date_uid = wx.BoxSizer(wx.HORIZONTAL)
        sizer_uid = wx.BoxSizer(wx.VERTICAL)
        sizer_input_date = wx.BoxSizer(wx.VERTICAL)
        sizer_input_mrn_db = wx.BoxSizer(wx.HORIZONTAL)
        sizer_mrn = wx.BoxSizer(wx.VERTICAL)
        label_mrn = wx.StaticText(self, wx.ID_ANY, "MRN:")
        sizer_mrn.Add(label_mrn, 0, wx.BOTTOM, 5)
        sizer_mrn.Add(self.text_ctrl_mrn, 0, wx.EXPAND | wx.RIGHT, 40)
        sizer_input_mrn_db.Add(sizer_mrn, 1, wx.TOP, 12)
        sizer_input_mrn_db.Add(self.radio_box_delete_from_db, 0, wx.ALL, 5)
        sizer_input.Add(sizer_input_mrn_db, 0, wx.EXPAND | wx.LEFT, 5)
        label_date = wx.StaticText(self, wx.ID_ANY, "Sim Study Date:")
        sizer_input_date.Add(label_date, 0, wx.BOTTOM, 5)
        sizer_input_date.Add(self.combo_box_study_date, 0, 0, 0)
        sizer_input_date_uid.Add(sizer_input_date, 0, wx.ALL | wx.EXPAND, 5)
        label_uid = wx.StaticText(self, wx.ID_ANY, "Study Instance UID:")
        sizer_uid.Add(label_uid, 0, wx.BOTTOM, 5)
        sizer_uid.Add(self.combo_box_uid, 0, wx.EXPAND, 0)
        sizer_input_date_uid.Add(sizer_uid, 1, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_input_date_uid, 0, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_input, 0, wx.ALL | wx.EXPAND, 5)
        sizer_ok_cancel.Add(self.button_reimport, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 5)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.SetMinSize((700, 190))
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()
