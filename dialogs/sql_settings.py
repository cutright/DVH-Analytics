import wx
from options import get_settings, parse_settings_file


class SQLSettingsDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="SQL Connection Settings")

        self.keys = ['host', 'port', 'dbname', 'user', 'password']
        self.SetSize((300, 240))

        self.input = {key: wx.TextCtrl(self, wx.ID_ANY, "") for key in self.keys if key != 'password'}
        self.input['password'] = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PASSWORD)
        self.button = {'ok': wx.Button(self, wx.ID_OK, "OK"),
                       'cancel': wx.Button(self, wx.ID_CANCEL, "Cancel")}

        self.__set_properties()
        self.__do_layout()
        self.Center()

        self.load_sql_settings()

    def __set_properties(self):
        self.SetTitle("SQL Connection Settings")

    def __do_layout(self):
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer = wx.GridSizer(5, 2, 5, 10)

        label_titles = ['Host:', 'Port:', 'Database Name:', 'User Name:', 'Password:']
        label = {key: wx.StaticText(self, wx.ID_ANY, label_titles[i]) for i, key in enumerate(self.keys)}

        for key in self.keys:
            grid_sizer.Add(label[key], 0, wx.ALL, 0)
            grid_sizer.Add(self.input[key], 0, wx.ALL | wx.EXPAND, 0)

        sizer_frame.Add(grid_sizer, 0, wx.ALL, 20)
        sizer_buttons.Add(self.button['ok'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button['cancel'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_frame.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_frame)
        self.Layout()

    def load_sql_settings(self):
        abs_file_path = get_settings('sql')
        config = parse_settings_file(abs_file_path)

        for input_type in self.keys:
            if input_type in config:
                self.input[input_type].SetValue(config[input_type])


# class SQLSettingsDialog(wx.Dialog):
#
#     def __init__(self, *args, **kw):
#         wx.Dialog.__init__(self, None, title="SQL Connection Settings")
#
#         self.button_ok = wx.Button(self, label='OK', id=wx.ID_OK)
#         self.button_cancel = wx.Button(self, label='Cancel', id=wx.ID_CANCEL)
#
#         self.host = TextInput(self, title='Host:')
#         self.port = TextInput(self, title='Port:')
#         self.dbname = TextInput(self, title='Database Name:')
#         self.user = TextInput(self, title='User Name:')
#         self.password = TextInput(self, title='Password:')
#
#         layout = column(row(self.host),
#                         row(self.port),
#                         row(self.dbname),
#                         row(self.user),
#                         row(self.password),
#                         row(self.button_ok, self.button_cancel))
#
#         self.load_sql_settings()
#
#         self.SetSizer(layout)
#         self.SetSize((500, 400))
#         self.Center()
#
#     def load_sql_settings(self):
#         abs_file_path = get_settings('sql')
#         config = parse_settings_file(abs_file_path)
#
#         for input_type in ['host', 'port', 'dbname', 'user', 'password']:
#             if input_type in config:
#                 getattr(self, input_type).set_value(config[input_type])
