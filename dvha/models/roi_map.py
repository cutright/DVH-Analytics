import wx
import wx.html2
from dialogs.roi_map import AddPhysician, RoiManager
from db.sql_connector import DVH_SQL, echo_sql_db
from models.plot import PlotROIMap
from tools.roi_name_manager import clean_name


class ROIMapDialog(wx.Frame):
    def __init__(self, roi_map, *args, **kwds):
        wx.Frame.__init__(self, None, title='ROI Map')

        self.roi_map = roi_map

        self.SetSize((1500, 800))
        self.window = wx.SplitterWindow(self, wx.ID_ANY)
        self.window_tree = wx.Panel(self.window, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        # self.roi_tree = RoiTree(self.window_tree, self.roi_map)
        # self.roi_tree.rebuild_tree()
        self.combo_box_tree_physician = wx.ComboBox(self.window_tree, wx.ID_ANY,
                                                    choices=self.roi_map.get_physicians(),
                                                    style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_tree_plot_data = wx.ComboBox(self.window_tree, wx.ID_ANY,
                                                    choices=['All', 'Linked', 'Unlinked', 'Branched'],
                                                    style=wx.CB_DROPDOWN | wx.CB_READONLY)

        self.plot = PlotROIMap(self.window_tree, roi_map)
        self.window_editor = wx.Panel(self.window, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.combo_box_physician = wx.ComboBox(self.window_editor, wx.ID_ANY, choices=self.roi_map.get_physicians(),
                                               style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_add_physician = wx.Button(self.window_editor, wx.ID_ANY, "Add")
        self.button_rename_physician = wx.Button(self.window_editor, wx.ID_ANY, "Rename")
        self.button_delete_physician = wx.Button(self.window_editor, wx.ID_ANY, "Delete")
        self.combo_box_roi_type = wx.ComboBox(self.window_editor, wx.ID_ANY,
                                              choices=["Institutional", "Physician", "Variation"],
                                              style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_add_roi = wx.Button(self.window_editor, wx.ID_ANY, "Add")
        self.button_rename_roi = wx.Button(self.window_editor, wx.ID_ANY, "Rename")
        self.button_delete_roi = wx.Button(self.window_editor, wx.ID_ANY, "Delete")
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

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.plot.update_roi_map_source_data(self.physician)

        self.run()

    def __set_properties(self):
        self.combo_box_roi_type.SetSelection(0)
        self.combo_box_uncategorized_ignored.SetSelection(0)
        self.combo_box_physician.SetMinSize((150, 25))
        self.combo_box_roi_type.SetMinSize((150, 25))
        self.combo_box_uncategorized_ignored_roi.SetMinSize((240, 25))
        self.combo_box_uncategorized_ignored.SetMinSize((150, 25))
        self.combo_box_physician_roi_a.SetMinSize((250, 25))
        self.combo_box_physician_roi_b.SetMinSize((250, 25))
        # self.window.SetMinimumPaneSize(20)

        self.combo_box_physician.SetValue('DEFAULT')
        self.combo_box_tree_physician.SetValue('DEFAULT')
        self.combo_box_tree_plot_data.SetValue('ALL')

        self.update_uncategorized_ignored_choices(None)

    def __do_bind(self):
        self.window_editor.Bind(wx.EVT_BUTTON, self.add_physician, id=self.button_add_physician.GetId())

        self.window_tree.Bind(wx.EVT_COMBOBOX, self.on_physician_change, id=self.combo_box_tree_physician.GetId())
        self.window_editor.Bind(wx.EVT_COMBOBOX, self.update_uncategorized_ignored_choices,
                                id=self.combo_box_uncategorized_ignored.GetId())
        self.window_tree.Bind(wx.EVT_COMBOBOX, self.on_plot_data_type_change, id=self.combo_box_tree_plot_data.GetId())

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
        sizer_roi_editor = wx.StaticBoxSizer(wx.StaticBox(self.window_editor, wx.ID_ANY, "ROI Editor"), wx.HORIZONTAL)
        sizer_delete_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_rename_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_add_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_type = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_editor = wx.StaticBoxSizer(wx.StaticBox(self.window_editor, wx.ID_ANY, "Physician Editor"), wx.HORIZONTAL)
        sizer_delete_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_rename_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_add_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_tree_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tree_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_tree_plot_data = wx.BoxSizer(wx.VERTICAL)

        label_tree_plot_data = wx.StaticText(self.window_tree, wx.ID_ANY, 'Institutional Data to Display:')
        sizer_tree_plot_data.Add(label_tree_plot_data, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_tree_plot_data.Add(self.combo_box_tree_plot_data, 0, wx.EXPAND | wx.ALL, 5)

        label_tree_physician = wx.StaticText(self.window_tree, wx.ID_ANY, 'Physician:')
        sizer_tree_physician.Add(label_tree_physician, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_tree_physician.Add(self.combo_box_tree_physician, 0, wx.EXPAND | wx.ALL, 5)

        sizer_tree_input.Add(sizer_tree_plot_data, 0, wx.EXPAND, 0)
        sizer_tree_input.Add(sizer_tree_physician, 0, wx.EXPAND, 0)

        sizer_tree.Add(sizer_tree_input, 0, wx.EXPAND, 0)
        sizer_tree.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.window_tree.SetSizer(sizer_tree)

        label_physician = wx.StaticText(self.window_editor, wx.ID_ANY, "Physician:")
        label_physician.SetMinSize((65, 16))

        sizer_physician.Add(label_physician, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_physician.Add(self.combo_box_physician, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_editor.Add(sizer_physician, 0, wx.EXPAND, 0)

        sizer_add_physician.Add((20, 16), 0, wx.ALL, 0)
        sizer_add_physician.Add(self.button_add_physician, 0, wx.ALL, 5)
        sizer_physician_editor.Add(sizer_add_physician, 0, wx.EXPAND, 0)

        sizer_rename_physician.Add((20, 16), 0, 0, 0)
        sizer_rename_physician.Add(self.button_rename_physician, 0, wx.ALL, 5)
        sizer_physician_editor.Add(sizer_rename_physician, 0, wx.EXPAND, 0)

        sizer_delete_physician.Add((20, 16), 0, 0, 0)
        sizer_delete_physician.Add(self.button_delete_physician, 0, wx.ALL, 5)
        sizer_physician_editor.Add(sizer_delete_physician, 0, wx.EXPAND, 0)
        sizer_editor.Add(sizer_physician_editor, 0, wx.ALL | wx.EXPAND, 5)

        label_roi_type = wx.StaticText(self.window_editor, wx.ID_ANY, "ROI Type:")
        label_roi_type.SetMinSize((63, 16))
        sizer_roi_type.Add(label_roi_type, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_roi_type.Add(self.combo_box_roi_type, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_roi_editor.Add(sizer_roi_type, 0, wx.ALL | wx.EXPAND, 0)

        sizer_add_roi.Add((20, 16), 0, 0, 0)
        sizer_add_roi.Add(self.button_add_roi, 0, wx.ALL, 5)
        sizer_roi_editor.Add(sizer_add_roi, 0, wx.EXPAND, 0)

        sizer_rename_roi.Add((20, 16), 0, 0, 0)
        sizer_rename_roi.Add(self.button_rename_roi, 0, wx.ALL, 5)
        sizer_roi_editor.Add(sizer_rename_roi, 0, wx.EXPAND, 0)
        sizer_delete_roi.Add((20, 16), 0, 0, 0)
        sizer_delete_roi.Add(self.button_delete_roi, 0, wx.ALL, 5)
        sizer_roi_editor.Add(sizer_delete_roi, 0, wx.EXPAND, 0)
        sizer_editor.Add(sizer_roi_editor, 0, wx.ALL | wx.EXPAND, 5)

        label_uncategorized_ignored = wx.StaticText(self.window_editor, wx.ID_ANY, "Type:")
        label_uncategorized_ignored.SetMinSize((38, 16))
        sizer_uncategorized_ignored_type.Add(label_uncategorized_ignored, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_uncategorized_ignored_type.Add(self.combo_box_uncategorized_ignored, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_type, 0, wx.EXPAND, 0)
        label_uncategorized_ignored_roi = wx.StaticText(self.window_editor, wx.ID_ANY, "ROI:")
        label_uncategorized_ignored_roi.SetMinSize((30, 16))
        sizer_uncategorized_ignored_roi.Add(label_uncategorized_ignored_roi, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_uncategorized_ignored_roi.Add(self.combo_box_uncategorized_ignored_roi, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_roi, 0, wx.EXPAND, 0)
        sizer_uncategorized_ignored_delete.Add((20, 16), 0, 0, 0)
        sizer_uncategorized_ignored_delete.Add(self.button_uncategorized_ignored_delete, 0, wx.ALL, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_delete, 0, wx.EXPAND, 0)
        sizer_uncategorized_ignored_ignore.Add((20, 16), 0, 0, 0)
        sizer_uncategorized_ignored_ignore.Add(self.button_uncategorized_ignored_ignore, 0, wx.ALL, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_ignore, 0, wx.EXPAND, 0)
        sizer_editor.Add(sizer_uncategorized_ignored, 0, wx.ALL | wx.EXPAND, 5)

        label_physician_roi_a = wx.StaticText(self.window_editor, wx.ID_ANY, "Merge Physician ROI A:")
        label_physician_roi_a.SetMinSize((200, 16))
        sizer_physician_roi_a.Add(label_physician_roi_a, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_physician_roi_a.Add(self.combo_box_physician_roi_a, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_a, 0, wx.ALL | wx.EXPAND, 0)
        label_physician_roi_b = wx.StaticText(self.window_editor, wx.ID_ANY, "Into Physician ROI B:")
        label_physician_roi_b.SetMinSize((200, 16))
        sizer_physician_roi_b.Add(label_physician_roi_b, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_physician_roi_b.Add(self.combo_box_physician_roi_b, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_b, 0, wx.ALL | wx.EXPAND, 0)
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

    def add_physician(self, evt):
        physicians = self.roi_map.get_physicians()
        AddPhysician(self.roi_map)
        self.update_physicians(old_physicians=physicians)

    def update_physicians(self, old_physicians=None):

        old_physician = self.combo_box_physician.GetValue()

        choices = self.roi_map.get_physicians()
        new = choices[0]
        if old_physicians:
            new = list(set(choices) - set(old_physicians))
            if new:
                new = clean_name(new[0]).upper()

        self.update_combo_box_choices(self.combo_box_physician, choices, new)

        if old_physician != self.combo_box_physician.GetValue():
            self.update_roi_map()

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
        return self.combo_box_tree_physician.GetValue()

    @property
    def plot_data_type(self):
        return self.combo_box_tree_plot_data.GetValue()

    def on_physician_change(self, evt):
        self.update_roi_map()
        self.update_uncategorized_ignored_choices(None)

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


# class RoiTree:
#     def __init__(self, parent, db_rois):
#
#         self.tree_ctrl = wx.TreeCtrl(parent, wx.ID_ANY)
#         self.db = db_rois
#         self.root = self.tree_ctrl.AddRoot('Physicians')
#         self.physician_nodes = {}
#         self.institutional_status_nodes = {}
#         self.physician_roi_nodes = {}
#         self.roi_variation_nodes = {}
#
#     def rebuild_tree(self):
#         self.tree_ctrl.DeleteChildren(self.root)
#         tree = self.db.tree
#
#         self.physician_nodes = {}
#         self.institutional_status_nodes = {}
#         self.physician_roi_nodes = {}
#         self.roi_variation_nodes = {}
#
#         for physician, linked_statuses in tree.items():
#             self.append_physician(physician)
#             for linked_status, physician_rois in linked_statuses.items():
#                 for physician_roi, variations in physician_rois.items():
#                     self.append_physician_roi(physician, physician_roi, linked_status)
#                     for variation in variations:
#                         self.append_variation(physician, physician_roi, variation)
#
#         self.tree_ctrl.Expand(self.root)
#
#     def append_variation(self, physician, physician_roi, variation):
#         parent_node = self.physician_roi_nodes[physician][physician_roi]
#         nodes = self.roi_variation_nodes[physician][physician_roi]
#         self.append_tree_item(parent_node, nodes, variation)
#
#     def append_physician_roi(self, physician, physician_roi, linked_status):
#         parent_node = self.institutional_status_nodes[physician][linked_status]
#         nodes = self.physician_roi_nodes[physician]
#         self.append_tree_item(parent_node, nodes, physician_roi)
#         if physician_roi not in list(self.roi_variation_nodes[physician]):
#             self.roi_variation_nodes[physician][physician_roi] = {}
#         if physician_roi not in list(self.physician_roi_nodes[physician]):
#             self.physician_roi_nodes[physician][physician_roi] = {}
#
#     def append_physician(self, physician):
#         self.append_tree_item(self.root, self.physician_nodes, physician)
#         if physician not in list(self.institutional_status_nodes):
#             self.institutional_status_nodes[physician] = {'Linked to Institutional ROI': [],
#                                                           'Unlinked to Institutional ROI': []}
#         self.append_tree_item(self.physician_nodes[physician],
#                               self.institutional_status_nodes[physician], 'Linked to Institutional ROI')
#         self.append_tree_item(self.physician_nodes[physician],
#                               self.institutional_status_nodes[physician], 'Unlinked to Institutional ROI')
#
#         if physician not in list(self.physician_roi_nodes):
#             self.physician_roi_nodes[physician] = {}
#         if physician not in list(self.roi_variation_nodes):
#             self.roi_variation_nodes[physician] = {}
#
#     def append_tree_item(self, parent_node, nodes, key):
#         nodes[key] = self.tree_ctrl.AppendItem(parent_node, key)
#
#     def sort_tree(self):
#         self.tree_ctrl.SortChildren(self.root)
