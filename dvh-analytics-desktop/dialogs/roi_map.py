import wx
from models.datatable import DataTable
from tools.errors import ROIVariationErrorDialog
from tools.utilities import get_selected_listctrl_items
from tools.roi_name_manager import ROIVariationError


class AddPhysician(wx.Dialog):
    def __init__(self, roi_map, initial_physician=None):
        wx.Dialog.__init__(self, None)

        self.roi_map = roi_map
        self.initial_physician = initial_physician

        self.text_ctrl_physician = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_box_copy_from = wx.ComboBox(self, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN)
        # self.checkbox_institutional_mapping = wx.CheckBox(self, wx.ID_ANY, "Institutional Mapping")
        self.checkbox_variations = wx.CheckBox(self, wx.ID_ANY, "Include Variations")
        self.button_OK = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Add Physician to ROI Map")
        # self.checkbox_institutional_mapping.SetValue(1)
        self.checkbox_variations.SetValue(1)
        if self.initial_physician:
            self.text_ctrl_physician.SetValue(self.initial_physician)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        # sizer_include = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Include:"), wx.VERTICAL)
        sizer_copy_from = wx.BoxSizer(wx.VERTICAL)
        sizer_new_physician = wx.BoxSizer(wx.VERTICAL)
        label_new_physician = wx.StaticText(self, wx.ID_ANY, "New Physician:")
        sizer_new_physician.Add(label_new_physician, 0, wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_new_physician.Add(self.text_ctrl_physician, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_widgets.Add(sizer_new_physician, 1, wx.EXPAND | wx.TOP, 10)
        label_copy_from = wx.StaticText(self, wx.ID_ANY, "Copy From:")
        sizer_copy_from.Add(label_copy_from, 0, wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_copy_from.Add(self.combo_box_copy_from, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_widgets.Add(sizer_copy_from, 1, wx.EXPAND | wx.TOP, 10)
        # sizer_include.Add(self.checkbox_institutional_mapping, 0, 0, 0)
        # sizer_include.Add(self.checkbox_variations, 0, 0, 0)
        sizer_widgets.Add(self.checkbox_variations, 0, wx.EXPAND | wx.ALL, 10)
        sizer_wrapper.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 10)
        sizer_ok_cancel.Add(self.button_OK, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def action(self):
        self.roi_map.copy_physician(self.text_ctrl_physician.GetValue(),
                                    copy_from=self.combo_box_copy_from.GetValue(),
                                    include_variations=self.checkbox_variations.GetValue())

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()


class VariationManager(wx.Dialog):
    def __init__(self, parent, roi_map, physician, physician_roi):
        wx.Dialog.__init__(self, parent)
        self.parent = parent
        self.roi_map = roi_map
        self.initial_physician = physician
        self.initial_physician_roi = physician_roi

        self.combo_box_physician = wx.ComboBox(self, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_physician_roi = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.list_ctrl_variations = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_NO_HEADER | wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.button_select_all = wx.Button(self, wx.ID_ANY, "Select All")
        self.button_deselect_all = wx.Button(self, wx.ID_ANY, "Deselect All")
        self.button_add = wx.Button(self, wx.ID_ANY, "Add")
        self.button_delete = wx.Button(self, wx.ID_ANY, "Delete")
        self.button_move = wx.Button(self, wx.ID_ANY, "Move")
        self.button_dismiss = wx.Button(self, wx.ID_CANCEL, "Dismiss")

        self.columns = ['Variations']
        self.data_table = DataTable(self.list_ctrl_variations, columns=self.columns, widths=[400])

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()

        self.run()

    def __set_properties(self):
        self.SetTitle("Variation Manager")
        self.combo_box_physician.SetValue(self.initial_physician)
        self.update_physician_rois()
        self.combo_box_physician_roi.SetValue(self.initial_physician_roi)
        self.update_variations()

    def __do_bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.physician_ticker, id=self.combo_box_physician.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.physician_roi_ticker, id=self.combo_box_physician_roi.GetId())
        self.Bind(wx.EVT_BUTTON, self.select_all, id=self.button_select_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.deselect_all, id=self.button_deselect_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.add_variation, id=self.button_add.GetId())
        self.Bind(wx.EVT_BUTTON, self.move_variations, id=self.button_move.GetId())
        self.Bind(wx.EVT_BUTTON, self.delete_variations, id=self.button_delete.GetId())

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_select = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        sizer_select_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_variations = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_physician = wx.BoxSizer(wx.VERTICAL)
        label_physician = wx.StaticText(self, wx.ID_ANY, "Physician:")
        sizer_physician.Add(label_physician, 0, 0, 0)
        sizer_physician.Add(self.combo_box_physician, 0, wx.EXPAND, 0)
        sizer_select.Add(sizer_physician, 0, wx.ALL | wx.EXPAND, 5)
        label_physician_roi = wx.StaticText(self, wx.ID_ANY, "Physician ROI:")
        sizer_physician_roi.Add(label_physician_roi, 0, 0, 0)
        sizer_physician_roi.Add(self.combo_box_physician_roi, 0, wx.EXPAND, 0)
        sizer_select.Add(sizer_physician_roi, 0, wx.ALL | wx.EXPAND, 5)
        label_variations = wx.StaticText(self, wx.ID_ANY, "Variations:")
        sizer_variations.Add(label_variations, 0, 0, 0)
        sizer_variations.Add(self.list_ctrl_variations, 1, wx.ALL | wx.EXPAND, 0)
        sizer_select.Add(sizer_variations, 0, wx.ALL | wx.EXPAND, 5)
        sizer_select_buttons.Add(self.button_select_all, 0, wx.ALL, 5)
        sizer_select_buttons.Add(self.button_deselect_all, 0, wx.ALL, 5)
        sizer_select.Add(sizer_select_buttons, 0, wx.ALIGN_CENTER | wx.ALL, 0)
        sizer_wrapper.Add(sizer_select, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_add, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_delete, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_move, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_dismiss, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def run(self):
        self.ShowModal()
        self.Destroy()

    def update_physician_rois(self):
        new_physician_rois = self.roi_map.get_physician_rois(self.physician)
        self.combo_box_physician_roi.Clear()
        self.combo_box_physician_roi.AppendItems(new_physician_rois)
        if self.physician_roi not in new_physician_rois:
            self.combo_box_physician_roi.SetValue(new_physician_rois[0])

    def update_variations(self):
        self.data_table.set_data(self.variation_table_data, self.columns)

    def physician_ticker(self, evt):
        self.update_physician_rois()
        self.update_variations()

    def physician_roi_ticker(self, evt):
        self.update_variations()

    @property
    def physician(self):
        return self.combo_box_physician.GetValue()

    @property
    def physician_roi(self):
        return self.combo_box_physician_roi.GetValue()

    @property
    def variations(self):
        return self.roi_map.get_variations(self.combo_box_physician.GetValue(),
                                           self.combo_box_physician_roi.GetValue())

    @property
    def variation_table_data(self):
        return {'Variations': self.variations}

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl_variations)

    @property
    def selected_values(self):
        return [self.list_ctrl_variations.GetItem(i, 0).GetText() for i in self.selected_indices]

    @property
    def variation_count(self):
        return len(self.variations)

    def select_all(self, evt):
        self.apply_global_selection()

    def deselect_all(self, evt):
        self.apply_global_selection(on=0)

    def apply_global_selection(self, on=1):
        for i in range(self.variation_count):
            self.list_ctrl_variations.Select(i, on=on)

    def delete_variations(self, evt):
        self.roi_map.delete_variations(self.physician, self.physician_roi, self.selected_values)
        self.update_variations()

    def add_variation(self, evt):
        dlg = AddVariationDialog(self.parent, self.physician, self.physician_roi)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            try:
                self.roi_map.add_variation(self.physician, self.physician_roi, dlg.text_ctrl_variation.GetValue())
                self.update_variations()
            except ROIVariationError as e:
                ROIVariationErrorDialog(self.parent, e)
        dlg.Destroy()

    def move_variations(self, evt):
        # variations = self.variations
        # self.roi_map.delete_variations(self.physician, self.physician_roi, self.selected_values)
        # for variation in self.variations:
        #     pass
        choices = [roi for roi in self.roi_map.get_physician_rois(self.physician) if roi != self.physician_roi]
        MoveVariationDialog(self, choices)


class AddVariationDialog(wx.Dialog):
    def __init__(self, parent, physician, physician_roi):
        wx.Dialog.__init__(self, parent)
        self.physician = physician
        self.physician_roi = physician_roi
        self.text_ctrl_variation = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetTitle("Add Variation to %s for %s" % (self.physician_roi, self.physician))
        self.text_ctrl_variation.SetMinSize((300, 22))

    def __do_layout(self):
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_variation = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        label_variation = wx.StaticText(self, wx.ID_ANY, "New variation:")
        sizer_variation.Add(label_variation, 0, 0, 0)
        sizer_variation.Add(self.text_ctrl_variation, 0, wx.EXPAND, 0)
        sizer_frame.Add(sizer_variation, 0, wx.EXPAND, 0)
        sizer_buttons.Add(self.button_ok, 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_cancel, 1, wx.ALL | wx.EXPAND, 5)
        sizer_frame.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_frame)
        sizer_frame.Fit(self)
        self.Layout()
        self.Center()


class MoveVariationDialog(wx.Dialog):
    def __init__(self, parent, choices):
        wx.Dialog.__init__(self, parent)
        self.choices = choices
        self.combo_box = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Move Variations")
        self.combo_box.SetValue(self.choices[0])

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL)
        label_physician_roi = wx.StaticText(self, wx.ID_ANY, "Move to Physician ROI:")
        sizer_input.Add(label_physician_roi, 0, 0, 0)
        sizer_input.Add(self.combo_box, 0, 0, 0)
        sizer_wrapper.Add(sizer_input, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sizer_buttons.Add(self.button_ok, 0, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        pass


class AddPhysicianROI(wx.Dialog):
    def __init__(self, parent, physician, institutional_rois):
        wx.Dialog.__init__(self, parent)
        self.SetSize((500, 135))

        self.physician = physician
        self.institutional_rois = institutional_rois
        self.text_ctrl_physician_roi = wx.TextCtrl(self, wx.ID_ANY, "")
        self.combo_box_institutional_roi = wx.ComboBox(self, wx.ID_ANY, choices=institutional_rois,
                                                       style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Add Physician ROI for %s" % self.physician)
        self.text_ctrl_physician_roi.SetToolTip("New entry must be unique from all other institutional, physician, "
                                                "or variation ROIs for this physician.")
        self.combo_box_institutional_roi.SetToolTip("If the institutional ROI you’re looking for isn’t here, it may "
                                                    "already be assigned.")
        if 'uncategorized' in self.institutional_rois:
            self.combo_box_institutional_roi.SetValue('uncategorized')

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_institutional_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        label_physician_roi = wx.StaticText(self, wx.ID_ANY, "New Physician ROI:")
        sizer_physician_roi.Add(label_physician_roi, 0, 0, 0)
        sizer_physician_roi.Add(self.text_ctrl_physician_roi, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_physician_roi, 1, wx.ALL | wx.EXPAND, 5)
        label_institutional_roi = wx.StaticText(self, wx.ID_ANY, "Linked Institutional ROI:")
        sizer_institutional_roi.Add(label_institutional_roi, 0, 0, 0)
        sizer_institutional_roi.Add(self.combo_box_institutional_roi, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_institutional_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_input, 0, wx.EXPAND, 0)
        sizer_buttons.Add(self.button_ok, 1, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 1, wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 0, wx.ALIGN_RIGHT, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        pass


class AddROIType(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent)
        self.SetSize((250, 135))
        self.text_ctrl_roi_type = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Add New ROI Type")

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        label_roi_type = wx.StaticText(self, wx.ID_ANY, "New ROI Type:")
        sizer_physician_roi.Add(label_roi_type, 0, 0, 0)
        sizer_physician_roi.Add(self.text_ctrl_roi_type, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_physician_roi, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_input, 0, wx.EXPAND, 0)
        sizer_buttons.Add(self.button_ok, 1, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 1, wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 0, wx.ALIGN_CENTER, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Center()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        pass
