import wx


class LayoutObj:
    def __init__(self):
        self.border = 5
        self.layout = []


def row(*objects, flags=None, border=5):
    return get_sizer(wx.HORIZONTAL, objects, flags, border)


def column(*objects, flags=None, border=5):
    return get_sizer(wx.VERTICAL, objects, flags, border)


def get_sizer(orientation, objects, flags, border):
    if not flags:
        flags = [0] * len(objects)
    sizer = wx.BoxSizer(orientation)
    for i, obj in enumerate(objects):
        if isinstance(obj, LayoutObj):
            sizer.Add(obj.layout, flags[i], wx.EXPAND | wx.ALL, obj.border)
        else:
            sizer.Add(obj, flags[i], wx.EXPAND | wx.ALL, border)
    return sizer


class TableColumn:
    def __init__(self, field=None, title=None, width=100, format=wx.LIST_FORMAT_LEFT):
        self.field = field
        if not title:
            self.title = field
        else:
            self.title = title
        self.width = width
        self.format = format
