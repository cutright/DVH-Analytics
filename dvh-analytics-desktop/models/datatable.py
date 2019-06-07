from copy import deepcopy
import wx
from tools.utilities import get_selected_listctrl_items


class DataTable:

    def __init__(self, listctrl, data=None, columns=None, widths=None, formats=None):

        self.layout = listctrl

        # TODO: Initializing class with data does not display data?
        self.data = deepcopy(data)
        self.columns = deepcopy(columns)
        self.widths = widths
        if formats:
            self.formats = formats
        else:
            self.formats = [wx.LIST_FORMAT_LEFT] * len(self.columns)

        self.set_data_in_layout()

    def get_save_data(self):
        return deepcopy({'data': self.data,
                         'columns': self.columns,
                         'widths': self.widths,
                         'formats': self.formats})

    def load_save_data(self, save_data, ignore_layout=False):
        self.widths = deepcopy(save_data['widths'])
        self.set_data(save_data['data'], save_data['columns'], ignore_layout=ignore_layout)

    def set_data(self, data, columns, formats=None, ignore_layout=False):
        if formats:
            self.formats = formats
        elif len(columns) != len(self.formats):
            self.formats = [wx.LIST_FORMAT_LEFT] * len(columns)
        delete_rows = bool(self.row_count)
        self.data = deepcopy(data)
        self.columns = deepcopy(columns)
        if delete_rows:
            self.delete_all_rows(layout_only=True)

        if not ignore_layout:
            self.set_layout_columns()
            self.set_data_in_layout()

        if self.widths:
            self.set_column_widths()

    def set_layout_columns(self):
        self.layout.DeleteAllColumns()
        for i, col in enumerate(self.columns):
            self.layout.AppendColumn(col, format=self.formats[i])

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

    def add_column(self, column, format=wx.LIST_FORMAT_LEFT):
        if self.layout:
            self.layout.AppendColumn(column, format=format)
        self.columns.append(column)
        self.data[column] = [''] * self.row_count

    def delete_column(self, column):
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
                if isinstance(row[i], float) or isinstance(row[i], int) and str(row[i]) not in {'True', 'False'}:
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
        if index is not None:
            if not layout_only:
                for key in self.keys:
                    self.data[key].pop(index)
            if self.layout:
                self.layout.DeleteItem(index)

    def delete_all_rows(self, layout_only=False, force_delete_data=False):
        if self.layout:
            self.layout.DeleteAllItems()

        if self.layout or force_delete_data:
            if not layout_only:
                if self.data:
                    for key in self.keys:
                        self.data[key] = []

    def edit_row(self, row, index):
        self.edit_row_to_data(row, index)
        if self.layout:
            for i in range(len(row)):
                self.layout.SetItem(index, i, str(row[i]))

    def get_value(self, row, column):
        return self.data[self.keys[column]][row]

    def get_row(self, index):
        return [self.data[key][index] for key in self.keys]

    def set_column_width(self, index, width):
        self.layout.SetColumnWidth(index, width)

    def set_column_widths(self):
        for i, width in enumerate(self.widths):
            self.set_column_width(i, width)

    def clear(self):
        self.delete_all_rows()
        self.layout.DeleteAllColumns()

    def get_csv(self, extra_column_data=None):
        """
        This function will return a csv string of the data currently in this object
        :param extra_column_data: if there is additional data you'd like in the csv, pass the column data as a
        dictionary with keys corresponding to column index, values are dicts like {'title': str, 'data': list_of_data}
        :type extra_column_data: dict
        :return: csv string
        :rtype: str
        """

        data = self.data_for_csv
        if extra_column_data:
            self.insert_columns_into_data_for_csv(data, extra_column_data)
        csv_data = []
        for row in data:
            csv_data.append(','.join(str(i) for i in row))

        return '\n'.join(csv_data)

    @property
    def data_for_csv(self):
        data = [self.columns]
        for row_index in range(self.row_count):
            row = []
            for key in self.keys:
                raw_value = self.data[key][row_index]
                if isinstance(raw_value, float):
                    value = "%0.2f" % raw_value
                else:
                    value = str(raw_value).replace(',', ';')
                row.append(value)
            data.append(row)
        return data

    @staticmethod
    def insert_column_into_data_for_csv(data_for_csv, columns_dict, index):
        columns_dict['data'].insert(0, columns_dict['title'])
        for i, row in enumerate(data_for_csv):
            row.insert(index, columns_dict['data'][i])

    def insert_columns_into_data_for_csv(self, data_for_csv, columns_dict):
        indices = list(columns_dict)
        indices.sort()
        for index in indices:
            self.insert_column_into_data_for_csv(data_for_csv, columns_dict[index], index)

    @property
    def selected_row_data(self):
        return [self.get_row(index) for index in get_selected_listctrl_items(self.layout)]

    def apply_selection_to_all(self, state):
        for i in range(self.row_count):
            self.layout.Select(i, on=state)

    @property
    def has_data(self):
        return bool(self.row_count)
