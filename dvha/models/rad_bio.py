#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.rad_bio.py
"""
Class for the Rad Bio frame in the main view
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from copy import deepcopy
from dvha.models.data_table import DataTable
from dvha.models.dvh import calc_eud, calc_tcp
from dvha.tools.utilities import convert_value_to_str, get_selected_listctrl_items, float_or_none, get_window_size
from dvha.dialogs.export import save_data_to_file


class RadBioFrame:
    """
    Object to be passed into notebook panel for the Rad Bio tab
    """
    def __init__(self, parent, dvh, time_series, regression, control_chart):
        """
        :param parent:  notebook panel in main view
        :type parent: Panel
        :param dvh: dvh data object
        :type dvh: DVH
        :param time_series: Time Series object in notebook
        :type time_series: TimeSeriesFrame
        :param regression: Regression frame object in notebook
        :type regression: RegressionFrame
        :param control_chart: Control Chart frame object in notebook
        :type control_chart: ControlChartFrame
        """

        self.parent = parent
        self.dvh = dvh
        self.time_series = time_series
        self.regression = regression
        self.control_chart = control_chart

        self.table_published_values = wx.ListCtrl(self.parent, wx.ID_ANY,
                                                  style=wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.text_input_eud_a = wx.TextCtrl(self.parent, wx.ID_ANY, "")
        self.text_input_gamma_50 = wx.TextCtrl(self.parent, wx.ID_ANY, "")
        self.text_input_td_50 = wx.TextCtrl(self.parent, wx.ID_ANY, "")
        self.button_apply_parameters = wx.Button(self.parent, wx.ID_ANY, "Apply Parameters")
        self.button_export = wx.Button(self.parent, wx.ID_ANY, "Export")
        self.table_rad_bio = wx.ListCtrl(self.parent, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.columns = ['MRN', 'ROI Name', 'a', u'\u03b3_50', 'TD or TCD', 'EUD', 'NTCP or TCP', 'PTV Overlap',
                        'ROI Type', 'Rx Dose', 'Total Fxs', 'Fx Dose']
        self.width = [100, 175, 50, 50, 80, 80, 80, 100, 100, 100, 100, 100]
        formats = [wx.LIST_FORMAT_RIGHT] * len(self.columns)
        formats[0] = wx.LIST_FORMAT_LEFT
        formats[1] = wx.LIST_FORMAT_LEFT
        self.data_table_rad_bio = DataTable(self.table_rad_bio, columns=self.columns,
                                            widths=self.width, formats=formats)

        self.__set_properties()
        self.__do_layout()

        parent.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_parameter_select, self.table_published_values)
        parent.Bind(wx.EVT_BUTTON, self.apply_parameters, id=self.button_apply_parameters.GetId())
        parent.Bind(wx.EVT_BUTTON, self.on_export_csv, id=self.button_export.GetId())

        self.disable_buttons()

    def __set_properties(self):
        self.table_published_values.AppendColumn("Structure", format=wx.LIST_FORMAT_LEFT, width=150)
        self.table_published_values.AppendColumn("Endpoint", format=wx.LIST_FORMAT_LEFT, width=300)
        self.table_published_values.AppendColumn("a", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_published_values.AppendColumn(u"\u03b3_50", format=wx.LIST_FORMAT_LEFT, width=-1)
        self.table_published_values.AppendColumn("TD_50", format=wx.LIST_FORMAT_LEFT, width=-1)

        for i, col in enumerate(self.columns):
            self.table_rad_bio.AppendColumn(col, width=self.width[i])

        self.published_data = [['Brain', 'Necrosis', 5, 3, 60],
                               ['Brainstem', 'Necrosis', 7, 3, 65],
                               ['Optic Chasm', 'Blindness', 25, 3, 65],
                               ['Colon', 'Obstruction/Perforation', 6, 4, 55],
                               ['Ear (mid/ext)', 'Acute serous otitus', 31, 3, 40],
                               ['Ear (mid/ext)', 'Chronic serous otitus', 31, 4, 65],
                               ['Esophagus', 'Perforation', 19, 4, 68],
                               ['Heart', 'Pericarditus', 3, 3, 50],
                               ['Kidney', 'Nephritis', 1, 3, 28],
                               ['Lens', 'Cataract', 3, 1, 18],
                               ['Liver', 'Liver Failure', 3, 3, 40],
                               ['Lung', 'Pneumontis', 1, 2, 24.5],
                               ['Optic Nerve', 'Blindness', 25, 3, 65],
                               ['Retina', 'Blindness', 15, 2, 65]]

        for row in self.published_data:
            index = self.table_published_values.InsertItem(50000, str(row[0]))
            for i in [1, 2, 3, 4]:
                self.table_published_values.SetItem(index, i, str(row[i]))

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_parameters = wx.BoxSizer(wx.VERTICAL)
        sizer_parameters_input = wx.StaticBoxSizer(wx.StaticBox(self.parent, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_button = wx.BoxSizer(wx.VERTICAL)
        sizer_button_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_td_50 = wx.BoxSizer(wx.VERTICAL)
        sizer_gamma_50 = wx.BoxSizer(wx.VERTICAL)
        sizer_eud = wx.BoxSizer(wx.VERTICAL)
        sizer_published_values = wx.BoxSizer(wx.VERTICAL)

        label_published_values = wx.StaticText(self.parent, wx.ID_ANY,
                                               "Published EUD Parameters from Emami et. al. for 1.8-2.0Gy "
                                               "fractions (Click to apply)")
        label_published_values.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                               wx.FONTWEIGHT_BOLD, 0, ""))
        sizer_published_values.Add(label_published_values, 0, wx.ALL, 5)
        sizer_published_values.Add(self.table_published_values, 1, wx.ALL, 10)
        sizer_published_values.SetMinSize(get_window_size(0.298, 0.319))
        sizer_main.Add(sizer_published_values, 1, wx.ALL | wx.EXPAND, 10)

        label_parameters = wx.StaticText(self.parent, wx.ID_ANY, "Parameters:")
        label_parameters.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, 0, ""))
        sizer_parameters.Add(label_parameters, 0, 0, 0)

        label_eud = wx.StaticText(self.parent, wx.ID_ANY, "EUD a-value:")
        sizer_eud.Add(label_eud, 0, 0, 0)
        sizer_eud.Add(self.text_input_eud_a, 0, wx.ALL | wx.EXPAND, 5)
        sizer_parameters_input.Add(sizer_eud, 1, wx.EXPAND, 0)

        label_gamma_50 = wx.StaticText(self.parent, wx.ID_ANY, u"\u03b3_50:")
        sizer_gamma_50.Add(label_gamma_50, 0, 0, 0)
        sizer_gamma_50.Add(self.text_input_gamma_50, 0, wx.ALL | wx.EXPAND, 5)
        sizer_parameters_input.Add(sizer_gamma_50, 1, wx.EXPAND, 0)

        label_td_50 = wx.StaticText(self.parent, wx.ID_ANY, "TD_50 or TCD_50:")
        sizer_td_50.Add(label_td_50, 0, 0, 0)
        sizer_td_50.Add(self.text_input_td_50, 0, wx.ALL | wx.EXPAND, 5)
        sizer_parameters_input.Add(sizer_td_50, 1, wx.EXPAND, 0)

        sizer_button.Add(self.button_apply_parameters, 1, wx.ALL | wx.EXPAND, 15)
        sizer_button_2.Add(self.button_export, 1, wx.ALL | wx.EXPAND, 15)
        sizer_parameters_input.Add(sizer_button, 1, wx.EXPAND, 0)
        sizer_parameters_input.Add(sizer_button_2, 1, wx.EXPAND, 0)
        sizer_parameters.Add(sizer_parameters_input, 1, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_parameters, 0, wx.ALL | wx.EXPAND, 10)

        sizer_main.Add(self.table_rad_bio, 1, wx.ALL | wx.EXPAND, 10)

        self.layout = sizer_main

    def __set_tooltips(self):
        self.button_apply_parameters.SetToolTip("Shift or Ctrl click for targeted application.")

    def enable_buttons(self):
        self.button_apply_parameters.Enable()

    def disable_buttons(self):
        self.button_apply_parameters.Disable()

    def enable_initial_buttons(self):
        self.button_apply_parameters.Enable()

    def on_parameter_select(self, evt):
        index = self.table_published_values.GetFirstSelected()

        self.text_input_eud_a.SetValue(str(self.published_data[index][2]))
        self.text_input_gamma_50.SetValue(str(self.published_data[index][3]))
        self.text_input_td_50.SetValue(str(self.published_data[index][4]))

    def update_dvh_data(self, dvh):
        """
        Import dvh data, store into self.dvh and set data in data_table
        :param dvh: dvh object from main frame
        :type dvh: DVH
        """
        self.dvh = dvh
        data = {'MRN': self.dvh.mrn,
                'ROI Name': self.dvh.roi_name,
                'a': [''] * self.dvh.count,
                u'\u03b3_50': [''] * self.dvh.count,
                'TD or TCD': [''] * self.dvh.count,
                'EUD': [''] * self.dvh.count,
                'NTCP or TCP': [''] * self.dvh.count,
                'PTV Overlap': self.dvh.ptv_overlap,
                'ROI Type': self.dvh.roi_type,
                'Rx Dose': self.dvh.rx_dose,
                'Total Fxs': self.dvh.total_fxs,
                'Fx Dose': self.dvh.fx_dose}
        self.data_table_rad_bio.set_data(data, self.columns)

    def apply_parameters(self, evt):
        """
        Calculate rad bio values based on parameters supplied by user, pass information on to other tabs in GUI
        """

        # Get the indices of the selected rows, or assume all should be updated
        selected_indices = get_selected_listctrl_items(self.table_rad_bio)
        if not selected_indices:
            selected_indices = range(self.data_table_rad_bio.row_count)

        # Concert user supplied parameters from text to floats
        eud_a = float_or_none(self.text_input_eud_a.GetValue())
        gamma_50 = float_or_none(self.text_input_gamma_50.GetValue())
        td_50 = float_or_none(self.text_input_td_50.GetValue())

        # set the data in the datatable for the selected indices
        for i in selected_indices:
            current_row = self.data_table_rad_bio.get_row(i)
            for j in [7, 9]:
                current_row[j] = convert_value_to_str(current_row[j])
            new_row = deepcopy(current_row)
            new_row[2], new_row[3], new_row[4] = eud_a, gamma_50, td_50
            try:
                new_row[5] = "%0.2f" % round(calc_eud(self.dvh.dvh[:, i], eud_a), 2)
            except:
                new_row[5] = 'None'
            try:
                new_row[6] = "%0.2f" % round(calc_tcp(gamma_50, td_50, float(new_row[5])), 3)
            except:
                new_row[6] = 'None'
            self.data_table_rad_bio.edit_row(new_row, i)

        # Update data in in dvh object
        self.dvh.eud = []
        self.dvh.ntcp_or_tcp = []
        for i, eud in enumerate(self.data_table_rad_bio.data['EUD']):
            self.dvh.eud.append(float_or_none(eud))
            self.dvh.ntcp_or_tcp.append(float_or_none(self.data_table_rad_bio.data['NTCP or TCP'][i]))

        # update data in time series
        self.time_series.update_y_axis_options()
        if self.time_series.combo_box_y_axis.GetValue() in ['EUD', 'NTCP or TCP']:
            self.time_series.update_plot()

        # update data in regression
        self.regression.stats_data.update_endpoints_and_radbio()
        self.regression.update_combo_box_y_choices()

        # update data in control chart
        self.control_chart.update_combo_box_y_choices()
        if self.control_chart.combo_box_y_axis.GetValue() in ['EUD', 'NTCP or TCP']:
            self.control_chart.update_plot()

    def clear_data(self):
        self.data_table_rad_bio.delete_all_rows()

    def get_csv(self, selection=None):
        return self.data_table_rad_bio.get_csv()

    def on_export_csv(self, evt):
        save_data_to_file(self.parent, "Export RadBio table to CSV", self.get_csv())

    def get_save_data(self):
        return self.data_table_rad_bio.get_save_data()

    def load_save_data(self, save_data):
        self.data_table_rad_bio.load_save_data(save_data)

    @property
    def has_data(self):
        return any(self.data_table_rad_bio.data['a'])
