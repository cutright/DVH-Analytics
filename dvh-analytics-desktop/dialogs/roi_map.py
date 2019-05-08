import wx
from tools.roi_name_manager import DatabaseROIs


class PhysicianAdd(wx.Dialog):
    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None)

        self.roi_map = DatabaseROIs()

        self.text_ctrl_physician = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_box_copy_from = wx.ComboBox(self, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN)
        self.checkbox_institutional_mapping = wx.CheckBox(self, wx.ID_ANY, "Institutional Mapping")
        self.checkbox_variations = wx.CheckBox(self, wx.ID_ANY, "All Variations")
        self.button_OK = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetTitle("Add Physician to ROI Map")
        self.checkbox_institutional_mapping.SetValue(1)
        self.checkbox_variations.SetValue(1)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_include = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Include:"), wx.VERTICAL)
        sizer_copy_from = wx.BoxSizer(wx.VERTICAL)
        sizer_new_physician = wx.BoxSizer(wx.VERTICAL)
        label_new_physician = wx.StaticText(self, wx.ID_ANY, "New Physician:")
        sizer_new_physician.Add(label_new_physician, 0, wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_new_physician.Add(self.text_ctrl_physician, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_widgets.Add(sizer_new_physician, 1, wx.EXPAND | wx.TOP, 10)
        label_copy_from = wx.StaticText(self, wx.ID_ANY, "Copy From:")
        sizer_copy_from.Add(label_copy_from, 0, wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_copy_from.Add(self.combo_box_copy_from, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_widgets.Add(sizer_copy_from, 1, wx.EXPAND | wx.TOP, 10)
        sizer_include.Add(self.checkbox_institutional_mapping, 0, 0, 0)
        sizer_include.Add(self.checkbox_variations, 0, 0, 0)
        sizer_widgets.Add(sizer_include, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 10)
        sizer_ok_cancel.Add(self.button_OK, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
