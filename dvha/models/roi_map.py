import wx
import wx.html2
from dialogs.roi_map import AddPhysician, AddPhysicianROI, AddVariationDialog, MoveVariationDialog,\
    RenamePhysicianDialog, RenamePhysicianROIDialog, RenameInstitutionalROIDialog
from tools.errors import ROIVariationError, ROIVariationErrorDialog
from tools.utilities import get_selected_listctrl_items, MessageDialog
from db.sql_connector import DVH_SQL, echo_sql_db
from models.datatable import DataTable
from models.plot import PlotROIMap
from tools.roi_name_manager import clean_name


class ROIMapFrame(wx.Frame):
    def __init__(self, roi_map):
        wx.Frame.__init__(self, None, title='ROI Map')

        self.roi_map = roi_map

        self.SetSize((1500, 800))
        self.window = wx.SplitterWindow(self, wx.ID_ANY)
        self.window_tree = wx.Panel(self.window, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self.combo_box_tree_plot_data = wx.ComboBox(self.window_tree, wx.ID_ANY,
                                                    choices=['All', 'Linked', 'Unlinked', 'Branched'],
                                                    style=wx.CB_DROPDOWN | wx.CB_READONLY)

        self.plot = PlotROIMap(self.window_tree, roi_map)
        self.window_editor = wx.Panel(self.window, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self.combo_box_physician = wx.ComboBox(self.window_editor, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_physician_roi = wx.ComboBox(self.window_editor, wx.ID_ANY, choices=[],
                                                   style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.list_ctrl_variations = wx.ListCtrl(self.window_editor, wx.ID_ANY,
                                                style=wx.LC_NO_HEADER | wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.button_variation_select_all = wx.Button(self.window_editor, wx.ID_ANY, "Select All")
        self.button_variation_deselect_all = wx.Button(self.window_editor, wx.ID_ANY, "Deselect All")
        self.button_variation_add = wx.Button(self.window_editor, wx.ID_ANY, "Add")
        self.button_variation_delete = wx.Button(self.window_editor, wx.ID_ANY, "Delete")
        self.button_variation_move = wx.Button(self.window_editor, wx.ID_ANY, "Move")

        self.button_variation_move.Disable()
        self.button_variation_delete.Disable()
        self.button_variation_deselect_all.Disable()

        self.button_physician = {'add': wx.Button(self.window_editor, wx.ID_ANY, "+"),
                                 'del': wx.Button(self.window_editor, wx.ID_ANY, "-"),
                                 'edit': wx.Button(self.window_editor, wx.ID_ANY, "Δ")}
        self.button_physician_roi = {'add': wx.Button(self.window_editor, wx.ID_ANY, "+"),
                                     'del': wx.Button(self.window_editor, wx.ID_ANY, "-"),
                                     'edit': wx.Button(self.window_editor, wx.ID_ANY, "Δ")}

        self.combo_box_uncategorized_ignored = wx.ComboBox(self.window_editor, wx.ID_ANY,
                                                           choices=["Uncategorized", "Ignored"],
                                                           style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_uncategorized_ignored_roi = wx.ComboBox(self.window_editor, wx.ID_ANY, choices=[],
                                                               style=wx.CB_DROPDOWN)
        self.button_uncategorized_ignored_delete = wx.Button(self.window_editor, wx.ID_ANY, "Delete DVH")
        self.button_uncategorized_ignored_ignore = wx.Button(self.window_editor, wx.ID_ANY, "Ignore DVH")
        self.combo_box_physician_roi_a = wx.ComboBox(self.window_editor, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.combo_box_physician_roi_b = wx.ComboBox(self.window_editor, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.button_merge = wx.Button(self.window_editor, wx.ID_ANY, "Merge")

        self.uncategorized_variations = {}

        self.columns = ['Variations']
        self.data_table = DataTable(self.list_ctrl_variations, columns=self.columns, widths=[490])

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.plot.update_roi_map_source_data(self.physician)

        self.run()

    def __set_properties(self):
        self.combo_box_uncategorized_ignored.SetSelection(0)
        self.button_uncategorized_ignored_ignore.SetMinSize((110, 20))
        # self.combo_box_uncategorized_ignored_roi.SetMinSize((240, 25))
        # self.combo_box_uncategorized_ignored.SetMinSize((150, 25))
        # self.combo_box_physician_roi_a.SetMinSize((250, 25))
        # self.combo_box_physician_roi_b.SetMinSize((250, 25))

        self.combo_box_physician.SetValue('DEFAULT')
        self.update_physician_rois()
        # self.combo_box_physician_roi.SetValue(self.initial_physician_roi)
        self.update_variations()

        self.combo_box_physician.SetValue('DEFAULT')
        self.combo_box_tree_plot_data.SetValue('ALL')

        self.update_uncategorized_ignored_choices(None)

        self.window_tree.SetBackgroundColour('white')

        for button in self.button_physician.values():
            button.SetMaxSize((25, 25))
        for button in self.button_physician_roi.values():
            button.SetMaxSize((25, 25))

        self.update_physician_enable()

    def __do_bind(self):
        self.window_tree.Bind(wx.EVT_COMBOBOX, self.on_plot_data_type_change, id=self.combo_box_tree_plot_data.GetId())

        self.window_editor.Bind(wx.EVT_COMBOBOX, self.update_uncategorized_ignored_choices,
                                id=self.combo_box_uncategorized_ignored.GetId())

        self.window_editor.Bind(wx.EVT_COMBOBOX, self.physician_ticker, id=self.combo_box_physician.GetId())
        self.window_editor.Bind(wx.EVT_COMBOBOX, self.physician_roi_ticker, id=self.combo_box_physician_roi.GetId())
        self.window_editor.Bind(wx.EVT_COMBOBOX, self.uncategorized_ticker, id=self.combo_box_uncategorized_ignored.GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.add_physician, id=self.button_physician['add'].GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.on_delete_physician, id=self.button_physician['del'].GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.on_edit_physician, id=self.button_physician['edit'].GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.add_physician_roi, id=self.button_physician_roi['add'].GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.on_delete_physician_roi, id=self.button_physician_roi['del'].GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.on_edit_physician_roi, id=self.button_physician_roi['edit'].GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.select_all_variations, id=self.button_variation_select_all.GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.deselect_all_variations, id=self.button_variation_deselect_all.GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.add_variation, id=self.button_variation_add.GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.move_variations, id=self.button_variation_move.GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.delete_variations, id=self.button_variation_delete.GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.on_delete_dvh, id=self.button_uncategorized_ignored_delete.GetId())
        self.window_editor.Bind(wx.EVT_BUTTON, self.on_ignore_dvh, id=self.button_uncategorized_ignored_ignore.GetId())
        self.window_editor.Bind(wx.EVT_LIST_ITEM_SELECTED, self.update_button_variation_enable,
                                id=self.list_ctrl_variations.GetId())
        self.window_editor.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.update_button_variation_enable,
                                id=self.list_ctrl_variations.GetId())

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_editor = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_merger = wx.StaticBoxSizer(
            wx.StaticBox(self.window_editor, wx.ID_ANY, "Physician ROI Merger"), wx.HORIZONTAL)
        sizer_physician_roi_merger_merge = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_b = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_a = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored = wx.StaticBoxSizer(
            wx.StaticBox(self.window_editor, wx.ID_ANY, "Uncategorized / Ignored"), wx.HORIZONTAL)
        sizer_uncategorized_ignored_ignore = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_delete = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_type = wx.BoxSizer(wx.VERTICAL)

        sizer_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_tree_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tree_plot_data = wx.BoxSizer(wx.VERTICAL)

        sizer_roi_manager = wx.BoxSizer(wx.VERTICAL)
        sizer_variation_buttons = wx.BoxSizer(wx.VERTICAL)
        sizer_variation_table = wx.BoxSizer(wx.VERTICAL)
        sizer_select = wx.StaticBoxSizer(wx.StaticBox(self.window_editor, wx.ID_ANY, "ROI Manager"), wx.VERTICAL)
        sizer_variations = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_physician = wx.BoxSizer(wx.VERTICAL)

        sizer_physician_row = wx.BoxSizer(wx.HORIZONTAL)
        sizer_physician_roi_row = wx.BoxSizer(wx.HORIZONTAL)

        label_physician = wx.StaticText(self.window_editor, wx.ID_ANY, "Physician:")
        sizer_physician.Add(label_physician, 0, 0, 0)
        sizer_physician_row.Add(self.combo_box_physician, 1, wx.EXPAND | wx.RIGHT, 5)
        sizer_physician_row.Add(self.button_physician['add'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_physician_row.Add(self.button_physician['del'], 0, wx.RIGHT, 5)
        sizer_physician_row.Add(self.button_physician['edit'], 0, wx.RIGHT, 10)
        sizer_physician.Add(sizer_physician_row, 1, wx.EXPAND, 0)

        self.label_physician_roi = wx.StaticText(self.window_editor, wx.ID_ANY, "Institutional ROI:")
        sizer_physician_roi.Add(self.label_physician_roi, 0, 0, 0)
        sizer_physician_roi_row.Add(self.combo_box_physician_roi, 1, wx.EXPAND | wx.RIGHT, 5)
        sizer_physician_roi_row.Add(self.button_physician_roi['add'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_row.Add(self.button_physician_roi['del'], 0, wx.RIGHT, 5)
        sizer_physician_roi_row.Add(self.button_physician_roi['edit'], 0, wx.RIGHT, 10)
        sizer_physician_roi.Add(sizer_physician_roi_row, 0, wx.EXPAND, 0)

        sizer_select.Add(sizer_physician, 0, wx.ALL | wx.EXPAND, 5)
        sizer_select.Add(sizer_physician_roi, 0, wx.ALL | wx.EXPAND, 5)

        label_variations = wx.StaticText(self.window_editor, wx.ID_ANY, "Variations:")
        label_variations_buttons = wx.StaticText(self.window_editor, wx.ID_ANY, " ")
        sizer_variation_table.Add(label_variations, 0, 0, 0)
        sizer_variation_table.Add(self.list_ctrl_variations, 1, wx.ALL | wx.EXPAND, 0)
        sizer_variations.Add(sizer_variation_table, 1, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(label_variations_buttons, 0, 0, 0)
        sizer_variation_buttons.Add(self.button_variation_add, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer_variation_buttons.Add(self.button_variation_delete, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(self.button_variation_move, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(self.button_variation_select_all, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variation_buttons.Add(self.button_variation_deselect_all, 0, wx.EXPAND | wx.ALL, 5)
        sizer_variations.Add(sizer_variation_buttons, 0, wx.EXPAND | wx.ALL, 5)
        sizer_select.Add(sizer_variations, 0, wx.EXPAND, 0)
        sizer_roi_manager.Add(sizer_select, 1, wx.EXPAND, 0)
        sizer_editor.Add(sizer_roi_manager, 0, wx.EXPAND | wx.ALL, 5)

        label_tree_plot_data = wx.StaticText(self.window_tree, wx.ID_ANY, 'Institutional Data to Display:')
        sizer_tree_plot_data.Add(label_tree_plot_data, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_tree_plot_data.Add(self.combo_box_tree_plot_data, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)

        sizer_tree_input.Add(sizer_tree_plot_data, 0, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        sizer_tree.Add(sizer_tree_input, 0, wx.EXPAND, 0)
        sizer_tree.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.window_tree.SetSizer(sizer_tree)

        label_uncategorized_ignored = wx.StaticText(self.window_editor, wx.ID_ANY, "Type:")
        label_uncategorized_ignored.SetMinSize((38, 16))
        sizer_uncategorized_ignored_type.Add(label_uncategorized_ignored, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_uncategorized_ignored_type.Add(self.combo_box_uncategorized_ignored, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_type, 1, wx.EXPAND, 0)
        label_uncategorized_ignored_roi = wx.StaticText(self.window_editor, wx.ID_ANY, "ROI:")
        label_uncategorized_ignored_roi.SetMinSize((30, 16))
        sizer_uncategorized_ignored_roi.Add(label_uncategorized_ignored_roi, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_uncategorized_ignored_roi.Add(self.combo_box_uncategorized_ignored_roi, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_roi, 1, wx.EXPAND, 0)
        sizer_uncategorized_ignored_delete.Add((20, 16), 0, 0, 0)
        sizer_uncategorized_ignored_delete.Add(self.button_uncategorized_ignored_delete, 0, wx.ALL, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_delete, 0, wx.EXPAND, 0)
        sizer_uncategorized_ignored_ignore.Add((20, 16), 0, 0, 0)
        sizer_uncategorized_ignored_ignore.Add(self.button_uncategorized_ignored_ignore, 0, wx.ALL, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_ignore, 0, wx.EXPAND, 0)
        sizer_editor.Add(sizer_uncategorized_ignored, 0, wx.ALL | wx.EXPAND, 5)

        label_physician_roi_a = wx.StaticText(self.window_editor, wx.ID_ANY, "Merge Physician ROI A:")
        # label_physician_roi_a.SetMinSize((200, 16))
        sizer_physician_roi_a.Add(label_physician_roi_a, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_physician_roi_a.Add(self.combo_box_physician_roi_a, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_a, 1, wx.EXPAND, 0)
        label_physician_roi_b = wx.StaticText(self.window_editor, wx.ID_ANY, "Into Physician ROI B:")
        # label_physician_roi_b.SetMinSize((200, 16))
        sizer_physician_roi_b.Add(label_physician_roi_b, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_physician_roi_b.Add(self.combo_box_physician_roi_b, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_b, 1, wx.EXPAND, 0)
        sizer_physician_roi_merger_merge.Add((20, 16), 0, 0, 0)
        sizer_physician_roi_merger_merge.Add(self.button_merge, 0, wx.ALL, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_merger_merge, 0, wx.ALL | wx.EXPAND, 0)
        sizer_editor.Add(sizer_physician_roi_merger, 0, wx.ALL | wx.EXPAND, 5)
        self.window_editor.SetSizer(sizer_editor)
        self.window.SplitVertically(self.window_tree, self.window_editor)
        self.window.SetSashPosition(825)
        sizer_wrapper.Add(self.window, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Centre()

    def run(self):
        self.Show()

    @staticmethod
    def update_combo_box_choices(combo_box, choices, value):
        if not value:
            value = combo_box.GetValue()
        combo_box.Clear()
        combo_box.AppendItems(choices)
        combo_box.SetValue(value)

    def update_roi_map(self):
        self.plot.update_roi_map_source_data(self.physician, plot_type=self.plot_data_type)

    @property
    def physician(self):
        return self.combo_box_physician.GetValue()

    @property
    def physician_roi(self):
        return self.combo_box_physician_roi.GetValue()

    @property
    def plot_data_type(self):
        return self.combo_box_tree_plot_data.GetValue()

    def physician_ticker(self, evt):
        self.update_physician_roi_label()
        self.update_physician_enable()
        self.update_roi_map()
        self.update_uncategorized_ignored_choices(None)
        self.update_physician_rois()
        self.update_variations()

    def on_plot_data_type_change(self, evt):
        self.update_roi_map()

    def update_uncategorized_ignored_choices(self, evt):
        ignored_variations = self.combo_box_uncategorized_ignored.GetValue() == 'Ignored'
        self.uncategorized_variations = self.get_uncategorized_variations(self.physician,
                                                                          ignored_variations=ignored_variations)
        choices = list(self.uncategorized_variations)
        choices.sort()
        if not choices:
            choices = ['None']
            self.button_uncategorized_ignored_delete.Disable()
            self.button_uncategorized_ignored_ignore.Disable()
        else:
            self.button_uncategorized_ignored_delete.Enable()
            self.button_uncategorized_ignored_ignore.Enable()
        self.combo_box_uncategorized_ignored_roi.Clear()
        self.combo_box_uncategorized_ignored_roi.Append(choices)
        self.combo_box_uncategorized_ignored_roi.SetValue(choices[0])

    @staticmethod
    def get_uncategorized_variations(physician, ignored_variations=False):
        if echo_sql_db():
            with DVH_SQL() as cnx:
                physician = clean_name(physician).upper()
                condition = "physician_roi = '%s'" % ['uncategorized', 'ignored'][ignored_variations]
                cursor_rtn = cnx.query('dvhs', 'roi_name, study_instance_uid', condition)
                new_variations = {}
                for row in cursor_rtn:
                    variation = clean_name(str(row[0]))
                    study_instance_uid = str(row[1])
                    physician_db = cnx.get_unique_values('Plans', 'physician',
                                                         "study_instance_uid = '%s'" % study_instance_uid)
                    if physician_db and physician_db[0] == physician:
                        if variation not in list(new_variations):
                            new_variations[variation] = {'roi_name': variation,
                                                         'study_instance_uid': [study_instance_uid]}
                        else:
                            new_variations[variation]['study_instance_uid'].append(study_instance_uid)
                return new_variations

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl_variations)

    def update_button_variation_enable(self, evt):
        if self.selected_indices:
            self.button_variation_move.Enable()
            self.button_variation_delete.Enable()
            self.button_variation_deselect_all.Enable()
        else:
            self.button_variation_move.Disable()
            self.button_variation_delete.Disable()
            self.button_variation_deselect_all.Disable()

        self.button_variation_select_all.Enable(self.variation_count > 0)

    def update_variations(self):
        self.data_table.set_data(self.variation_table_data, self.columns)
        self.update_button_variation_enable(None)

    def physician_roi_ticker(self, evt):
        self.update_variations()

    def update_physicians(self, old_physicians=None):

        choices = self.roi_map.get_physicians()
        new = choices[0]
        if old_physicians:
            new = list(set(choices) - set(old_physicians))
            if new:
                new = clean_name(new[0]).upper()

        self.update_combo_box_choices(self.combo_box_physician, choices, new)
        self.update_physician_roi_label()
        self.update_physician_enable()

    def update_physician_rois(self, old_physician_rois=None):
        choices = self.roi_map.get_physician_rois(self.physician)
        new = choices[0]
        if old_physician_rois:
            new = list(set(choices) - set(old_physician_rois))
            if new:
                new = clean_name(new[0])

        self.update_combo_box_choices(self.combo_box_physician_roi, choices, new)

    @property
    def variations(self):
        variations = self.roi_map.get_variations(self.physician, self.physician_roi)
        variations = list(set(variations) - {self.physician_roi})  # remove physician roi
        variations.sort()
        return variations

    @property
    def variation_table_data(self):
        return {'Variations': self.variations}

    def add_physician_roi(self, evt):
        old_physician_rois = self.roi_map.get_physician_rois(self.physician)
        dlg = AddPhysicianROI(self, self.physician, self.roi_map)
        if dlg.res == wx.ID_OK:
            self.update_all(old_physician_rois=old_physician_rois)

    def add_physician(self, evt):
        old_physicians = self.roi_map.get_physicians()
        dlg = AddPhysician(self.roi_map)
        if dlg.res == wx.ID_OK:
            self.update_all(old_physicians=old_physicians)

    @property
    def variation_count(self):
        return len(self.variations)

    @property
    def selected_values(self):
        return [self.list_ctrl_variations.GetItem(i, 0).GetText() for i in self.selected_indices]

    def select_all_variations(self, evt):
        self.apply_global_selection()

    def deselect_all_variations(self, evt):
        self.apply_global_selection(on=0)

    def apply_global_selection(self, on=1):
        for i in range(self.variation_count):
            self.list_ctrl_variations.Select(i, on=on)

    def delete_variations(self, evt):
        self.roi_map.delete_variations(self.physician, self.physician_roi, self.selected_values)
        self.update_variations()

    def add_variation(self, evt):
        dlg = AddVariationDialog(self, self.physician, self.physician_roi, self.roi_map)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            try:
                self.roi_map.add_variation(self.physician, self.physician_roi, dlg.text_ctrl_variation.GetValue())
                self.update_variations()
            except ROIVariationError as e:
                ROIVariationErrorDialog(self, e)
        dlg.Destroy()

    def move_variations(self, evt):
        choices = [roi for roi in self.roi_map.get_physician_rois(self.physician) if roi != self.physician_roi]
        MoveVariationDialog(self, self.selected_values, self.physician, self.physician_roi, choices, self.roi_map)
        self.update_variations()

    def on_delete_physician(self, evt):
        MessageDialog(self, 'Delete Physician %s?' % self.physician, action_yes_func=self.delete_physician)

    def delete_physician(self):
        self.roi_map.delete_physician(self.physician)
        self.update_all()

    def on_delete_physician_roi(self, evt):
        if self.physician == 'DEFAULT':
            MessageDialog(self, "Delete Institutional ROI %s?" % self.physician_roi,
                          action_yes_func=self.delete_institutional_roi)
        else:
            MessageDialog(self, "Delete Physician ROI %s?" % self.physician_roi,
                          action_yes_func=self.delete_physician_roi)

    def delete_physician_roi(self):
        self.roi_map.delete_physician_roi(self.physician, self.physician_roi)
        self.update_all(skip_physicians=True)

    def delete_institutional_roi(self):
        self.roi_map.delete_institutional_roi(self.physician_roi)
        self.update_all(skip_physicians=True)

    def on_delete_dvh(self, evt):
        MessageDialog(self, "Delete all DVHs named %s for %s?" % (self.dvh, self.physician),
                      action_yes_func=self.delete_dvh)

    def delete_dvh(self):
        with DVH_SQL() as cnx:
            for uid in self.dvh_uids:
                cnx.delete_dvh(self.dvh, uid)
        self.update_uncategorized_ignored_choices(None)

    def on_ignore_dvh(self, evt):
        msg_type = ['Unignore', 'Ignore'][self.button_uncategorized_ignored_ignore.GetLabelText() == 'Ignore DVH']
        MessageDialog(self, "%s all DVHs named %s for %s?" % (msg_type, self.dvh, self.physician),
                      action_yes_func=self.ignore_dvh)

    def ignore_dvh(self):
        unignore = self.button_uncategorized_ignored_ignore.GetLabelText() == 'Unignore DVH'
        with DVH_SQL() as cnx:
            for uid in self.dvh_uids:
                cnx.ignore_dvh(self.dvh, uid, unignore=unignore)
        self.update_uncategorized_ignored_choices(None)

    @property
    def dvh(self):
        return self.combo_box_uncategorized_ignored_roi.GetValue()

    @property
    def dvh_uids(self):
        return self.uncategorized_variations[self.dvh]['study_instance_uid']

    def update_all(self, old_physicians=None, old_physician_rois=None, skip_physicians=False):
        if not skip_physicians:
            self.update_physicians(old_physicians=old_physicians)
        self.update_physician_rois(old_physician_rois=old_physician_rois)
        self.update_variations()
        self.update_uncategorized_ignored_choices(None)
        self.update_roi_map()

    def on_edit_physician(self, evt):
        current_physicians = self.roi_map.get_physicians()
        dlg = RenamePhysicianDialog(self.physician, self.roi_map)
        if dlg.res == wx.ID_OK:
            self.update_all(old_physicians=current_physicians)

    def on_edit_physician_roi(self, evt):
        current_physician_rois = self.roi_map.get_physician_rois(self.physician)
        if self.physician == 'DEFAULT':
            dlg = RenameInstitutionalROIDialog(self.physician_roi, self.roi_map)
        else:
            dlg = RenamePhysicianROIDialog(self.physician, self.physician_roi, self.roi_map)
        if dlg.res == wx.ID_OK:
            self.update_all(old_physician_rois=current_physician_rois, skip_physicians=True)

    def update_physician_enable(self):
        self.button_physician['del'].Enable(self.physician != 'DEFAULT')
        self.button_physician['edit'].Enable(self.physician != 'DEFAULT')
        self.button_variation_add.Enable(self.physician != 'DEFAULT')

    def update_physician_roi_label(self):
        label_text = ['Physician ROI:', 'Institutional ROI:'][self.physician == 'DEFAULT']
        self.label_physician_roi.SetLabelText(label_text)

    def uncategorized_ticker(self, evt):
        if self.combo_box_uncategorized_ignored.GetValue() == 'Uncategorized':
            self.button_uncategorized_ignored_ignore.SetLabelText('Ignore DVH')
        else:
            self.button_uncategorized_ignored_ignore.SetLabelText('Unignore DVH')
        self.update_uncategorized_ignored_choices(None)
