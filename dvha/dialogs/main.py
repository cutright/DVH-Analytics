#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dialogs.dvha_app.py
"""
Dialogs used in the main view of DVHA (e.g., query design, importing, etc.)
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
import wx.adv
from dateutil.parser import parse as parse_date
import matplotlib.colors as plot_colors
import numpy as np
import time
from os.path import isdir
from dvha.tools.utilities import (
    get_selected_listctrl_items,
    MessageDialog,
    get_window_size,
    get_installed_python_libraries,
    set_msw_background_color,
    set_frame_icon,
    backup_sqlite_db,
    is_edge_backend_available,
    is_windows,
)
from dvha.db import sql_columns
from dvha.db.sql_connector import DVH_SQL
from dvha.models.data_table import DataTable
from dvha.paths import LICENSE_PATH
from dvha.options import DefaultOptions
from dvha.tools.errors import ErrorDialog


class DatePicker(wx.Dialog):
    """
    Pop-up window to select a date to ensure proper formatting (over typing in a date into a text_ctrl directly)
    """

    def __init__(
        self, title="", initial_date=None, action=None, sql_date_format=False
    ):
        """
        :param title: optional title for the wx.Dialog
        :type title: str
        :param initial_date: optional initial date
        :type initial_date: str
        :param action: pointer to function to be executed on wx.ID_OK or
        :param sql_date_format: Set to True for SQL compatible format
        :type sql_date_format: bool
        """
        wx.Dialog.__init__(self, None, title=title)

        self.sql_date_format = sql_date_format

        self.calendar_ctrl = wx.adv.CalendarCtrl(
            self,
            wx.ID_ANY,
            style=wx.adv.CAL_SHOW_HOLIDAYS | wx.adv.CAL_SHOW_SURROUNDING_WEEKS,
        )
        if initial_date and initial_date.lower() != "none":
            self.calendar_ctrl.SetDate(parse_date(initial_date))

        self.button = {
            "ok": wx.Button(self, wx.ID_OK, "OK"),
            "delete": wx.Button(self, wx.ID_ANY, "Delete"),
            "cancel": wx.Button(self, wx.ID_CANCEL, "Cancel"),
        }

        self.button["delete"].Enable(not sql_date_format)

        self.none = (
            False  # If True after close of this dialog, user deleted the value
        )

        self.action = action

        self.__do_layout()
        self.__do_bind()

        self.run()

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(self.calendar_ctrl, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        for button in self.button.values():
            sizer_buttons.Add(button, 0, wx.ALL, 5)
        sizer_main.Add(
            sizer_buttons, 1, wx.ALIGN_CENTER | wx.BOTTOM | wx.TOP, 10
        )
        sizer_wrapper.Add(sizer_main, 1, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def __do_bind(self):
        self.Bind(
            wx.EVT_BUTTON, self.on_delete, id=self.button["delete"].GetId()
        )

    @property
    def date(self):
        if self.none:
            return ""
        date = self.calendar_ctrl.GetDate()
        date = "%s/%s/%s" % (date.month + 1, date.day, date.year)
        if self.sql_date_format:
            return str(parse_date(date).date())
        return date

    def on_delete(self, evt):
        self.none = True
        self.Close()  # resolve dialog with wx.ID_CANCEL

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK or (res == wx.ID_CANCEL and self.none):
            if self.action is not None:
                self.action(self.date)
        self.Destroy()


class AddEndpointDialog(wx.Dialog):
    """
    Add a new column to the endpoint table of the Endpoint tab
    """

    def __init__(self):
        wx.Dialog.__init__(self, None, title="Add Endpoint")

        self.combo_box_output = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["Dose (Gy)", "Dose(%)", "Volume (cc)", "Volume (%)"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.text_input = wx.TextCtrl(self, wx.ID_ANY, "")
        self.radio_box_units = wx.RadioBox(
            self,
            wx.ID_ANY,
            "",
            choices=["cc ", "% "],
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_ok.Disable()
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.radio_box_units.SetSelection(0)
        self.combo_box_output.SetValue("Dose (Gy)")

    def __do_bind(self):
        self.Bind(
            wx.EVT_COMBOBOX,
            self.combo_box_ticker,
            id=self.combo_box_output.GetId(),
        )
        self.Bind(
            wx.EVT_TEXT, self.text_input_ticker, id=self.text_input.GetId()
        )
        self.Bind(
            wx.EVT_RADIOBOX,
            self.radio_box_ticker,
            id=self.radio_box_units.GetId(),
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL
        )
        sizer_input_units = wx.BoxSizer(wx.VERTICAL)
        sizer_input_value = wx.BoxSizer(wx.VERTICAL)
        sizer_output = wx.BoxSizer(wx.VERTICAL)

        label_ouput = wx.StaticText(self, wx.ID_ANY, "Output:")
        sizer_output.Add(label_ouput, 0, wx.BOTTOM | wx.EXPAND, 8)
        sizer_output.Add(self.combo_box_output, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_output, 1, wx.ALL | wx.EXPAND, 5)

        self.label_input_value = wx.StaticText(
            self, wx.ID_ANY, "Input Volume (cc):"
        )
        sizer_input_value.Add(
            self.label_input_value, 0, wx.BOTTOM | wx.EXPAND, 8
        )
        sizer_input_value.Add(self.text_input, 0, wx.EXPAND | wx.LEFT, 5)
        sizer_input.Add(sizer_input_value, 1, wx.ALL | wx.EXPAND, 5)

        label_input_units = wx.StaticText(self, wx.ID_ANY, "Input Units:")
        sizer_input_units.Add(label_input_units, 0, wx.BOTTOM | wx.EXPAND, 3)
        sizer_input_units.Add(self.radio_box_units, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_input_units, 1, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_input, 0, wx.ALL | wx.EXPAND, 10)

        self.text_short_hand = wx.StaticText(self, wx.ID_ANY, "Short-hand: ")
        sizer_wrapper.Add(self.text_short_hand, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL | wx.EXPAND, 5)
        sizer_buttons_wrapper.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(
            sizer_buttons_wrapper, 0, wx.ALIGN_CENTER | wx.ALL, 5
        )

        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def combo_box_ticker(self, evt):
        self.update_radio_box_choices()
        self.update_label_input()
        self.update_short_hand()

    def text_input_ticker(self, evt):
        self.update_short_hand()

    def radio_box_ticker(self, evt):
        self.update_label_input()
        self.update_short_hand()

    def update_label_input(self):
        new_label = "%s (%s):" % (
            ["Input Dose", "Input Volume"][
                "Dose" in self.combo_box_output.GetValue()
            ],
            self.radio_box_units.GetItemLabel(
                self.radio_box_units.GetSelection()
            ).strip(),
        )
        self.label_input_value.SetLabelText(new_label)

    def update_radio_box_choices(self):
        choice_1 = ["Gy", "cc"]["Dose" in self.combo_box_output.GetValue()]
        self.radio_box_units.SetItemLabel(0, choice_1)

    def update_short_hand(self):
        short_hand = "Short-hand: "
        value = self.text_input.GetValue()
        if value:
            prepend = ["V_", "D_"]["Dose" in self.combo_box_output.GetValue()]
            units = self.radio_box_units.GetItemLabel(
                self.radio_box_units.GetSelection()
            ).strip()
            short_hand = short_hand + prepend + value + units
        self.text_short_hand.SetLabelText(short_hand)
        self.set_button_ok_enable(value)

    def set_button_ok_enable(self, value):
        try:
            if value.isdigit():
                value = int(value)
            else:
                value = float(value)
        except ValueError:
            self.text_short_hand.SetLabelText("Short-hand: ")
        self.button_ok.Enable(type(value) in [int, float])

    @property
    def is_endpoint_valid(self):
        return bool(len(self.short_hand_label))

    @property
    def short_hand_label(self):
        return (
            self.text_short_hand.GetLabel().replace("Short-hand: ", "").strip()
        )

    @property
    def output_type(self):
        return ["absolute", "relative"][
            "%" in self.combo_box_output.GetValue()
        ]

    @property
    def input_type(self):
        return ["absolute", "relative"][self.radio_box_units.GetSelection()]

    @property
    def units_in(self):
        return (
            self.radio_box_units.GetItemLabel(
                self.radio_box_units.GetSelection()
            )
            .replace("%", "")
            .strip()
        )

    @property
    def units_out(self):
        return (
            self.combo_box_output.GetValue()
            .split("(")[1][:-1]
            .replace("%", "")
            .strip()
        )

    @property
    def input_value(self):
        try:
            return float(self.text_input.GetValue())
        except ValueError:
            return 0.0

    @property
    def endpoint_row(self):
        return [
            self.short_hand_label,
            self.output_type,
            self.input_type,
            self.input_value,
            self.units_in,
            self.units_out,
        ]


class SelectFromListDialog(wx.Dialog):
    """
    Select an item in a list
    """

    def __init__(
        self,
        title,
        column,
        choices,
        exclude=None,
        size=None,
        column_width=200,
        selections=None,
        single_mode=False,
    ):
        wx.Dialog.__init__(self, None, title=title)

        self.column = column
        self.choices = choices
        self.exclude = [exclude, []][exclude is None]
        self.size = size
        self.column_width = column_width
        self.single_mode = single_mode

        style = (
            wx.LC_SINGLE_SEL | wx.LC_REPORT if single_mode else wx.LC_REPORT
        )
        self.list_ctrl = wx.ListCtrl(self, wx.ID_ANY, style=style)
        if not self.single_mode:
            self.button_select_all = wx.Button(self, wx.ID_ANY, "Select All")
            self.button_deselect_all = wx.Button(
                self, wx.ID_ANY, "Deselect All"
            )
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        if not self.single_mode:
            self.Bind(
                wx.EVT_BUTTON,
                self.select_all,
                id=self.button_select_all.GetId(),
            )
            self.Bind(
                wx.EVT_BUTTON,
                self.deselect_all,
                id=self.button_deselect_all.GetId(),
            )

        self.__set_properties()
        self.__do_layout()

        if selections:
            self.set_selection(selections)

    def __set_properties(self):
        self.list_ctrl.AppendColumn(
            self.column, format=wx.LIST_FORMAT_LEFT, width=self.column_width
        )

        for choice in self.choices:
            if choice not in self.exclude:
                self.list_ctrl.InsertItem(50000, choice)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_select = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_select_buttons = wx.BoxSizer(wx.HORIZONTAL)

        sizer_select.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        if not self.single_mode:
            sizer_select_buttons.Add(self.button_select_all, 0, wx.ALL, 5)
            sizer_select_buttons.Add(self.button_deselect_all, 0, wx.ALL, 5)
        sizer_select.Add(sizer_select_buttons, 0, wx.ALIGN_CENTER | wx.ALL, 0)
        sizer_wrapper.Add(sizer_select, 1, wx.ALL | wx.EXPAND, 5)

        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(sizer_wrapper)
        if self.size:
            self.SetSize(self.size)
        else:
            sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl)

    @property
    def selected_values(self):
        return [
            self.list_ctrl.GetItem(i, 0).GetText()
            for i in self.selected_indices
        ]

    @property
    def item_count(self):
        return len(self.choices) - len(self.exclude)

    def select_all(self, evt):
        self.apply_global_selection()

    def deselect_all(self, evt):
        self.apply_global_selection(on=0)

    def apply_global_selection(self, on=1):
        for i in range(self.item_count):
            self.list_ctrl.Select(i, on=on)

    def set_selection(self, selections):
        for selection in selections:
            if selection in self.choices:
                index = self.choices.index(selection)
                self.list_ctrl.Select(index, on=True)


class DelEndpointDialog(SelectFromListDialog):
    def __init__(self, endpoints):
        SelectFromListDialog.__init__(
            self,
            "Delete Endpoint",
            "Endpoints",
            endpoints,
            exclude={"MRN", "Tx Site", "ROI Name", "Volume (cc)"},
        )


class SelectRegressionVariablesDialog(SelectFromListDialog):
    def __init__(
        self, dependent_variable, independent_variable_choices, selections=None
    ):
        self.dependent_variable = dependent_variable
        self.independent_variable_choices = independent_variable_choices
        size = get_window_size(1, 0.8)
        SelectFromListDialog.__init__(
            self,
            "Select Variables for %s" % dependent_variable,
            "Independent Variables",
            independent_variable_choices,
            size=(350, size[1]),
            column_width=300,
            selections=selections,
        )


class SelectMLVarDialog(SelectFromListDialog):
    def __init__(
        self,
        variable_choices,
        selections=None,
        single_mode=True,
        algorithm=False,
        fit=False,
    ):
        if algorithm:
            column = "Algorithm"
            self.variable_choices = sorted(list(variable_choices))
        else:
            column = "Select %sependent Variable%s" % (
                ["D", "Ind"][single_mode],
                ["s", ""][single_mode],
            )
            self.variable_choices = variable_choices
        size = (350, get_window_size(1, 0.5)[1]) if not fit else None
        SelectFromListDialog.__init__(
            self,
            "Machine Learning",
            column,
            variable_choices,
            size=size,
            column_width=300,
            selections=selections,
            single_mode=single_mode,
        )


def query_dlg(parent, query_type, set_values=False):
    """
    Function to create either QueryCategoryDialog or QueryNumericalDialog
    :param parent: pointer to app object
    :type parent: DVHAMainFrame
    :param query_type: either 'categorical' or 'numerical'
    :type query_type: str
    :param set_values: If True, pre-populate dialog values with the currently selected row (i.e., edit a row)
    :type set_values: bool
    """
    dlg = {
        "categorical": QueryCategoryDialog,
        "numerical": QueryNumericalDialog,
    }[query_type]()
    data_table = {
        "categorical": parent.data_table_categorical,
        "numerical": parent.data_table_numerical,
    }[query_type]
    selected_index = {
        "categorical": parent.selected_index_categorical,
        "numerical": parent.selected_index_numerical,
    }[query_type]
    if set_values:
        dlg.set_values(data_table.get_row(selected_index))

    res = dlg.ShowModal()
    if res == wx.ID_OK:
        row = dlg.get_values()
        if set_values:
            data_table.edit_row(row, selected_index)
        else:
            data_table.append_row(row)
        parent.update_all_query_buttons()
    dlg.Destroy()


class QueryCategoryDialog(wx.Dialog):
    """
    Add/Edit query parameters for categorical data
    """

    def __init__(self):
        wx.Dialog.__init__(self, None, title="Query by Categorical Data")

        self.selector_categories = sql_columns.categorical

        selector_options = list(self.selector_categories)
        selector_options.sort()

        self.combo_box_1 = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=selector_options,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_2 = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.checkbox_1 = wx.CheckBox(self, wx.ID_ANY, "Exclude")
        self.button_OK = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__do_layout()

        self.combo_box_1.SetValue("ROI Institutional Category")
        self.update_category_2(None)
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_category_2,
            id=self.combo_box_1.GetId(),
        )

        self.Fit()
        self.Center()

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_vbox = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL
        )
        sizer_category_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_category_1 = wx.BoxSizer(wx.VERTICAL)
        label_category_1 = wx.StaticText(self, wx.ID_ANY, "Category 1:")
        sizer_category_1.Add(label_category_1, 0, wx.ALL | wx.EXPAND, 5)
        sizer_category_1.Add(self.combo_box_1, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_category_1, 1, wx.EXPAND, 0)
        label_category_2 = wx.StaticText(self, wx.ID_ANY, "Category 2:")
        sizer_category_2.Add(label_category_2, 0, wx.ALL | wx.EXPAND, 5)
        sizer_category_2.Add(self.combo_box_2, 0, wx.EXPAND | wx.ALL, 5)
        sizer_widgets.Add(sizer_category_2, 1, wx.EXPAND, 0)
        sizer_widgets.Add(self.checkbox_1, 0, wx.ALL | wx.EXPAND, 5)
        sizer_vbox.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 5)
        sizer_ok_cancel.Add(
            self.button_OK, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_vbox.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_vbox, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)

    def update_category_2(self, evt):
        key = self.combo_box_1.GetValue()
        table = self.selector_categories[key]["table"]
        col = self.selector_categories[key]["var_name"]
        with DVH_SQL() as cnx:
            options = cnx.get_unique_values(table, col)
        self.combo_box_2.Clear()
        self.combo_box_2.Append(options)
        if options:
            self.combo_box_2.SetValue(options[0])

    def set_category_1(self, value):
        self.combo_box_1.SetValue(value)
        self.update_category_2(None)

    def set_category_2(self, value):
        self.combo_box_2.SetValue(value)

    def set_check_box_not(self, value):
        self.checkbox_1.SetValue(value)

    def set_values(self, values):
        self.set_category_1(values[0])
        self.set_category_2(values[1])
        self.set_check_box_not({"Include": False, "Exclude": True}[values[2]])

    def get_values(self):
        return [
            self.combo_box_1.GetValue(),
            self.combo_box_2.GetValue(),
            ["Include", "Exclude"][self.checkbox_1.GetValue()],
        ]


class QueryNumericalDialog(wx.Dialog):
    """
    Add/Edit query parameters for numerical data
    """

    def __init__(self):
        wx.Dialog.__init__(self, None, title="Query by Numerical Data")

        self.numerical_categories = sql_columns.numerical

        numerical_options = list(self.numerical_categories)
        numerical_options.sort()

        self.combo_box_1 = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=numerical_options,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.text_ctrl_min = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ctrl_max = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_1 = wx.CheckBox(self, wx.ID_ANY, "Exclude")
        self.button_OK = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_date_picker = wx.Button(self, wx.ID_ANY, "Edit Dates")

        self.__do_layout()
        self.__do_bind()

        self.combo_box_1.SetValue("ROI Max Dose")
        self.update_range(None)

    def __do_bind(self):
        self.Bind(
            wx.EVT_COMBOBOX, self.update_range, id=self.combo_box_1.GetId()
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_date_picker,
            id=self.button_date_picker.GetId(),
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_vbox = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL
        )
        sizer_max = wx.BoxSizer(wx.VERTICAL)
        sizer_min = wx.BoxSizer(wx.VERTICAL)
        sizer_category_1 = wx.BoxSizer(wx.VERTICAL)
        label_category = wx.StaticText(self, wx.ID_ANY, "Category:")
        sizer_category_1.Add(label_category, 0, wx.ALL | wx.EXPAND, 5)
        sizer_category_1.Add(self.combo_box_1, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_category_1, 1, wx.EXPAND, 0)
        self.label_min = wx.StaticText(self, wx.ID_ANY, "Min:")
        sizer_min.Add(self.label_min, 0, wx.ALL | wx.EXPAND, 5)
        sizer_min.Add(self.text_ctrl_min, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_min, 0, wx.EXPAND, 0)
        self.label_max = wx.StaticText(self, wx.ID_ANY, "Max:")
        sizer_max.Add(self.label_max, 0, wx.ALL | wx.EXPAND, 5)
        sizer_max.Add(self.text_ctrl_max, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_max, 0, wx.EXPAND, 0)
        sizer_widgets.Add(self.checkbox_1, 0, wx.ALL | wx.EXPAND, 5)
        sizer_vbox.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 5)
        sizer_ok_cancel.Add(
            self.button_date_picker, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_ok_cancel.Add(
            self.button_OK, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_vbox.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_vbox, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)

        self.Fit()
        self.Center()

    def update_range(self, evt):
        key = self.combo_box_1.GetValue()
        table = self.numerical_categories[key]["table"]
        col = self.numerical_categories[key]["var_name"]
        units = self.numerical_categories[key]["units"]
        with DVH_SQL() as cnx:
            min_value = cnx.get_min_value(table, col)
            max_value = cnx.get_max_value(table, col)

        self.button_date_picker.Enable("date" in key.lower())
        self.text_ctrl_min.Enable("date" not in key.lower())
        self.text_ctrl_max.Enable("date" not in key.lower())

        self.set_min_value(min_value)
        self.set_max_value(max_value)

        if "date" in key.lower():
            self.update_min_max_text("Start:", "End:")
            self.on_date_picker()
        elif units:
            self.update_min_max_text("Min (%s):" % units, "Max (%s):" % units)
        else:
            self.update_min_max_text("Min:", "Max:")

        self.clean_numeric_input()

    def update_min_max_text(self, min_text, max_text):
        self.label_min.SetLabelText(min_text)
        self.label_max.SetLabelText(max_text)

    def set_category(self, value):
        self.combo_box_1.SetValue(value)
        self.update_range(None)

    def set_min_value(self, value):
        self.text_ctrl_min.SetValue(str(value))

    def set_max_value(self, value):
        self.text_ctrl_max.SetValue(str(value))

    def set_check_box_not(self, value):
        self.checkbox_1.SetValue(value)

    def set_values(self, values):
        self.set_category(values[0])
        self.set_min_value(str(values[1]))
        self.set_max_value(str(values[2]))
        self.set_check_box_not({"Include": False, "Exclude": True}[values[3]])

    def get_values(self):
        return [
            self.combo_box_1.GetValue(),
            self.text_ctrl_min.GetValue(),
            self.text_ctrl_max.GetValue(),
            ["Include", "Exclude"][self.checkbox_1.GetValue()],
        ]

    def validated_text(self, input_type):
        old_value = {
            "min": self.text_ctrl_min.GetValue(),
            "max": self.text_ctrl_max.GetValue(),
        }[input_type]

        try:
            new_value = float(old_value)
        except ValueError:
            key = self.combo_box_1.GetValue()
            table = self.numerical_categories[key]["table"]
            col = self.numerical_categories[key]["var_name"]
            with DVH_SQL() as cnx:
                if input_type == "min":
                    new_value = cnx.get_min_value(table, col)
                else:
                    new_value = cnx.get_max_value(table, col)
        return new_value

    def on_date_picker(self, *evt):
        DatePicker(
            initial_date=self.text_ctrl_min.GetValue(),
            title="Start Date",
            action=self.set_min_value,
            sql_date_format=True,
        )
        time.sleep(
            0.3
        )  # Immediately loading the next DatePicker looks like a glitch
        DatePicker(
            initial_date=self.text_ctrl_max.GetValue(),
            title="End Date",
            action=self.set_max_value,
            sql_date_format=True,
        )

    def clean_numeric_input(self):
        for text_ctrl in [self.text_ctrl_min, self.text_ctrl_max]:
            try:
                value = float(text_ctrl.GetValue())
                func = [np.floor, np.ceil][text_ctrl == self.text_ctrl_max]
                text_ctrl.SetValue("%0.2f" % func(value))
            except ValueError:
                pass


class UserSettings(wx.Frame):
    """
    Customize directories and visual settings for DVHA
    """

    def __init__(self, parent):
        """
        :param parent: main application frame
        """
        wx.Frame.__init__(self, None, title="User Settings")

        self.parent = parent
        self.options = parent.options
        self.options.edit_detected = False

        colors = list(plot_colors.cnames)
        colors.sort()

        color_variables = self.get_option_choices("COLOR")
        size_variables = self.get_option_choices("SIZE")
        width_variables = self.get_option_choices("LINE_WIDTH")
        line_dash_variables = self.get_option_choices("LINE_DASH")
        alpha_variables = self.get_option_choices("ALPHA")

        line_style_options = [
            "solid",
            "dashed",
            "dotted",
            "dotdash",
            "dashdot",
        ]

        # self.SetSize((500, 580))
        self.text_ctrl_inbox = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_DONTWRAP
        )
        self.button_inbox = wx.Button(self, wx.ID_ANY, u"…")
        self.text_ctrl_imported = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_DONTWRAP
        )
        self.button_imported = wx.Button(self, wx.ID_ANY, u"…")

        self.checkbox_dicom_dvh = wx.CheckBox(
            self, wx.ID_ANY, "Import DICOM DVH if available"
        )
        self.dvh_bin_width_input = wx.TextCtrl(
            self, wx.ID_ANY, str(self.options.dvh_bin_width)
        )
        self.dvh_bin_max_dose = wx.TextCtrl(self, wx.ID_ANY, "")
        self.dvh_bin_max_dose_units = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.options.dvh_bin_max_dose_options,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.dvh_small_volume_threshold = wx.SpinCtrl(
            self, wx.ID_ANY, "10", min=1, max=50, style=wx.SP_ARROW_KEYS
        )
        self.dvh_segments_between = wx.SpinCtrl(
            self, wx.ID_ANY, "10", min=0, max=20, style=wx.SP_ARROW_KEYS
        )
        self.dvh_high_resolution = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.options.DVH_HIGH_RESOLUTION_FACTOR_OPTIONS,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_colors_category = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=color_variables,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_colors_selection = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=colors,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_sizes_category = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=size_variables,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.spin_ctrl_sizes_input = wx.SpinCtrl(
            self, wx.ID_ANY, "0", min=0, max=20, style=wx.SP_ARROW_KEYS
        )
        self.combo_box_line_widths_category = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=width_variables,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.spin_ctrl_line_widths_input = wx.SpinCtrl(
            self, wx.ID_ANY, "0", min=0, max=10, style=wx.SP_ARROW_KEYS
        )
        self.combo_box_line_styles_category = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=line_dash_variables,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_line_styles_selection = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=line_style_options,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_alpha_category = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=alpha_variables,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.spin_ctrl_alpha_input = wx.SpinCtrlDouble(
            self,
            wx.ID_ANY,
            "0",
            min=0,
            max=1.0,
            style=wx.SP_ARROW_KEYS,
            inc=0.1,
        )

        if is_windows():
            self.checkbox_edge_backend = wx.CheckBox(
                self, wx.ID_ANY, "Enable Edge WebView Backend"
            )
            if not is_edge_backend_available():
                self.checkbox_edge_backend.Disable()

        self.button_restore_defaults = wx.Button(
            self, wx.ID_ANY, "Restore Defaults"
        )
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.button_apply = wx.Button(self, wx.ID_ANY, "Apply")

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()

        self.refresh_options()
        self.load_paths()

        self.is_edited = False

        set_msw_background_color(self)
        set_frame_icon(self)

    def __set_properties(self):
        self.text_ctrl_inbox.SetToolTip(
            "Default directory for batch processing of incoming DICOM files"
        )
        self.text_ctrl_inbox.SetMinSize((100, 21))
        self.button_inbox.SetMinSize((40, 21))
        self.text_ctrl_imported.SetToolTip(
            "Directory for post-processed DICOM files"
        )
        self.text_ctrl_imported.SetMinSize((100, 21))
        self.button_imported.SetMinSize((40, 21))
        self.checkbox_dicom_dvh.SetValue(self.options.USE_DICOM_DVH)
        self.checkbox_dicom_dvh.SetToolTip(
            "If a DICOM RT-Dose file has a DVH Sequence, use this DVH instead of "
            "recalculating during import."
        )
        self.dvh_bin_width_input.SetToolTip("Value must be an integer.")
        self.dvh_bin_width_input.SetMinSize((50, 21))
        self.dvh_bin_max_dose.SetToolTip(
            "Prevent memory issues if dose grid contains very large, unrealistic doses"
        )
        self.dvh_bin_max_dose.SetValue(
            str(
                self.options.dvh_bin_max_dose[
                    self.options.dvh_bin_max_dose_units
                ]
            )
        )
        self.dvh_bin_max_dose_units.SetValue(
            self.options.dvh_bin_max_dose_units
        )
        self.dvh_small_volume_threshold.SetToolTip(
            "If ROI volume is less than this value, it will be recalculated with a "
            "resolution of the dose grid spacing divided by 16"
        )
        self.dvh_small_volume_threshold.SetValue(
            str(self.options.DVH_SMALL_VOLUME_THRESHOLD)
        )
        self.dvh_segments_between.SetToolTip(
            "If ROI volume is less than threshold, it will be recalculated with a this many "
            "segments interpolated between slices"
        )
        self.dvh_segments_between.SetValue(
            str(self.options.DVH_HIGH_RESOLUTION_SEGMENTS_BETWEEN)
        )
        self.dvh_high_resolution.SetToolTip(
            "If ROI volume is less than the volume threshold, the in-plane resolution will be "
            "increased by this factor (e.g., interpolate in-between the dose grid)"
        )
        self.dvh_high_resolution.SetValue(
            str(self.options.DVH_HIGH_RESOLUTION_FACTOR)
        )
        # self.dvh_bin_width_input.SetMinSize((50, 22))
        # self.dvh_bin_max_dose_units.SetMinSize((50, 22))
        self.combo_box_colors_category.SetMinSize(
            (250, self.combo_box_colors_category.GetSize()[1])
        )
        self.combo_box_colors_selection.SetMinSize(
            (145, self.combo_box_colors_selection.GetSize()[1])
        )
        self.combo_box_sizes_category.SetMinSize(
            (250, self.combo_box_sizes_category.GetSize()[1])
        )
        self.spin_ctrl_sizes_input.SetMinSize((50, 22))
        self.combo_box_line_widths_category.SetMinSize(
            (250, self.combo_box_line_widths_category.GetSize()[1])
        )
        self.spin_ctrl_line_widths_input.SetMinSize((50, 22))
        self.combo_box_line_styles_category.SetMinSize(
            (250, self.combo_box_line_styles_category.GetSize()[1])
        )
        self.combo_box_line_styles_selection.SetMinSize(
            (145, self.combo_box_line_styles_selection.GetSize()[1])
        )
        self.combo_box_alpha_category.SetMinSize(
            (250, self.combo_box_alpha_category.GetSize()[1])
        )
        self.spin_ctrl_alpha_input.SetMinSize((70, 22))

        self.spin_ctrl_alpha_input.SetIncrement(0.1)

        # Windows needs this done explicitly or the value will be an empty string
        self.combo_box_alpha_category.SetValue("IQR Alpha")
        self.combo_box_colors_category.SetValue("Plot Color")
        self.combo_box_line_styles_category.SetValue("DVH Line Dash Selection")
        self.combo_box_line_widths_category.SetValue(
            "DVH Line Width Selection"
        )
        self.combo_box_sizes_category.SetValue("Plot Axis Label Font Size")

        if is_windows():
            self.checkbox_edge_backend.SetValue(
                self.options.ENABLE_EDGE_BACKEND
            )
            self.checkbox_edge_backend.SetToolTip(
                "Allows for more complete plot interaction. Must restart DVHA for "
                "change to be applied. If you cannot toggle this checkbox, "
                "Edge is not availabe. Requires MS Edge Beta to be installed: "
                "https://www.microsoftedgeinsider.com/en-us/download"
            )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plot_options = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Plot Options"), wx.VERTICAL
        )
        sizer_dvh_options = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "DVH Options"), wx.VERTICAL
        )
        sizer_dvh_bin_width = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dvh_bin_max = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dvh_small_vol = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dvh_segments_between = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dvh_high_resolution = wx.BoxSizer(wx.HORIZONTAL)
        sizer_alpha = wx.BoxSizer(wx.VERTICAL)
        sizer_alpha_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_line_styles = wx.BoxSizer(wx.VERTICAL)
        sizer_line_styles_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_line_widths = wx.BoxSizer(wx.VERTICAL)
        sizer_line_widths_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sizes = wx.BoxSizer(wx.VERTICAL)
        sizer_sizes_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_colors = wx.BoxSizer(wx.VERTICAL)
        sizer_colors_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dicom_directories = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "DICOM Directories"), wx.VERTICAL
        )
        sizer_imported_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_imported = wx.BoxSizer(wx.VERTICAL)
        sizer_imported_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_inbox_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_inbox = wx.BoxSizer(wx.VERTICAL)
        sizer_inbox_input = wx.BoxSizer(wx.HORIZONTAL)

        label_inbox = wx.StaticText(self, wx.ID_ANY, "Inbox:")
        label_inbox.SetToolTip(
            "Default directory for batch processing of incoming DICOM files"
        )
        sizer_inbox.Add(label_inbox, 0, 0, 5)
        sizer_inbox_input.Add(self.text_ctrl_inbox, 1, wx.ALL, 5)
        sizer_inbox_input.Add(self.button_inbox, 0, wx.ALL, 5)
        sizer_inbox.Add(sizer_inbox_input, 1, wx.EXPAND, 0)
        sizer_inbox_wrapper.Add(sizer_inbox, 1, wx.EXPAND, 0)
        sizer_dicom_directories.Add(sizer_inbox_wrapper, 1, wx.EXPAND, 0)

        label_imported = wx.StaticText(self, wx.ID_ANY, "Imported:")
        label_imported.SetToolTip("Directory for post-processed DICOM files")
        sizer_imported.Add(label_imported, 0, 0, 5)
        sizer_imported_input.Add(self.text_ctrl_imported, 1, wx.ALL, 5)
        sizer_imported_input.Add(self.button_imported, 0, wx.ALL, 5)
        sizer_imported.Add(sizer_imported_input, 1, wx.EXPAND, 0)
        sizer_imported_wrapper.Add(sizer_imported, 1, wx.EXPAND, 0)
        sizer_dicom_directories.Add(sizer_imported_wrapper, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_dicom_directories, 0, wx.ALL | wx.EXPAND, 10)

        sizer_dvh_options.Add(self.checkbox_dicom_dvh, 0, wx.LEFT, 5)
        sizer_dvh_options.Add((20, 10), 0, 0, 0)
        label_dvh_bin_width = wx.StaticText(
            self, wx.ID_ANY, "DVH Bin Width (cGy):"
        )
        label_dvh_bin_width.SetToolTip("Value must be an integer")
        sizer_dvh_bin_width.Add(
            label_dvh_bin_width, 1, wx.EXPAND | wx.TOP | wx.LEFT, 5
        )
        sizer_dvh_bin_width.Add(self.dvh_bin_width_input, 0, wx.ALL, 5)
        label_max_dose_bin = wx.StaticText(
            self, wx.ID_ANY, "Max Dose Bin Limit:"
        )
        label_max_dose_bin.SetToolTip(
            "Prevent memory issues if dose grid contains very large doses"
        )
        sizer_dvh_bin_max.Add(
            label_max_dose_bin, 1, wx.EXPAND | wx.TOP | wx.LEFT, 5
        )
        sizer_dvh_bin_max.Add((20, 20), 0, 0, 0)
        sizer_dvh_bin_max.Add(self.dvh_bin_max_dose, 0, 0, 0)
        sizer_dvh_bin_max.Add((20, 20), 0, 0, 0)
        sizer_dvh_bin_max.Add(self.dvh_bin_max_dose_units, 0, 0, 0)
        sizer_dvh_options.Add(sizer_dvh_bin_width, 0, wx.EXPAND | wx.BOTTOM, 0)
        sizer_dvh_options.Add(sizer_dvh_bin_max, 0, wx.EXPAND, 0)

        label_dvh_small_volume = wx.StaticText(
            self, wx.ID_ANY, "Small volume threshold (cc):"
        )
        label_dvh_small_volume.SetToolTip(
            "If ROI volume is less than this value, it will be recalculated with "
            "a higher resolution using interpolation"
        )
        sizer_dvh_small_vol.Add(
            label_dvh_small_volume, 1, wx.EXPAND | wx.TOP, 5
        )
        sizer_dvh_small_vol.Add(self.dvh_small_volume_threshold, 0, wx.TOP, 5)
        sizer_dvh_options.Add(
            sizer_dvh_small_vol, 0, wx.EXPAND | wx.TOP | wx.LEFT, 5
        )

        label_dvh_segments_between = wx.StaticText(
            self, wx.ID_ANY, "Interpolated segments between planes:"
        )
        label_dvh_segments_between.SetToolTip(
            "If ROI volume is less than threshold, it will be recalculated with a this many "
            "segments interpolated between slices"
        )
        sizer_dvh_segments_between.Add(
            label_dvh_segments_between, 1, wx.EXPAND | wx.TOP, 5
        )
        sizer_dvh_segments_between.Add(self.dvh_segments_between, 0, wx.TOP, 5)
        sizer_dvh_options.Add(
            sizer_dvh_segments_between, 0, wx.EXPAND | wx.TOP | wx.LEFT, 5
        )

        label_dvh_high_resolution = wx.StaticText(
            self, wx.ID_ANY, "High resolution interpolation factor :"
        )
        label_dvh_high_resolution.SetToolTip(
            "If ROI volume is less than the volume threshold, the in-plane resolution will be "
            "increased by this factor (e.g., interpolate in-between the dose grid)"
        )
        sizer_dvh_high_resolution.Add(
            label_dvh_high_resolution, 1, wx.EXPAND | wx.TOP, 5
        )
        sizer_dvh_high_resolution.Add(self.dvh_high_resolution, 0, wx.TOP, 5)
        sizer_dvh_options.Add(
            sizer_dvh_high_resolution, 0, wx.EXPAND | wx.TOP | wx.LEFT, 5
        )

        sizer_wrapper.Add(sizer_dvh_options, 0, wx.ALL | wx.EXPAND, 10)

        label_colors = wx.StaticText(self, wx.ID_ANY, "Colors:")
        sizer_colors.Add(label_colors, 0, 0, 0)
        sizer_colors_input.Add(self.combo_box_colors_category, 0, 0, 0)
        sizer_colors_input.Add((20, 20), 0, 0, 0)
        sizer_colors_input.Add(self.combo_box_colors_selection, 0, 0, 0)
        sizer_colors.Add(sizer_colors_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_colors, 1, wx.EXPAND, 0)

        label_sizes = wx.StaticText(self, wx.ID_ANY, "Sizes:")
        sizer_sizes.Add(label_sizes, 0, 0, 0)
        sizer_sizes_input.Add(self.combo_box_sizes_category, 0, 0, 0)
        sizer_sizes_input.Add((20, 20), 0, 0, 0)
        sizer_sizes_input.Add(self.spin_ctrl_sizes_input, 0, 0, 0)
        sizer_sizes.Add(sizer_sizes_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_sizes, 1, wx.EXPAND, 0)

        label_line_widths = wx.StaticText(self, wx.ID_ANY, "Line Widths:")
        sizer_line_widths.Add(label_line_widths, 0, 0, 0)
        sizer_line_widths_input.Add(
            self.combo_box_line_widths_category, 0, 0, 0
        )
        sizer_line_widths_input.Add((20, 20), 0, 0, 0)
        sizer_line_widths_input.Add(self.spin_ctrl_line_widths_input, 0, 0, 0)
        sizer_line_widths.Add(sizer_line_widths_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_line_widths, 1, wx.EXPAND, 0)

        label_line_styles = wx.StaticText(self, wx.ID_ANY, "Line Styles:")
        sizer_line_styles.Add(label_line_styles, 0, 0, 0)
        sizer_line_styles_input.Add(
            self.combo_box_line_styles_category, 0, 0, 0
        )
        sizer_line_styles_input.Add((20, 20), 0, 0, 0)
        sizer_line_styles_input.Add(
            self.combo_box_line_styles_selection, 0, 0, 0
        )
        sizer_line_styles.Add(sizer_line_styles_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_line_styles, 1, wx.EXPAND, 0)

        label_alpha = wx.StaticText(self, wx.ID_ANY, "Alpha:")
        sizer_alpha.Add(label_alpha, 0, 0, 0)
        sizer_alpha_input.Add(self.combo_box_alpha_category, 0, 0, 0)
        sizer_alpha_input.Add((20, 20), 0, 0, 0)
        sizer_alpha_input.Add(self.spin_ctrl_alpha_input, 0, 0, 0)
        sizer_alpha.Add(sizer_alpha_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_alpha, 1, wx.EXPAND, 0)
        if is_windows():
            sizer_plot_options.Add(
                self.checkbox_edge_backend, 0, wx.EXPAND | wx.TOP, 5
            )
        sizer_wrapper.Add(
            sizer_plot_options, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10
        )

        sizer_ok_cancel.Add(self.button_restore_defaults, 0, wx.RIGHT, 20)
        sizer_ok_cancel.Add(self.button_apply, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer_wrapper)
        self.Layout()
        self.Fit()

        self.options.apply_window_position(self, "user_settings")

    def __do_bind(self):
        self.Bind(
            wx.EVT_BUTTON, self.inbox_dir_dlg, id=self.button_inbox.GetId()
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.imported_dir_dlg,
            id=self.button_imported.GetId(),
        )

        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_use_dicom_dvh,
            id=self.checkbox_dicom_dvh.GetId(),
        )

        self.Bind(
            wx.EVT_TEXT,
            self.update_dvh_bin_width_val,
            id=self.dvh_bin_width_input.GetId(),
        )
        self.Bind(
            wx.EVT_TEXT,
            self.update_dvh_bin_max_dose_val,
            id=self.dvh_bin_max_dose.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_dvh_bin_max_dose_units_val,
            id=self.dvh_bin_max_dose_units.GetId(),
        )
        self.Bind(
            wx.EVT_TEXT,
            self.update_dvh_small_volume_val,
            id=self.dvh_small_volume_threshold.GetId(),
        )
        self.Bind(
            wx.EVT_TEXT,
            self.update_dvh_segments_between,
            id=self.dvh_segments_between.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_dvh_high_resolution_factor,
            id=self.dvh_high_resolution.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_input_colors_var,
            id=self.combo_box_colors_category.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_size_var,
            id=self.combo_box_sizes_category.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_line_width_var,
            id=self.combo_box_line_widths_category.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_line_style_var,
            id=self.combo_box_line_styles_category.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_alpha_var,
            id=self.combo_box_alpha_category.GetId(),
        )

        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_input_colors_val,
            id=self.combo_box_colors_selection.GetId(),
        )
        self.Bind(
            wx.EVT_TEXT,
            self.update_size_val,
            id=self.spin_ctrl_sizes_input.GetId(),
        )
        self.Bind(
            wx.EVT_TEXT,
            self.update_line_width_val,
            id=self.spin_ctrl_line_widths_input.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX,
            self.update_line_style_val,
            id=self.combo_box_line_styles_selection.GetId(),
        )
        self.Bind(
            wx.EVT_TEXT,
            self.update_alpha_val,
            id=self.spin_ctrl_alpha_input.GetId(),
        )
        if is_windows() and is_edge_backend_available():
            self.Bind(
                wx.EVT_CHECKBOX,
                self.on_enable_edge,
                id=self.checkbox_edge_backend.GetId(),
            )

        self.Bind(
            wx.EVT_BUTTON,
            self.restore_defaults,
            id=self.button_restore_defaults.GetId(),
        )
        self.Bind(wx.EVT_BUTTON, self.on_apply, id=self.button_apply.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=wx.ID_CANCEL)

        self.Bind(wx.EVT_CLOSE, self.on_cancel)

    def on_ok(self, *evt):
        if self.options.is_edited:  # Tracks edits since last redraw
            self.apply_and_redraw_plots()
        self.close()

    def on_cancel(self, *evt):
        self.options.load()
        if self.is_edited:  # Tracks edits since last options save
            self.apply_and_redraw_plots()
        self.close()

    def close(self, *evt):
        self.save_window_position()
        self.options.save()
        self.parent.user_settings = None
        self.Destroy()

    def save_window_position(self):
        self.options.save_window_position(self, "user_settings")

    def inbox_dir_dlg(self, evt):
        self.dir_dlg("inbox", self.text_ctrl_inbox)

    def imported_dir_dlg(self, evt):
        self.dir_dlg("imported", self.text_ctrl_imported)

    def dir_dlg(self, dir_type, text_ctrl):
        """
        Create a DirDialog and edit the associated TextCtrl
        :param dir_type: the directory type to be displayed in DirDialog title
        :type dir_type: str
        :param text_ctrl: the associated TextCtrl from the user settings dialog
        :type text_ctrl: TextCtrl
        """
        starting_dir = text_ctrl.GetValue()
        if not isdir(starting_dir):
            starting_dir = ""
        dlg = wx.DirDialog(
            self,
            "Select %s directory" % dir_type,
            starting_dir,
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            text_ctrl.SetValue(dlg.GetPath())
            option_attr = (
                "INBOX_DIR" if dir_type == "inbox" else "IMPORTED_DIR"
            )
            self.options.set_option(option_attr, dlg.GetPath())
        dlg.Destroy()

    def get_option_choices(self, category):
        """
        Lookup properties in Options.option_attr that fit the specified category
        :param category: COLOR, SIZE, ALPHA, LINE_WIDTH, LINE_DASH
        :type category: str
        :return: all options with the category in their name
        :rtype: list
        """
        choices = [
            self.clean_option_variable(c)
            for c in self.options.option_attr
            if c.find(category) > -1
        ]
        choices.sort()
        return choices

    @staticmethod
    def clean_option_variable(option_variable, inverse=False):
        """
        Convert option variable between UI and python format
        :param option_variable: option available for edit user settings UI
        :type option_variable: str
        :param inverse: True to return python format, False to return UI format
        :type inverse: bool
        :return: formatted option variable
        :rtype: str
        """
        if inverse:
            return option_variable.upper().replace(" ", "_")
        else:
            return (
                option_variable.replace("_", " ")
                .title()
                .replace("Dvh", "DVH")
                .replace("Iqr", "IQR")
            )

    def update_input_colors_var(self, *args):
        var = self.clean_option_variable(
            self.combo_box_colors_category.GetValue(), inverse=True
        )
        val = getattr(self.options, var)
        self.combo_box_colors_selection.SetValue(val)

    def update_input_colors_val(self, *args):
        var = self.clean_option_variable(
            self.combo_box_colors_category.GetValue(), inverse=True
        )
        val = self.combo_box_colors_selection.GetValue()
        self.options.set_option(var, val)

    def update_size_var(self, *args):
        var = self.clean_option_variable(
            self.combo_box_sizes_category.GetValue(), inverse=True
        )
        try:
            val = getattr(self.options, var).replace("pt", "")
        except AttributeError:
            val = str(getattr(self.options, var))
        try:
            val = int(float(val))
        except ValueError:
            pass
        self.spin_ctrl_sizes_input.SetValue(val)

    def update_size_val(self, *args):
        new = self.spin_ctrl_sizes_input.GetValue()
        if "Font" in self.combo_box_sizes_category.GetValue():
            try:
                val = str(int(new)) + "pt"
            except ValueError:
                val = "10pt"
        else:
            try:
                val = float(new)
            except ValueError:
                val = 1.0

        var = self.clean_option_variable(
            self.combo_box_sizes_category.GetValue(), inverse=True
        )
        self.options.set_option(var, val)

    def update_line_width_var(self, *args):
        var = self.clean_option_variable(
            self.combo_box_line_widths_category.GetValue(), inverse=True
        )
        val = str(getattr(self.options, var))
        try:
            val = int(float(val))
        except ValueError:
            pass
        self.spin_ctrl_line_widths_input.SetValue(val)

    def update_line_width_val(self, *args):
        new = self.spin_ctrl_line_widths_input.GetValue()
        try:
            val = int(float(new))
        except ValueError:
            val = 1
        var = self.clean_option_variable(
            self.combo_box_line_widths_category.GetValue(), inverse=True
        )
        self.options.set_option(var, val)

    def update_line_style_var(self, *args):
        var = self.clean_option_variable(
            self.combo_box_line_styles_category.GetValue(), inverse=True
        )
        self.combo_box_line_styles_selection.SetValue(
            getattr(self.options, var)
        )

    def update_line_style_val(self, *args):
        var = self.clean_option_variable(
            self.combo_box_line_styles_category.GetValue(), inverse=True
        )
        val = self.combo_box_line_styles_selection.GetValue()
        self.options.set_option(var, val)

    def update_alpha_var(self, *args):
        var = self.clean_option_variable(
            self.combo_box_alpha_category.GetValue(), inverse=True
        )
        self.spin_ctrl_alpha_input.SetValue(str(getattr(self.options, var)))

    def update_alpha_val(self, *args):
        new = self.spin_ctrl_alpha_input.GetValue()
        try:
            val = float(new)
        except ValueError:
            val = 1.0
        var = self.clean_option_variable(
            self.combo_box_alpha_category.GetValue(), inverse=True
        )
        self.options.set_option(var, val)

    def update_dvh_bin_width_val(self, *args):
        new = self.dvh_bin_width_input.GetValue()
        try:
            val = abs(int(new))
            self.options.set_option("dvh_bin_width", val)
        except ValueError:
            if new != "":
                self.dvh_bin_width_input.SetValue(
                    str(self.options.dvh_bin_width)
                )

    def update_dvh_bin_width_var(self, *args):
        self.dvh_bin_width_input.SetValue(str(self.options.dvh_bin_width))

    def update_dvh_bin_max_dose_val(self, *args):
        new_val = self.dvh_bin_max_dose.GetValue()
        units = self.dvh_bin_max_dose_units.GetValue()
        try:
            val = abs(float(new_val))
            new = {
                key: value
                for key, value in self.options.dvh_bin_max_dose.items()
            }
            new[units] = val
            self.options.set_option("dvh_bin_max_dose", new)
        except ValueError:
            if new_val != "":
                self.dvh_bin_max_dose.SetValue(
                    str(self.options.dvh_bin_max_dose[units])
                )

    def update_dvh_bin_max_dose_var(self, *args):
        units = self.dvh_bin_max_dose_units.GetValue()
        self.dvh_bin_max_dose.SetValue(
            str(self.options.dvh_bin_max_dose[units])
        )

    def update_dvh_bin_max_dose_units_val(self, *args):
        new = self.dvh_bin_max_dose_units.GetValue()
        self.options.set_option("dvh_bin_max_dose_units", new)
        self.dvh_bin_max_dose.SetValue(str(self.options.dvh_bin_max_dose[new]))

    def update_dvh_bin_max_dose_units_var(self, *args):
        self.dvh_bin_max_dose_units.SetValue(
            self.options.dvh_bin_max_dose_units
        )

    def update_dvh_small_volume_val(self, *args):
        try:
            new = int(float(self.dvh_small_volume_threshold.GetValue()))
            self.options.set_option("DVH_SMALL_VOLUME_THRESHOLD", new)
        except ValueError:
            self.dvh_small_volume_threshold.SetValue(
                str(self.options.DVH_SMALL_VOLUME_THRESHOLD)
            )

    def update_dvh_segments_between(self, *args):
        try:
            new = int(float(self.dvh_segments_between.GetValue()))
            self.options.set_option(
                "DVH_HIGH_RESOLUTION_SEGMENTS_BETWEEN", new
            )
        except ValueError:
            self.dvh_small_volume_threshold.SetValue(
                str(self.options.DVH_HIGH_RESOLUTION_SEGMENTS_BETWEEN)
            )

    def update_dvh_high_resolution_factor(self, *args):
        new = int(float(self.dvh_high_resolution.GetValue()))
        self.options.set_option("DVH_HIGH_RESOLUTION_FACTOR", new)

    def refresh_options(self):
        self.update_dvh_bin_width_var()
        self.update_dvh_bin_max_dose_var()
        self.update_dvh_bin_max_dose_units_var()
        self.update_alpha_var()
        self.update_input_colors_var()
        self.update_line_style_var()
        self.update_line_width_var()
        self.update_size_var()

    def load_paths(self):
        self.text_ctrl_inbox.SetValue(self.options.INBOX_DIR)
        self.text_ctrl_imported.SetValue(self.options.IMPORTED_DIR)

    def restore_defaults(self, *args):
        MessageDialog(
            self,
            "Restore default preferences?",
            action_yes_func=self.options.restore_defaults,
        )
        self.update_size_val()
        self.refresh_options()
        self.on_apply()

    def on_use_dicom_dvh(self, *evt):
        self.options.set_option(
            "USE_DICOM_DVH", self.checkbox_dicom_dvh.GetValue()
        )

    def on_enable_edge(self, *evt):
        self.options.set_option(
            "ENABLE_EDGE_BACKEND", self.checkbox_edge_backend.GetValue()
        )

    def on_apply(self, *evt):
        self.apply_and_redraw_plots()
        self.is_edited = True  # Used to track edits since last options save
        self.options.is_edited = False  # Used to track edits since redraw, is set to True on options.set_option()

    def apply_and_redraw_plots(self):
        self.parent.apply_plot_options()
        self.parent.redraw_plots()


class About(wx.Dialog):
    """
    Simple dialog to display the LICENSE file and a brief text header in a scrollable window
    """

    def __init__(self, *evt):
        wx.Dialog.__init__(self, None, title="About DVH Analytics")

        scrolled_window = wx.ScrolledWindow(self, wx.ID_ANY)

        with open(LICENSE_PATH, "r", encoding="utf8") as license_file:
            license_text = "".join([line for line in license_file])

        license_text = "DVH Analytics v%s\ndvhanalytics.com\n\n%s" % (
            DefaultOptions().VERSION,
            license_text,
        )

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_text = wx.BoxSizer(wx.VERTICAL)

        scrolled_window.SetScrollRate(20, 20)

        license_text = wx.StaticText(scrolled_window, wx.ID_ANY, license_text)
        sizer_text.Add(license_text, 0, wx.EXPAND | wx.ALL, 5)
        scrolled_window.SetSizer(sizer_text)
        sizer_wrapper.Add(scrolled_window, 1, wx.EXPAND, 0)

        self.SetBackgroundColour(wx.WHITE)

        self.SetSizer(sizer_wrapper)
        self.SetSize((750, 900))
        self.Center()

        self.ShowModal()
        self.Destroy()


class PythonLibraries(wx.Dialog):
    """Simple dialog to display the installed python libraries"""

    def __init__(self, *evt):
        wx.Dialog.__init__(self, None, title="Installed Python Libraries")

        self.list_ctrl = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.BORDER_SUNKEN
            | wx.LC_HRULES
            | wx.LC_REPORT
            | wx.LC_VRULES,
        )
        self.data_table = DataTable(self.list_ctrl, widths=[200, 150])

        self.__set_data()
        self.__do_layout()

        self.run()

    def __set_data(self):
        columns = ["Library", "Version"]
        try:
            libraries = get_installed_python_libraries()
        except Exception:
            libraries = {"Library": ["pip list failed"], "Version": [" "]}
        self.data_table.set_data(libraries, columns)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        note = wx.StaticText(
            self,
            wx.ID_ANY,
            "NOTE: If running from source, this might reflect global packages.\n"
            "If running from an executable, this should be accurate.",
        )
        note.Wrap(500)

        sizer_main.Add(note, 0, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(self.list_ctrl, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND | wx.ALL, 10)

        self.SetBackgroundColour(wx.WHITE)
        self.SetSizer(sizer_wrapper)
        self.SetSize(get_window_size(0.3, 0.8))
        self.Center()

    def run(self):
        self.ShowModal()
        self.Destroy()


class ShowList(wx.Dialog):
    """Simple dialog to display a non-interactive List"""

    def __init__(self, list_items, title="List of Items", *evt):
        wx.Dialog.__init__(self, None, title=title)

        self.list_ctrl = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.BORDER_SUNKEN
            | wx.LC_REPORT
            | wx.LC_NO_HEADER
            | wx.LC_SINGLE_SEL,
        )
        self.data_table = DataTable(self.list_ctrl, widths=[400])
        self.list_items = list_items
        self.data_table.set_data({"col": self.list_items}, ["col"])

        self.data_table.set_column_widths(auto=True)

        self.__do_bind()
        self.__do_layout()

        self.run()

    def __do_bind(self):
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            self.on_select,
            id=self.list_ctrl.GetId(),
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.list_ctrl, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND | wx.ALL, 10)

        self.SetBackgroundColour(wx.WHITE)
        self.SetSizer(sizer_wrapper)
        self.SetSize(get_window_size(0.25, 0.8))
        self.Center()

    def run(self):
        self.ShowModal()
        self.Destroy()

    def on_select(self, *evt):
        self.data_table.apply_selection_to_all(False)


def do_sqlite_backup(parent, options):
    flags = wx.ICON_ERROR | wx.OK | wx.OK_DEFAULT
    if options.DB_TYPE_GRPS[1] == "sqlite":
        try:
            file_paths = backup_sqlite_db(options)
            if file_paths is not None:
                msg = "Current DB: %s\nCopied to: %s" % (tuple(file_paths))
                caption = "SQLite DB Backup Successful"
                flags = wx.OK | wx.OK_DEFAULT
            else:
                msg = "Your SQLite DB was not backed up for an unknown reason."
                caption = "SQLite DB Backup Unsuccessful"
        except Exception as e:
            msg = str(e)
            caption = "SQLite DB Backup Error"
    else:
        msg = (
            "This feature only applies to SQLite users. PostgreSQL users should contact their DB "
            "administrator or look into the pg_dump command."
        )
        caption = "SQLite DB Backup Error"

    ErrorDialog(parent, msg, caption, flags=flags)
