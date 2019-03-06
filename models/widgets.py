import wx
from .layout import LayoutObj
from copy import deepcopy


class Text(LayoutObj):
    def __init__(self, fp, value=''):
        super().__init__()

        self.layout = wx.StaticText(fp, label=value)

    def get_value(self):
        return self.layout.GetLabel()

    def set_value(self, value):
        self.layout.SetLabel(value)


class TextInput(LayoutObj):
    def __init__(self, fp, title='Title', value='', id=wx.ID_ANY):
        """
        :param fp: pointer to wx.Frame
        :param title: title of input widget
        :type title: str
        :param value: initial value
        :type value: str
        """
        super().__init__()

        self.layout = wx.BoxSizer(wx.VERTICAL)

        self.title = wx.StaticText(fp, label=title)
        self.text = wx.TextCtrl(fp, value=value, id=id, style=wx.TE_PROCESS_ENTER)
        self.id = id

        self.text_row = wx.BoxSizer(wx.HORIZONTAL)
        self.text_row.Add(self.text, 1, wx.EXPAND, self.border)

        self.layout.Add(self.title, 0, wx.EXPAND, self.border)
        self.layout.AddSpacer(5)
        self.layout.Add(self.text_row, 0, wx.EXPAND, self.border)

    def get_value(self):
        return self.text.GetValue()

    def get_title(self):
        return self.title.GetLabel()

    def set_value(self, value):
        self.text.SetValue(str(value))

    def set_title(self, title):
        self.title.SetLabelText(title)


class DropDown(LayoutObj):
    def __init__(self, fp, title='Title', value='', options=[''], id=wx.ID_ANY, width=200):
        """
        :param fp: pointer to wx.Frame
        :param title: title of input widget
        :type title: str
        """
        super().__init__()

        self.id = id

        self.layout = wx.BoxSizer(wx.VERTICAL)

        self.title = wx.StaticText(fp, label=title)
        self.text = wx.ComboBox(fp, choices=options, id=id, size=(width, 27), style=wx.CB_READONLY)

        if value and value in options:
            self.set_value(value)

        self.text_row = wx.BoxSizer(wx.HORIZONTAL)
        self.text_row.Add(self.text, 1, wx.EXPAND, self.border)

        self.layout.Add(self.title, 0, wx.EXPAND, self.border)
        self.layout.AddSpacer(5)
        self.layout.Add(self.text_row, 0, wx.EXPAND, self.border)

    def get_value(self):
        return self.text.GetValue()

    def get_title(self):
        return self.title.GetLabelText()

    def set_value(self, value):
        self.text.SetValue(value)

    def set_title(self, title):
        self.title.SetLabelText(title)

    def set_options(self, options):
        self.text.Clear()
        self.text.Append(options)


class DataTable:

    def __init__(self, listctrl, data=None, columns=None):
        self.round = round
        self.layout = listctrl

        self.data = deepcopy(data)
        self.columns = deepcopy(columns)

        self.set_data_in_layout()

    def set_data(self, data, columns):
        delete_table_rows = bool(self.row_count)
        self.data = deepcopy(data)
        self.columns = deepcopy(columns)
        if delete_table_rows:
            self.delete_all_rows(layout_only=True)
        self.set_layout_columns()
        self.set_data_in_layout()

    def set_layout_columns(self):
        self.layout.DeleteAllColumns()
        for col in self.columns:
            self.layout.AppendColumn(col)

    @property
    def keys(self):
        return [col for col in self.columns]

    @property
    def column_count(self):
        return len(self.columns)

    @property
    def row_count(self):
        if self.data:
            return len(self.data[self.columns[0]])
        return 0

    def data_to_list_of_rows(self):
        if self.data and self.keys:
            return [[self.data[col][row] for col in self.columns] for row in range(self.row_count)]
        else:
            return []

    def add_column(self, column):
        if self.layout:
            self.layout.AppendColumn(column)
        self.columns.append(column)
        self.data[column] = [''] * self.row_count

    def del_column(self, column):
        if column in self.keys:
            index = self.columns.index(column)
            if self.layout:
                self.layout.DeleteColumn(index)
            self.data.pop(column)
            self.columns.pop(index)

    def row_to_initial_data(self, row_data):
        columns = self.keys
        self.data = {columns[i]: [value] for i, value in enumerate(row_data)}

    def set_data_in_layout(self):
        row_data = self.data_to_list_of_rows()

        for row in row_data:
            self.append_row(row, layout_only=True)

    def append_row(self, row, layout_only=False):
        if not layout_only:
            self.append_row_to_data(row)
        if self.layout:
            index = self.layout.InsertItem(50000, str(row[0]))
            for i in range(len(row))[1:]:
                if isinstance(row[i], float) or isinstance(row[i], int) and self.round is not None:
                    value = "%0.2f" % row[i]
                else:
                    value = str(row[i])
                self.layout.SetItem(index, i, value)

    def append_row_to_data(self, row):
        if not self.data:
            self.row_to_initial_data(row)
        else:
            for i, key in enumerate(self.keys):
                self.data[key].append(row[i])

    def edit_row_to_data(self, row, index):
        for i, key in enumerate(self.keys):
            self.data[key][index] = row[i]

    def delete_row(self, index, layout_only=False):
        if not layout_only:
            for key in self.keys:
                self.data[key].pop(index)
        if self.layout:
            self.layout.DeleteItem(index)

    def delete_all_rows(self, layout_only=False):
        for i in list(range(self.row_count))[::-1]:
            self.delete_row(i, layout_only=layout_only)


    def edit_row(self, row, index):
        self.edit_row_to_data(row, index)
        if self.layout:
            for i in range(len(row))[1:]:
                self.layout.SetItem(index, i, str(row[i]))

    def get_value(self, row, column):
        return self.data[self.keys[column]][row]

    def get_row(self, index):
        return [self.data[key][index] for key in self.keys]

    def set_column_width(self, index, width):
        self.layout.SetColumnWidth(index, width)
