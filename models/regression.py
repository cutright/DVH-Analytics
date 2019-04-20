#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import wx
from models.plot import PlotRegression


class RegressionFrame:
    def __init__(self, parent, data, *args, **kwds):
        self.parent = parent
        # self.dvh = dvh
        self.data = data
        self.choices = []

        self.__define_gui_objects()
        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

    def __define_gui_objects(self):
        self.window = wx.SplitterWindow(self.parent, wx.ID_ANY)
        self.pane_tree = wx.ScrolledWindow(self.window, wx.ID_ANY, style=wx.TAB_TRAVERSAL)
        self.tree_ctrl = wx.TreeCtrl(self.pane_tree, wx.ID_ANY)
        self.pane_plot = wx.Panel(self.window, wx.ID_ANY)
        self.combo_box_x_axis = wx.ComboBox(self.pane_plot, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.TE_READONLY)
        self.spin_button_x_axis = wx.SpinButton(self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP)
        self.combo_box_y_axis = wx.ComboBox(self.pane_plot, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.TE_READONLY)
        self.spin_button_y_axis = wx.SpinButton(self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP)
        self.checkbox = wx.CheckBox(self.pane_plot, wx.ID_ANY, "Include in Regression")
        self.plot = PlotRegression(self.pane_plot)

    def __set_properties(self):
        self.pane_tree.SetScrollRate(10, 10)
        self.window.SetMinimumPaneSize(20)
        self.combo_box_x_axis.SetValue('ROI Max Dose')
        self.combo_box_y_axis.SetValue('ROI Volume')

    def __do_bind(self):
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box, id=self.combo_box_x_axis.GetId())
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box, id=self.combo_box_y_axis.GetId())
        self.parent.Bind(wx.EVT_SPIN, self.spin_x, id=self.spin_button_x_axis.GetId())
        self.parent.Bind(wx.EVT_SPIN, self.spin_y, id=self.spin_button_y_axis.GetId())

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plot_pane = wx.BoxSizer(wx.VERTICAL)
        sizer_plot_view = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.BoxSizer(wx.HORIZONTAL)

        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_y_axis_select = wx.BoxSizer(wx.HORIZONTAL)
        sizer_x_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_x_axis_select = wx.BoxSizer(wx.HORIZONTAL)

        sizer_tree = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tree.Add(self.tree_ctrl, 1, wx.EXPAND, 0)
        self.pane_tree.SetSizer(sizer_tree)

        label_x_axis = wx.StaticText(self.pane_plot, wx.ID_ANY, "Independent Variable (x-axis):")
        sizer_x_axis.Add(label_x_axis, 0, 0, 0)
        sizer_x_axis_select.Add(self.combo_box_x_axis, 1, wx.EXPAND, 0)
        sizer_x_axis_select.Add(self.spin_button_x_axis, 0, 0, 0)
        sizer_x_axis.Add(sizer_x_axis_select, 1, wx.EXPAND, 0)
        sizer_input.Add(sizer_x_axis, 1, wx.ALL, 5)

        label_y_axis = wx.StaticText(self.pane_plot, wx.ID_ANY, "Dependent Variable (y-axis):")
        sizer_y_axis.Add(label_y_axis, 0, 0, 0)
        sizer_y_axis_select.Add(self.combo_box_y_axis, 1, wx.EXPAND, 0)
        sizer_y_axis_select.Add(self.spin_button_y_axis, 0, 0, 0)
        sizer_y_axis.Add(sizer_y_axis_select, 1, wx.EXPAND, 0)
        sizer_input.Add(sizer_y_axis, 1, wx.ALL, 5)

        sizer_input.Add(self.checkbox, 0, wx.ALL, 20)
        sizer_plot_pane.Add(sizer_input, 0, wx.EXPAND, 0)
        sizer_plot.Add(self.plot.layout)
        sizer_plot_view.Add(sizer_plot, 1, wx.EXPAND, 10)
        sizer_plot_pane.Add(sizer_plot_view, 1, wx.EXPAND, 0)
        self.pane_plot.SetSizer(sizer_plot_pane)
        self.window.SplitVertically(self.pane_tree, self.pane_plot)
        sizer_wrapper.Add(self.window, 1, wx.EXPAND, 0)
        self.window.SetSashPosition(150)

        self.layout = sizer_wrapper

    def update_combo_box_choices(self):
        if self.data:
            self.choices = self.data.variables
            self.choices.sort()
            self.combo_box_x_axis.SetItems(self.choices)
            self.combo_box_y_axis.SetItems(self.choices)
            self.spin_button_x_axis.SetMax(len(self.choices)-1)
            self.spin_button_y_axis.SetMax(len(self.choices)-1)
            self.spin_button_x_axis.SetValue(0)
            self.spin_button_y_axis.SetValue(0)
            self.combo_box_x_axis.SetValue(self.choices[-1])
            self.combo_box_y_axis.SetValue(self.choices[-1])
            self.update_plot()

    def on_combo_box(self, evt):
        self.sync_spin_buttons()
        self.update_plot()

    def update_plot(self):
        x_axis, y_axis = self.combo_box_x_axis.GetValue(), self.combo_box_y_axis.GetValue()
        self.plot.update_plot(self.data.get_bokeh_data(x_axis, y_axis), x_axis, y_axis)

    def spin_x(self, evt):
        new_index = len(self.choices)-1 - int(self.spin_button_x_axis.GetValue())
        self.combo_box_x_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def spin_y(self, evt):
        new_index = len(self.choices)-1 - int(self.spin_button_y_axis.GetValue())
        self.combo_box_y_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def sync_spin_buttons(self):
        index = self.choices.index(self.combo_box_x_axis.GetValue())
        self.spin_button_x_axis.SetValue(len(self.choices)-1 - index)

        index = self.choices.index(self.combo_box_y_axis.GetValue())
        self.spin_button_y_axis.SetValue(len(self.choices)-1 - index)
