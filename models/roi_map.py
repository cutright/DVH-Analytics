import wx
import wx.html2
from bokeh.layouts import row
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, LabelSet, Range1d
from bokeh.io.export import get_layout_html
from tools.roi_name_manager import DatabaseROIs


class ROIMapDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        wx.Dialog.__init__(self, None, title='ROI Map')

        self.SetSize((1500, 800))
        self.panel_tree = wx.Window(self, wx.ID_ANY, style=wx.TAB_TRAVERSAL)
        self.roi_map = RoiMap(self.panel_tree, (800, 800))
        self.combo_box_physician = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.button_add_physician = wx.Button(self, wx.ID_ANY, "Add")
        self.button_rename_physician = wx.Button(self, wx.ID_ANY, "Rename")
        self.button_delete_physician = wx.Button(self, wx.ID_ANY, "Delete")
        self.combo_box_displayed_data = wx.ComboBox(self, wx.ID_ANY, choices=["All", "Linked to Institutional ROI", "Unlinked to Institutional ROI", "Branched"], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_roi_type = wx.ComboBox(self, wx.ID_ANY, choices=["Institutional", "Physician", "Variation"], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.button_add_roi = wx.Button(self, wx.ID_ANY, "Add")
        self.button_rename_roi = wx.Button(self, wx.ID_ANY, "Rename")
        self.button_delete_roi = wx.Button(self, wx.ID_ANY, "Delete")
        self.combo_box_uncategorized_ignored = wx.ComboBox(self, wx.ID_ANY, choices=["Uncategorized", "Ignored"], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_uncategorized_ignored_roi = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.button_uncategorized_ignored_delete = wx.Button(self, wx.ID_ANY, "Delete DVH")
        self.button_uncategorized_ignored_ignore = wx.Button(self, wx.ID_ANY, "Ignore DVH")
        self.combo_box_physician_roi_a = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.combo_box_physician_roi_b = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.button_merge = wx.Button(self, wx.ID_ANY, "Merge")

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.panel_tree.SetMinSize((850, 400))
        # self.panel_tree.SetScrollRate(10, 10)
        self.combo_box_displayed_data.SetSelection(0)
        self.combo_box_roi_type.SetSelection(0)
        self.combo_box_uncategorized_ignored.SetSelection(0)
        self.combo_box_physician_roi_a.SetMinSize((200, 25))
        self.combo_box_physician_roi_b.SetMinSize((200, 25))

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_editor = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_merger = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Physician ROI Merger"), wx.HORIZONTAL)
        sizer_physician_roi_merger_merge = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_b = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_roi_a = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Uncategorized / Ignored"), wx.HORIZONTAL)
        sizer_uncategorized_ignored_ignore = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_delete = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_uncategorized_ignored_type = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_editor = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "ROI Editor"), wx.HORIZONTAL)
        sizer_delete_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_rename_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_add_roi = wx.BoxSizer(wx.VERTICAL)
        sizer_roi_type = wx.BoxSizer(wx.VERTICAL)
        sizer_display = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Display"), wx.VERTICAL)
        sizer_displayed_data = wx.BoxSizer(wx.VERTICAL)
        sizer_physician_editor = wx.BoxSizer(wx.HORIZONTAL)
        sizer_delete_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_rename_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_add_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_physician = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.roi_map.layout, 1, 0, 5)
        self.panel_tree.SetSizer(sizer_2)
        sizer_wrapper.Add(self.panel_tree, 1, wx.EXPAND, 0)
        label_physician = wx.StaticText(self, wx.ID_ANY, "Physician:")
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
        sizer_display.Add(sizer_physician_editor, 1, wx.EXPAND, 0)
        label_displayed_data = wx.StaticText(self, wx.ID_ANY, "Display Filter:")
        sizer_displayed_data.Add(label_displayed_data, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_displayed_data.Add(self.combo_box_displayed_data, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_display.Add(sizer_displayed_data, 0, wx.ALL | wx.EXPAND, 0)
        sizer_editor.Add(sizer_display, 0, wx.ALL | wx.EXPAND, 5)
        label_roi_type = wx.StaticText(self, wx.ID_ANY, "ROI Type:")
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
        label_uncategorized_ignored = wx.StaticText(self, wx.ID_ANY, "Type:")
        label_uncategorized_ignored.SetMinSize((38, 16))
        sizer_uncategorized_ignored_type.Add(label_uncategorized_ignored, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_uncategorized_ignored_type.Add(self.combo_box_uncategorized_ignored, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_uncategorized_ignored.Add(sizer_uncategorized_ignored_type, 0, wx.EXPAND, 0)
        label_uncategorized_ignored_roi = wx.StaticText(self, wx.ID_ANY, "ROI:")
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
        label_physician_roi_a = wx.StaticText(self, wx.ID_ANY, "Merge Physician ROI A:")
        label_physician_roi_a.SetMinSize((200, 16))
        sizer_physician_roi_a.Add(label_physician_roi_a, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_physician_roi_a.Add(self.combo_box_physician_roi_a, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_a, 0, wx.ALL | wx.EXPAND, 0)
        label_physician_roi_b = wx.StaticText(self, wx.ID_ANY, "Into Physician ROI B:")
        label_physician_roi_b.SetMinSize((200, 16))
        sizer_physician_roi_b.Add(label_physician_roi_b, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer_physician_roi_b.Add(self.combo_box_physician_roi_b, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_b, 0, wx.ALL | wx.EXPAND, 0)
        sizer_physician_roi_merger_merge.Add((20, 16), 0, 0, 0)
        sizer_physician_roi_merger_merge.Add(self.button_merge, 0, wx.ALL, 5)
        sizer_physician_roi_merger.Add(sizer_physician_roi_merger_merge, 0, wx.ALL | wx.EXPAND, 0)
        sizer_editor.Add(sizer_physician_roi_merger, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_editor, 1, wx.ALL | wx.EXPAND, 20)
        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Centre()


class RoiMap:
    def __init__(self, parent, frame_size):

        self.layout = wx.html2.WebView.New(parent, size=frame_size)

        self.categories = ["Institutional ROI", "Physician", "Physician ROI", "Variation"]
        self.operators = ["Add", "Delete", "Rename"]

        # Load ROI map
        self.db = DatabaseROIs()

        self.roi_map_plot = figure(plot_height=750, plot_width=810,
                                   x_range=["Institutional ROI", "Physician ROI", "Variations"],
                                   x_axis_location="above",
                                   title="(Linked by Physician dropdowns)",
                                   tools="reset, ywheel_zoom, ywheel_pan",
                                   active_scroll='ywheel_pan')
        self.roi_map_plot.title.align = 'center'
        # self.roi_map_plot.title.text_font_style = "italic"
        self.roi_map_plot.title.text_font_size = "15pt"
        self.roi_map_plot.xaxis.axis_line_color = None
        self.roi_map_plot.xaxis.major_tick_line_color = None
        self.roi_map_plot.xaxis.minor_tick_line_color = None
        self.roi_map_plot.xaxis.major_label_text_font_size = "12pt"
        self.roi_map_plot.xgrid.grid_line_color = None
        self.roi_map_plot.ygrid.grid_line_color = None
        self.roi_map_plot.yaxis.visible = False
        self.roi_map_plot.outline_line_color = None
        self.roi_map_plot.y_range = Range1d(-25, 0)
        self.roi_map_plot.border_fill_color = "whitesmoke"
        self.roi_map_plot.min_border_left = 50
        self.roi_map_plot.min_border_bottom = 30
        self.source = ColumnDataSource(data={'name': [], 'color': [], 'x': [], 'y': [],
                                             'x0': [], 'y0': [], 'x1': [], 'y1': []})
        self.roi_map_plot.circle("x", "y", size=12, source=self.source, line_color="black", fill_alpha=0.8,
                                 color='color')
        labels = LabelSet(x="x", y="y", text="name", y_offset=8, text_color="#555555",
                          source=self.source, text_align='center')
        self.roi_map_plot.add_layout(labels)
        self.roi_map_plot.segment(x0='x0', y0='y0', x1='x1', y1='y1', source=self.source, alpha=0.5)
        # self.update_roi_map_source_data('BBM', 'All')

        self.bokeh_layout = row(self.roi_map_plot)

        self.update_plot('BBM', 'All')

    def update_roi_map_source_data(self, physician, display_filter):
        new_data = self.db.get_all_institutional_roi_visual_coordinates(physician)

        i_roi = new_data['institutional_roi']
        p_roi = new_data['physician_roi']
        b_roi = self.db.branched_institutional_rois[physician]
        if display_filter == 'Linked':
            ignored_roi = [p_roi[i] for i in range(len(i_roi)) if i_roi[i] == 'uncategorized']
        elif display_filter == 'Unlinked':
            ignored_roi = [p_roi[i] for i in range(len(i_roi)) if i_roi[i] != 'uncategorized']
        elif display_filter == 'Branched':
            ignored_roi = [p_roi[i] for i in range(len(i_roi)) if i_roi[i] not in b_roi]
        else:
            ignored_roi = []

        new_data = self.db.get_all_institutional_roi_visual_coordinates(physician, ignored_physician_rois=ignored_roi)

        self.source.data = new_data
        self.roi_map_plot.title.text = 'ROI Map for %s' % physician
        self.roi_map_plot.y_range.bounds = (min(self.source.data['y']) - 3, max(self.source.data['y']) + 3)

    def update_plot(self, physician, display_filter):
        self.update_roi_map_source_data(physician, display_filter)
        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")

    def clear_plot(self):
        self.source.data = {key: [] for key in ['name', 'color', 'x', 'y', 'x0', 'y0', 'x1', 'y1']}
        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")
