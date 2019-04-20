import wx
import wx.adv
from dateutil.parser import parse as parse_date


class DatePicker(wx.Dialog):
    def __init__(self, title='', initial_date=None):
        wx.Dialog.__init__(self, None, title=title)

        self.calendar_ctrl = wx.adv.CalendarCtrl(self, wx.ID_ANY,
                                                 style=wx.adv.CAL_SHOW_HOLIDAYS | wx.adv.CAL_SHOW_SURROUNDING_WEEKS)
        if initial_date:
            self.calendar_ctrl.SetDate(parse_date(initial_date))

        self.button = {'apply': wx.Button(self, wx.ID_OK, "Apply"),
                       'delete': wx.Button(self, wx.ID_ANY, "Delete"),
                       'cancel': wx.Button(self, wx.ID_CANCEL, "Cancel")}

        self.none = False

        self.__do_layout()
        self.__do_bind()

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(self.calendar_ctrl, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        for button in self.button.values():
            sizer_buttons.Add(button, 0, wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 1, wx.ALIGN_CENTER | wx.BOTTOM | wx.TOP, 10)
        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_delete, id=self.button['delete'].GetId())

    @property
    def date(self):
        if self.none:
            return ''
        date = self.calendar_ctrl.GetDate()
        return "%s/%s/%s" % (date.month+1, date.day, date.year)

    def on_delete(self, evt):
        self.none = True
        self.Close()
