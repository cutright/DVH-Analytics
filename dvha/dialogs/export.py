import wx
import wx.adv
from wx.lib.agw.customtreectrl import CustomTreeCtrl, TR_AUTO_CHECK_CHILD, TR_AUTO_CHECK_PARENT, TR_DEFAULT_STYLE
from models.datatable import DataTable
from paths import DATA_DIR
from tools.utilities import get_selected_listctrl_items


def save_string_to_file(frame, title, data, wildcard="CSV files (*.csv)|*.csv"):
    # from https://wxpython.org/Phoenix/docs/html/wx.FileDialog.html

    with wx.FileDialog(frame, title, DATA_DIR, wildcard=wildcard,
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return

        pathname = fileDialog.GetPath()
        try:
            with open(pathname, 'w') as file:
                file.write(data)
        except IOError:
            wx.LogError("Cannot save current data in file '%s'." % pathname)


class ExportCSVDialog(wx.Dialog):
    def __init__(self, app):
        wx.Dialog.__init__(self, None)

        self.app = app

        self.enabled = {'DVHs': self.app.dvh.has_data,
                        'DVHs Summary': self.app.dvh.has_data,
                        'Endpoints': self.app.endpoint.has_data,
                        'Radbio': self.app.radbio.has_data,
                        'Time Series': self.app.time_series.has_data,
                        'Regression': self.app.regression.has_data,
                        # 'Control Chart': self.app.control_chart.has_data
                        }

        checkbox_keys = ['DVHs', 'DVHs Summary', 'Endpoints', 'Radbio', 'Time Series', 'Regression']
        self.checkbox = {key: wx.CheckBox(self, wx.ID_ANY, key) for key in checkbox_keys}

        self.list_ctrl = {'Time Series': wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES),
                          # 'Control Chart': wx.ListCtrl(self, wx.ID_ANY,
                          # style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
                          }

        styles = TR_AUTO_CHECK_CHILD | TR_AUTO_CHECK_PARENT | TR_DEFAULT_STYLE
        self.tree_ctrl_regression = CustomTreeCtrl(self, wx.ID_ANY, agwStyle=styles)
        self.tree_ctrl_regression.SetBackgroundColour(wx.WHITE)
        # self.tree_ctrl_regression = wx.TreeCtrl(self, wx.ID_ANY)
        self.y_variable_nodes = {}
        self.x_variable_nodes = {}

        time_series_column = "Time Series Y-Axis"
        time_series_variables = self.app.time_series.combo_box_y_axis.GetItems()
        time_series_data = {time_series_column: time_series_variables}
        self.data_table_time_series = DataTable(self.list_ctrl['Time Series'],
                                                columns=[time_series_column], widths=[400])
        self.data_table_time_series.set_data(time_series_data, [time_series_column])

        # control_chart_column = "Charting Variable"
        # control_chart_variables = self.app.control_chart.combo_box_y_axis.GetItems()
        # control_chart_data = {control_chart_column: control_chart_variables}
        # self.data_table_control_chart = DataTable(self.list_ctrl['Control Chart'],
        #                                           columns=[control_chart_column], widths=[400])
        # self.data_table_control_chart.set_data(control_chart_data, [control_chart_column])

        self.button_select_data = {'Time Series': {'Select': wx.Button(self, wx.ID_ANY, "Select All"),
                                                   'Deselect': wx.Button(self, wx.ID_ANY, "Deselect All")}}
        # self.button_select_data = {'Time Series': {'Select': wx.Button(self, wx.ID_ANY, "Select All"),
        #                                            'Deselect': wx.Button(self, wx.ID_ANY, "Deselect All")},
        #                            'Control Chart': {'Select': wx.Button(self, wx.ID_ANY, "Select All"),
        #                                              'Deselect': wx.Button(self, wx.ID_ANY, "Deselect All")}}

        self.button_save = wx.Button(self, wx.ID_OK, "Save")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_select_all = wx.Button(self, wx.ID_ANY, 'Select All')
        self.button_deselect_all = wx.Button(self, wx.ID_ANY, 'Deselect All')

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.tree_ctrl_root = self.tree_ctrl_regression.AddRoot('Regressions', ct_type=1)
        self.image_list = wx.ImageList(16, 16)
        self.images = {'y': self.image_list.Add(wx.Image("icons/icon_custom_Y.png",
                                                         wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'x': self.image_list.Add(wx.Image("icons/icon_custom_X.png",
                                                         wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())}
        self.tree_ctrl_regression.AssignImageList(self.image_list)
        self.build_regression_tree()

        self.run()

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Export Data to CSV")

        self.button_select_all.SetToolTip('Only data objects with data will be enabled.')

        self.validate_ui_objects()

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_select_all, id=self.button_select_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_deselect_all, id=self.button_deselect_all.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_time_series_select_all,
                  id=self.button_select_data['Time Series']['Select'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_time_series_deselect_all,
                  id=self.button_select_data['Time Series']['Deselect'].GetId())
        # self.Bind(wx.EVT_BUTTON, self.on_control_chart_select_all,
        #           id=self.button_select_data['Control Chart']['Select'].GetId())
        # self.Bind(wx.EVT_BUTTON, self.on_control_chart_deselect_all,
        #           id=self.button_select_data['Control Chart']['Deselect'].GetId())
        # self.Bind(wx.EVT_CHECKBOX, self.on_dvh_check, id=self.checkbox['DVHs'].GetId())

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_data = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Data Selection"), wx.VERTICAL)
        # sizer_control_chart = wx.BoxSizer(wx.VERTICAL)
        # sizer_control_chart_listctrl = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_control_chart_checkboxes = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_control_chart_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_regression = wx.BoxSizer(wx.VERTICAL)
        sizer_regression_treectrl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time_series = wx.BoxSizer(wx.VERTICAL)
        sizer_time_series_listctrl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time_series_checkboxes = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time_series_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_radbio = wx.BoxSizer(wx.VERTICAL)
        sizer_endpoints = wx.BoxSizer(wx.VERTICAL)
        sizer_dvhs = wx.BoxSizer(wx.VERTICAL)
        sizer_dvhs_checkboxes = wx.BoxSizer(wx.HORIZONTAL)

        keys = ['DVHs', 'Endpoints', 'Radbio', 'Time Series', 'Regression']
        static_line = {key: wx.StaticLine(self, wx.ID_ANY) for key in keys}

        sizer_dvhs_checkboxes.Add(self.checkbox['DVHs'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_dvhs_checkboxes.Add(self.checkbox['DVHs Summary'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_dvhs.Add(sizer_dvhs_checkboxes, 1, wx.ALIGN_CENTER | wx.EXPAND, 0)
        sizer_dvhs.Add(static_line['DVHs'], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_dvhs, 0, wx.ALL | wx.EXPAND, 5)

        sizer_endpoints.Add(self.checkbox['Endpoints'], 0, wx.ALL, 5)
        sizer_endpoints.Add(static_line['Endpoints'], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_endpoints, 0, wx.ALL | wx.EXPAND, 5)

        sizer_radbio.Add(self.checkbox['Radbio'], 0, wx.ALL, 5)
        sizer_radbio.Add(static_line['Radbio'], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_radbio, 0, wx.ALL | wx.EXPAND, 5)

        sizer_time_series_checkboxes.Add(self.checkbox['Time Series'], 1, wx.EXPAND, 0)
        sizer_time_series_buttons.Add(self.button_select_data['Time Series']['Select'], 0, wx.ALL | wx.EXPAND, 5)
        sizer_time_series_buttons.Add(self.button_select_data['Time Series']['Deselect'], 0, wx.ALL | wx.EXPAND, 5)
        sizer_time_series_checkboxes.Add(sizer_time_series_buttons, 1, wx.EXPAND, 0)
        sizer_time_series.Add(sizer_time_series_checkboxes, 0, wx.ALL | wx.EXPAND, 5)
        sizer_time_series_listctrl.Add((20, 20), 0, 0, 0)
        sizer_time_series_listctrl.Add(self.list_ctrl['Time Series'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_time_series.Add(sizer_time_series_listctrl, 0, wx.ALL | wx.EXPAND, 5)
        sizer_time_series.Add(static_line['Time Series'], 0, wx.EXPAND | wx.TOP, 5)
        sizer_data.Add(sizer_time_series, 0, wx.ALL | wx.EXPAND, 5)

        sizer_regression.Add(self.checkbox['Regression'], 0, wx.ALL, 5)
        sizer_regression_treectrl.Add((20, 20), 0, 0, 0)
        sizer_regression_treectrl.Add(self.tree_ctrl_regression, 1, wx.EXPAND, 0)
        sizer_regression.Add(sizer_regression_treectrl, 0, wx.ALL | wx.EXPAND, 5)
        # sizer_regression.Add(static_line['Regression'], 0, wx.EXPAND, 0)
        sizer_data.Add(sizer_regression, 0, wx.ALL | wx.EXPAND, 5)

        # sizer_control_chart_checkboxes.Add(self.checkbox['Control Chart'], 1, wx.EXPAND, 0)
        # sizer_control_chart_buttons.Add(self.button_select_data['Control Chart']['Select'], 0, wx.ALL | wx.EXPAND, 5)
        # sizer_control_chart_buttons.Add(self.button_select_data['Control Chart']['Deselect'], 0, wx.ALL | wx.EXPAND, 5)
        # sizer_control_chart_checkboxes.Add(sizer_control_chart_buttons, 1, wx.EXPAND, 0)
        # sizer_control_chart.Add(sizer_control_chart_checkboxes, 0, wx.ALL | wx.EXPAND, 5)
        # sizer_control_chart_listctrl.Add((20, 20), 0, 0, 0)
        # sizer_control_chart_listctrl.Add(self.list_ctrl['Control Chart'], 1, wx.ALL | wx.EXPAND, 5)
        # sizer_control_chart.Add(sizer_control_chart_listctrl, 0, wx.ALL | wx.EXPAND, 5)
        # sizer_data.Add(sizer_control_chart, 0, wx.ALL | wx.EXPAND, 5)

        sizer_main.Add(sizer_data, 0, wx.ALL | wx.EXPAND, 5)

        sizer_main_buttons.Add(self.button_select_all, 0, wx.ALL, 5)
        sizer_main_buttons.Add(self.button_deselect_all, 0, wx.ALL, 5)
        # sizer_main_buttons.Add((50, 20), 0, 0, 0)
        sizer_main_buttons.Add(self.button_save, 0, wx.ALL, 5)
        sizer_main_buttons.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_main.Add(sizer_main_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()
        self.Center()

    def build_regression_tree(self):
        reg = self.app.regression
        for y_value in list(reg.y_variable_nodes):
            for x_value in list(reg.x_variable_nodes[y_value]):
                if y_value not in list(self.y_variable_nodes):
                    self.y_variable_nodes[y_value] = self.tree_ctrl_regression.AppendItem(self.tree_ctrl_root, y_value, ct_type=1)
                    self.tree_ctrl_regression.SetItemData(self.y_variable_nodes[y_value], None)
                    self.tree_ctrl_regression.SetItemImage(self.y_variable_nodes[y_value], self.images['y'],
                                                           wx.TreeItemIcon_Normal)
                if y_value not in list(self.x_variable_nodes):
                    self.x_variable_nodes[y_value] = {}
                if x_value not in self.x_variable_nodes[y_value]:
                    self.x_variable_nodes[y_value][x_value] = \
                        self.tree_ctrl_regression.AppendItem(self.y_variable_nodes[y_value], x_value, ct_type=1)
                    self.tree_ctrl_regression.SetItemData(self.x_variable_nodes[y_value][x_value], None)
                    self.tree_ctrl_regression.SetItemImage(self.x_variable_nodes[y_value][x_value], self.images['x'],
                                                           wx.TreeItemIcon_Normal)
            self.tree_ctrl_regression.ExpandAll()

    def set_checkbox_values(self, value):
        for checkbox in self.checkbox.values():
            checkbox.SetValue(value)

    def on_select_all(self, evt):
        self.set_checkbox_values(True)
        self.validate_ui_objects(allow_enable=False)

    def on_deselect_all(self, evt):
        self.set_checkbox_values(False)
        self.validate_ui_objects(allow_enable=False)

    def on_time_series_select_all(self, evt):
        self.data_table_time_series.apply_selection_to_all(1)

    def on_time_series_deselect_all(self, evt):
        self.data_table_time_series.apply_selection_to_all(0)

    # def on_control_chart_select_all(self, evt):
    #     self.data_table_control_chart.apply_selection_to_all(1)
    #
    # def on_control_chart_deselect_all(self, evt):
    #     self.data_table_control_chart.apply_selection_to_all(0)

    def validate_ui_objects(self, allow_enable=True):
        tables = {'Time Series': self.data_table_time_series,
                  # 'Control Chart': self.data_table_control_chart
                  }
        for key, data_table in tables.items():
            state = data_table.has_data
            if not state or (state and allow_enable):
                self.list_ctrl[key].Enable(state)
                self.button_select_data[key]['Select'].Enable(state)
                self.button_select_data[key]['Deselect'].Enable(state)

        for key, value in self.enabled.items():
            if not value or (value and allow_enable):
                self.checkbox[key].SetValue(value)
                self.checkbox[key].Enable(value)

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            save_string_to_file(self, 'Export CSV Data', self.csv)
        self.Destroy()

    def is_checked(self, key):
        return self.checkbox[key].GetValue()

    def on_dvh_check(self, evt):
        if not self.is_checked('DVHs'):
            self.checkbox['DVHs Summary'].SetValue(False)

    @property
    def csv(self):
        csv_data = []

        csv_key = ['DVHs', 'Endpoints', 'Radbio', 'Time Series']
        csv_obj = [None, self.app.endpoint, self.app.radbio, self.app.time_series, self.app.control_chart]
        for i, key in enumerate(csv_key):
            if self.is_checked(key):
                csv_data.append('%s\n' % key)
                if key == 'DVHs':
                    csv_data.append(self.app.plot.get_csv(include_summary=self.is_checked('DVHs Summary'),
                                                          include_dvhs=self.is_checked('DVHs')))
                else:
                    if key == 'Time Series':
                        selection_indices = get_selected_listctrl_items(self.list_ctrl['Time Series'])
                        y_choices = self.app.control_chart.combo_box_y_axis.GetItems()
                        selection = [y for i, y in enumerate(y_choices) if i in selection_indices]
                    else:
                        selection = None
                    csv_data.append(csv_obj[i].get_csv(selection=selection))
                csv_data.append('\n\n')

        return '\n'.join(csv_data)
