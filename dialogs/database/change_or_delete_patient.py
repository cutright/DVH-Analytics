import wx


class BaseClass(wx.Dialog):
    def __init__(self, text_input_1_label, text_input_2_label, ok_button_label, title, *args, **kw):
        wx.Dialog.__init__(self, None, title=title)

        self.text_input_1_label = text_input_1_label
        self.text_input_2_label = text_input_2_label

        self.combo_box_patient_identifier = wx.ComboBox(self, wx.ID_ANY, choices=["MRN", "Study Instance UID"], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.text_ctrl_1 = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ctrl_2 = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, ok_button_label)
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        # self.SetTitle("Title")
        self.text_ctrl_1.SetMinSize((365, 22))

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_new_value = wx.BoxSizer(wx.VERTICAL)
        sizer_value = wx.BoxSizer(wx.VERTICAL)
        sizer_patient_identifier = wx.BoxSizer(wx.HORIZONTAL)
        label_patient_identifier = wx.StaticText(self, wx.ID_ANY, "Patient Identifier:")
        sizer_patient_identifier.Add(label_patient_identifier, 0, wx.ALL, 5)
        sizer_patient_identifier.Add(self.combo_box_patient_identifier, 0, wx.TOP, 2)
        sizer_input.Add(sizer_patient_identifier, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        label_text_input_1 = wx.StaticText(self, wx.ID_ANY, self.text_input_1_label)
        sizer_value.Add(label_text_input_1, 0, wx.EXPAND | wx.ALL, 5)
        sizer_value.Add(self.text_ctrl_1, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_input.Add(sizer_value, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        label_text_input_2 = wx.StaticText(self, wx.ID_ANY, self.text_input_2_label)
        sizer_new_value.Add(label_text_input_2, 0, wx.EXPAND | wx.ALL, 5)
        sizer_new_value.Add(self.text_ctrl_2, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_input.Add(sizer_new_value, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_input, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 10)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()


class ChangePatientIdentifierDialog(BaseClass):
    def __init__(self, *args, **kw):
        BaseClass.__init__(self, 'Value:', 'New Value:', 'Change', "Change Patient Identifier")


class DeletePatientDialog(BaseClass):
    def __init__(self, *args, **kw):
        BaseClass.__init__(self, 'Patient Identifier:', 'Type "delete" to authorize:', 'Delete', "Delete Patient")
