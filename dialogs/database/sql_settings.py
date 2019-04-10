import wx
from paths import SQL_CNF_PATH, parse_settings_file
from db.sql_connector import echo_sql_db
from db.sql_settings import write_sql_connection_settings, validate_sql_connection


class SQLSettingsDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="Database Connection Settings")

        self.keys = ['host', 'port', 'dbname', 'user', 'password']

        self.input = {key: wx.TextCtrl(self, wx.ID_ANY, "") for key in self.keys if key != 'password'}
        self.input['password'] = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PASSWORD)
        self.button = {'ok': wx.Button(self, wx.ID_OK, "OK"),
                       'cancel': wx.Button(self, wx.ID_CANCEL, "Cancel"),
                       'echo': wx.Button(self, wx.ID_ANY, "Echo")}

        self.Bind(wx.EVT_BUTTON, self.button_echo, id=self.button['echo'].GetId())

        self.__set_properties()
        self.__do_layout()
        self.Center()

        self.load_sql_settings()

    def __set_properties(self):
        self.SetTitle("SQL Connection Settings")

    def __do_layout(self):
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_echo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer = wx.GridSizer(5, 2, 5, 10)

        label_titles = ['Host:', 'Port:', 'Database Name:', 'User Name:', 'Password:']
        label = {key: wx.StaticText(self, wx.ID_ANY, label_titles[i]) for i, key in enumerate(self.keys)}

        for key in self.keys:
            grid_sizer.Add(label[key], 0, wx.ALL, 0)
            grid_sizer.Add(self.input[key], 0, wx.ALL | wx.EXPAND, 0)

        sizer_frame.Add(grid_sizer, 0, wx.ALL, 10)
        sizer_buttons.Add(self.button['ok'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button['cancel'], 1, wx.ALL | wx.EXPAND, 5)
        sizer_echo.Add(self.button['echo'], 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        sizer_frame.Add(sizer_echo, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        sizer_frame.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_frame)
        self.Fit()
        self.Layout()

    def load_sql_settings(self):
        config = parse_settings_file(SQL_CNF_PATH)

        for input_type in self.keys:
            if input_type in config:
                self.input[input_type].SetValue(config[input_type])

    def button_echo(self, evt):
        if self.valid_sql_settings:
            wx.MessageBox('Success!', 'Echo SQL Database', wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox('Invalid credentials!', 'Echo SQL Database', wx.OK | wx.ICON_WARNING)

    @property
    def valid_sql_settings(self):
        config = {key: self.input[key].GetValue() for key in self.keys if self.input[key].GetValue()}
        return echo_sql_db(config)


def run_sql_settings_dlg():
    dlg = SQLSettingsDialog()
    res = dlg.ShowModal()
    if res == wx.ID_OK:
        new_config = {key: dlg.input[key].GetValue() for key in dlg.keys if dlg.input[key].GetValue()}
        write_sql_connection_settings(new_config)
        if not validate_sql_connection(new_config):
            dlg = wx.MessageDialog(dlg, 'Connection to database could not be established.', 'ERROR!', wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
    dlg.Destroy()

    return res
