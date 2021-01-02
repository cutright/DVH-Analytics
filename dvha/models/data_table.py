#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.data_table.py
"""
A class to sync a data object and list_ctrl
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from copy import deepcopy
import wx
from dvha.tools.errors import push_to_log
from dvha.tools.utilities import (
    get_selected_listctrl_items,
    get_sorted_indices,
)


class DataTable:
    """
    This is a helper class containing the UI elements of the list_ctrl.  Adding / Changing data with this class
    will automatically update UI elements.
    """

    def __init__(
        self, list_ctrl, data=None, columns=None, widths=None, formats=None
    ):
        """
        :param list_ctrl: the list_ctrl in the GUI to be updated with data in this class
        :type list_ctrl: ListCtrl
        :param data: data should be formatted in a dictionary with keys being the column names and values being lists
        :type data: dict
        :param columns: the keys of the data object to be visible in the list_ctrl
        :type columns: list
        :param widths: optionally specify the widths of the columns
        :type widths: list
        :param formats: optionally specify wx Format values (e.g., wx.LIST_FORMAT_LEFT)
        :type formats: list
        """

        self.layout = list_ctrl

        self.sort_indices = None

        self.data = deepcopy(data)
        self.columns = deepcopy(columns)
        self.widths = widths
        if formats:
            self.formats = formats
        else:
            if not self.columns:
                column_length = 0
            else:
                column_length = len(self.columns)
            self.formats = [wx.LIST_FORMAT_LEFT] * column_length
        if data:
            # TODO: Initializing class with duplicates data in view?
            self.set_data(data, columns, formats=formats)
        self.set_data_in_layout()

    def get_save_data(self):
        """
        This function is used to save data within a .dvha file
        :return: a copy of the data, columns, widths, and formats
        :rtype: dict
        """
        return deepcopy(
            {
                "data": self.data,
                "columns": self.columns,
                "widths": self.widths,
                "formats": self.formats,
            }
        )

    def load_save_data(self, save_data, ignore_layout=False):
        """
        This function is used to load data from saved .dvha file
        :param save_data: output from get_save_data
        :type save_data: dict
        :param ignore_layout: If true, do not update layout
        :type ignore_layout: bool
        """
        self.widths = deepcopy(save_data["widths"])
        self.set_column_widths()
        self.set_data(
            save_data["data"],
            save_data["columns"],
            ignore_layout=ignore_layout,
        )

    def set_data(self, data, columns, formats=None, ignore_layout=False):
        """
        Use this function to update data and properly update the layout
        :param data: data should be formatted in a dictionary with keys being the column names and values being lists
        :type data: dict
        :param columns: the keys of the data object to be visible in the list_ctrl
        :type columns: list
        :param formats: optionally specify wx Format values (e.g., wx.LIST_FORMAT_LEFT)
        :type formats: list
        :param ignore_layout: If true, do not update layout
        :type ignore_layout: bool
        """
        if formats:
            self.formats = formats
        elif columns and len(columns) != len(self.formats):
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

        self.sort_indices = None  # If len of new data is different than previous, sorting may crash

    def set_layout_columns(self):
        self.layout.DeleteAllColumns()
        for i, col in enumerate(self.columns):
            self.layout.AppendColumn(col, format=self.formats[i])

    @property
    def keys(self):
        return [col for col in self.columns]

    @property
    def column_count(self):
        if self.columns:
            return len(self.columns)
        return 0

    @property
    def row_count(self):
        if self.data:
            return len(self.data[self.columns[0]])
        return 0

    def data_to_list_of_rows(self):
        """
        Convert self.data which is formatted as a dict by columns into a list of rows as needed for list_ctrl
        self.data is formatted this way out of convience for plotting with bokeh
        :return: data in the format of list of rows
        :rtype: list
        """
        if self.data and self.keys:
            return [
                [self.data[col][row] for col in self.columns]
                for row in range(self.row_count)
            ]
        else:
            return []

    def add_column(self, column, format=wx.LIST_FORMAT_LEFT):
        """
        Add an empty column to the data and layout
        :param column: name of the column
        :type column: str
        :param format: optionally specify the wx format value (wx.LIST_FORMAT_LEFT by default)
        """
        if self.layout:
            self.layout.AppendColumn(column, format=format)
        self.columns.append(column)
        self.data[column] = [""] * self.row_count

    def delete_column(self, column):
        """
        Delete the specified column data and the layout
        :param column: column to be deleted
        :type column: str
        """
        if column in self.keys:
            index = self.columns.index(column)
            if self.layout:
                try:
                    self.layout.DeleteColumn(index)
                except Exception as e:
                    msg = "DataTable.delete_column: Could not delete column in layout"
                    push_to_log(e, msg=msg)
            self.data.pop(column)
            self.columns.pop(index)

    def set_data_in_layout(self):
        """
        Retrieve data from self.data, convert to row_data format, add to layout
        """
        row_data = self.data_to_list_of_rows()

        for row in row_data:
            self.append_row(row, layout_only=True)

    def append_row(self, row, layout_only=False):
        """
        Add a row of data
        :param row: data ordered by self.columns
        :type row: list
        :param layout_only: If true, only add row to the GUI
        :type layout_only: bool
        """
        if not layout_only:
            self.append_row_to_data(row)
        if self.layout:
            index = self.layout.InsertItem(50000, str(row[0]))
            for i in range(len(row))[1:]:
                if isinstance(row[i], int):
                    value = "%d" % row[i]
                elif isinstance(row[i], float):
                    value = "%0.2f" % row[i]
                else:
                    value = str(row[i])
                self.layout.SetItem(index, i, value)

    def append_row_to_data(self, row):
        """
        Add a row of data to self.data
        :param row: data ordered by self.columns
        :type row: list
        """
        if not self.data:
            columns = self.keys
            self.data = {columns[i]: [value] for i, value in enumerate(row)}
        else:
            for i, key in enumerate(self.keys):
                self.data[key].append(row[i])

    def edit_row_to_data(self, row, index):
        """
        Replace a row of data with a provided row and index, edits self.data only
        :param row: data ordered by self.columns
        :type row: list
        :param index: the row index
        :type index: int
        """
        for i, key in enumerate(self.keys):
            self.data[key][index] = row[i]

    def delete_row(self, index, layout_only=False):
        """
        Delete a specific row of data
        :param index: the row index
        :type index: int
        :param layout_only: If True, do not remove the row from self.data
        :type layout_only: bool
        """
        if index is not None:
            if not layout_only:
                for key in self.keys:
                    self.data[key].pop(index)
            if self.layout:
                self.layout.DeleteItem(index)

    def delete_all_rows(self, layout_only=False, force_delete_data=False):
        """
        Clear all data from self.data and the layout view
        :param layout_only: If True, do not remove the row from self.data
        :type layout_only: bool
        :param force_delete_data: If true, force deletion even if layout is not set
        """
        if self.layout:
            self.layout.DeleteAllItems()

        if self.layout or force_delete_data:
            if not layout_only:
                if self.data:
                    for key in self.keys:
                        self.data[key] = []

    def edit_row(self, row, index):
        """
        Replace a row of data with a provided row and index, update table view
        :param row: data ordered by self.columns
        :type row: list
        :param index: the row index
        :type index: int
        """
        self.edit_row_to_data(row, index)
        if self.layout:
            for i in range(len(row)):
                self.layout.SetItem(index, i, str(row[i]))

    def get_value(self, row_index, column_index):
        """
        Get a specific table value with a column name and row index
        :param row_index: retrieve value from row with this index
        :type row_index: int
        :param column_index: retrieve value from column with this index
        :type column_index: int
        :return: value corresponding to provided indices
        """
        return self.data[self.keys[column_index]][row_index]

    def get_row(self, row_index):
        """
        Get a row of data from self.data wtih the given row index
        :param row_index: retrieve all values from row with this index
        :type row_index: int
        :return: values for the specified row
        :rtype: list
        """
        return [self.data[key][row_index] for key in self.keys]

    def set_column_width(self, index, width):
        """
        Change the column width in the view
        :param index: index of column
        :type index: int
        :param width: the specified width
        :type width: int
        """
        self.layout.SetColumnWidth(index, width)

    def set_column_widths(self, auto=False):
        """Set all widths in layout based on self.widths"""
        if auto:
            for i in range(len(self.columns)):
                self.set_column_width(i, wx.LIST_AUTOSIZE_USEHEADER)
        else:
            if self.widths is not None:
                for i, width in enumerate(self.widths):
                    self.set_column_width(i, width)

    def clear(self):
        """Delete all data in self.data and clear the table view"""
        self.delete_all_rows()
        self.layout.DeleteAllColumns()

    def get_csv(self, extra_column_data=None):
        """
        This function will return a csv string of the data currently in this object
        :param extra_column_data: if there is additional data you'd like in the csv, pass the column data as a
        dictionary with:
            keys corresponding to column index
            values are dicts like {'title': str, 'data': list_of_data}
        :type extra_column_data: dict
        :return: csv string
        :rtype: str
        """

        data = deepcopy(self.data_for_csv)
        if extra_column_data:
            self.insert_columns_into_data_for_csv(data, extra_column_data)
        csv_data = []
        for row in data:
            csv_data.append(",".join(str(i) for i in row))

        return "\n".join(csv_data)

    @property
    def data_for_csv(self):
        """
        Iterate through self.data to get a list of csv rows
        :return: csv data
        :rtype: list
        """
        data = [self.columns]
        for row_index in range(self.row_count):
            row = []
            for key in self.keys:
                raw_value = self.data[key][row_index]
                if isinstance(raw_value, float):
                    value = "%0.2f" % raw_value
                else:
                    value = str(raw_value).replace(",", ";")
                row.append(value)
            data.append(row)
        return data

    @staticmethod
    def insert_column_into_data_for_csv(
        data_for_csv, columns_dict_value, index
    ):
        """
        Insert a column of data into the data returned from data_for_csv
        :param data_for_csv: rows of csv data
        :type data_for_csv: list
        :param columns_dict_value: title and data information. see extra_column_information in get_csv
        :type columns_dict_value: dict
        :param index: index of column to be inserted
        :type index: int
        """
        columns_dict_value["data"].insert(0, columns_dict_value["title"])
        for i, row in enumerate(data_for_csv):
            row.insert(
                index, str(columns_dict_value["data"][i]).replace(",", ";")
            )

    def insert_columns_into_data_for_csv(self, data_for_csv, columns_dict):
        """
        Insert columns_dict data into the provided data_for_csv
        :param data_for_csv: return from data_for_csv function
        :type data_for_csv: list
        :param columns_dict: extra columns data formatted as specified in get_csv
        :type columns_dict: dict
        """
        indices = list(columns_dict)
        indices.sort()
        for index in indices:
            self.insert_column_into_data_for_csv(
                data_for_csv, columns_dict[index], index
            )

    @property
    def selected_row_data(self):
        """
        :return: row data of the currently selected row in the GUI
        :rtype: list
        """
        return [
            self.get_row(index)
            for index in get_selected_listctrl_items(self.layout)
        ]

    @property
    def selected_row_data_with_index(self):
        return [
            [index, self.get_row(index)]
            for index in get_selected_listctrl_items(self.layout)
        ]

    def apply_selection_to_all(self, state):
        """
        Select or Deselect all rows in the layout
        :param state: True for selection, False for deselection
        :type state: bool
        """
        for i in range(self.row_count):
            self.layout.Select(i, on=state)

    @property
    def has_data(self):
        return bool(self.row_count)

    def sort_table(self, evt):

        if self.data:
            key = self.columns[
                evt.Column
            ]  # get the column name from the column index (evt.Column)
            sort_indices = get_sorted_indices(
                self.data[key]
            )  # handles str and float mixtures

            if self.sort_indices is None:
                self.sort_indices = list(range(len(self.data[key])))

            # reverse order if already sorted
            if sort_indices == list(range(len(sort_indices))):
                sort_indices = sort_indices[::-1]

            self.sort_indices = [
                self.sort_indices[i] for i in sort_indices
            ]  # keep original order

            # reorder data and reinitialize table view
            self.data = {
                column: [self.data[column][i] for i in sort_indices]
                for column in self.columns
            }
            self.set_data(self.data, self.columns, self.formats)

    def get_data_in_original_order(self):
        if self.sort_indices is None:
            return self.data
        return {
            column: [self.data[column][i] for i in self.sort_indices]
            for column in self.columns
        }

    def get_unique_values(self, column):
        return sorted(set(self.data[column]))
