#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import wx
from models.datatable import DataTable
from db.sql_columns import all_columns as sql_column_info


class QueriedDataFrame(wx.Frame):
    def __init__(self, title, data_obj, sql_table):
        wx.Frame.__init__(self, None, title=title)

        self.data = data_obj
        self.sql_table = sql_table

        self.list_ctrl = wx.ListCtrl(self, wx.ID_ANY,
                                     style=wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.data_table = DataTable(self.list_ctrl, data=self.table_data, columns=self.columns)

        self.__set_properties()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetSize((1200, 800))

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 20)
        self.SetSizer(sizer_wrapper)
        # self.Fit()
        self.Center()

    @property
    def columns(self):
        if self.sql_table == 'DVHs':
            columns = self.data.keys
        elif self.sql_table == 'Rxs':
            columns = ['plan_name', 'fx_dose', 'rx_percent', 'fxs', 'rx_dose', 'fx_grp_number', 'fx_grp_count',
                       'fx_grp_name', 'normalization_method', 'normalization_object']
        else:
            columns = [obj['var_name'] for obj in sql_column_info.values() if obj['table'] == self.sql_table]

        for starter_column in ['study_instance_uid', 'mrn']:
            if starter_column in columns:
                columns.pop(columns.index(starter_column))
            columns.insert(0, starter_column)

        return columns

    @property
    def table_data(self):
        return {column: getattr(self.data, column) for column in self.columns}

    def run(self):
        self.Show()
